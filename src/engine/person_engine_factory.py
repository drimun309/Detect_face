"""Factory for person detection backends (ONNX, Ultralytics, CrowdHuman)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.engine.package_yolo_ultralytics_engine import PackageYoloUltralyticsEngine
from src.engine.person_yolo_crowdhuman_engine import PersonYoloCrowdHumanEngine
from src.engine.person_yolo_onnx_engine import PersonYoloOnnxEngine
from src.engine.person_yolo_ultralytics_engine import PersonYoloUltralyticsEngine
from src.schema.yolo_schema import YoloResultSchema


class PersonDetector(Protocol):
    def setup(self) -> None: ...
    def predict(
        self, imgs: list, conf: float = 0.25, nms: float = 0.45
    ) -> list[YoloResultSchema]: ...


def _is_crowdhuman_model(path: Path) -> bool:
    name = path.name.lower()
    return "crowdhuman" in name


def _is_package_model(path: Path) -> bool:
    name = path.name.lower()
    return "package_label" in name or "package" in name and "label" in name


def create_person_engine(model_path: str, provider: str) -> PersonDetector:
    path = Path(model_path)
    suffix = path.suffix.lower()
    if suffix == ".pt" and _is_package_model(path):
        return PackageYoloUltralyticsEngine(model_path=str(path), device=provider)
    if suffix == ".pt" and _is_crowdhuman_model(path):
        return PersonYoloCrowdHumanEngine(model_path=str(path), device=provider)
    if suffix == ".pt":
        return PersonYoloUltralyticsEngine(model_path=str(path), device=provider)
    return PersonYoloOnnxEngine(engine_path=str(path), provider=provider)


def apply_crowdhuman_det_type(engine: PersonDetector, detection_type: str) -> None:
    setter = getattr(engine, "set_detection_type", None)
    if callable(setter):
        setter(detection_type)
