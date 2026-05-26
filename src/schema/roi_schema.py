"""ROI API schemas."""

from pydantic import BaseModel, Field


class RoiPoint(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class RoiPolygon(BaseModel):
    points: list[RoiPoint] = Field(..., min_length=3)


class RoiUpdate(BaseModel):
    enabled: bool = False
    polygons: list[RoiPolygon] = Field(default_factory=list)


class RoiResponse(BaseModel):
    enabled: bool
    polygons: list[RoiPolygon]
