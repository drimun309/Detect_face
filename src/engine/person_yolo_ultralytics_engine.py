"""Ultralytics YOLO (.pt) person detector with CUDA/CPU."""

from __future__ import annotations

from pathlib import Path
from typing import List

import cv2
import numpy as np

from src.schema.yolo_schema import YoloResultSchema
from src.utils.logger import get_logger

log = get_logger()


class PersonYoloUltralyticsEngine:
    """Person detection via Ultralytics YOLO PyTorch weights (.pt)."""

    def __init__(
        self,
        model_path: str,
        device: str = "cuda",
        person_class_idx: int = 0,
        min_box_area_ratio: float = 0.0008,
        max_box_area_ratio: float = 0.7,
    ) -> None:
        self.model_path = Path(model_path)
        self.requested_device = device
        self.person_class_idx = person_class_idx
        self.min_box_area_ratio = min_box_area_ratio
        self.max_box_area_ratio = max_box_area_ratio
        self.model = None
        self.device: str | int = "cpu"

    def setup(self) -> None:
        from ultralytics import YOLO

        if not self.model_path.exists():
            raise FileNotFoundError(f"Person model not found: {self.model_path}")

        self.device = self._resolve_device(self.requested_device)
        log.info(f"Loading person YOLO (.pt): {self.model_path} on device={self.device}")
        self.model = YOLO(str(self.model_path))
        # warmup
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model.predict(
            dummy,
            conf=0.25,
            classes=[self.person_class_idx],
            verbose=False,
            device=self.device,
        )
        log.info("Ultralytics person detector ready")

    @staticmethod
    def _resolve_device(requested: str) -> str | int:
        import torch

        if requested == "gpu" and torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            log.info(f"CUDA available: {name}")
            return 0
        if requested == "gpu":
            log.warning("GPU requested but CUDA unavailable, using CPU for YOLOv8")
        return "cpu"

    def predict(
        self, imgs: List[np.ndarray], conf: float = 0.25, nms: float = 0.45
    ) -> List[YoloResultSchema]:
        if self.model is None:
            raise RuntimeError("PersonYoloUltralyticsEngine.setup() was not called")

        results: List[YoloResultSchema] = []
        for img_rgb in imgs:
            bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            pred = self.model.predict(
                bgr,
                conf=conf,
                iou=nms,
                classes=[self.person_class_idx],
                verbose=False,
                device=self.device,
            )[0]
            boxes, scores = self._parse_boxes(pred, bgr.shape[1], bgr.shape[0])
            results.append(
                YoloResultSchema(
                    boxes=boxes,
                    scores=scores,
                    categories=["person"] * len(boxes),
                )
            )
        return results

    def _parse_boxes(self, pred, width: int, height: int) -> tuple[list[list[int]], list[float]]:
        if pred.boxes is None or len(pred.boxes) == 0:
            return [], []

        frame_area = float(max(width, 1) * max(height, 1))
        min_area = frame_area * self.min_box_area_ratio
        max_area = frame_area * self.max_box_area_ratio

        boxes: list[list[int]] = []
        scores: list[float] = []
        for box in pred.boxes:
            xyxy = box.xyxy[0].detach().cpu().numpy()
            score = float(box.conf[0].detach().cpu().item())
            ix1 = int(round(float(xyxy[0])))
            iy1 = int(round(float(xyxy[1])))
            ix2 = int(round(float(xyxy[2])))
            iy2 = int(round(float(xyxy[3])))
            bw = ix2 - ix1
            bh = iy2 - iy1
            if bw < 16 or bh < 24:
                continue
            area = float(bw * bh)
            if area < min_area or area > max_area:
                continue
            aspect = bh / max(bw, 1)
            if aspect < 0.35 or aspect > 5.0:
                continue
            boxes.append([ix1, iy1, ix2, iy2])
            scores.append(score)
        return boxes, scores
