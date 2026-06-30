"""People zone (whole area) statistics schemas."""

from pydantic import BaseModel, Field


class PeopleZoneDailyRow(BaseModel):
    date: str
    person_seconds: float = 0
    seconds_0_workers: float = 0
    seconds_1_worker: float = 0
    seconds_2_workers: float = 0
    seconds_3_workers: float = 0
    max_workers: int = 3


class PeopleZoneDailyRangeResponse(BaseModel):
    camera_id: int
    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")
    timezone: str = "UTC"
    server_today: str = ""
    view_start_hour: int = 7
    view_end_hour: int = 19
    days: list[PeopleZoneDailyRow] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class PeopleZoneStatDatesResponse(BaseModel):
    camera_id: int
    dates: list[str] = Field(default_factory=list)
    server_today: str = ""
    timezone: str = "UTC"


class PeopleZoneTimelineSegment(BaseModel):
    start: float
    end: float
    workers: int = 0


class PeopleZoneTimelineResponse(BaseModel):
    camera_id: int
    date: str
    range_start: float = 0
    range_end: float = 0
    timezone: str = "UTC"
    person_seconds: float = 0
    seconds_0_workers: float = 0
    seconds_1_worker: float = 0
    seconds_2_workers: float = 0
    seconds_3_workers: float = 0
    max_workers: int = 3
    segments: list[PeopleZoneTimelineSegment] = Field(default_factory=list)
