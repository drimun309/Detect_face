"""API schemas for the detection-model catalog."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ModelTask = Literal["face", "person", "package", "pose", "custom"]
ModelBackend = Literal["onnx", "ultralytics", "crowdhuman", "custom"]


class ModelBaseSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    code: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    task: ModelTask
    backend: ModelBackend
    path: str = Field(..., min_length=1, max_length=500)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "code", "path")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ModelCreateSchema(ModelBaseSchema):
    pass


class ModelUpdateSchema(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    code: str | None = Field(None, min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    task: ModelTask | None = None
    backend: ModelBackend | None = None
    path: str | None = Field(None, min_length=1, max_length=500)
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class ModelSchema(ModelBaseSchema):
    id: int
    builtin: bool = False
    exists: bool = False
    created_at: datetime
    updated_at: datetime


class ModelListSchema(BaseModel):
    items: list[ModelSchema]


class CameraModelAssignmentSchema(BaseModel):
    id: int
    camera_id: int
    model_id: int
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    model: ModelSchema


class CameraModelAssignmentListSchema(BaseModel):
    items: list[CameraModelAssignmentSchema]


class CameraModelsUpdateSchema(BaseModel):
    model_ids: list[int] = Field(default_factory=list)

    @field_validator("model_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value):
            raise ValueError("model_ids must contain positive integers")
        return list(dict.fromkeys(value))
