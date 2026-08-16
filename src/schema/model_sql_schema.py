"""SQLModel tables for detection models and camera assignments."""

from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class DetectionModelSqlSchema(SQLModel, table=True):
    __tablename__ = "detection_models"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120, index=True)
    code: str = Field(max_length=80, unique=True, index=True)
    task: str = Field(max_length=40, index=True)
    backend: str = Field(max_length=40)
    path: str = Field(max_length=500)
    enabled: bool = Field(default=True)
    builtin: bool = Field(default=False)
    config: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CameraModelSqlSchema(SQLModel, table=True):
    __tablename__ = "camera_models"
    __table_args__ = (
        UniqueConstraint("camera_id", "model_id", name="uq_camera_model"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    camera_id: int = Field(foreign_key="cameras.id", index=True)
    model_id: int = Field(foreign_key="detection_models.id", index=True)
    enabled: bool = Field(default=True)
    config: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.now)

