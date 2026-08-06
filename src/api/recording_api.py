"""Recording API endpoints."""

from datetime import datetime

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from src.schema.sealer_stats_schema import (
    SealerDailyRangeResponse,
    SealerStatDatesResponse,
)
from src.schema.people_zone_stats_schema import (
    PeopleZoneDailyRangeResponse,
    PeopleZoneStatDatesResponse,
    PeopleZoneTimelineResponse,
)
from src.schema.roi_stats_schema import (
    RoiDailyStatsRangeResponse,
    RoiStatDatesResponse,
    RoiWorkersTimelineResponse,
    RoiWorkersTimelineZone,
)
from src.schema.roi_timeline_schema import RoiTimelineResponse, TimelineShift
from src.schema.settings_schema import RecordingSettingsSchema
from src.services.camera_store import CameraStore
from src.services.people_counter_store import PeopleCounterStore
from src.services.roi_people_counter_store import RoiPeopleCounterStore, TZ, VIEW_START_HOUR, VIEW_END_HOUR
from src.services.recording_service import get_recording_service
from src.services.recording_settings_store import RecordingSettingsStore
from src.services.roi_timer_store import RoiTimerStore
from src.services.settings_store import SettingsStore
from src.streaming.stream_manager import get_stream_manager
from src.utils.range_file import video_file_response


