"""People-hours zone schemas."""

from pydantic import BaseModel, Field


class PeopleZonePoint(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class PeopleZoneConfig(BaseModel):
    model_config = {"extra": "ignore"}

    enabled: bool = False
    polygon: list[PeopleZonePoint] = Field(default_factory=list)
    max_workers: int = Field(3, ge=1, le=3)


class PeopleZoneResponse(PeopleZoneConfig):
    current_workers: int = 0
    seconds_0_workers: float = 0
    seconds_1_worker: float = 0
    seconds_2_workers: float = 0
    seconds_3_workers: float = 0
    person_seconds: float = 0
