"""Schemas for camera management API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CameraBaseSchema(BaseModel):
    """Shared fields for camera configuration."""

    name: str = Field(..., min_length=1, max_length=100)
    ip: str = Field(..., min_length=1, max_length=128)
    port: int = Field(554, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, max_length=256)
    protocol: Literal["rtsp"] = "rtsp"
    path: str = Field("/Streaming/Channels/101", min_length=1, max_length=255)
    enabled: bool = True

    @field_validator("path")
    @classmethod
    def ensure_path_prefix(cls, value: str) -> str:
        value = value.strip()
        return value if value.startswith("/") else f"/{value}"


class CameraCreateSchema(CameraBaseSchema):
    """Payload for camera creation."""


class CameraUpdateSchema(BaseModel):
    """Payload for camera update."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    ip: Optional[str] = Field(None, min_length=1, max_length=128)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=128)
    password: Optional[str] = Field(None, max_length=256)
    protocol: Optional[Literal["rtsp"]] = None
    path: Optional[str] = Field(None, min_length=1, max_length=255)
    enabled: Optional[bool] = None

    @field_validator("path")
    @classmethod
    def ensure_path_prefix(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value if value.startswith("/") else f"/{value}"


class CameraSchema(CameraBaseSchema):
    """Camera record returned by API."""

    id: int


class CameraListSchema(BaseModel):
    """List response."""

    items: list[CameraSchema]
