"""Recording API endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from src.schema.roi_timeline_schema import RoiTimelineResponse, TimelineShift
from src.schema.settings_schema import RecordingSettingsSchema
from src.services.recording_service import get_recording_service
from src.services.recording_settings_store import RecordingSettingsStore
from src.services.roi_timer_store import RoiTimerStore
from src.services.settings_store import SettingsStore
from src.streaming.stream_manager import get_stream_manager


class RecordingApi:
    def __init__(
        self,
        store: RecordingSettingsStore,
        roi_timer_store: RoiTimerStore | None = None,
        settings_store: SettingsStore | None = None,
    ) -> None:
        self.store = store
        self.roi_timer_store = roi_timer_store
        self.settings_store = settings_store
        self.router = APIRouter()
        self.setup()

    @staticmethod
    def _shift_meta(settings: RecordingSettingsSchema) -> TimelineShift:
        sh = settings.shift
        start_sec = 0
        end_sec = 0
        try:
            start_sec = (
                datetime.strptime(sh.start_time, "%H:%M").hour * 3600
                + datetime.strptime(sh.start_time, "%H:%M").minute * 60
            )
            end_sec = (
                datetime.strptime(sh.end_time, "%H:%M").hour * 3600
                + datetime.strptime(sh.end_time, "%H:%M").minute * 60
            )
        except ValueError:
            pass
        return TimelineShift(
            enabled=sh.enabled,
            start_time=sh.start_time,
            end_time=sh.end_time,
            start_sec=start_sec,
            end_sec=end_sec,
        )

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

        @self.router.get(
            "/recordings/{camera_id}/{camera_name}/{date}/timeline",
            response_model=RoiTimelineResponse,
        )
        async def get_recording_timeline(
            camera_id: int,
            camera_name: str,
            date: str,
            from_ts: float | None = Query(None, description="Начало интервала (unix)"),
            to_ts: float | None = Query(None, description="Конец интервала (unix)"),
        ) -> RoiTimelineResponse:
            store = self.roi_timer_store
            if store is None:
                try:
                    store = get_stream_manager().roi_timer_store
                except RuntimeError:
                    store = None
            switch_sec = 60.0
            if self.settings_store is not None:
                switch_sec = self.settings_store.get().roi_timer_switch_sec
            if store is not None:
                raw = store.get_timeline(
                    camera_id, date, from_ts, to_ts, switch_sec=switch_sec
                )
            else:
                raw = {
                    "camera_id": camera_id,
                    "date": date,
                    "range_start": 0,
                    "range_end": 0,
                    "day_end": 0,
                    "zones": [],
                    "events_in_range": 0,
                    "timezone": "UTC",
                }

            rec = get_recording_service()
            settings = rec.settings if rec else self.store.get()
            clips = []
            if rec:
                clips = rec.build_clips_for_timeline(camera_id, camera_name, date)

            return RoiTimelineResponse(
                camera_id=camera_id,
                date=date,
                range_start=raw["range_start"],
                range_end=raw["range_end"],
                day_end=float(raw.get("day_end") or raw["range_end"]),
                shift=self._shift_meta(settings),
                zones=raw["zones"],
                clips=clips,
                events_in_range=int(raw.get("events_in_range") or 0),
                timezone=str(raw.get("timezone") or "UTC"),
            )

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