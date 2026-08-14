"""Schemas for department management API."""

from pydantic import BaseModel, Field


class DepartmentCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class DepartmentUpdateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class DepartmentSchema(BaseModel):
    id: int
    name: str
    camera_count: int = 0


class DepartmentListSchema(BaseModel):
    items: list[DepartmentSchema]


class DashboardZoneSchema(BaseModel):
    camera_id: int
    camera_name: str
    roi_index: int
    name: str
    work_seconds: float = 0
    idle_seconds: float = 0
    person_seconds: float = 0


class DashboardDepartmentSchema(BaseModel):
    id: int | None = None
    name: str
    camera_count: int = 0
    enabled_camera_count: int = 0
    zone_count: int = 0
    work_seconds: float = 0
    idle_seconds: float = 0
    person_seconds: float = 0
    cycles: int = 0
    packages: int = 0
    zones: list[DashboardZoneSchema] = Field(default_factory=list)


class DashboardSummarySchema(BaseModel):
    date: str
    department_count: int = 0
    camera_count: int = 0
    enabled_camera_count: int = 0
    zone_count: int = 0
    work_seconds: float = 0
    idle_seconds: float = 0
    person_seconds: float = 0
    cycles: int = 0
    packages: int = 0
    departments: list[DashboardDepartmentSchema] = Field(default_factory=list)
