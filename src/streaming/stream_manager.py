"""Manages face-annotated RTSP publishers per camera."""

import threading
from typing import Dict, Optional

from src.db.pg_db import PgSyncDb
from src.engine.fr_onnx_engine import FrOnnxEngine
from src.engine.person_engine_factory import apply_crowdhuman_det_type, create_person_engine
from src.schema.person_model_catalog import infer_person_model_id, resolve_person_model_path
from src.services.face_embedding_store import init_face_embedding_store
from src.services.roi_timer_store import RoiTimerStore
from src.schema.camera_schema import CameraSchema
from src.schema.configs import Configs
from src.schema.settings_schema import DetectionSettingsSchema
from src.services.camera_store import CameraStore
from src.streaming.face_annotated_stream import (
    FaceAnnotatedStreamer,
    FaceStreamerConfig,
    MAX_STREAM_HEIGHT,
    MAX_STREAM_WIDTH,
)
from src.utils.stream_quality import (
    MAX_STREAM_HEIGHT as SQ_MAX_H,
    MAX_STREAM_WIDTH as SQ_MAX_W,
    resolve_stream_output_size,
    size_to_preset,
)
from src.services.package_counter_store import PackageCounterStore
from src.services.people_counter_store import PeopleCounterStore
from src.services.package_detection_service import get_package_detection_service
from src.services.roi_people_counter_store import RoiPeopleCounterStore
from src.utils.logger import get_logger
from src.utils.roi_helpers import RoiPolygonData, polygons_points
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
        self._session_override: dict[int, tuple[int, int]] = {}
        self._package_camera_ids: set[int] = set()

        self.engine = FrOnnxEngine(
            det_engine_path=cfg.FR_DET_ENGINE_PATH,
            rec_engine_path=cfg.FR_REC_ENGINE_PATH,
            det_max_end2end=cfg.FR_DET_MAX_END2END,
            provider=cfg.FR_PROVIDER,
        )
        self.engine.setup()
        self._person_model_id = ""
        self.person_engine = self._create_person_engine(
            infer_person_model_id(cfg.PERSON_DET_ENGINE_PATH)
        )

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
        self.people_counter_store = PeopleCounterStore(self.db)
        self.roi_people_counter_store = RoiPeopleCounterStore(self.db)
        self.package_counter_store = PackageCounterStore(self.db)
        log.info(f"Face DB ready: {self.face_store.count} embedding(s) loaded")

    def _create_person_engine(self, model_id: str):
        path = resolve_person_model_path(model_id)
        log.info(f"Initializing person detector: {model_id} ({path})")
        engine = create_person_engine(path, self.cfg.FR_PROVIDER)
        engine.setup()
        self._person_model_id = model_id
        self.cfg.PERSON_DET_ENGINE_PATH = path
        return engine

    def _apply_person_model_settings(self, settings: DetectionSettingsSchema) -> None:
        if settings.person_det_model != self._person_model_id:
            self.person_engine = self._create_person_engine(settings.person_det_model)
            for streamer in self.streamers.values():
                streamer.person_engine = self.person_engine
            log.info(f"Person detector switched to {settings.person_det_model}")
        apply_crowdhuman_det_type(self.person_engine, settings.crowdhuman_det_type)

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

        self._apply_person_model_settings(settings)

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
            f"person_model={settings.person_det_model} "
            f"crowdhuman_type={settings.crowdhuman_det_type} "
            f"conf={settings.fr_det_conf:.2f} distance={settings.fr_distance:.2f} "
            f"interval={settings.stream_frame_interval} "
            f"roi_switch={settings.roi_timer_switch_sec:.0f}s"
        )

    def reload_embeddings(self) -> int:
        return self.face_store.reload()

    def _resolve_output_size(self, camera: CameraSchema) -> tuple[int, int, bool]:
        override = self._session_override.get(camera.id)
        return resolve_stream_output_size(
            camera.stream_width,
            camera.stream_height,
            self.cfg.STREAM_WIDTH,
            self.cfg.STREAM_HEIGHT,
            override,
        )

    def _streamer_config(self, camera: CameraSchema) -> FaceStreamerConfig:
        roi_enabled, roi_defs = False, []
        if self.camera_store:
            roi_enabled, roi_defs = self.camera_store.get_roi_polygons(camera.id)
        active_polygons = roi_defs if roi_enabled else []
        roi_keys = self.roi_timer_store.sync_camera_rois(camera.id, active_polygons)
        roi_points = polygons_points(active_polygons)
        people_enabled, people_polygon, people_max_workers = (
            False,
            [],
            3,
        )
        if self.camera_store:
            people_enabled, people_polygon, people_max_workers = (
                self.camera_store.get_people_zone_runtime(camera.id)
            )
        direct_rtsp = build_rtsp_url(camera)
        go2rtc_rtsp = (
            build_go2rtc_rtsp_url(camera, self.cfg.GO2RTC_RTSP_URL)
            if self.cfg.GO2RTC_RTSP_URL
            else ""
        )
        output_w, output_h, max_q = self._resolve_output_size(camera)
        output_size = (output_w, output_h)
        return FaceStreamerConfig(
            camera_id=camera.id,
            camera_name=camera.name,
            rtsp_input_url=go2rtc_rtsp or direct_rtsp,
            rtsp_fallback_url=direct_rtsp if go2rtc_rtsp else "",
            publish_url=f"{self.mediamtx_url}/annot_cam_{camera.id}",
            output_size=output_size,
            detection_mode=self.cfg.DETECTION_MODE,
            fps=self.cfg.STREAM_FPS,
            frame_interval=self.cfg.STREAM_FRAME_INTERVAL,
            det_conf=self.cfg.FR_DET_CONF,
            det_nms=self.cfg.FR_DET_NMS,
            distance=self.cfg.FR_DISTANCE,
            min_det_score=self.cfg.FR_MIN_DET_SCORE,
            show_unknown_distance=self.cfg.STREAM_SHOW_UNKNOWN_DISTANCE,
            roi_enabled=roi_enabled,
            roi_polygons=roi_points,
            roi_keys=roi_keys,
            max_quality=max_q,
            people_zone_enabled=people_enabled,
            people_zone_polygon=people_polygon,
            people_zone_max_workers=people_max_workers,
            package_detection_enabled=bool(
                getattr(camera, "package_detection_enabled", False)
            ),
            package_det_conf=self.cfg.PACKAGE_DET_CONF,
            package_det_imgsz=self.cfg.PACKAGE_DET_IMGSZ,
            package_count_dwell_sec=self.cfg.PACKAGE_COUNT_DWELL_SEC,
        )

    def _apply_camera_config_to_streamer(
        self, camera_id: int, streamer: FaceAnnotatedStreamer
    ) -> None:
        """Подтянуть ROI и общую зону из БД в уже запущенный стример."""
        if not self.camera_store:
            return
        roi_enabled, roi_defs = self.camera_store.get_roi_polygons(camera_id)
        active_polygons = roi_defs if roi_enabled else []
        roi_keys = self.roi_timer_store.sync_camera_rois(camera_id, active_polygons)
        streamer.update_roi_polygons(
            roi_enabled, polygons_points(active_polygons), roi_keys
        )
        people_enabled, people_polygon, people_max_workers = (
            self.camera_store.get_people_zone_runtime(camera_id)
        )
        streamer.update_people_zone(
            people_enabled, people_polygon, people_max_workers
        )

    def _release_package_if_needed(self, camera_id: int) -> None:
        if camera_id not in self._package_camera_ids:
            return
        try:
            get_package_detection_service().release()
        except RuntimeError:
            pass
        self._package_camera_ids.discard(camera_id)

    def update_package_detection(self, camera_id: int, enabled: bool) -> None:
        streamer = self.streamers.get(camera_id)
        if streamer:
            streamer.update_package_detection(enabled)

    def update_roi_polygons(
        self,
        camera_id: int,
        enabled: bool,
        polygons: list[RoiPolygonData],
    ) -> None:
        active_polygons = polygons if enabled else []
        roi_keys = self.roi_timer_store.sync_camera_rois(camera_id, active_polygons)
        streamer = self.streamers.get(camera_id)
        if streamer:
            streamer.update_roi_polygons(
                enabled, polygons_points(active_polygons), roi_keys
            )

    def update_people_zone(
        self,
        camera_id: int,
        enabled: bool,
        polygon: list[tuple[float, float]],
        max_workers: int = 3,
    ) -> None:
        streamer = self.streamers.get(camera_id)
        if streamer:
            streamer.update_people_zone(enabled, polygon, max_workers)

    def delete_roi_timers(self, camera_id: int) -> None:
        self.roi_timer_store.delete_camera(camera_id)
        self.roi_people_counter_store.delete_camera(camera_id)
        self.package_counter_store.delete_camera(camera_id)

    def start_stream(self, camera: CameraSchema) -> bool:
        if not camera.enabled:
            return False
        if not self.cfg.ENABLE_ANNOTATED_STREAM:
            log.info("Annotated stream disabled (ENABLE_ANNOTATED_STREAM=false)")
            return False

        with self._lock:
            existing = self.streamers.get(camera.id)
            if existing:
                self._apply_camera_config_to_streamer(camera.id, existing)
                return True
            if len(self.streamers) >= MAX_STREAMERS:
                log.error(f"Max streamers ({MAX_STREAMERS}) reached")
                return False

            package_engine = None
            if getattr(camera, "package_detection_enabled", False):
                try:
                    package_engine = get_package_detection_service().acquire()
                    self._package_camera_ids.add(camera.id)
                except RuntimeError as exc:
                    log.error(f"Package detection unavailable for cam{camera.id}: {exc}")
                    return False

            streamer = FaceAnnotatedStreamer(
                self._streamer_config(camera),
                self.engine,
                self.face_store,
                person_engine=self.person_engine,
                package_engine=package_engine,
                roi_timer_store=self.roi_timer_store,
                people_counter_store=self.people_counter_store,
                roi_people_counter_store=self.roi_people_counter_store,
                package_counter_store=self.package_counter_store,
                roi_switch_seconds=self.cfg.ROI_TIMER_SWITCH_SEC,
                roi_reset_grace_seconds=self.cfg.ROI_TIMER_RESET_GRACE_SEC,
            )
            if not streamer.start():
                self._release_package_if_needed(camera.id)
                return False
            self.streamers[camera.id] = streamer
            log.info(
                f"Started face stream cam{camera.id} ({camera.name}) "
                f"model={self._person_model_id} "
                f"package_det={getattr(camera, 'package_detection_enabled', False)} "
                f"-> {streamer.config.publish_url}"
            )
            return True

    def stop_stream(self, camera_id: int) -> bool:
        with self._lock:
            streamer = self.streamers.pop(camera_id, None)
        if not streamer:
            return False
        self._release_package_if_needed(camera_id)
        streamer.stop()
        return True

    def restart_stream(self, camera: CameraSchema) -> bool:
        self.stop_stream(camera.id)
        if not camera.enabled:
            return True
        return self.start_stream(camera)

    def set_camera_stream_quality(
        self, camera_id: int, preset: str, *, persist: bool = True
    ) -> dict:
        from src.utils.stream_quality import preset_to_size

        if not self.camera_store:
            raise RuntimeError("Camera store not configured")
        camera = self.camera_store.get(camera_id)
        if not camera:
            raise ValueError("Camera not found")

        width, height = preset_to_size(preset)
        if persist:
            camera = self.camera_store.set_stream_quality(camera_id, width, height)
            if not camera:
                raise ValueError("Camera not found")
            self._session_override.pop(camera_id, None)
        else:
            if width is None or height is None:
                self._session_override.pop(camera_id, None)
            else:
                self._session_override[camera_id] = (width, height)

        eff_w, eff_h, max_q = self._resolve_output_size(camera)
        if self.is_running(camera_id):
            self.restart_stream(camera)
            streamer = self.streamers.get(camera_id)
            if streamer:
                eff_w, eff_h = streamer.config.output_size
                max_q = streamer.config.max_quality

        return {
            "ok": True,
            "camera_id": camera_id,
            "preset": size_to_preset(camera.stream_width, camera.stream_height),
            "stream_width": camera.stream_width,
            "stream_height": camera.stream_height,
            "effective_width": eff_w,
            "effective_height": eff_h,
            "max_quality": max_q,
        }

    def boost_stream_quality_for_recording(self, camera_id: int) -> None:
        self._session_override[camera_id] = (SQ_MAX_W, SQ_MAX_H)
        if not self.is_running(camera_id) or not self.camera_store:
            return
        camera = self.camera_store.get(camera_id)
        if camera:
            self.restart_stream(camera)

    def clear_recording_boost(self, camera_id: int) -> None:
        if camera_id not in self._session_override:
            return
        self._session_override.pop(camera_id, None)
        if not self.is_running(camera_id) or not self.camera_store:
            return
        camera = self.camera_store.get(camera_id)
        if camera:
            self.restart_stream(camera)

    def set_stream_max_quality(self, camera_id: int, max_quality: bool) -> dict:
        if max_quality:
            return self.set_camera_stream_quality(
                camera_id, "2560x1440", persist=False
            )
        self._session_override.pop(camera_id, None)
        if not self.camera_store:
            raise RuntimeError("Camera store not configured")
        camera = self.camera_store.get(camera_id)
        if not camera:
            raise ValueError("Camera not found")
        eff_w, eff_h, max_q = self._resolve_output_size(camera)
        if self.is_running(camera_id):
            self.restart_stream(camera)
            streamer = self.streamers.get(camera_id)
            if streamer:
                eff_w, eff_h = streamer.config.output_size
                max_q = streamer.config.max_quality
        return {
            "ok": True,
            "camera_id": camera_id,
            "preset": size_to_preset(camera.stream_width, camera.stream_height),
            "stream_width": camera.stream_width,
            "stream_height": camera.stream_height,
            "effective_width": eff_w,
            "effective_height": eff_h,
            "max_quality": max_q,
        }

    def get_camera_stream_quality(self, camera_id: int) -> dict:
        if not self.camera_store:
            raise RuntimeError("Camera store not configured")
        camera = self.camera_store.get(camera_id)
        if not camera:
            raise ValueError("Camera not found")
        eff_w, eff_h, max_q = self._resolve_output_size(camera)
        return {
            "camera_id": camera_id,
            "preset": size_to_preset(camera.stream_width, camera.stream_height),
            "stream_width": camera.stream_width,
            "stream_height": camera.stream_height,
            "effective_width": eff_w,
            "effective_height": eff_h,
            "max_quality": max_q,
        }

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
            eff_w, eff_h, max_q = self._resolve_output_size(camera)
            if metrics:
                eff_w = metrics.get("stream_width") or eff_w
                eff_h = metrics.get("stream_height") or eff_h
                max_q = bool(metrics.get("max_quality"))
            statuses.append(
                {
                    "camera_id": camera.id,
                    "name": camera.name,
                    "enabled": camera.enabled,
                    "stream_running": metrics is not None,
                    "faces_count": metrics.get("faces_count", 0) if metrics else 0,
                    "workers_count": metrics.get("workers_count", 0) if metrics else 0,
                    "people_zone_workers": (
                        metrics.get("people_zone_workers", 0) if metrics else 0
                    ),
                    "people_zone_person_seconds": (
                        metrics.get("people_zone_person_seconds", 0.0) if metrics else 0.0
                    ),
                    "infer_fps": metrics.get("infer_fps", 0.0) if metrics else 0.0,
                    "encode_fps": metrics.get("encode_fps", 0.0) if metrics else 0.0,
                    "errors": metrics.get("errors", 0) if metrics else 0,
                    "enrolled_faces": (
                        metrics.get("enrolled_faces", self.face_store.count)
                        if metrics
                        else self.face_store.count
                    ),
                    "publish_url": self.get_publish_url(camera.id),
                    "stream_width": eff_w,
                    "stream_height": eff_h,
                    "stream_quality_preset": size_to_preset(
                        camera.stream_width, camera.stream_height
                    ),
                    "configured_stream_width": camera.stream_width,
                    "configured_stream_height": camera.stream_height,
                    "max_quality": max_q,
                    "package_detection_enabled": bool(
                        getattr(camera, "package_detection_enabled", False)
                    ),
                    "packages_count": metrics.get("packages_count", 0) if metrics else 0,
                    "labels_count": metrics.get("labels_count", 0) if metrics else 0,
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