class RecordingApi:
    def __init__(
        self,
        store: RecordingSettingsStore,
        roi_timer_store: RoiTimerStore | None = None,
        settings_store: SettingsStore | None = None,
        camera_store: CameraStore | None = None,
    ) -> None:
        self.store = store
        self.roi_timer_store = roi_timer_store
        self.settings_store = settings_store
        self.camera_store = camera_store
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

    def _roi_timer_store(self) -> RoiTimerStore | None:
        store = self.roi_timer_store
        if store is None:
            try:
                store = get_stream_manager().roi_timer_store
            except RuntimeError:
                store = None
        return store

    def _people_counter_store(self) -> PeopleCounterStore | None:
        try:
            return get_stream_manager().people_counter_store
        except RuntimeError:
            return None

    def _roi_people_counter_store(self) -> RoiPeopleCounterStore | None:
        try:
            return get_stream_manager().roi_people_counter_store
        except RuntimeError:
            return None

    def _camera_has_people_zone(self, camera_id: int) -> bool:
        store = self.camera_store
        if store is None:
            try:
                store = get_stream_manager().camera_store
            except RuntimeError:
                store = None
        if store is None:
            return True
        enabled, polygon, _max_workers = store.get_people_zone_runtime(camera_id)
        return enabled and len(polygon) >= 3

    def _sealer_counter_store(self):
        try:
            return get_stream_manager().sealer_counter_store
        except RuntimeError:
            return None

    def _camera_has_sealer(self, camera_id: int) -> bool:
        store = self.camera_store
        if store is None:
            try:
                store = get_stream_manager().camera_store
            except RuntimeError:
                store = None
        if store is None:
            return False
        enabled, *_rest = store.get_sealer_roi_runtime(camera_id)
        camera = store.get(camera_id)
        rod_pose_enabled = bool(getattr(camera, "rod_pose_enabled", False)) if camera else False
        return bool(enabled or rod_pose_enabled)

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
            "/roi-stats/{camera_id}/dates",
            response_model=RoiStatDatesResponse,
        )
        async def get_roi_stat_dates(camera_id: int) -> RoiStatDatesResponse:
            store = self._roi_timer_store()
            people_store = self._roi_people_counter_store()
            dates: set[str] = set()
            if store is not None:
                dates.update(store.get_stat_dates(camera_id))
            if people_store is not None:
                dates.update(people_store.get_stat_dates(camera_id))
            return RoiStatDatesResponse(
                camera_id=camera_id, dates=sorted(dates)
            )

        @self.router.get(
            "/roi-stats/{camera_id}/daily",
            response_model=RoiDailyStatsRangeResponse,
        )
        async def get_roi_daily_stats(
            camera_id: int,
            from_date: str = Query(..., alias="from", description="YYYY-MM-DD"),
            to_date: str = Query(..., alias="to", description="YYYY-MM-DD"),
        ) -> RoiDailyStatsRangeResponse:
            store = self._roi_timer_store()
            if store is None:
                return RoiDailyStatsRangeResponse(
                    camera_id=camera_id,
                    from_date=from_date,
                    to_date=to_date,
                    timezone="UTC",
                    days=[],
                )
            raw = store.get_daily_stats_range(camera_id, from_date, to_date)
            people_store = self._roi_people_counter_store()
            if people_store is not None:
                raw = people_store.merge_into_daily_stats(raw)
            return RoiDailyStatsRangeResponse(**raw)

        @self.router.get(
            "/roi-stats/{camera_id}/{date}/workers-timeline",
            response_model=RoiWorkersTimelineResponse,
        )
        async def get_roi_workers_timeline(
            camera_id: int,
            date: str,
        ) -> RoiWorkersTimelineResponse:
            people_store = self._roi_people_counter_store()
            if people_store is None:
                return RoiWorkersTimelineResponse(camera_id=camera_id, date=date)
            zones_raw = people_store.get_timelines_for_camera(camera_id, date)
            range_start = 0.0
            range_end = 0.0
            if zones_raw:
                parts = date.split("-")
                if len(parts) == 3:
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    start = datetime(y, m, d, VIEW_START_HOUR, 0, 0, tzinfo=TZ)
                    end = datetime(y, m, d, VIEW_END_HOUR, 0, 0, tzinfo=TZ)
                    range_start = start.timestamp()
                    range_end = end.timestamp()
            zones = [RoiWorkersTimelineZone(**z) for z in zones_raw]
            return RoiWorkersTimelineResponse(
                camera_id=camera_id,
                date=date,
                range_start=range_start,
                range_end=range_end,
                timezone=str(TZ),
                zones=zones,
            )

        @self.router.get(
            "/roi-stats/{camera_id}/{date}/timeline",
            response_model=RoiTimelineResponse,
        )
        async def get_roi_stat_timeline(
            camera_id: int,
            date: str,
            from_ts: float | None = Query(None, description="Начало интервала (unix)"),
            to_ts: float | None = Query(None, description="Конец интервала (unix)"),
        ) -> RoiTimelineResponse:
            store = self._roi_timer_store()
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
            return RoiTimelineResponse(
                camera_id=camera_id,
                date=date,
                range_start=raw["range_start"],
                range_end=raw["range_end"],
                day_end=float(raw.get("day_end") or raw["range_end"]),
                shift=self._shift_meta(settings),
                zones=raw["zones"],
                clips=[],
                events_in_range=int(raw.get("events_in_range") or 0),
                timezone=str(raw.get("timezone") or "UTC"),
            )

        @self.router.get(
            "/people-zone-stats/{camera_id}/dates",
            response_model=PeopleZoneStatDatesResponse,
        )
        async def get_people_zone_stat_dates(
            camera_id: int,
        ) -> PeopleZoneStatDatesResponse:
            if not self._camera_has_people_zone(camera_id):
                return PeopleZoneStatDatesResponse(camera_id=camera_id, dates=[])
            store = self._people_counter_store()
            if store is None:
                return PeopleZoneStatDatesResponse(camera_id=camera_id, dates=[])
            return PeopleZoneStatDatesResponse(**store.get_stat_dates_meta(camera_id))

        @self.router.get(
            "/people-zone-stats/{camera_id}/daily",
            response_model=PeopleZoneDailyRangeResponse,
        )
        async def get_people_zone_daily_stats(
            camera_id: int,
            from_date: str = Query(..., alias="from", description="YYYY-MM-DD"),
            to_date: str = Query(..., alias="to", description="YYYY-MM-DD"),
        ) -> PeopleZoneDailyRangeResponse:
            if not self._camera_has_people_zone(camera_id):
                return PeopleZoneDailyRangeResponse(
                    camera_id=camera_id,
                    from_date=from_date,
                    to_date=to_date,
                    timezone="UTC",
                    days=[],
                )
            store = self._people_counter_store()
            if store is None:
                return PeopleZoneDailyRangeResponse(
                    camera_id=camera_id,
                    from_date=from_date,
                    to_date=to_date,
                    timezone="UTC",
                    days=[],
                )
            raw = store.get_daily_stats_range(camera_id, from_date, to_date)
            return PeopleZoneDailyRangeResponse(**raw)

        @self.router.get(
            "/people-zone-stats/{camera_id}/{date}/timeline",
            response_model=PeopleZoneTimelineResponse,
        )
        async def get_people_zone_timeline(
            camera_id: int,
            date: str,
        ) -> PeopleZoneTimelineResponse:
            if not self._camera_has_people_zone(camera_id):
                return PeopleZoneTimelineResponse(camera_id=camera_id, date=date)
            store = self._people_counter_store()
            if store is None:
                return PeopleZoneTimelineResponse(camera_id=camera_id, date=date)
            raw = store.get_timeline(camera_id, date)
            return PeopleZoneTimelineResponse(**raw)

        @self.router.get(
            "/sealer-stats/{camera_id}/dates",
            response_model=SealerStatDatesResponse,
        )
        async def get_sealer_stat_dates(camera_id: int) -> SealerStatDatesResponse:
            if not self._camera_has_sealer(camera_id):
                return SealerStatDatesResponse(camera_id=camera_id, dates=[])
            store = self._sealer_counter_store()
            if store is None:
                return SealerStatDatesResponse(camera_id=camera_id, dates=[])
            return SealerStatDatesResponse(**store.get_stat_dates_meta(camera_id))

        @self.router.get(
            "/sealer-stats/{camera_id}/daily",
            response_model=SealerDailyRangeResponse,
        )
        async def get_sealer_daily_stats(
            camera_id: int,
            from_date: str = Query(..., alias="from", description="YYYY-MM-DD"),
            to_date: str = Query(..., alias="to", description="YYYY-MM-DD"),
        ) -> SealerDailyRangeResponse:
            if not self._camera_has_sealer(camera_id):
                return SealerDailyRangeResponse(
                    camera_id=camera_id,
                    from_date=from_date,
                    to_date=to_date,
                    timezone="UTC",
                    days=[],
                )
            store = self._sealer_counter_store()
            if store is None:
                return SealerDailyRangeResponse(
                    camera_id=camera_id,
                    from_date=from_date,
                    to_date=to_date,
                    timezone="UTC",
                    days=[],
                )
            raw = store.get_daily_stats_range(camera_id, from_date, to_date)
            return SealerDailyRangeResponse(**raw)

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
            store = self._roi_timer_store()
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
            request: Request,
            camera_id: int,
            camera_name: str,
            date: str,
            filename: str,
        ):
            service = get_recording_service()
            if not service:
                raise HTTPException(status_code=404, detail="Recording service not initialized")
            path = Path(service.get_file_path(camera_id, camera_name, date, filename))
            if not path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            try:
                return video_file_response(request, path)
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="File not found") from None

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