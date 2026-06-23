"""Schemas for ROI work/idle timeline API."""

from pydantic import BaseModel, Field


class TimelineSegment(BaseModel):
    start: float = Field(..., description="Unix timestamp (сек)")
    end: float = Field(..., description="Unix timestamp (сек)")
    mode: str = Field(..., description="work | idle | standby")


class TimelineZone(BaseModel):
    roi_index: int
    roi_key: str
    roi_name: str = ""
    segments: list[TimelineSegment] = Field(default_factory=list)
    daily_work_seconds: float = Field(
        0, description="Итого работа за календарный день (roi_timer_daily)"
    )
    daily_idle_seconds: float = Field(
        0, description="Итого простой за календарный день (roi_timer_daily)"
    )
    timeline_source: str = Field(
        "events",
        description="events = журнал смен; hourly = почасовая история",
    )


class TimelineShift(BaseModel):
    enabled: bool = False
    start_time: str = "09:00"
    end_time: str = "18:00"
    start_sec: int = Field(0, description="Секунды от полуночи")
    end_sec: int = Field(0, description="Секунды от полуночи")


class TimelineClip(BaseModel):
    filename: str
    start: float
    end: float


class RoiTimelineResponse(BaseModel):
    camera_id: int
    date: str
    range_start: float
    range_end: float
    day_end: float = Field(
        0, description="Конец календарных суток (unix), для шкалы 24 ч"
    )
    shift: TimelineShift
    zones: list[TimelineZone] = Field(default_factory=list)
    clips: list[TimelineClip] = Field(default_factory=list)
    events_in_range: int = Field(
        0, description="Число смен режима в roi_timer_events за интервал"
    )
    timezone: str = Field("UTC", description="TZ границ календарного дня")
