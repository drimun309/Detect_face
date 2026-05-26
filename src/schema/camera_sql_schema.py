"""SQLModel table for cameras (PostgreSQL)."""

from typing import Optional

from sqlmodel import Field, SQLModel


class CameraSqlSchema(SQLModel, table=True):
    __tablename__ = "cameras"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    ip: str = Field(max_length=128)
    port: int = Field(default=554)
    username: Optional[str] = Field(default=None, max_length=128)
    password: Optional[str] = Field(default=None, max_length=256)
    protocol: str = Field(default="rtsp", max_length=16)
    path: str = Field(default="/Streaming/Channels/101", max_length=255)
    enabled: bool = Field(default=True)
    roi_enabled: bool = Field(default=False)
    rois: str = Field(default="[]")
