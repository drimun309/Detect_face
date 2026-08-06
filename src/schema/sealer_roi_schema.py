"""ROI ручки запайщика для подсчёта циклов упаковки."""

from pydantic import BaseModel, Field


class SealerRoiConfig(BaseModel):
    model_config = {"extra": "ignore"}

    enabled: bool = False
    x: float = Field(0.0, ge=0.0, le=1.0)
    y: float = Field(0.0, ge=0.0, le=1.0)
    w: float = Field(0.0, ge=0.0, le=1.0)
    h: float = Field(0.0, ge=0.0, le=1.0)
    spike_thresh: float = Field(20.0, ge=0.5, le=200.0)
    rest_thresh: float = Field(-15.0, ge=-100.0, le=80.0)
    cooldown_frames: int = Field(8, ge=1, le=120)


class SealerRoiResponse(SealerRoiConfig):
    cycle_count: int = 0
    cycles_today: int = 0
    activity: float = 0.0
