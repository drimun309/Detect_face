"""Статистика циклов запайщика."""

from pydantic import BaseModel, Field


class SealerDailyRow(BaseModel):
    date: str
    cycle_count: int = 0


class SealerDailyRangeResponse(BaseModel):
    camera_id: int
    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")
    timezone: str = "UTC"
    server_today: str = ""
    view_start_hour: int = 7
    view_end_hour: int = 19
    days: list[SealerDailyRow] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class SealerStatDatesResponse(BaseModel):
    camera_id: int
    dates: list[str] = Field(default_factory=list)
    server_today: str = ""
    timezone: str = "UTC"
