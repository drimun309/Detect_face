"""YOLO pose-детектор палки (best_pose.pt)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.utils.logger import get_logger
from src.utils.rod_metrics import rod_angle_deg

log = get_logger()


@dataclass(frozen=True)
class RodPoseDetection:
    top: tuple[float, float]
    bottom: tuple[float, float]
    angle_deg: float
    score: float
    keypoint_conf: tuple[float, float]


class RodPoseEngine:
    def __init__(
        self,
        model_path: str,
        device: str = "cuda",
        min_kpt_conf: float = 0.25,
    ) -> None:
        self.model_path = Path(model_path)
        self.requested_device = device
        self.min_kpt_conf = float(min_kpt_conf)
        self.model = None
        self.device: str | int = "cpu"

    def setup(self) -> None:
        from ultralytics import YOLO

        if not self.model_path.exists():
            raise FileNotFoundError(f"Rod pose model not found: {self.model_path}")

        self.device = self._resolve_device(self.requested_device)
        log.info(f"Loading rod pose YOLO: {self.model_path} on device={self.device}")
        self.model = YOLO(str(self.model_path))
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model.predict(dummy, conf=0.25, verbose=False, device=self.device)
        log.info("Rod pose detector ready")

    @staticmethod
    def _resolve_device(requested: str) -> str | int:
        import torch

        if requested == "gpu" and torch.cuda.is_available():
            log.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            return 0
        if requested == "gpu":
            log.warning("GPU requested but CUDA unavailable, using CPU for rod pose")
        return "cpu"

    def predict(
        self,
        frame_bgr: np.ndarray,
        conf: float = 0.25,
        imgsz: int = 640,
    ) -> RodPoseDetection | None:
        if self.model is None:
            raise RuntimeError("RodPoseEngine.setup() was not called")

        pred = self.model.predict(
            frame_bgr,
            conf=conf,
            imgsz=imgsz,
            verbose=False,
            device=self.device,
        )[0]
        if pred.keypoints is None or pred.boxes is None or len(pred.boxes) == 0:
            return None

        best_idx = 0
        best_score = -1.0
        for idx, box in enumerate(pred.boxes):
            score = float(box.conf[0].detach().cpu().item())
            if score > best_score:
              best_score = score
              best_idx = idx

        xy = pred.keypoints.xy[best_idx].detach().cpu().numpy()
        kconf = None
        if pred.keypoints.conf is not None and len(pred.keypoints.conf) > best_idx:
            kconf = pred.keypoints.conf[best_idx].detach().cpu().numpy()
        if xy.shape[0] < 2:
            return None

        pts: list[tuple[float, float, float]] = []
        for i in range(xy.shape[0]):
            c = float(kconf[i]) if kconf is not None and i < len(kconf) else 1.0
            pts.append((float(xy[i, 0]), float(xy[i, 1]), c))
        pts = [p for p in pts if p[2] >= self.min_kpt_conf]
        if len(pts) < 2:
            return None

        pts.sort(key=lambda p: p[1])
        top = (pts[0][0], pts[0][1])
        bottom = (pts[-1][0], pts[-1][1])
        angle = rod_angle_deg(top, bottom)
        return RodPoseDetection(
            top=top,
            bottom=bottom,
            angle_deg=angle,
            score=best_score,
            keypoint_conf=(pts[0][2], pts[-1][2]),
        )
