"""Available person-detection model presets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PersonModelInfo:
    id: str
    path: str
    label_ru: str
    label_en: str
    backend: str


PERSON_MODELS: dict[str, PersonModelInfo] = {
    "yolov8s": PersonModelInfo(
        id="yolov8s",
        path="assets/yolov8s.pt",
        label_ru="YOLOv8s (COCO, человек)",
        label_en="YOLOv8s (COCO person)",
        backend="ultralytics",
    ),
    "crowdhuman_yolov5m": PersonModelInfo(
        id="crowdhuman_yolov5m",
        path="assets/crowdhuman_yolov5m.pt",
        label_ru="YOLOv5 CrowdHuman (тело + голова)",
        label_en="YOLOv5 CrowdHuman (body + head)",
        backend="crowdhuman",
    ),
    "yolo26n": PersonModelInfo(
        id="yolo26n",
        path="assets/yolo26n.onnx",
        label_ru="YOLO26n ONNX",
        label_en="YOLO26n ONNX",
        backend="onnx",
    ),
}

DEFAULT_PERSON_MODEL_ID = "yolov8s"


def infer_person_model_id(model_path: str) -> str:
    path = model_path.lower()
    if "crowdhuman" in path:
        return "crowdhuman_yolov5m"
    if "yolo26" in path:
        return "yolo26n"
    return DEFAULT_PERSON_MODEL_ID


def resolve_person_model_path(model_id: str) -> str:
    info = PERSON_MODELS.get(model_id)
    if info is None:
        info = PERSON_MODELS[DEFAULT_PERSON_MODEL_ID]
    return info.path


def list_person_models() -> list[dict[str, str]]:
    return [
        {
            "id": m.id,
            "path": m.path,
            "label_ru": m.label_ru,
            "label_en": m.label_en,
            "backend": m.backend,
            "exists": Path(m.path).exists(),
        }
        for m in PERSON_MODELS.values()
    ]
