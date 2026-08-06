"""YOLO seg-детектор палки: маска по точкам датасета -> ось S/E -> угол."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    contour: list[tuple[float, float]] = field(default_factory=list)


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
        log.info(f"Loading rod seg YOLO: {self.model_path} on device={self.device}")
        self.model = YOLO(str(self.model_path))
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model.predict(
            dummy,
            conf=0.25,
            imgsz=640,
            retina_masks=True,
            verbose=False,
            device=self.device,
        )
        log.info("Rod seg detector ready")

    @staticmethod
    def _segment_axis_ends(
        poly: np.ndarray,
    ) -> tuple[tuple[float, float], tuple[float, float]] | None:
        """Диагональ OBB маски: top/bottom по экрану (как в palka_seg_roi)."""
        if poly is None or len(poly) < 2:
            return None
        pts = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
        if len(pts) < 2:
            return None
        box = cv2.boxPoints(cv2.minAreaRect(pts))
        diagonals: list[tuple[tuple[float, float], tuple[float, float]]] = []
        for i, j in ((0, 2), (1, 3)):
            a = (float(box[i][0]), float(box[i][1]))
            b = (float(box[j][0]), float(box[j][1]))
            diagonals.append((a, b))
        if not diagonals:
            return None
        a, b = max(diagonals, key=lambda se: abs(se[0][1] - se[1][1]))
        return (a, b) if a[1] <= b[1] else (b, a)

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
            retina_masks=True,
            conf=conf,
            imgsz=imgsz,
            verbose=False,
            device=self.device,
        )[0]
        if pred.boxes is None or len(pred.boxes) == 0:
            return None

        best_idx = 0
        best_score = -1.0
        for idx, box in enumerate(pred.boxes):
            score = float(box.conf[0].detach().cpu().item())
            if score > best_score:
                best_score = score
                best_idx = idx

        # Seg-маска датасета: полигон по точкам разметки.
        if pred.masks is not None and pred.masks.xy is not None and best_idx < len(pred.masks.xy):
            poly = np.asarray(pred.masks.xy[best_idx], dtype=np.float32).reshape(-1, 2)
            if len(poly) >= 2:
                ends = self._segment_axis_ends(poly)
                if ends is not None:
                    top, bottom = ends
                    return RodPoseDetection(
                        top=top,
                        bottom=bottom,
                        angle_deg=rod_angle_deg(top, bottom),
                        score=best_score,
                        keypoint_conf=(best_score, best_score),
                        contour=[(float(x), float(y)) for x, y in poly.tolist()],
                    )

        # Fallback: старая pose-модель с keypoints.
        if pred.keypoints is None or len(pred.keypoints.xy) <= best_idx:
            return None
        xy = pred.keypoints.xy[best_idx].detach().cpu().numpy()
        kconf = None
        if pred.keypoints.conf is not None and len(pred.keypoints.conf) > best_idx:
            kconf = pred.keypoints.conf[best_idx].detach().cpu().numpy()
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
        return RodPoseDetection(
            top=top,
            bottom=bottom,
            angle_deg=rod_angle_deg(top, bottom),
            score=best_score,
            keypoint_conf=(pts[0][2], pts[-1][2]),
            contour=[],
        )
