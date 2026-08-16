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
from src.services.sealer_counter_store import SealerCounterStore
from src.services.people_counter_store import PeopleCounterStore
from src.services.package_detection_service import get_package_detection_service
from src.services.rod_pose_service import get_rod_pose_service
from src.services.rod_counter_store import RodCounterStore
from src.services.inference_scheduler import SharedInferenceScheduler
from src.services.roi_people_counter_store import RoiPeopleCounterStore
from src.utils.logger import get_logger
from src.utils.roi_helpers import RoiPolygonData, polygons_points
from src.utils.rtsp import build_go2rtc_rtsp_url, build_rtsp_url

log = get_logger()

MAX_STREAMERS = 8


class FaceStreamManager:
    def __init__(
        self, cfg: Configs, camera_store: CameraStore | None = None, model_store=None
    ) -> None:
        self.cfg = cfg
        self.camera_store = camera_store
        self.model_store = model_store
        self.inference_scheduler = SharedInferenceScheduler()
        self._runtime_engines: dict[str, object] = {}
        self.mediamtx_url = cfg.MEDIAMTX_URL.rstrip("/")
        self.streamers: Dict[int, FaceAnnotatedStreamer] = {}
        self._lock = threading.Lock()
        self._session_override: dict[int, tuple[int, int]] = {}
        self._package_camera_ids: set[int] = set()
        self._rod_camera_ids: set[int] = set()

        self.engine: FrOnnxEngine | None = None
        self._person_model_id = ""
        self._person_tracker = "bytetrack"
        self._person_track_buffer = 90
        self.person_engine = None

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
        self.sealer_counter_store = SealerCounterStore(self.db)
        self.rod_counter_store = RodCounterStore(self.db)
        log.info(f"Face DB ready: {self.face_store.count} embedding(s) loaded")

    def _create_person_engine(self, model_id: str):
        path = resolve_person_model_path(model_id)
        log.info(f"Initializing person detector: {model_id} ({path})")
        engine = create_person_engine(path, self.cfg.FR_PROVIDER)
        engine.setup()
        self._person_model_id = model_id
        self.cfg.PERSON_DET_ENGINE_PATH = path
        return engine

    def _register_runtime_engine(self, key: str, engine, task: str) -> str:
        if key in self._runtime_engines:
            return key
        self._runtime_engines[key] = engine
        if task == "face":
            self.inference_scheduler.register(
                key,
                lambda frame, params, e=engine: e.predict(
                    [frame],
                    det_conf=float(params.get("conf", 0.25)),
                    det_nms=float(params.get("nms", 0.45)),
                )[0],
            )
        elif task in ("person", "package"):
            self.inference_scheduler.register(
                key,
                lambda frame, params, e=engine: e.predict(
                    [frame],
                    conf=float(params.get("conf", 0.25)),
                    nms=float(params.get("nms", 0.45)),
                    **(
                        {"imgsz": int(params["imgsz"])}
                        if "imgsz" in params
                        else {}
                    ),
                )[0],
            )
        elif task == "pose":
            self.inference_scheduler.register(
                key,
                lambda frame, params, e=engine: e.predict(
                    frame,
                    conf=float(params.get("conf", 0.25)),
                    imgsz=int(params.get("imgsz", 640)),
                ),
            )
        return key

    def _camera_runtime(self, camera: CameraSchema) -> dict:
        """Resolve catalog assignments to shared engines; legacy flags remain fallback."""
        runtime = {
            "mode": self.cfg.DETECTION_MODE,
            "face_key": "",
            "person_keys": [],
            "package_keys": [],
            "pose_keys": [],
            "catalog": False,
        }
        assignments = (
            self.model_store.list_camera_models(camera.id) if self.model_store else None
        )
        assignments = [
            item for item in (assignments or []) if item.enabled and item.model.enabled
        ]
        if assignments:
            runtime["catalog"] = True
            tasks = {item.model.task for item in assignments}
            runtime["mode"] = (
                "face_person"
                if "face" in tasks and "person" in tasks
                else "face"
                if "face" in tasks
                else "person"
                if "person" in tasks
                else "off"
            )
            if "face" in tasks:
                face_models = [
                    item.model for item in assignments if item.model.task == "face"
                ]
                det_model = next(
                    (
                        model
                        for model in face_models
                        if any(token in model.code.lower() for token in ("yolox", "scrfd", "det"))
                    ),
                    None,
                )
                rec_model = next(
                    (
                        model
                        for model in face_models
                        if any(token in model.code.lower() for token in ("mobile", "arc", "w600", "rec"))
                    ),
                    None,
                )
                det_path = det_model.path if det_model else self.cfg.FR_DET_ENGINE_PATH
                rec_path = rec_model.path if rec_model else self.cfg.FR_REC_ENGINE_PATH
                face_key = (
                    f"face:{det_model.code if det_model else 'default-det'}+"
                    f"{rec_model.code if rec_model else 'default-rec'}"
                )
                face_engine = self._runtime_engines.get(face_key)
                if face_engine is None:
                    face_engine = FrOnnxEngine(
                        det_engine_path=det_path,
                        rec_engine_path=rec_path,
                        det_max_end2end=self.cfg.FR_DET_MAX_END2END,
                        provider=self.cfg.FR_PROVIDER,
                    )
                    face_engine.setup()
                runtime["face_key"] = self._register_runtime_engine(
                    face_key, face_engine, "face"
                )
            for assignment in assignments:
                model = assignment.model
                key = f"{model.task}:{model.code}"
                try:
                    if model.task == "person":
                        engine = self._runtime_engines.get(key)
                        if engine is None:
                            engine = create_person_engine(model.path, self.cfg.FR_PROVIDER)
                            engine.setup()
                        runtime["person_keys"].append(
                            self._register_runtime_engine(key, engine, "person")
                        )
                    elif model.task == "package":
                        engine = self._runtime_engines.get(key)
                        if engine is None:
                            engine = create_person_engine(model.path, self.cfg.FR_PROVIDER)
                            engine.setup()
                        runtime["package_keys"].append(
                            self._register_runtime_engine(key, engine, "package")
                        )
                    elif model.task == "pose":
                        engine = self._runtime_engines.get(key)
                        if engine is None:
                            from src.engine.rod_pose_engine import RodPoseEngine

                            engine = RodPoseEngine(model.path, device=self.cfg.FR_PROVIDER)
                            engine.setup()
                        runtime["pose_keys"].append(
                            self._register_runtime_engine(key, engine, "pose")
                        )
                except Exception as exc:
                    log.error(
                        f"Model {model.code} unavailable for cam{camera.id}: {exc}"
                    )
        else:
            if self.engine is not None:
                runtime["face_key"] = self._register_runtime_engine(
                    "face:recognition-pipeline", self.engine, "face"
                )
            if self.person_engine is not None:
                runtime["person_keys"] = [
                    self._register_runtime_engine(
                        f"person:{self._person_model_id or 'default'}",
                        self.person_engine,
                        "person",
                    )
                ]
        return runtime

    def _apply_fr_engine(self, mode: str) -> None:
        if mode not in ("face", "face_person"):
            self.engine = None
            return
        if self.engine is not None:
            return
        try:
            self.engine = FrOnnxEngine(
                det_engine_path=self.cfg.FR_DET_ENGINE_PATH,
                rec_engine_path=self.cfg.FR_REC_ENGINE_PATH,
                det_max_end2end=self.cfg.FR_DET_MAX_END2END,
                provider=self.cfg.FR_PROVIDER,
            )
            self.engine.setup()
            log.info("Face recognition engine loaded")
        except Exception as exc:
            self.engine = None
            log.warning(f"Face engine skipped: {exc}")

    def _apply_person_model_settings(self, settings: DetectionSettingsSchema) -> None:
        mode = settings.detection_mode
        if mode not in ("person", "face_person"):
            self.person_engine = None
            self._person_model_id = ""
            for streamer in self.streamers.values():
                streamer.person_engine = None
            return
        if settings.person_det_model != self._person_model_id or self.person_engine is None:
            try:
                self.person_engine = self._create_person_engine(settings.person_det_model)
            except Exception as exc:
                self.person_engine = None
                self._person_model_id = ""
                log.warning(f"Person detector skipped: {exc}")
                return
            for streamer in self.streamers.values():
                streamer.person_engine = self.person_engine
            log.info(f"Person detector switched to {settings.person_det_model}")
        apply_crowdhuman_det_type(self.person_engine, settings.crowdhuman_det_type)

    def apply_detection_settings(self, settings: DetectionSettingsSchema) -> None:
        """Применить настройки к cfg и активным стримам."""
        old_size = (self.cfg.STREAM_WIDTH, self.cfg.STREAM_HEIGHT)
        old_fps = self.cfg.STREAM_FPS
        old_mode = self.cfg.DETECTION_MODE
        old_person_model = self._person_model_id
        new_size = (settings.stream_width, settings.stream_height)

        self.cfg.DETECTION_MODE = settings.detection_mode
        self._apply_fr_engine(settings.detection_mode)
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
        self._person_tracker = settings.person_tracker
        self._person_track_buffer = int(settings.person_track_buffer)
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
            streamer.set_person_tracker(
                settings.person_tracker,
                track_buffer=settings.person_track_buffer,
            )

        need_restart = (
            old_size != new_size
            or old_fps != settings.stream_fps
            or old_mode != settings.detection_mode
            or (
                old_person_model
                and old_person_model != settings.person_det_model
            )
        )
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
            f"roi_switch={settings.roi_timer_switch_sec:.0f}s "
            f"tracker={settings.person_tracker} buffer={settings.person_track_buffer}"
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

    def _streamer_config(self, camera: CameraSchema, runtime: dict | None = None) -> FaceStreamerConfig:
        runtime = runtime or {}
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
        sealer_enabled, sx, sy, sw, sh, spike, rest, cooldown = (
            False,
            0.0,
            0.0,
            0.0,
            0.0,
            8.0,
            2.0,
            8,
        )
        if self.camera_store:
            sealer_enabled, sx, sy, sw, sh, spike, rest, cooldown = (
                self.camera_store.get_sealer_roi_runtime(camera.id)
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
            detection_mode=runtime.get("mode", self.cfg.DETECTION_MODE),
            fps=self.cfg.STREAM_FPS,
            frame_interval=(
                int(camera.inference_interval)
                if camera.inference_interval is not None
                else self.cfg.STREAM_FRAME_INTERVAL
            ),
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
            package_detection_enabled=bool(runtime.get("package_keys"))
            if runtime.get("catalog")
            else bool(getattr(camera, "package_detection_enabled", False)),
            package_det_conf=self.cfg.PACKAGE_DET_CONF,
            package_det_imgsz=self.cfg.PACKAGE_DET_IMGSZ,
            package_count_dwell_sec=self.cfg.PACKAGE_COUNT_DWELL_SEC,
            rod_pose_enabled=bool(runtime.get("pose_keys"))
            if runtime.get("catalog")
            else bool(getattr(camera, "rod_pose_enabled", False)),
            rod_pose_conf=self.cfg.ROD_POSE_CONF,
            rod_pose_imgsz=self.cfg.ROD_POSE_IMGSZ,
            sealer_roi_enabled=sealer_enabled,
            sealer_roi_x=sx,
            sealer_roi_y=sy,
            sealer_roi_w=sw,
            sealer_roi_h=sh,
            sealer_roi_spike_thresh=spike,
            sealer_roi_rest_thresh=rest,
            sealer_roi_cooldown_frames=cooldown,
            sealer_cycle_dwell_sec=self.cfg.SEALER_CYCLE_DWELL_SEC,
            person_tracker=self._person_tracker,  # type: ignore[arg-type]
            person_track_buffer=self._person_track_buffer,
            face_model_key=runtime.get("face_key", ""),
            person_model_keys=list(runtime.get("person_keys", [])),
            package_model_keys=list(runtime.get("package_keys", [])),
            pose_model_keys=list(runtime.get("pose_keys", [])),
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
        sealer_enabled, sx, sy, sw, sh, spike, rest, cooldown = (
            self.camera_store.get_sealer_roi_runtime(camera_id)
        )
        streamer.update_sealer_roi(
            sealer_enabled, sx, sy, sw, sh, spike, rest, cooldown
        )

    def _release_rod_if_needed(self, camera_id: int) -> None:
        if camera_id not in self._rod_camera_ids:
            return
        # Scheduler owns the single model instance for the process lifetime.
        self._rod_camera_ids.discard(camera_id)

    def _release_package_if_needed(self, camera_id: int) -> None:
        if camera_id not in self._package_camera_ids:
            return
        # Scheduler owns the single model instance for the process lifetime.
        self._package_camera_ids.discard(camera_id)

    def update_package_detection(self, camera_id: int, enabled: bool) -> None:
        streamer = self.streamers.get(camera_id)
        if streamer:
            streamer.update_package_detection(enabled)

    def update_rod_pose(self, camera_id: int, enabled: bool) -> None:
        streamer = self.streamers.get(camera_id)
        if enabled:
            try:
                rod_engine = get_rod_pose_service().acquire()
                self._rod_camera_ids.add(camera_id)
                if streamer:
                    streamer.rod_pose_engine = rod_engine
            except RuntimeError as exc:
                log.error(f"Rod pose unavailable for cam{camera_id}: {exc}")
                raise
        else:
            if streamer:
                streamer.rod_pose_engine = None
            self._release_rod_if_needed(camera_id)
        if streamer:
            streamer.update_rod_pose(enabled)

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

    def update_sealer_roi(
        self,
        camera_id: int,
        enabled: bool,
        x: float,
        y: float,
        w: float,
        h: float,
        spike_thresh: float = 20.0,
        rest_thresh: float = -15.0,
        cooldown_frames: int = 8,
    ) -> None:
        streamer = self.streamers.get(camera_id)
        if streamer:
            streamer.update_sealer_roi(
                enabled, x, y, w, h, spike_thresh, rest_thresh, cooldown_frames
            )

    def get_sealer_metrics(self, camera_id: int) -> dict:
        streamer = self.streamers.get(camera_id)
        activity = 0.0
        if streamer:
            activity = float(streamer.metrics.get("sealer_activity", 0.0))
        cycles_today = self.sealer_counter_store.get_cycles_today(camera_id)
        return {
            "cycle_count": cycles_today,
            "cycles_today": cycles_today,
            "activity": activity,
        }

    def delete_roi_timers(self, camera_id: int) -> None:
        self.roi_timer_store.delete_camera(camera_id)
        self.roi_people_counter_store.delete_camera(camera_id)
        self.package_counter_store.delete_camera(camera_id)
        self.sealer_counter_store.delete_camera(camera_id)
        self.rod_counter_store.delete_camera(camera_id)

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

            runtime = self._camera_runtime(camera)
            package_engine = None
            rod_pose_engine = None
            pkg_enabled = bool(runtime.get("package_keys")) if runtime.get("catalog") else bool(
                getattr(camera, "package_detection_enabled", False)
            )
            rod_enabled = bool(runtime.get("pose_keys")) if runtime.get("catalog") else bool(
                getattr(camera, "rod_pose_enabled", False)
            )
            if pkg_enabled and not runtime.get("catalog"):
                try:
                    package_engine = self._runtime_engines.get("package:legacy")
                    if package_engine is None:
                        package_engine = get_package_detection_service().acquire()
                    runtime["package_keys"] = [
                        self._register_runtime_engine(
                            "package:legacy", package_engine, "package"
                        )
                    ]
                    self._package_camera_ids.add(camera.id)
                except RuntimeError as exc:
                    log.error(f"Package detection unavailable for cam{camera.id}: {exc}")
                    return False
            if rod_enabled and not runtime.get("catalog"):
                try:
                    rod_pose_engine = self._runtime_engines.get("pose:legacy")
                    if rod_pose_engine is None:
                        rod_pose_engine = get_rod_pose_service().acquire()
                    runtime["pose_keys"] = [
                        self._register_runtime_engine(
                            "pose:legacy", rod_pose_engine, "pose"
                        )
                    ]
                    self._rod_camera_ids.add(camera.id)
                except RuntimeError as exc:
                    log.error(f"Rod pose unavailable for cam{camera.id}: {exc}")
                    self._release_package_if_needed(camera.id)
                    return False

            streamer = FaceAnnotatedStreamer(
                self._streamer_config(camera, runtime),
                self.engine,
                self.face_store,
                person_engine=self.person_engine,
                package_engine=package_engine,
                rod_pose_engine=rod_pose_engine,
                roi_timer_store=self.roi_timer_store,
                people_counter_store=self.people_counter_store,
                roi_people_counter_store=self.roi_people_counter_store,
                package_counter_store=self.package_counter_store,
                sealer_counter_store=self.sealer_counter_store,
                rod_counter_store=self.rod_counter_store,
                inference_scheduler=self.inference_scheduler,
                roi_switch_seconds=self.cfg.ROI_TIMER_SWITCH_SEC,
                roi_reset_grace_seconds=self.cfg.ROI_TIMER_RESET_GRACE_SEC,
            )
            if not streamer.start():
                self._release_package_if_needed(camera.id)
                self._release_rod_if_needed(camera.id)
                return False
            self.streamers[camera.id] = streamer
            log.info(
                f"Started face stream cam{camera.id} ({camera.name}) "
                f"model={self._person_model_id} "
                f"package_det={pkg_enabled} rod_pose={rod_enabled} "
                f"-> {streamer.config.publish_url}"
            )
            return True

    def stop_stream(self, camera_id: int) -> bool:
        with self._lock:
            streamer = self.streamers.pop(camera_id, None)
        if not streamer:
            return False
        self._release_package_if_needed(camera_id)
        self._release_rod_if_needed(camera_id)
        self.inference_scheduler.detach_camera(camera_id)
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
                    "ingest_fps": metrics.get("ingest_fps", 0.0) if metrics else 0.0,
                    "dropped_frames": (
                        metrics.get("dropped_frames", 0) if metrics else 0
                    ),
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
                    "rod_pose_enabled": bool(
                        getattr(camera, "rod_pose_enabled", False)
                    ),
                    "packages_count": metrics.get("packages_count", 0) if metrics else 0,
                    "labels_count": metrics.get("labels_count", 0) if metrics else 0,
                    "rod_press_count": metrics.get("rod_press_count", 0) if metrics else 0,
                    "rod_angle": metrics.get("rod_angle", 0.0) if metrics else 0.0,
                    "rod_ref_dA": metrics.get("rod_ref_dA", 0.0) if metrics else 0.0,
                }
            )
        return statuses

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self.streamers.keys())
        for camera_id in ids:
            self.stop_stream(camera_id)

    def shutdown(self) -> None:
        self.stop_all()
        self.inference_scheduler.stop()


_manager: Optional[FaceStreamManager] = None


def init_stream_manager(
    cfg: Configs, camera_store: CameraStore | None = None, model_store=None
) -> FaceStreamManager:
    global _manager
    if _manager is None:
        _manager = FaceStreamManager(
            cfg, camera_store=camera_store, model_store=model_store
        )
    return _manager


def get_stream_manager() -> FaceStreamManager:
    if _manager is None:
        raise RuntimeError("Stream manager not initialized")
    return _manager


def shutdown_stream_manager() -> None:
    global _manager
    if _manager is not None:
        _manager.shutdown()
        _manager = None
