"""Rod / handle YOLO segmentation toggle API schemas."""

from pydantic import BaseModel, Field


class RodPoseUpdate(BaseModel):
    enabled: bool = Field(
        ..., description="Включить YOLO-сегментацию ручки (палки) на камере"
    )


class RodPoseResponse(BaseModel):
    camera_id: int
    rod_pose_enabled: bool
    press_count: int = 0
