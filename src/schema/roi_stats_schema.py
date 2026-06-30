"""ROI work/idle statistics schemas."""

from pydantic import BaseModel, Field


class RoiDailyZoneStats(BaseModel):
    roi_index: int
    roi_key: str
    roi_name: str = ""
    work_seconds: float = 0
    idle_seconds: float = 0
    standby_seconds: float = 0
    max_workers: int = 2
    person_seconds: float = 0
    seconds_0_workers: float = 0
    seconds_1_worker: float = 0
    seconds_2_workers: float = 0


class RoiDailyStatsRow(BaseModel):
    date: str
    work_seconds: float = 0
    idle_seconds: float = 0
    standby_seconds: float = 0
    max_workers: int = 2
    person_seconds: float = 0
    seconds_0_workers: float = 0
    seconds_1_worker: float = 0
    seconds_2_workers: float = 0
    zones: list[RoiDailyZoneStats] = Field(default_factory=list)


class RoiDailyStatsRangeResponse(BaseModel):
    camera_id: int
    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")
    timezone: str = "UTC"
    view_start_hour: int = 7
    view_end_hour: int = 19
    days: list[RoiDailyStatsRow] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class RoiStatDatesResponse(BaseModel):
    camera_id: int
    dates: list[str] = Field(default_factory=list)


class RoiWorkersTimelineSegment(BaseModel):
    start: float
    end: float
    workers: int = 0


class RoiWorkersTimelineZone(BaseModel):
    roi_index: int
    roi_key: str
    roi_name: str = ""
    person_seconds: float = 0
    seconds_0_workers: float = 0
    seconds_1_worker: float = 0
    seconds_2_workers: float = 0
    max_workers: int = 2
    segments: list[RoiWorkersTimelineSegment] = Field(default_factory=list)


class RoiWorkersTimelineResponse(BaseModel):
    camera_id: int
    date: str
    range_start: float = 0
    range_end: float = 0
    timezone: str = "UTC"
    zones: list[RoiWorkersTimelineZone] = Field(default_factory=list)
