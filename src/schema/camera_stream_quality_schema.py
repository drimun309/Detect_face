"""Качество annotated-потока на камере."""

from pydantic import BaseModel, Field


class CameraStreamQualityUpdate(BaseModel):
    preset: str = Field(
        ...,
        description="global | 640x360 | 960x540 | 1280x720 | 1920x1080 | 2560x1440",
    )


class CameraStreamQualityResponse(BaseModel):
    camera_id: int
    preset: str
    stream_width: int | None = None
    stream_height: int | None = None
    effective_width: int
    effective_height: int
