"""RTSP in → face detect/recognize → annotated RTSP out (MediaMTX)."""

import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

import cv2
import numpy as np

from src.engine.fr_onnx_engine import FrOnnxEngine
from src.services.face_embedding_store import FaceEmbeddingStore
from src.utils.face_draw import draw_face_results, draw_roi_polygons
from src.utils.roi_helpers import point_in_any_polygon
from src.utils.logger import get_logger

if TYPE_CHECKING:
    pass

log = get_logger()


@dataclass
class FaceStreamerConfig:
    camera_id: int
    camera_name: str
    rtsp_input_url: str
    publish_url: str
    output_size: tuple[int, int] = (1280, 720)
    fps: int = 10
    frame_interval: int = 2
    det_conf: float = 0.25
    det_nms: float = 0.45
    distance: float = 0.5
    min_det_score: float = 0.5
    show_unknown_distance: bool = False
    roi_enabled: bool = False
    roi_polygons: list[list[tuple[float, float]]] = field(default_factory=list)


class FaceAnnotatedStreamer:
    """Reads camera RTSP, runs FR ONNX, publishes annotated H264 to MediaMTX."""

    def __init__(
        self,
        config: FaceStreamerConfig,
        engine: FrOnnxEngine,
        face_store: FaceEmbeddingStore,
    ) -> None:
        self.config = config
        self.engine = engine
        self.face_store = face_store

        self.is_running = False
        self.capture: cv2.VideoCapture | None = None
        self.ffmpeg_process: subprocess.Popen | None = None
        self.frame_queue: Queue = Queue(maxsize=2)
        self.reader_thread: threading.Thread | None = None
        self.worker_thread: threading.Thread | None = None

        self._frame_idx = 0
        self._last_boxes: list[list[int]] = []
        self._last_scores: list[float] = []
        self._last_names: list[str | None] = []
        self._last_distances: list[float | None] = []
        self.metrics: dict = {
            "camera_id": config.camera_id,
            "camera_name": config.camera_name,
            "publish_url": config.publish_url,
            "faces_count": 0,
            "enrolled_faces": face_store.count,
            "infer_fps": 0.0,
            "encode_fps": 0.0,
            "errors": 0,
        }
        self._infer_count = 0
        self._encode_count = 0
        self._last_infer_ts = time.time()
        self._last_encode_ts = time.time()

    def _safe_url(self) -> str:
        url = self.config.rtsp_input_url
        if "@" in url and "://" in url:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                _, host_part = rest.rsplit("@", 1)
                return f"{protocol}://***@{host_part}"
        return url

    def _run_inference(self, frame_bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.engine.predict(
            [rgb],
            det_conf=self.config.det_conf,
            det_nms=self.config.det_nms,
        )[0]
        names, distances = self.face_store.match_batch(
            result.embeddings,
            result.scores,
            distance_threshold=self.config.distance,
            min_det_score=self.config.min_det_score,
        )
        self.metrics["enrolled_faces"] = self.face_store.count
        boxes, scores, names, distances = self._filter_by_roi(
            result.boxes, result.scores, names, distances, frame_bgr.shape[1], frame_bgr.shape[0]
        )
        self._last_boxes = boxes
        self._last_scores = scores
        self._last_names = names
        self._last_distances = distances
        self.metrics["faces_count"] = len(boxes)

    def _filter_by_roi(
        self,
        boxes: list[list[int]],
        scores: list[float],
        names: list[str | None],
        distances: list[float | None],
        width: int,
        height: int,
    ) -> tuple[list[list[int]], list[float], list[str | None], list[float | None]]:
        if not self.config.roi_enabled or not self.config.roi_polygons:
            return boxes, scores, names, distances
        if width <= 0 or height <= 0:
            return boxes, scores, names, distances

        fb: list[list[int]] = []
        fs: list[float] = []
        fn: list[str | None] = []
        fd: list[float | None] = []
        for box, score, name, dist in zip(boxes, scores, names, distances):
            cx = ((box[0] + box[2]) / 2.0) / width
            cy = ((box[1] + box[3]) / 2.0) / height
            if point_in_any_polygon((cx, cy), self.config.roi_polygons):
                fb.append(box)
                fs.append(score)
                fn.append(name)
                fd.append(dist)
        return fb, fs, fn, fd

    def update_roi_polygons(
        self, enabled: bool, polygons: list[list[tuple[float, float]]]
    ) -> None:
        self.config.roi_enabled = enabled and len(polygons) > 0
        self.config.roi_polygons = polygons if self.config.roi_enabled else []
        self._last_boxes = []
        self._last_scores = []
        self._last_names = []
        self._last_distances = []

    def _annotate(self, frame_bgr: np.ndarray) -> np.ndarray:
        out = frame_bgr
        if self.config.roi_enabled and self.config.roi_polygons:
            out = draw_roi_polygons(out, self.config.roi_polygons)
        return draw_face_results(
            out,
            self._last_boxes,
            self._last_scores,
            self._last_names,
            self._last_distances,
            show_unknown_distance=self.config.show_unknown_distance,
        )

    def _build_ffmpeg_cmd(self) -> list[str]:
        width, height = self.config.output_size
        ffmpeg = os.environ.get("FFMPEG_PATH", "ffmpeg")
        return [
            ffmpeg,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(self.config.fps),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-g",
            str(self.config.fps * 2),
            "-keyint_min",
            str(self.config.fps * 2),
            "-sc_threshold",
            "0",
            "-b:v",
            "2M",
            "-maxrate",
            "2M",
            "-bufsize",
            "1M",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "rtsp",
            "-rtsp_transport",
            "tcp",
            self.config.publish_url,
        ]

    def _mediamtx_ready(self, retries: int = 5) -> bool:
        parsed = urlparse(self.config.publish_url)
        host = parsed.hostname or "mediamtx"
        port = parsed.port or 8554
        for attempt in range(retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                ok = sock.connect_ex((host, port)) == 0
                sock.close()
                if ok:
                    return True
            except OSError:
                pass
            time.sleep(1.0)
        return False

    def _start_ffmpeg(self) -> None:
        if not self._mediamtx_ready():
            raise RuntimeError("MediaMTX is not reachable")
        cmd = self._build_ffmpeg_cmd()
        log.info(f"[cam {self.config.camera_id}] ffmpeg: {' '.join(cmd)}")
        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.3)
        if self.ffmpeg_process.poll() is not None:
            raise RuntimeError("ffmpeg exited immediately")

    def _stop_ffmpeg(self) -> None:
        if not self.ffmpeg_process:
            return
        try:
            if self.ffmpeg_process.stdin:
                self.ffmpeg_process.stdin.close()
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait(timeout=5)
        except Exception:
            try:
                self.ffmpeg_process.kill()
            except Exception:
                pass
        self.ffmpeg_process = None

    def _connect_rtsp(self) -> bool:
        self._disconnect_rtsp()
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|stimeout;5000000"
        )
        self.capture = cv2.VideoCapture(self.config.rtsp_input_url, cv2.CAP_FFMPEG)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            self.capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10_000)
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            self.capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10_000)
        if not self.capture.isOpened():
            return False
        ret, _ = self.capture.read()
        return bool(ret)

    def _disconnect_rtsp(self) -> None:
        if self.capture is not None:
            try:
                self.capture.release()
            except Exception:
                pass
            self.capture = None

    def _reader_loop(self) -> None:
        width, height = self.config.output_size
        interval = 1.0 / max(self.config.fps, 1)
        empty_reads = 0

        while self.is_running:
            if not self.capture or not self.capture.isOpened():
                if not self._connect_rtsp():
                    self.metrics["errors"] += 1
                    time.sleep(1.0)
                    continue

            latest = None
            for _ in range(3):
                ret, frame = self.capture.read()
                if ret and frame is not None and frame.size > 0:
                    latest = frame
                else:
                    break

            if latest is None:
                empty_reads += 1
                if empty_reads >= 15:
                    self._disconnect_rtsp()
                    empty_reads = 0
                time.sleep(0.05)
                continue
            empty_reads = 0

            resized = cv2.resize(latest, (width, height), interpolation=cv2.INTER_LINEAR)
            try:
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        pass
                self.frame_queue.put_nowait(resized)
            except Exception:
                pass
            time.sleep(interval * 0.5)

    def _worker_loop(self) -> None:
        width, height = self.config.output_size
        frame_bytes = width * height * 3
        interval = 1.0 / max(self.config.fps, 1)

        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=0.2)
            except Empty:
                continue

            self._frame_idx += 1
            run_infer = (
                self._frame_idx % max(self.config.frame_interval, 1) == 0
                or not self._last_boxes
            )
            if run_infer:
                try:
                    infer_start = time.time()
                    self._run_inference(frame)
                    elapsed = time.time() - infer_start
                    self._infer_count += 1
                    if elapsed > 0:
                        self.metrics["infer_fps"] = 0.7 * self.metrics["infer_fps"] + 0.3 * (
                            1.0 / elapsed
                        )
                except Exception as exc:
                    log.error(f"[cam {self.config.camera_id}] infer error: {exc}")
                    self.metrics["errors"] += 1

            annotated = self._annotate(frame)

            if self.ffmpeg_process and self.ffmpeg_process.stdin:
                try:
                    self.ffmpeg_process.stdin.write(annotated.tobytes())
                    self._encode_count += 1
                    now = time.time()
                    if now - self._last_encode_ts >= 1.0:
                        self.metrics["encode_fps"] = self._encode_count / (
                            now - self._last_encode_ts
                        )
                        self._encode_count = 0
                        self._last_encode_ts = now
                except Exception as exc:
                    log.error(f"[cam {self.config.camera_id}] ffmpeg write: {exc}")
                    self.metrics["errors"] += 1
                    self._stop_ffmpeg()
                    try:
                        self._start_ffmpeg()
                    except Exception:
                        self.is_running = False
                        break

            time.sleep(max(0.0, interval * 0.2))

    def start(self) -> bool:
        if self.is_running:
            return True
        log.info(
            f"[cam {self.config.camera_id}] starting annotated stream "
            f"{self._safe_url()} -> {self.config.publish_url}"
        )
        if not self._connect_rtsp():
            log.error(f"[cam {self.config.camera_id}] RTSP connect failed")
            return False
        try:
            self._start_ffmpeg()
        except Exception as exc:
            log.error(f"[cam {self.config.camera_id}] ffmpeg start failed: {exc}")
            self._disconnect_rtsp()
            return False

        self.is_running = True
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.reader_thread.start()
        self.worker_thread.start()
        return True

    def stop(self) -> None:
        self.is_running = False
        for thread in (self.reader_thread, self.worker_thread):
            if thread and thread.is_alive():
                thread.join(timeout=3.0)
        self.reader_thread = None
        self.worker_thread = None
        self._stop_ffmpeg()
        self._disconnect_rtsp()
        log.info(f"[cam {self.config.camera_id}] annotated stream stopped")

    def get_metrics(self) -> dict:
        return dict(self.metrics)
