"""Camera management API."""

from fastapi import APIRouter, HTTPException, status

from src.schema.camera_schema import (
    CameraCreateSchema,
    CameraListSchema,
    CameraSchema,
    CameraUpdateSchema,
)
from src.schema.roi_schema import RoiResponse, RoiUpdate
from src.services.camera_store import CameraStore
from src.services.go2rtc_sync import sync_go2rtc_config
from src.streaming.stream_manager import get_stream_manager


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
            polygons = [[(p.x, p.y) for p in poly.points] for poly in roi.polygons]
            manager.update_roi_polygons(camera_id, roi.enabled, polygons)
        except RuntimeError:
            pass

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
            camera = self.store.update(camera_id, payload)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
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
