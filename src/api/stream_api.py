"""Start/stop face-annotated RTSP streams."""

from fastapi import APIRouter, HTTPException

from src.services.camera_store import CameraStore
from src.streaming.stream_manager import get_stream_manager


class StreamApi:
    def __init__(self, store: CameraStore) -> None:
        self.store = store
        self.router = APIRouter()
        self.setup()

    def setup(self) -> None:
        @self.router.get("/streams/status")
        async def streams_status() -> dict:
            manager = get_stream_manager()
            cameras = self.store.list()
            return {"items": manager.get_all_statuses(cameras)}

        @self.router.post("/cameras/{camera_id}/stream/start")
        async def start_stream(camera_id: int) -> dict:
            camera = self.store.get(camera_id)
            if not camera:
                raise HTTPException(status_code=404, detail="Camera not found")
            manager = get_stream_manager()
            if not manager.start_stream(camera):
                raise HTTPException(status_code=500, detail="Failed to start stream")
            return {
                "ok": True,
                "camera_id": camera_id,
                "publish_url": manager.get_publish_url(camera_id),
                "go2rtc_stream": f"cam{camera_id}_annot",
            }

        @self.router.post("/cameras/{camera_id}/stream/stop")
        async def stop_stream(camera_id: int) -> dict:
            manager = get_stream_manager()
            if not manager.stop_stream(camera_id):
                raise HTTPException(status_code=404, detail="Stream not running")
            return {"ok": True, "camera_id": camera_id}

        @self.router.post("/streams/start-all")
        async def start_all() -> dict:
            manager = get_stream_manager()
            started = []
            for camera in self.store.list():
                if camera.enabled and manager.start_stream(camera):
                    started.append(camera.id)
            return {"ok": True, "started": started}

        @self.router.post("/streams/stop-all")
        async def stop_all() -> dict:
            get_stream_manager().stop_all()
            return {"ok": True}

        @self.router.post("/faces/reload-embeddings")
        async def reload_embeddings() -> dict:
            """Перечитать таблицу faces из PostgreSQL (после enroll)."""
            count = get_stream_manager().reload_embeddings()
            return {"ok": True, "enrolled_faces": count}
