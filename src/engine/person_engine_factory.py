"""Factory for person detection backends (ONNX or Ultralytics .pt)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.engine.person_yolo_onnx_engine import PersonYoloOnnxEngine
from src.engine.person_yolo_ultralytics_engine import PersonYoloUltralyticsEngine
from src.schema.yolo_schema import YoloResultSchema


class PersonDetector(Protocol):
    def setup(self) -> None: ...
    def predict(
        self, imgs: list, conf: float = 0.25, nms: float = 0.45
    ) -> list[YoloResultSchema]: ...


def create_person_engine(model_path: str, provider: str) -> PersonDetector:
    path = Path(model_path)
    suffix = path.suffix.lower()
    if suffix == ".pt":
        return PersonYoloUltralyticsEngine(model_path=str(path), device=provider)
    return PersonYoloOnnxEngine(engine_path=str(path), provider=provider)
