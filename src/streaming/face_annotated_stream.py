"""RTSP in → face detect/recognize → annotated RTSP out (MediaMTX)."""

import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import TYPE_CHECKING, Literal, Optional
from urllib.parse import urlparse

import cv2
import numpy as np

from src.engine.fr_onnx_engine import FrOnnxEngine
from src.engine.person_engine_factory import PersonDetector
from src.services.face_embedding_store import FaceEmbeddingStore
from src.utils.face_draw import (
    count_workers,
    draw_detections,
    draw_people_zone_badge,
    draw_roi_polygons,
    draw_rod_pose_overlay,
    draw_sealer_cycle_badge,
    draw_sealer_roi_rect,
    draw_worker_count_badge,
)
from src.utils.sealer_handle_detector import (
    DEFAULT_MIN_HYSTERESIS,
    DEFAULT_REST_THRESHOLD,
    DEFAULT_SPIKE_THRESHOLD,
    FixedRoiDetector,
    SealerMotionDetector,
    norm_rect_to_pixels,
    probe_thresholds_from_scores,
)
from src.utils.person_tracker import PersonTracker
from src.utils.rod_metrics import RodTracker
from src.utils.roi_helpers import (
    assign_detection_to_roi,
    box_intersects_polygon,
    count_roi_workers,
    point_in_any_polygon,
    point_in_polygon,
)
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.engine.rod_pose_engine import RodPoseEngine, RodPoseDetection
    from src.services.package_counter_store import PackageCounterStore
    from src.services.people_counter_store import PeopleCounterStore
    from src.services.rod_counter_store import RodCounterStore
    from src.services.roi_people_counter_store import RoiPeopleCounterStore
    from src.services.roi_timer_store import RoiTimerStore

log = get_logger()

MAX_STREAM_WIDTH = 2560
MAX_STREAM_HEIGHT = 1440
WORKER_CATEGORIES = frozenset({"face", "person", "head"})
PACKAGE_CATEGORIES = frozenset({"package", "label"})


@dataclass
class FaceStreamerConfig:
    camera_id: int
    camera_name: str
    rtsp_input_url: str
    rtsp_fallback_url: str = ""
    publish_url: str = ""
    output_size: tuple[int, int] = (1280, 720)
    detection_mode: Literal["face", "person", "face_person"] = "face"
    fps: int = 10
    frame_interval: int = 2
    det_conf: float = 0.25
    det_nms: float = 0.45
    distance: float = 0.5
    min_det_score: float = 0.5
    show_unknown_distance: bool = False
    roi_enabled: bool = False
    roi_polygons: list[list[tuple[float, float]]] = field(default_factory=list)
    roi_keys: list[str] = field(default_factory=list)
    max_quality: bool = False
    people_zone_enabled: bool = False
    people_zone_polygon: list[tuple[float, float]] = field(default_factory=list)
    people_zone_max_workers: int = 3
    package_detection_enabled: bool = False
    package_det_conf: float = 0.25
    package_det_imgsz: int = 960
    package_count_dwell_sec: float = 1.0
    rod_pose_enabled: bool = False
    rod_pose_conf: float = 0.25
    rod_pose_imgsz: int = 640
    sealer_roi_enabled: bool = False
    sealer_roi_x: float = 0.0
    sealer_roi_y: float = 0.0
    sealer_roi_w: float = 0.0
    sealer_roi_h: float = 0.0
    sealer_roi_spike_thresh: float = DEFAULT_SPIKE_THRESHOLD
    sealer_roi_rest_thresh: float = DEFAULT_REST_THRESHOLD
    sealer_roi_cooldown_frames: int = 8
    sealer_cycle_dwell_sec: float = 1.0
    person_tracker: Literal["off", "bytetrack", "botsort", "sort"] = "bytetrack"
    person_track_buffer: int = 45


