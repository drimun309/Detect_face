"""ROI work/idle statistics schemas."""

from pydantic import BaseModel, Field


class RoiDailyZoneStats(BaseModel):
    roi_index: int
    roi_key: str
    work_seconds: float = 0
    idle_seconds: float = 0
    standby_seconds: float = 0


class RoiDailyStatsRow(BaseModel):
    date: str
    work_seconds: float = 0
    idle_seconds: float = 0
    standby_seconds: float = 0
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
