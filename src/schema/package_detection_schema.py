"""Package detection toggle API schemas."""

from pydantic import BaseModel, Field


class PackageDetectionUpdate(BaseModel):
    enabled: bool = Field(..., description="Включить детекцию пакетов и этикеток на камере")


class PackageRoiCounterItem(BaseModel):
    roi_key: str
    packed_today: int = 0


class PackageDetectionResponse(BaseModel):
    camera_id: int
    package_detection_enabled: bool
    packed_today: int = 0
    packed_by_roi: list[PackageRoiCounterItem] = Field(default_factory=list)
