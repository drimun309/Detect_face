"""Manages face-annotated RTSP publishers per camera."""

import threading
from typing import Dict, Optional

from src.db.pg_db import PgSyncDb
from src.engine.fr_onnx_engine import FrOnnxEngine
from src.engine.person_engine_factory import create_person_engine
from src.services.face_embedding_store import init_face_embedding_store
from src.services.roi_timer_store import RoiTimerStore
from src.schema.camera_schema import CameraSchema
from src.schema.configs import Configs
from src.schema.settings_schema import DetectionSettingsSchema
from src.services.camera_store import CameraStore
from src.streaming.face_annotated_stream import FaceAnnotatedStreamer, FaceStreamerConfig
from src.utils.logger import get_logger
from src.utils.rtsp import build_go2rtc_rtsp_url, build_rtsp_url

log = get_logger()

MAX_STREAMERS = 8


class FaceStreamManager:
    def __init__(self, cfg: Configs, camera_store: CameraStore | None = None) -> None:
        self.cfg = cfg
        self.camera_store = camera_store
        self.mediamtx_url = cfg.MEDIAMTX_URL.rstrip("/")
        self.streamers: Dict[int, FaceAnnotatedStreamer] = {}
        self._lock = threading.Lock()

        self.engine = FrOnnxEngine(
            det_engine_path=cfg.FR_DET_ENGINE_PATH,
            rec_engine_path=cfg.FR_REC_ENGINE_PATH,
            det_max_end2end=cfg.FR_DET_MAX_END2END,
            provider=cfg.FR_PROVIDER,
        )
        self.engine.setup()
        self.person_engine = create_person_engine(
            cfg.PERSON_DET_ENGINE_PATH,
            cfg.FR_PROVIDER,
        )
        self.person_engine.setup()

        self.db = PgSyncDb(
            host=cfg.POSTGRES_HOST,
            port=cfg.POSTGRES_PORT,
            user=cfg.POSTGRES_USER,
            password=cfg.POSTGRES_PASSWORD,
            db=cfg.POSTGRES_DB,
        )
        self.db.setup()
        self.face_store = init_face_embedding_store(self.db)
        self.roi_timer_store = RoiTimerStore(self.db)
        log.info(f"Face DB ready: {self.face_store.count} embedding(s) loaded")

    def apply_detection_settings(self, settings: DetectionSettingsSchema) -> None:
        """Применить настройки к cfg и активным стримам."""
        old_size = (self.cfg.STREAM_WIDTH, self.cfg.STREAM_HEIGHT)
        old_fps = self.cfg.STREAM_FPS
        new_size = (settings.stream_width, settings.stream_height)

        self.cfg.DETECTION_MODE = settings.detection_mode
        self.cfg.FR_DET_CONF = settings.fr_det_conf
        self.cfg.FR_DET_NMS = settings.fr_det_nms
        self.cfg.FR_DISTANCE = settings.fr_distance
        self.cfg.FR_MIN_DET_SCORE = settings.min_det_score
        self.cfg.STREAM_FRAME_INTERVAL = settings.stream_frame_interval
        self.cfg.STREAM_FPS = settings.stream_fps
        self.cfg.STREAM_WIDTH = settings.stream_width
        self.cfg.STREAM_HEIGHT = settings.stream_height
        self.cfg.STREAM_SHOW_UNKNOWN_DISTANCE = settings.stream_show_unknown_distance
        self.cfg.EMBEDDING_REFRESH_SEC = settings.embedding_refresh_sec
        self.cfg.ROI_TIMER_SWITCH_SEC = settings.roi_timer_switch_sec
        self.cfg.ROI_TIMER_RESET_GRACE_SEC = settings.roi_timer_reset_grace_sec
        self.face_store.refresh_interval_sec = settings.embedding_refresh_sec

        for streamer in self.streamers.values():
            streamer.roi_switch_seconds = settings.roi_timer_switch_sec
            streamer.roi_reset_grace_seconds = settings.roi_timer_reset_grace_sec
            streamer.config.detection_mode = settings.detection_mode
            streamer.config.det_conf = settings.fr_det_conf
            streamer.config.det_nms = settings.fr_det_nms
            streamer.config.distance = settings.fr_distance
            streamer.config.min_det_score = settings.min_det_score
            streamer.config.frame_interval = settings.stream_frame_interval
            streamer.config.fps = settings.stream_fps
            streamer.config.show_unknown_distance = settings.stream_show_unknown_distance
            streamer.config.output_size = new_size

        need_restart = old_size != new_size or old_fps != settings.stream_fps
        if need_restart and self.camera_store:
            running_ids = list(self.streamers.keys())
            cameras = {c.id: c for c in self.camera_store.list()}
            for camera_id in running_ids:
                camera = cameras.get(camera_id)
                if camera:
                    self.restart_stream(camera)
            log.info("Restarted streams after resolution/fps change")

        log.info(
            f"Detection settings applied: mode={settings.detection_mode} "
            f"conf={settings.fr_det_conf:.2f} distance={settings.fr_distance:.2f} "
            f"interval={settings.stream_frame_interval} "
            f"roi_switch={settings.roi_timer_switch_sec:.0f}s"
        )

    def reload_embeddings(self) -> int:
        return self.face_store.reload()

    def _streamer_config(self, camera: CameraSchema) -> FaceStreamerConfig:
        roi_enabled, roi_polygons = False, []
        if self.camera_store:
            roi_enabled, roi_polygons = self.camera_store.get_roi_polygons(camera.id)
        active_polygons = roi_polygons if roi_enabled else []
        roi_keys = self.roi_timer_store.sync_camera_rois(camera.id, active_polygons)
        direct_rtsp = build_rtsp_url(camera)
        go2rtc_rtsp = (
            build_go2rtc_rtsp_url(camera, self.cfg.GO2RTC_RTSP_URL)
            if self.cfg.GO2RTC_RTSP_URL
            else ""
        )
        return FaceStreamerConfig(
            camera_id=camera.id,
            camera_name=camera.name,
            rtsp_input_url=go2rtc_rtsp or direct_rtsp,
            rtsp_fallback_url=direct_rtsp if go2rtc_rtsp else "",
            publish_url=f"{self.mediamtx_url}/annot_cam_{camera.id}",
            output_size=(self.cfg.STREAM_WIDTH, self.cfg.STREAM_HEIGHT),
            detection_mode=self.cfg.DETECTION_MODE,
            fps=self.cfg.STREAM_FPS,
            frame_interval=self.cfg.STREAM_FRAME_INTERVAL,
            det_conf=self.cfg.FR_DET_CONF,
            det_nms=self.cfg.FR_DET_NMS,
            distance=self.cfg.FR_DISTANCE,
            min_det_score=self.cfg.FR_MIN_DET_SCORE,
            show_unknown_distance=self.cfg.STREAM_SHOW_UNKNOWN_DISTANCE,
            roi_enabled=roi_enabled,
            roi_polygons=roi_polygons,
            roi_keys=roi_keys,
        )

    def update_roi_polygons(
        self,
        camera_id: int,
        enabled: bool,
        polygons: list[list[tuple[float, float]]],
    ) -> None:
        active_polygons = polygons if enabled else []
        roi_keys = self.roi_timer_store.sync_camera_rois(camera_id, active_polygons)
        streamer = self.streamers.get(camera_id)
        if streamer:
            streamer.update_roi_polygons(enabled, polygons, roi_keys)

    def delete_roi_timers(self, camera_id: int) -> None:
        self.roi_timer_store.delete_camera(camera_id)

    def start_stream(self, camera: CameraSchema) -> bool:
        if not camera.enabled:
            return False
        if not self.cfg.ENABLE_ANNOTATED_STREAM:
            log.info("Annotated stream disabled (ENABLE_ANNOTATED_STREAM=false)")
            return False

        with self._lock:
            if camera.id in self.streamers:
                return True
            if len(self.streamers) >= MAX_STREAMERS:
                log.error(f"Max streamers ({MAX_STREAMERS}) reached")
                return False

            streamer = FaceAnnotatedStreamer(
                self._streamer_config(camera),
                self.engine,
                self.face_store,
                person_engine=self.person_engine,
                roi_timer_store=self.roi_timer_store,
                roi_switch_seconds=self.cfg.ROI_TIMER_SWITCH_SEC,
                roi_reset_grace_seconds=self.cfg.ROI_TIMER_RESET_GRACE_SEC,
            )
            if not streamer.start():
                return False
            self.streamers[camera.id] = streamer
            log.info(f"Started face stream cam{camera.id} -> {streamer.config.publish_url}")
            return True

    def stop_stream(self, camera_id: int) -> bool:
        with self._lock:
            streamer = self.streamers.pop(camera_id, None)
        if not streamer:
            return False
        streamer.stop()
        return True

    def restart_stream(self, camera: CameraSchema) -> bool:
        self.stop_stream(camera.id)
        if not camera.enabled:
            return True
        return self.start_stream(camera)

    def is_running(self, camera_id: int) -> bool:
        return camera_id in self.streamers

    def get_status(self, camera_id: int) -> Optional[dict]:
        streamer = self.streamers.get(camera_id)
        if not streamer:
            return None
        return streamer.get_metrics()

    def get_publish_url(self, camera_id: int) -> str:
        return f"{self.mediamtx_url}/annot_cam_{camera_id}"

    def get_all_statuses(self, cameras: list[CameraSchema]) -> list[dict]:
        statuses = []
        for camera in cameras:
            metrics = self.get_status(camera.id)
            statuses.append(
                {
                    "camera_id": camera.id,
                    "name": camera.name,
                    "enabled": camera.enabled,
                    "stream_running": metrics is not None,
                    "faces_count": metrics.get("faces_count", 0) if metrics else 0,
                    "infer_fps": metrics.get("infer_fps", 0.0) if metrics else 0.0,
                    "encode_fps": metrics.get("encode_fps", 0.0) if metrics else 0.0,
                    "errors": metrics.get("errors", 0) if metrics else 0,
                    "enrolled_faces": (
                        metrics.get("enrolled_faces", self.face_store.count)
                        if metrics
                        else self.face_store.count
                    ),
                    "publish_url": self.get_publish_url(camera.id),
                }
            )
        return statuses

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self.streamers.keys())
        for camera_id in ids:
            self.stop_stream(camera_id)


_manager: Optional[FaceStreamManager] = None


def init_stream_manager(cfg: Configs, camera_store: CameraStore | None = None) -> FaceStreamManager:
    global _manager
    if _manager is None:
        _manager = FaceStreamManager(cfg, camera_store=camera_store)
    return _manager


def get_stream_manager() -> FaceStreamManager:
    if _manager is None:
        raise RuntimeError("Stream manager not initialized")
    return _manager


def shutdown_stream_manager() -> None:
    global _manager
    if _manager is not None:
        _manager.stop_all()
        _manager = None
