"""YOLOv5 CrowdHuman person detector (body + head) via torch.hub."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import List

import cv2
import numpy as np
import torch

from src.schema.yolo_schema import YoloResultSchema
from src.utils.logger import get_logger

log = get_logger()

_CLS_BODY = 0
_CLS_HEAD = 1
_CATEGORY_BY_CLS = {_CLS_BODY: "person", _CLS_HEAD: "head"}
_DET_TYPES = frozenset({"both", "body", "head"})


class PersonYoloCrowdHumanEngine:
    """Person detection via YOLOv5 CrowdHuman weights (.pt)."""

    def __init__(
        self,
        model_path: str,
        device: str = "cpu",
        input_size: int = 640,
        min_box_area_ratio: float = 0.0008,
        max_box_area_ratio: float = 0.7,
    ) -> None:
        self.model_path = Path(model_path)
        self.requested_device = device
        self.input_size = input_size
        self.min_box_area_ratio = min_box_area_ratio
        self.max_box_area_ratio = max_box_area_ratio
        self.model = None
        self.device = "cpu"
        self.detection_type = "both"

    def setup(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"CrowdHuman model not found: {self.model_path}")

        self.device = self._resolve_device(self.requested_device)
        log.info(
            f"Loading YOLOv5 CrowdHuman: {self.model_path} on device={self.device}"
        )

        original_torch_load = torch.load

        def _patched_torch_load(*args, **kwargs):
            kwargs["weights_only"] = False
            return original_torch_load(*args, **kwargs)

        torch.load = _patched_torch_load
        try:
            hub_kwargs: dict = {"path": str(self.model_path), "trust_repo": True}
            try:
                if "trust_repo" not in inspect.signature(torch.hub.load).parameters:
                    hub_kwargs.pop("trust_repo", None)
            except (TypeError, ValueError):
                hub_kwargs.pop("trust_repo", None)

            self.model = torch.hub.load(
                "ultralytics/yolov5",
                "custom",
                **hub_kwargs,
            )
        finally:
            torch.load = original_torch_load

        self.model.conf = 0.25
        self.model.iou = 0.45
        self.model.max_det = 300
        self._apply_model_classes()
        self.model.to(self.device)

        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model(dummy, size=self.input_size)
        log.info("YOLOv5 CrowdHuman detector ready")

    def set_detection_type(self, detection_type: str) -> None:
        if detection_type not in _DET_TYPES:
            detection_type = "both"
        self.detection_type = detection_type
        self._apply_model_classes()
        log.info(f"CrowdHuman detection type: {detection_type}")

    def _active_classes(self) -> list[int]:
        if self.detection_type == "body":
            return [_CLS_BODY]
        if self.detection_type == "head":
            return [_CLS_HEAD]
        return [_CLS_BODY, _CLS_HEAD]

    def _apply_model_classes(self) -> None:
        if self.model is not None:
            self.model.classes = self._active_classes()

    @staticmethod
    def _resolve_device(requested: str) -> str:
        if requested == "gpu" and torch.cuda.is_available():
            log.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            return "cuda"
        if requested == "gpu":
            log.warning("GPU requested but CUDA unavailable, using CPU for CrowdHuman")
        return "cpu"

    def predict(
        self, imgs: List[np.ndarray], conf: float = 0.25, nms: float = 0.45
    ) -> List[YoloResultSchema]:
        if self.model is None:
            raise RuntimeError("PersonYoloCrowdHumanEngine.setup() was not called")

        self.model.conf = conf
        self.model.iou = nms
        self._apply_model_classes()

        results: List[YoloResultSchema] = []
        for img_rgb in imgs:
            bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            pred = self.model(bgr, size=self.input_size)
            boxes, scores, categories = self._parse_boxes(
                pred, bgr.shape[1], bgr.shape[0]
            )
            results.append(
                YoloResultSchema(boxes=boxes, scores=scores, categories=categories)
            )
        return results

    def _parse_boxes(
        self, pred, width: int, height: int
    ) -> tuple[list[list[int]], list[float], list[str]]:
        if pred is None or len(pred.xyxy) == 0:
            return [], [], []

        boxes_tensor = pred.xyxy[0]
        if len(boxes_tensor) == 0:
            return [], [], []

        frame_area = float(max(width, 1) * max(height, 1))
        min_area = frame_area * self.min_box_area_ratio
        max_area = frame_area * self.max_box_area_ratio

        boxes: list[list[int]] = []
        scores: list[float] = []
        categories: list[str] = []
        for row in boxes_tensor.cpu().numpy():
            x1, y1, x2, y2 = row[:4]
            score = float(row[4])
            cls = int(row[5]) if len(row) > 5 else _CLS_BODY

            ix1 = int(round(float(x1)))
            iy1 = int(round(float(y1)))
            ix2 = int(round(float(x2)))
            iy2 = int(round(float(y2)))
            bw = ix2 - ix1
            bh = iy2 - iy1
            if bw < 12 or bh < 12:
                continue
            area = float(bw * bh)
            if area < min_area or area > max_area:
                continue

            min_h = 16 if cls == _CLS_HEAD else 24
            if bw < 12 or bh < min_h:
                continue

            boxes.append([ix1, iy1, ix2, iy2])
            scores.append(score)
            categories.append(_CATEGORY_BY_CLS.get(cls, "person"))

        return boxes, scores, categories
