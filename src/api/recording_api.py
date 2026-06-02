"""Recording API endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.schema.settings_schema import RecordingSettingsSchema
from src.services.recording_service import get_recording_service
from src.services.recording_settings_store import RecordingSettingsStore


class RecordingApi:
    def __init__(self, store: RecordingSettingsStore) -> None:
        self.store = store
        self.router = APIRouter()
        self.setup()

    def setup(self) -> None:
        @self.router.get("/settings/recording", response_model=RecordingSettingsSchema)
        async def get_recording_settings() -> RecordingSettingsSchema:
            service = get_recording_service()
            if service:
                return service.settings
            return self.store.get()

        @self.router.put("/settings/recording", response_model=RecordingSettingsSchema)
        async def update_recording_settings(
            payload: RecordingSettingsSchema,
        ) -> RecordingSettingsSchema:
            saved = self.store.save(payload)
            service = get_recording_service()
            if service:
                service.update_settings(saved)
            return saved

        @self.router.get("/recordings/{camera_id}/{camera_name}/dates")
        async def get_recording_dates(camera_id: int, camera_name: str) -> list[str]:
            service = get_recording_service()
            if not service:
                return []
            return service.get_available_dates(camera_id, camera_name)

        @self.router.get("/recordings/{camera_id}/{camera_name}/{date}")
        async def get_recordings_for_date(
            camera_id: int,
            camera_name: str,
            date: str,
        ) -> list[dict]:
            service = get_recording_service()
            if not service:
                return []
            return service.get_recordings_list(camera_id, camera_name, date)

        @self.router.get("/recordings/{camera_id}/{camera_name}/{date}/{filename}/file")
        async def get_recording_file(
            camera_id: int,
            camera_name: str,
            date: str,
            filename: str,
        ) -> FileResponse:
            service = get_recording_service()
            if not service:
                raise HTTPException(status_code=404, detail="Recording service not initialized")
            path = service.get_file_path(camera_id, camera_name, date, filename)
            if not path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            return FileResponse(path, media_type="video/mp4", filename=filename)

        @self.router.get("/recordings/{camera_id}/status")
        async def get_recording_status(camera_id: int) -> dict:
            service = get_recording_service()
            if not service:
                return {"recording": False}
            return {"recording": service.is_recording(camera_id)}

        @self.router.delete("/recordings/{camera_id}/{camera_name}/{date}/{filename}")
        async def delete_recording(
            camera_id: int,
            camera_name: str,
            date: str,
            filename: str,
        ) -> dict:
            service = get_recording_service()
            if not service:
                raise HTTPException(status_code=404, detail="Recording service not initialized")
            success = service.delete_recording(camera_id, camera_name, date, filename)
            return {"success": success}

        @self.router.post("/recordings/{camera_id}/start")
        async def start_recording(
            camera_id: int,
            camera_name: str,
            rtsp_url: str,
            manual: bool = True,
        ) -> dict:
            service = get_recording_service()
            if not service:
                raise HTTPException(status_code=404, detail="Recording service not initialized")
            if not service.settings.enabled:
                return {"recording": False, "error": "recording_disabled"}
            if (
                not manual
                and service.settings.shift.enabled
                and not service.is_shift_active()
            ):
                return {"recording": False, "error": "outside_shift"}
            success = service.start_recording(
                camera_id, camera_name, rtsp_url, manual=manual
            )
            if not success:
                return {"recording": False, "error": "start_failed"}
            return {"recording": service.is_recording(camera_id)}

        @self.router.post("/recordings/{camera_id}/stop")
        async def stop_recording(camera_id: int) -> dict:
            service = get_recording_service()
            if not service:
                raise HTTPException(status_code=404, detail="Recording service not initialized")
            service.stop_recording(camera_id)
            return {"recording": False}