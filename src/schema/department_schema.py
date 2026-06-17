"""Schemas for department management API."""

from pydantic import BaseModel, Field


class DepartmentCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class DepartmentSchema(BaseModel):
    id: int
    name: str
    camera_count: int = 0


class DepartmentListSchema(BaseModel):
    items: list[DepartmentSchema]