class FaceAnnotatedStreamer:
    """Reads camera RTSP, runs FR ONNX, publishes annotated H264 to MediaMTX."""

    def __init__(
        self,
        config: FaceStreamerConfig,
        engine: FrOnnxEngine,
        face_store: FaceEmbeddingStore,
        person_engine: PersonDetector | None = None,
        package_engine: PersonDetector | None = None,
        rod_pose_engine: "RodPoseEngine | None" = None,
        roi_timer_store: "RoiTimerStore | None" = None,
        people_counter_store: "PeopleCounterStore | None" = None,
        roi_people_counter_store: "RoiPeopleCounterStore | None" = None,
        package_counter_store: "PackageCounterStore | None" = None,
        sealer_counter_store: "SealerCounterStore | None" = None,
        rod_counter_store: "RodCounterStore | None" = None,
        roi_switch_seconds: float = 60.0,
        roi_reset_grace_seconds: float = 7.0,
    ) -> None:
        self.config = config
        self.engine = engine
        self.face_store = face_store
        self.person_engine = person_engine
        self.package_engine = package_engine
        self.rod_pose_engine = rod_pose_engine
        self.roi_timer_store = roi_timer_store
        self.people_counter_store = people_counter_store
        self.roi_people_counter_store = roi_people_counter_store
        self.package_counter_store = package_counter_store
        self.sealer_counter_store = sealer_counter_store
        self.rod_counter_store = rod_counter_store
        self.roi_switch_seconds = roi_switch_seconds
        self.roi_reset_grace_seconds = roi_reset_grace_seconds

        self.is_running = False
        self.capture: cv2.VideoCapture | None = None
        self.ffmpeg_process: subprocess.Popen | None = None
        self.frame_queue: Queue = Queue(maxsize=2)
        self.reader_thread: threading.Thread | None = None
        self.worker_thread: threading.Thread | None = None

        self._frame_idx = 0
        self._last_boxes: list[list[int]] = []
        self._last_scores: list[float] = []
        self._last_categories: list[str] = []
        self._last_names: list[str | None] = []
        self._last_distances: list[float | None] = []
        self._roi_labels: list[str] = []
        self.metrics: dict = {
            "camera_id": config.camera_id,
            "camera_name": config.camera_name,
            "publish_url": config.publish_url,
            "faces_count": 0,
            "workers_count": 0,
            "packages_count": 0,
            "labels_count": 0,
            "packed_today": 0,
            "package_detection_enabled": config.package_detection_enabled,
            "sealer_cycle_count": 0,
            "sealer_activity": 0.0,
            "sealer_state": "OPEN",
            "rod_press_count": 0,
            "rod_angle": 0.0,
            "rod_ref_dA": 0.0,
            "rod_armed": True,
            "enrolled_faces": face_store.count,
            "infer_fps": 0.0,
            "encode_fps": 0.0,
            "errors": 0,
        }
        self._infer_count = 0
        self._encode_count = 0
        self._last_infer_ts = time.time()
        self._last_encode_ts = time.time()
        self._source_size: tuple[int, int] | None = None
        self._people_tracks: dict[int, tuple[float, float, float]] = {}
        self._next_people_track_id = 1
        self._sealer_detector: FixedRoiDetector | None = None
        self._sealer_motion: SealerMotionDetector | None = None
        self._sealer_frame_idx = 0
        self._sealer_probe_scores: list[float] = []
        self._sealer_probe_activities: list[float] = []
        self._sealer_probe_done = False
        self._sealer_initial_spike = DEFAULT_SPIKE_THRESHOLD
        self._sealer_initial_rest = DEFAULT_REST_THRESHOLD
        self._rod_tracker = RodTracker()
        self._last_rod_pose: RodPoseDetection | None = None
        self._rod_ref_dA = 0.0
        self._person_tracker = PersonTracker(
            tracker_type=config.person_tracker,
            track_buffer=config.person_track_buffer,
        )
        self._sync_sealer_cycle_count_from_store()
        self._sync_rod_press_count_from_store()

    def set_person_tracker(
        self,
        tracker_type: str,
        track_buffer: int | None = None,
    ) -> None:
        self.config.person_tracker = tracker_type  # type: ignore[assignment]
        if track_buffer is not None:
            self.config.person_track_buffer = int(track_buffer)
        self._person_tracker.set_type(
            tracker_type, track_buffer=self.config.person_track_buffer
        )

    def _sync_sealer_cycle_count_from_store(self) -> int:
        """Подтянуть циклы за сегодняшнюю смену из БД (не обнулять при старте)."""
        if self.sealer_counter_store is None:
            return int(self.metrics.get("sealer_cycle_count", 0))
        try:
            cycles = int(
                self.sealer_counter_store.get_cycles_today(self.config.camera_id)
            )
        except Exception:
            cycles = int(self.metrics.get("sealer_cycle_count", 0))
        self.metrics["sealer_cycle_count"] = cycles
        return cycles

    def _sync_rod_press_count_from_store(self) -> int:
        """События палки = циклы запайщика (одна таблица sealer_*)."""
        cycles = self._sync_sealer_cycle_count_from_store()
        self.metrics["rod_press_count"] = cycles
        self._rod_tracker.change_count = cycles
        return cycles

    def _safe_url(self, url: str | None = None) -> str:
        url = url or self.config.rtsp_input_url
        if "@" in url and "://" in url:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                _, host_part = rest.rsplit("@", 1)
                return f"{protocol}://***@{host_part}"
        return url

    def _run_face_inference(
        self, rgb: np.ndarray
    ) -> tuple[list[list[int]], list[float], list[str], list[str | None], list[float | None]]:
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
        return (
            result.boxes,
            result.scores,
            result.categories or ["face"] * len(result.boxes),
            names,
            distances,
        )

    def _run_person_inference(
        self, rgb: np.ndarray
    ) -> tuple[list[list[int]], list[float], list[str], list[str | None], list[float | None]]:
        if self.person_engine is None:
            return [], [], [], [], []
        result = self.person_engine.predict(
            [rgb],
            conf=self.config.det_conf,
            nms=self.config.det_nms,
        )[0]
        return (
            result.boxes,
            result.scores,
            result.categories or ["person"] * len(result.boxes),
            [None] * len(result.boxes),
            [None] * len(result.boxes),
        )

    def _run_package_inference(
        self, rgb: np.ndarray
    ) -> tuple[list[list[int]], list[float], list[str], list[str | None], list[float | None]]:
        if not self.config.package_detection_enabled or self.package_engine is None:
            return [], [], [], [], []
        result = self.package_engine.predict(
            [rgb],
            conf=self.config.package_det_conf,
            nms=self.config.det_nms,
            imgsz=self.config.package_det_imgsz,
        )[0]
        return (
            result.boxes,
            result.scores,
            result.categories or [],
            [None] * len(result.boxes),
            [None] * len(result.boxes),
        )

    def _run_inference(self, frame_bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mode = self.config.detection_mode
        boxes: list[list[int]] = []
        scores: list[float] = []
        categories: list[str] = []
        names: list[str | None] = []
        distances: list[float | None] = []

        if mode in ("face", "face_person"):
            fb, fs, fc, fn, fd = self._run_face_inference(rgb)
            boxes.extend(fb)
            scores.extend(fs)
            categories.extend(fc)
            names.extend(fn)
            distances.extend(fd)

        if mode in ("person", "face_person"):
            pb, ps, pc, pn, pd = self._run_person_inference(rgb)
            tracked = self._person_tracker.update(pb, ps, pc, frame_bgr)
            if tracked is not None:
                # Трекер только по телу; головы оставляем как сырые детекции
                head_boxes: list[list[int]] = []
                head_scores: list[float] = []
                head_cats: list[str] = []
                head_names: list[str | None] = []
                head_dists: list[float | None] = []
                for box, score, cat, name, dist in zip(pb, ps, pc, pn, pd):
                    if (cat or "").lower() == "head":
                        head_boxes.append(box)
                        head_scores.append(score)
                        head_cats.append(cat)
                        head_names.append(name)
                        head_dists.append(dist)
                pb = [t.box for t in tracked] + head_boxes
                ps = [t.score for t in tracked] + head_scores
                pc = [t.category for t in tracked] + head_cats
                pn = [
                    f"t:{t.track_id}{'~' if t.predicted else ''}" for t in tracked
                ] + head_names
                pd = [None] * len(tracked) + head_dists
            boxes.extend(pb)
            scores.extend(ps)
            categories.extend(pc)
            names.extend(pn)
            distances.extend(pd)

        if self.config.package_detection_enabled:
            pkg_b, pkg_s, pkg_c, pkg_n, pkg_d = self._run_package_inference(rgb)
            boxes.extend(pkg_b)
            scores.extend(pkg_s)
            categories.extend(pkg_c)
            names.extend(pkg_n)
            distances.extend(pkg_d)

        self.metrics["enrolled_faces"] = self.face_store.count
        self._update_roi_timers(
            boxes=boxes,
            scores=scores,
            categories=categories,
            width=frame_bgr.shape[1],
            height=frame_bgr.shape[0],
        )
        self._update_people_counter(
            boxes=boxes,
            categories=categories,
            width=frame_bgr.shape[1],
            height=frame_bgr.shape[0],
        )
        self._update_package_counter(
            boxes=boxes,
            categories=categories,
            width=frame_bgr.shape[1],
            height=frame_bgr.shape[0],
        )
        self._update_sealer_cycle(frame_bgr)
        self._update_rod_pose(frame_bgr)
        boxes, scores, categories, names, distances = self._filter_by_roi(
            boxes,
            scores,
            categories,
            names,
            distances,
            frame_bgr.shape[1],
            frame_bgr.shape[0],
        )
        self._last_boxes = boxes
        self._last_scores = scores
        self._last_categories = categories
        self._last_names = names
        self._last_distances = distances
        self.metrics["workers_count"] = count_workers(boxes, categories)
        self.metrics["faces_count"] = self.metrics["workers_count"]
        self.metrics["packages_count"] = sum(
            1 for c in categories if (c or "").lower() == "package"
        )
        self.metrics["labels_count"] = sum(
            1 for c in categories if (c or "").lower() == "label"
        )
        self.metrics["package_detection_enabled"] = self.config.package_detection_enabled
        if self.package_counter_store is not None:
            self.metrics["packed_today"] = self.package_counter_store.get_total_today(
                self.config.camera_id
            )

    def _packages_per_roi(
        self,
        boxes: list[list[int]],
        categories: list[str],
        width: int,
        height: int,
    ) -> list[int]:
        """Число детекций package внутри каждого ROI (пересечение bbox)."""
        n = len(self.config.roi_polygons)
        counts = [0] * n
        if width <= 0 or height <= 0 or n == 0:
            return counts
        for box, category in zip(boxes, categories):
            if (category or "").lower() != "package":
                continue
            matching = [
                idx
                for idx, poly in enumerate(self.config.roi_polygons)
                if box_intersects_polygon(box, poly, width, height)
            ]
            if not matching:
                continue
            if len(matching) == 1:
                counts[matching[0]] += 1
                continue
            cx = ((box[0] + box[2]) / 2.0) / width
            cy = ((box[1] + box[3]) / 2.0) / height
            sub_polys = [self.config.roi_polygons[i] for i in matching]
            rel = assign_detection_to_roi((cx, cy), sub_polys)
            counts[matching[rel if rel is not None else 0]] += 1
        return counts

    def _update_package_counter(
        self,
        boxes: list[list[int]],
        categories: list[str],
        width: int,
        height: int,
    ) -> None:
        if (
            self.package_counter_store is None
            or not self.config.package_detection_enabled
            or not self.config.roi_enabled
            or not self.config.roi_polygons
            or width <= 0
            or height <= 0
        ):
            return

        if len(self.config.roi_keys) != len(self.config.roi_polygons):
            if self.roi_timer_store is None:
                return
            from src.utils.roi_helpers import RoiPolygonData, default_roi_name

            self.config.roi_keys = self.roi_timer_store.sync_camera_rois(
                self.config.camera_id,
                [
                    RoiPolygonData(
                        points=poly,
                        name=default_roi_name(idx),
                    )
                    for idx, poly in enumerate(self.config.roi_polygons, start=1)
                ],
            )
        if not self.config.roi_keys:
            return

        self.package_counter_store.sync_camera_rois(
            self.config.camera_id, self.config.roi_keys
        )
        package_counts = self._packages_per_roi(boxes, categories, width, height)
        dwell = max(0.1, float(self.config.package_count_dwell_sec))
        for roi_key, count in zip(self.config.roi_keys, package_counts):
            self.package_counter_store.tick(
                camera_id=self.config.camera_id,
                roi_key=roi_key,
                packages_in_zone=count,
                dwell_seconds=dwell,
            )
        self.metrics["packed_today"] = self.package_counter_store.get_total_today(
            self.config.camera_id
        )

    def _normalize_sealer_thresholds(
        self, spike: float, rest: float
    ) -> tuple[float, float]:
        spike = max(float(spike), DEFAULT_SPIKE_THRESHOLD)
        rest = float(rest)
        if rest > DEFAULT_REST_THRESHOLD:
            rest = DEFAULT_REST_THRESHOLD
        if spike - rest < DEFAULT_MIN_HYSTERESIS:
            rest = spike - DEFAULT_MIN_HYSTERESIS
        return spike, rest

    def _reset_sealer_runtime(self, reset_count: bool = True) -> None:
        self._sealer_detector = None
        self._sealer_motion = None
        self._sealer_frame_idx = 0
        self._sealer_probe_scores = []
        self._sealer_probe_activities = []
        self._sealer_probe_done = False
        if reset_count:
            self.metrics["sealer_activity"] = 0.0
            self.metrics["sealer_state"] = "OPEN"
        # Всегда берём счётчик за смену из БД — не обнуляем при старте/смене ROI
        self._sync_sealer_cycle_count_from_store()

    def _update_sealer_cycle(self, frame_bgr: np.ndarray) -> None:
        if not self.config.sealer_roi_enabled:
            return
        if self.config.sealer_roi_w <= 0 or self.config.sealer_roi_h <= 0:
            return

        width = frame_bgr.shape[1]
        height = frame_bgr.shape[0]
        if width <= 0 or height <= 0:
            return

        roi_px = norm_rect_to_pixels(
            self.config.sealer_roi_x,
            self.config.sealer_roi_y,
            self.config.sealer_roi_w,
            self.config.sealer_roi_h,
            width,
            height,
        )
        try:
            spike, rest = self._normalize_sealer_thresholds(
                self.config.sealer_roi_spike_thresh,
                self.config.sealer_roi_rest_thresh,
            )
            self.config.sealer_roi_spike_thresh = spike
            self.config.sealer_roi_rest_thresh = rest

            if self._sealer_detector is None:
                self._sealer_initial_spike = spike
                self._sealer_initial_rest = rest
                self._sealer_detector = FixedRoiDetector(roi_px)
                self._sealer_detector.set_reference(frame_bgr)
                self._sealer_motion = SealerMotionDetector(
                    spike_threshold=spike,
                    rest_threshold=rest,
                    cooldown_frames=self.config.sealer_roi_cooldown_frames,
                    min_active_sec=self.config.sealer_cycle_dwell_sec,
                )
            elif self._sealer_detector.roi != roi_px:
                self._reset_sealer_runtime(reset_count=False)
                self._sealer_initial_spike = spike
                self._sealer_initial_rest = rest
                self._sealer_detector = FixedRoiDetector(roi_px)
                self._sealer_detector.set_reference(frame_bgr)
                self._sealer_motion = SealerMotionDetector(
                    spike_threshold=spike,
                    rest_threshold=rest,
                    cooldown_frames=self.config.sealer_roi_cooldown_frames,
                    min_active_sec=self.config.sealer_cycle_dwell_sec,
                )

            score = self._sealer_detector.measure(frame_bgr)
            fired = self._sealer_motion.update(score, self._sealer_frame_idx)
            activity = self._sealer_motion.activity
            self._sealer_frame_idx += 1

            if not self._sealer_probe_done and self._sealer_frame_idx <= 300:
                self._sealer_probe_scores.append(score)
                self._sealer_probe_activities.append(activity)
                if self._sealer_frame_idx == 300 and self._sealer_motion is not None:
                    probed_spike, probed_rest = probe_thresholds_from_scores(
                        self._sealer_probe_scores,
                        self._sealer_probe_activities,
                    )
                    spike, rest = self._normalize_sealer_thresholds(
                        max(probed_spike, self._sealer_initial_spike),
                        min(probed_rest, self._sealer_initial_rest),
                    )
                    self.config.sealer_roi_spike_thresh = spike
                    self.config.sealer_roi_rest_thresh = rest
                    self._sealer_motion.set_thresholds(spike, rest)
                    self._sealer_probe_done = True

            self._sealer_detector.adapt_reference_if_resting(
                frame_bgr,
                activity,
                self.config.sealer_roi_rest_thresh,
            )
            self.metrics["sealer_activity"] = activity
            self.metrics["sealer_state"] = self._sealer_motion.state
            if fired:
                cycles_today = 0
                if self.sealer_counter_store is not None:
                    cycles_today = self.sealer_counter_store.record_cycle(
                        self.config.camera_id,
                        activity=activity,
                    )
                else:
                    cycles_today = int(self.metrics.get("sealer_cycle_count", 0)) + 1
                self.metrics["sealer_cycle_count"] = cycles_today
        except Exception as exc:
            log.warning(f"Sealer cycle detector error cam={self.config.camera_id}: {exc}")

    def _update_rod_pose(self, frame_bgr: np.ndarray) -> None:
        if not self.config.rod_pose_enabled or self.rod_pose_engine is None:
            self._last_rod_pose = None
            return
        try:
            det = self.rod_pose_engine.predict(
                frame_bgr,
                conf=self.config.rod_pose_conf,
                imgsz=self.config.rod_pose_imgsz,
            )
            if det is None:
                return
            upd = self._rod_tracker.update(det.angle_deg)
            self._last_rod_pose = det
            self._rod_ref_dA = upd.ref_dA
            self.metrics["rod_angle"] = float(upd.ema_angle or det.angle_deg)
            self.metrics["rod_ref_dA"] = upd.ref_dA
            self.metrics["rod_armed"] = upd.armed
            # activity для веб-статистики ROI ручки / запайщика
            self.metrics["sealer_activity"] = float(upd.ref_dA)
            self.metrics["sealer_state"] = "OPEN" if upd.armed else "CLOSED"
            if upd.event_fired:
                cycles_today = 0
                if self.sealer_counter_store is not None:
                    cycles_today = self.sealer_counter_store.record_cycle(
                        self.config.camera_id,
                        activity=float(upd.ref_dA),
                    )
                else:
                    cycles_today = int(self.metrics.get("sealer_cycle_count", 0)) + 1
                self.metrics["sealer_cycle_count"] = cycles_today
                self.metrics["rod_press_count"] = cycles_today
                self._rod_tracker.change_count = cycles_today
            else:
                cycles = int(self.metrics.get("sealer_cycle_count", upd.change_count))
                self.metrics["rod_press_count"] = cycles
        except Exception as exc:
            log.warning(f"Rod pose error cam={self.config.camera_id}: {exc}")

    def update_rod_pose(self, enabled: bool) -> None:
        self.config.rod_pose_enabled = enabled
        if not enabled:
            self._last_rod_pose = None
            self._rod_tracker.reset()
            self._sync_rod_press_count_from_store()

    def _people_zone_track_centers(
        self,
        boxes: list[list[int]],
        categories: list[str],
        width: int,
        height: int,
    ) -> list[tuple[float, float]]:
        if width <= 0 or height <= 0:
            return []
        polygon = self.config.people_zone_polygon
        if len(polygon) < 3:
            return []
        cats = [(c or "").lower() for c in categories]
        if any(c == "person" for c in cats):
            targets = {"person"}
        elif any(c == "head" for c in cats):
            targets = {"head"}
        else:
            targets = {"face"}
        centers: list[tuple[float, float]] = []
        for box, cat in zip(boxes, cats):
            if cat not in targets:
                continue
            cx = ((box[0] + box[2]) / 2.0) / width
            cy = ((box[1] + box[3]) / 2.0) / height
            point = (cx, cy)
            if point_in_polygon(point, polygon):
                centers.append(point)
        return centers

    def _worker_centers(
        self,
        boxes: list[list[int]],
        categories: list[str],
        width: int,
        height: int,
    ) -> list[tuple[float, float]]:
        return self._people_zone_track_centers(boxes, categories, width, height)

    def _update_people_counter(
        self,
        boxes: list[list[int]],
        categories: list[str],
        width: int,
        height: int,
    ) -> None:
        if (
            self.people_counter_store is None
            or not self.config.people_zone_enabled
            or len(self.config.people_zone_polygon) < 3
        ):
            self._people_tracks = {}
            return

        centers = self._people_zone_track_centers(boxes, categories, width, height)
        max_workers = min(3, max(1, int(self.config.people_zone_max_workers or 3)))
        inside_count = min(max_workers, len(centers))

        state = self.people_counter_store.tick(
            camera_id=self.config.camera_id,
            target_workers=inside_count,
            max_workers=max_workers,
        )
        self._people_tracks = {}
        self.metrics["people_zone_workers"] = state.current_workers
        self.metrics["people_zone_person_seconds"] = state.person_seconds

    def _filter_by_roi(
        self,
        boxes: list[list[int]],
        scores: list[float],
        categories: list[str],
        names: list[str | None],
        distances: list[float | None],
        width: int,
        height: int,
    ) -> tuple[list[list[int]], list[float], list[str], list[str | None], list[float | None]]:
        if not self.config.roi_enabled or not self.config.roi_polygons:
            return boxes, scores, categories, names, distances
        if width <= 0 or height <= 0:
            return boxes, scores, categories, names, distances

        fb: list[list[int]] = []
        fs: list[float] = []
        fc: list[str] = []
        fn: list[str | None] = []
        fd: list[float | None] = []
        pkg_boxes: list[list[int]] = []
        pkg_scores: list[float] = []
        pkg_categories: list[str] = []
        pkg_names: list[str | None] = []
        pkg_distances: list[float | None] = []
        for box, score, category, name, dist in zip(boxes, scores, categories, names, distances):
            cat = (category or "").lower()
            if cat in PACKAGE_CATEGORIES:
                pkg_boxes.append(box)
                pkg_scores.append(score)
                pkg_categories.append(category)
                pkg_names.append(name)
                pkg_distances.append(dist)
                continue
            cx = ((box[0] + box[2]) / 2.0) / width
            cy = ((box[1] + box[3]) / 2.0) / height
            if point_in_any_polygon((cx, cy), self.config.roi_polygons):
                fb.append(box)
                fs.append(score)
                fc.append(category)
                fn.append(name)
                fd.append(dist)
        return fb + pkg_boxes, fs + pkg_scores, fc + pkg_categories, fn + pkg_names, fd + pkg_distances

    def _workers_per_roi(
        self,
        boxes: list[list[int]],
        categories: list[str],
        width: int,
        height: int,
    ) -> list[int]:
        """Число людей в каждом ROI (макс. 2): тело + голова без дубля."""
        n = len(self.config.roi_polygons)
        if width <= 0 or height <= 0 or n == 0:
            return [0] * n

        persons: list[list[list[int]]] = [[] for _ in range(n)]
        heads: list[list[list[int]]] = [[] for _ in range(n)]
        for box, category in zip(boxes, categories):
            cat = (category or "").lower()
            if cat not in ("person", "head"):
                continue
            cx = ((box[0] + box[2]) / 2.0) / width
            cy = ((box[1] + box[3]) / 2.0) / height
            idx = assign_detection_to_roi((cx, cy), self.config.roi_polygons)
            if idx is None:
                continue
            if cat == "person":
                persons[idx].append(box)
            else:
                heads[idx].append(box)

        return [
            count_roi_workers(persons[i], heads[i], max_workers=2) for i in range(n)
        ]

    def _update_roi_timers(
        self,
        boxes: list[list[int]],
        scores: list[float],
        categories: list[str],
        width: int,
        height: int,
    ) -> None:
        if (
            self.roi_timer_store is None
            or not self.config.roi_enabled
            or not self.config.roi_polygons
            or width <= 0
            or height <= 0
        ):
            self._roi_labels = []
            return

        if len(self.config.roi_keys) != len(self.config.roi_polygons):
            from src.utils.roi_helpers import RoiPolygonData, default_roi_name

            self.config.roi_keys = self.roi_timer_store.sync_camera_rois(
                self.config.camera_id,
                [
                    RoiPolygonData(
                        points=poly,
                        name=default_roi_name(idx),
                    )
                    for idx, poly in enumerate(self.config.roi_polygons, start=1)
                ],
            )
        if not self.config.roi_keys:
            self._roi_labels = []
            return

        worker_counts = self._workers_per_roi(boxes, categories, width, height)
        presence = [c > 0 for c in worker_counts]

        if self.roi_people_counter_store is not None:
            self.roi_people_counter_store.sync_camera_rois(
                self.config.camera_id, self.config.roi_keys
            )
            for roi_key, count in zip(self.config.roi_keys, worker_counts):
                self.roi_people_counter_store.tick(
                    camera_id=self.config.camera_id,
                    roi_key=roi_key,
                    target_workers=count,
                )

        self.roi_timer_store.tick(
            camera_id=self.config.camera_id,
            roi_keys=self.config.roi_keys,
            presence_flags=presence,
            switch_seconds=self.roi_switch_seconds,
            reset_grace_seconds=self.roi_reset_grace_seconds,
        )
        self._roi_labels = self.roi_timer_store.get_overlay_labels(
            camera_id=self.config.camera_id,
            roi_keys=self.config.roi_keys,
            switch_seconds=self.roi_switch_seconds,
            presence_flags=presence,
            reset_grace_seconds=self.roi_reset_grace_seconds,
        )

    def update_roi_polygons(
        self,
        enabled: bool,
        polygons: list[list[tuple[float, float]]],
        roi_keys: list[str] | None = None,
    ) -> None:
        self.config.roi_enabled = enabled and len(polygons) > 0
        self.config.roi_polygons = polygons if self.config.roi_enabled else []
        self.config.roi_keys = list(roi_keys or []) if self.config.roi_enabled else []
        self._last_boxes = []
        self._last_scores = []
        self._last_categories = []
        self._last_names = []
        self._last_distances = []
        self._roi_labels = []

    def update_people_zone(
        self,
        enabled: bool,
        polygon: list[tuple[float, float]],
        max_workers: int = 3,
    ) -> None:
        self.config.people_zone_enabled = enabled and len(polygon) >= 3
        self.config.people_zone_polygon = list(polygon) if len(polygon) >= 3 else []
        self.config.people_zone_max_workers = min(3, max(1, int(max_workers or 3)))
        self._people_tracks = {}

    def update_package_detection(self, enabled: bool) -> None:
        self.config.package_detection_enabled = enabled
        self.metrics["package_detection_enabled"] = enabled

    def update_sealer_roi(
        self,
        enabled: bool,
        x: float,
        y: float,
        w: float,
        h: float,
        spike_thresh: float = DEFAULT_SPIKE_THRESHOLD,
        rest_thresh: float = DEFAULT_REST_THRESHOLD,
        cooldown_frames: int = 8,
    ) -> None:
        active = enabled and w > 0 and h > 0
        spike, rest = self._normalize_sealer_thresholds(spike_thresh, rest_thresh)
        self.config.sealer_roi_enabled = active
        self.config.sealer_roi_x = x
        self.config.sealer_roi_y = y
        self.config.sealer_roi_w = w
        self.config.sealer_roi_h = h
        self.config.sealer_roi_spike_thresh = spike
        self.config.sealer_roi_rest_thresh = rest
        self.config.sealer_roi_cooldown_frames = cooldown_frames
        self._reset_sealer_runtime()

    def _annotate(self, frame_bgr: np.ndarray) -> np.ndarray:
        out = frame_bgr
        if self.config.people_zone_enabled and self.config.people_zone_polygon:
            out = draw_roi_polygons(
                out,
                [self.config.people_zone_polygon],
                color=(255, 0, 255),
            )
        if self.config.roi_enabled and self.config.roi_polygons:
            out = draw_roi_polygons(out, self.config.roi_polygons, labels=self._roi_labels)
        annotated = draw_detections(
            out,
            self._last_boxes,
            self._last_scores,
            self._last_categories,
            self._last_names,
            self._last_distances,
            show_unknown_distance=self.config.show_unknown_distance,
        )
        if self.config.people_zone_enabled:
            annotated = draw_people_zone_badge(
                annotated,
                int(self.metrics.get("people_zone_workers", 0)),
                float(self.metrics.get("people_zone_person_seconds", 0.0)),
                self.config.people_zone_max_workers,
            )
        if self.config.sealer_roi_enabled and self.config.sealer_roi_w > 0:
            annotated = draw_sealer_roi_rect(
                annotated,
                self.config.sealer_roi_x,
                self.config.sealer_roi_y,
                self.config.sealer_roi_w,
                self.config.sealer_roi_h,
                int(self.metrics.get("sealer_cycle_count", 0)),
                str(self.metrics.get("sealer_state", "OPEN")),
            )
        # Бейдж «Запайщик за смену» — и для ROI ручки, и для pose-палки (один счётчик)
        if (
            (self.config.sealer_roi_enabled and self.config.sealer_roi_w > 0)
            or self.config.rod_pose_enabled
        ):
            annotated = draw_sealer_cycle_badge(
                annotated,
                int(self.metrics.get("sealer_cycle_count", 0)),
                float(self.metrics.get("sealer_activity", 0.0)),
            )
        if self._last_rod_pose is not None:
            annotated = draw_rod_pose_overlay(
                annotated,
                self._last_rod_pose.top,
                self._last_rod_pose.bottom,
                ema_angle=float(self.metrics.get("rod_angle", 0.0)),
                ref_dA=float(self._rod_ref_dA),
                press_count=int(self.metrics.get("sealer_cycle_count", 0)),
                armed=bool(self.metrics.get("rod_armed", True)),
            )
        return draw_worker_count_badge(
            annotated,
            int(self.metrics.get("workers_count", 0)),
        )

    def _video_bitrate(self) -> tuple[str, str, str]:
        width, height = self.config.output_size
        pixels = width * height
        if self.config.max_quality or pixels > 1280 * 720:
            mb = min(12, max(4, int(pixels / (1280 * 720) * 2)))
            rate = f"{mb}M"
            return rate, rate, f"{mb * 2}M"
        return "2M", "2M", "1M"

    @staticmethod
    def fit_output_size(
        src_w: int,
        src_h: int,
        max_w: int = MAX_STREAM_WIDTH,
        max_h: int = MAX_STREAM_HEIGHT,
    ) -> tuple[int, int]:
        if src_w <= 0 or src_h <= 0:
            return max_w, max_h
        scale = min(max_w / src_w, max_h / src_h, 1.0)
        w = max(320, int(src_w * scale) // 2 * 2)
        h = max(240, int(src_h * scale) // 2 * 2)
        return w, h

    def probe_source_size(self) -> tuple[int, int]:
        if self._source_size and self._source_size[0] > 0 and self._source_size[1] > 0:
            return self._source_size
        if self.capture and self.capture.isOpened():
            for _ in range(5):
                ret, frame = self.capture.read()
                if ret and frame is not None and frame.size > 0:
                    h, w = frame.shape[:2]
                    if w > 0 and h > 0:
                        self._source_size = (w, h)
                        return w, h
        return self.config.output_size

    def resolve_max_output_size(
        self,
        max_w: int = MAX_STREAM_WIDTH,
        max_h: int = MAX_STREAM_HEIGHT,
    ) -> tuple[int, int]:
        sw, sh = self.probe_source_size()
        return self.fit_output_size(sw, sh, max_w, max_h)

    def _build_ffmpeg_cmd(self) -> list[str]:
        width, height = self.config.output_size
        bitrate, maxrate, bufsize = self._video_bitrate()
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
            bitrate,
            "-maxrate",
            maxrate,
            "-bufsize",
            bufsize,
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

    def _input_urls(self) -> list[str]:
        urls = [self.config.rtsp_input_url]
        if self.config.rtsp_fallback_url and self.config.rtsp_fallback_url not in urls:
            urls.append(self.config.rtsp_fallback_url)
        return urls

    def _connect_rtsp(self) -> bool:
        for url in self._input_urls():
            if self._try_connect_rtsp(url):
                log.info(
                    f"[cam {self.config.camera_id}] RTSP connected via {self._safe_url(url)}"
                )
                return True
            log.warning(
                f"[cam {self.config.camera_id}] RTSP connect failed for {self._safe_url(url)}"
            )
        return False

    def _try_connect_rtsp(self, url: str, read_attempts: int = 40) -> bool:
        self._disconnect_rtsp()
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|stimeout;15000000"
        )
        self.capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            self.capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 30_000)
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            self.capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15_000)
        if not self.capture.isOpened():
            self._disconnect_rtsp()
            return False
        for _ in range(read_attempts):
            ret, frame = self.capture.read()
            if ret and frame is not None and frame.size > 0:
                h, w = frame.shape[:2]
                if w > 0 and h > 0:
                    self._source_size = (w, h)
                return True
            time.sleep(0.5)
        self._disconnect_rtsp()
        return False

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
            # 1:1 — детекция на каждом кадре, который уходит в трансляцию
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
        if self.config.max_quality:
            self.config.output_size = self.resolve_max_output_size()
            log.info(
                f"[cam {self.config.camera_id}] max quality output "
                f"{self.config.output_size[0]}x{self.config.output_size[1]} "
                f"(source {self._source_size})"
            )
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
        out = dict(self.metrics)
        w, h = self.config.output_size
        out["stream_width"] = w
        out["stream_height"] = h
        out["max_quality"] = self.config.max_quality
        if self._source_size:
            out["source_width"] = self._source_size[0]
            out["source_height"] = self._source_size[1]
        return out
