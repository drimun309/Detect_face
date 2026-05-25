"""Arcface ONNX engine."""

import rootutils

ROOT = rootutils.autosetup()

from pathlib import Path
from typing import List

import cv2
import numpy as np
import onnx

from src.engine.onnx_engine import CommonOnnxEngine
from src.utils.logger import get_logger

log = get_logger()


def _read_input_norm(engine_path: str) -> tuple[float, float]:
    """InsightFace: mxnet models use 0/1, ONNX exports use 127.5/127.5."""
    path = Path(engine_path)
    name = path.name.lower()
    if "mbf" in name or "mobile" in name:
        return 0.0, 255.0

    try:
        model = onnx.load(engine_path)
        find_sub = find_mul = False
        for node in model.graph.node[:8]:
            if node.name.startswith(("Sub", "_minus")):
                find_sub = True
            if node.name.startswith(("Mul", "_mul")):
                find_mul = True
        if find_sub and find_mul:
            return 0.0, 1.0
    except Exception:
        pass

    return 127.5, 127.5


class ArcfaceOnnxEngine(CommonOnnxEngine):
    """Arcface ONNX engine module."""

    def __init__(self, engine_path: str, provider: str = "cpu") -> None:
        super().__init__(engine_path, provider)
        self.input_mean, self.input_std = _read_input_norm(engine_path)

    def predict(self, imgs: List[np.ndarray]) -> List[np.ndarray]:
        """Predict embeddings from image(s). Model supports batch size 1 only."""
        embeddings: List[np.ndarray] = []
        for img in imgs:
            batch = self.preprocess_imgs([img])
            outputs = self.engine.run(None, {self.metadata[0].input_name: batch})
            vector = outputs[0]
            if vector.ndim == 2:
                vector = vector[0]
            embeddings.append(np.array(vector, dtype=np.float32))
        return embeddings

    def preprocess_imgs(self, imgs: List[np.ndarray]) -> np.ndarray:
        dst_h, dst_w = self.img_shape

        if self.input_std == 255.0:
            resized = []
            for img in imgs:
                resized.append(cv2.resize(img, (dst_w, dst_h)))
            batch = np.zeros((len(imgs), 3, dst_h, dst_w), dtype=np.float32)
            for i, img in enumerate(resized):
                batch[i] = img.transpose(2, 0, 1) / 255.0
            return batch

        bgr_imgs = [cv2.cvtColor(cv2.resize(img, (dst_w, dst_h)), cv2.COLOR_RGB2BGR) for img in imgs]
        scale = 1.0 / self.input_std
        return cv2.dnn.blobFromImages(
            bgr_imgs,
            scale,
            (dst_w, dst_h),
            (self.input_mean, self.input_mean, self.input_mean),
            swapRB=False,
        )
