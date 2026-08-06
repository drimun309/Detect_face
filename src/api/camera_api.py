"""Camera management API."""

from fastapi import APIRouter, HTTPException, status

from src.schema.camera_schema import (
    CameraCreateSchema,
    CameraListSchema,
    CameraSchema,
    CameraUpdateSchema,
)
from src.schema.package_detection_schema import (
    PackageDetectionResponse,
    PackageDetectionUpdate,
    PackageRoiCounterItem,
)
from src.schema.rod_pose_schema import RodPoseResponse, RodPoseUpdate
from src.schema.people_zone_schema import PeopleZoneConfig, PeopleZoneResponse
from src.schema.sealer_roi_schema import SealerRoiConfig, SealerRoiResponse
from src.schema.roi_schema import RoiResponse, RoiUpdate
from src.services.camera_store import CameraStore
from src.services.go2rtc_sync import sync_go2rtc_config
from src.streaming.stream_manager import get_stream_manager
from src.utils.roi_helpers import RoiPolygonData, default_roi_name


class CameraApi:
    """REST endpoints for camera settings and go2rtc sync."""

    def __init__(
        self,
        store: CameraStore,
        go2rtc_config_path: str,
        mediamtx_url: str,
    ) -> None:
        self.router = APIRouter()
        self.store = store
        self.go2rtc_config_path = go2rtc_config_path
        self.mediamtx_url = mediamtx_url
        self.setup()

    def _sync_go2rtc(self) -> None:
        cameras = self.store.list()
        sync_go2rtc_config(
            cameras=cameras,
            config_path=self.go2rtc_config_path,
            mediamtx_url=self.mediamtx_url,
        )

    def _apply_roi_to_stream(self, camera_id: int) -> None:
        roi = self.store.get_roi(camera_id)
        if not roi:
            return
        try:
            manager = get_stream_manager()
            polygons = [
                RoiPolygonData(
                    name=(poly.name or "").strip() or default_roi_name(idx),
                    points=[(p.x, p.y) for p in poly.points],
                )
                for idx, poly in enumerate(roi.polygons, start=1)
            ]
            manager.update_roi_polygons(camera_id, roi.enabled, polygons)
        except RuntimeError:
            pass

    def _apply_people_zone_to_stream(self, camera_id: int) -> None:
        try:
            manager = get_stream_manager()
            enabled, polygon, max_workers = self.store.get_people_zone_runtime(
                camera_id
            )
            manager.update_people_zone(camera_id, enabled, polygon, max_workers)
        except RuntimeError:
            pass

    def _apply_sealer_roi_to_stream(self, camera_id: int) -> None:
        try:
            manager = get_stream_manager()
            enabled, x, y, w, h, spike, rest, cooldown = (
                self.store.get_sealer_roi_runtime(camera_id)
            )
            manager.update_sealer_roi(
                camera_id, enabled, x, y, w, h, spike, rest, cooldown
            )
        except RuntimeError:
            pass

    def _sealer_response(self, camera_id: int) -> SealerRoiResponse:
        zone = self.store.get_sealer_roi(camera_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Camera not found")
        try:
            live = get_stream_manager().get_sealer_metrics(camera_id)
            zone.cycles_today = int(live.get("cycles_today", 0))
            zone.cycle_count = zone.cycles_today
            zone.activity = float(live.get("activity", 0.0))
        except RuntimeError:
            pass
        return zone

    def _on_camera_changed(self, camera, *, deleted: bool = False) -> None:
        try:
            manager = get_stream_manager()
        except RuntimeError:
            return
        if deleted or not camera.enabled:
            manager.stop_stream(camera.id)
        elif camera.enabled:
            manager.restart_stream(camera)

    def setup(self) -> None:
        @self.router.get("/cameras", response_model=CameraListSchema)
        async def list_cameras() -> CameraListSchema:
            return CameraListSchema(items=self.store.list())

        @self.router.post(
            "/cameras",
            response_model=CameraSchema,
            status_code=status.HTTP_201_CREATED,
        )
        async def create_camera(payload: CameraCreateSchema) -> CameraSchema:
            camera = self.store.create(payload)
            self._sync_go2rtc()
            self._on_camera_changed(camera)
            return camera

        @self.router.get("/cameras/{camera_id}", response_model=CameraSchema)
        async def get_camera(camera_id: int) -> CameraSchema:
            camera = self.store.get(camera_id)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            return camera

        @self.router.put("/cameras/{camera_id}", response_model=CameraSchema)
        async def update_camera(camera_id: int, payload: CameraUpdateSchema) -> CameraSchema:
            updates = payload.model_dump(exclude_unset=True)
            try:
                camera = self.store.update(camera_id, payload)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            if updates.keys() - {"department_id"}:
                self._sync_go2rtc()
                self._on_camera_changed(camera)
            return camera

        @self.router.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
        async def delete_camera(camera_id: int) -> None:
            deleted = self.store.delete(camera_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Camera not found")
            try:
                manager = get_stream_manager()
                manager.stop_stream(camera_id)
                manager.delete_roi_timers(camera_id)
            except RuntimeError:
                pass
            self._sync_go2rtc()

        @self.router.post("/cameras/sync-go2rtc", response_model=dict)
        async def manual_sync() -> dict:
            self._sync_go2rtc()
            return {"ok": True, "go2rtc_reloaded": True}

        @self.router.get("/cameras/{camera_id}/roi", response_model=RoiResponse)
        async def get_roi(camera_id: int) -> RoiResponse:
            roi = self.store.get_roi(camera_id)
            if not roi:
                raise HTTPException(status_code=404, detail="Camera not found")
            return roi

        @self.router.put("/cameras/{camera_id}/roi", response_model=RoiResponse)
        async def update_roi(camera_id: int, payload: RoiUpdate) -> RoiResponse:
            if payload.enabled and not payload.polygons:
                raise HTTPException(
                    status_code=400,
                    detail="При включённом ROI нужен хотя бы один полигон (≥3 точек)",
                )
            roi = self.store.update_roi(camera_id, payload)
            if not roi:
                raise HTTPException(status_code=404, detail="Camera not found")
            self._apply_roi_to_stream(camera_id)
            return roi

        @self.router.delete("/cameras/{camera_id}/roi", response_model=RoiResponse)
        async def delete_roi(camera_id: int) -> RoiResponse:
            roi = self.store.delete_roi(camera_id)
            if not roi:
                raise HTTPException(status_code=404, detail="Camera not found")
            self._apply_roi_to_stream(camera_id)
            return roi

        @self.router.get(
            "/cameras/{camera_id}/people-zone", response_model=PeopleZoneResponse
        )
        async def get_people_zone(camera_id: int) -> PeopleZoneResponse:
            zone = self.store.get_people_zone(camera_id)
            if not zone:
                raise HTTPException(status_code=404, detail="Camera not found")
            try:
                state = get_stream_manager().people_counter_store.get_state_live(
                    camera_id, zone.max_workers
                )
                data = zone.model_dump()
                data.update(
                    current_workers=state.current_workers,
                    seconds_0_workers=state.seconds_0_workers,
                    seconds_1_worker=state.seconds_1_worker,
                    seconds_2_workers=state.seconds_2_workers,
                    seconds_3_workers=state.seconds_3_workers,
                    person_seconds=state.person_seconds,
                )
                return PeopleZoneResponse(**data)
            except RuntimeError:
                pass
            return zone

        @self.router.put(
            "/cameras/{camera_id}/people-zone", response_model=PeopleZoneResponse
        )
        async def update_people_zone(
            camera_id: int, payload: PeopleZoneConfig
        ) -> PeopleZoneResponse:
            if payload.enabled and len(payload.polygon) < 3:
                raise HTTPException(
                    status_code=400,
                    detail="Для общей зоны нужен полигон (≥3 точки)",
                )
            zone = self.store.update_people_zone(camera_id, payload)
            if not zone:
                raise HTTPException(status_code=404, detail="Camera not found")
            self._apply_people_zone_to_stream(camera_id)
            return zone

        @self.router.get(
            "/cameras/{camera_id}/package-detection",
            response_model=PackageDetectionResponse,
        )
        async def get_package_detection(camera_id: int) -> PackageDetectionResponse:
            camera = self.store.get(camera_id)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            packed_today = 0
            packed_by_roi: list[PackageRoiCounterItem] = []
            try:
                store = get_stream_manager().package_counter_store
                states = store.get_states(camera_id)
                packed_by_roi = [
                    PackageRoiCounterItem(
                        roi_key=s.roi_key, packed_today=s.packed_today
                    )
                    for s in states
                ]
                packed_today = sum(s.packed_today for s in states)
            except RuntimeError:
                pass
            return PackageDetectionResponse(
                camera_id=camera.id,
                package_detection_enabled=camera.package_detection_enabled,
                packed_today=packed_today,
                packed_by_roi=packed_by_roi,
            )

        @self.router.put(
            "/cameras/{camera_id}/package-detection",
            response_model=PackageDetectionResponse,
        )
        async def update_package_detection(
            camera_id: int, payload: PackageDetectionUpdate
        ) -> PackageDetectionResponse:
            camera = self.store.set_package_detection(camera_id, payload.enabled)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            try:
                manager = get_stream_manager()
                if manager.is_running(camera_id):
                    manager.restart_stream(camera)
            except RuntimeError:
                pass
            return PackageDetectionResponse(
                camera_id=camera.id,
                package_detection_enabled=camera.package_detection_enabled,
                packed_today=0,
                packed_by_roi=[],
            )

        @self.router.get(
            "/cameras/{camera_id}/rod-pose",
            response_model=RodPoseResponse,
        )
        async def get_rod_pose(camera_id: int) -> RodPoseResponse:
            camera = self.store.get(camera_id)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            press_count = 0
            try:
                press_count = int(
                    get_stream_manager().sealer_counter_store.get_cycles_today(camera_id)
                )
            except RuntimeError:
                pass
            return RodPoseResponse(
                camera_id=camera.id,
                rod_pose_enabled=bool(getattr(camera, "rod_pose_enabled", False)),
                press_count=press_count,
            )

        @self.router.put(
            "/cameras/{camera_id}/rod-pose",
            response_model=RodPoseResponse,
        )
        async def update_rod_pose(
            camera_id: int, payload: RodPoseUpdate
        ) -> RodPoseResponse:
            camera = self.store.set_rod_pose(camera_id, payload.enabled)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            try:
                manager = get_stream_manager()
                if manager.is_running(camera_id):
                    manager.restart_stream(camera)
            except RuntimeError:
                pass
            return RodPoseResponse(
                camera_id=camera.id,
                rod_pose_enabled=bool(getattr(camera, "rod_pose_enabled", False)),
                press_count=0,
            )

        @self.router.get(
            "/cameras/{camera_id}/sealer-roi",
            response_model=SealerRoiResponse,
        )
        async def get_sealer_roi(camera_id: int) -> SealerRoiResponse:
            return self._sealer_response(camera_id)

        @self.router.put(
            "/cameras/{camera_id}/sealer-roi",
            response_model=SealerRoiResponse,
        )
        async def update_sealer_roi(
            camera_id: int, payload: SealerRoiConfig
        ) -> SealerRoiResponse:
            if payload.enabled and (payload.w <= 0 or payload.h <= 0):
                raise HTTPException(
                    status_code=400,
                    detail="Для зоны запайщика нужен прямоугольник (w,h > 0)",
                )
            zone = self.store.update_sealer_roi(camera_id, payload)
            if not zone:
                raise HTTPException(status_code=404, detail="Camera not found")
            self._apply_sealer_roi_to_stream(camera_id)
            return self._sealer_response(camera_id)

        @self.router.delete(
            "/cameras/{camera_id}/sealer-roi",
            response_model=SealerRoiResponse,
        )
        async def delete_sealer_roi(camera_id: int) -> SealerRoiResponse:
            zone = self.store.delete_sealer_roi(camera_id)
            if not zone:
                raise HTTPException(status_code=404, detail="Camera not found")
            self._apply_sealer_roi_to_stream(camera_id)
            return self._sealer_response(camera_id)
