"""YOLO ONNX person detector engine (YOLO26 end2end + YOLOv5 layouts)."""

from __future__ import annotations

from typing import List

import cv2
import numpy as np

from src.engine.onnx_engine import CommonOnnxEngine
from src.schema.yolo_schema import YoloResultSchema


class PersonYoloOnnxEngine(CommonOnnxEngine):
    """ONNX Runtime wrapper for COCO YOLO person detection (class 0)."""

    def __init__(
        self,
        engine_path: str,
        provider: str = "cpu",
        person_class_idx: int = 0,
        min_box_area_ratio: float = 0.0008,
        max_box_area_ratio: float = 0.7,
    ) -> None:
        super().__init__(engine_path, provider)
        self.person_class_idx = person_class_idx
        self.min_box_area_ratio = min_box_area_ratio
        self.max_box_area_ratio = max_box_area_ratio

    def predict(
        self, imgs: List[np.ndarray], conf: float = 0.25, nms: float = 0.45
    ) -> List[YoloResultSchema]:
        results: List[YoloResultSchema] = []
        for img in imgs:
            input_blob, ratio, pad, orig_w, orig_h = self._preprocess(img)
            outputs = self.engine.run(None, {self.metadata[0].input_name: input_blob})
            boxes, scores = self._postprocess(outputs, ratio, pad, orig_w, orig_h, conf, nms)
            results.append(
                YoloResultSchema(
                    boxes=boxes,
                    scores=scores,
                    categories=["person"] * len(boxes),
                )
            )
        return results

    def _preprocess(
        self, img_rgb: np.ndarray
    ) -> tuple[np.ndarray, float, tuple[float, float], int, int]:
        src_h, src_w = img_rgb.shape[:2]
        dst_h, dst_w = self.img_shape
        ratio = min(dst_w / src_w, dst_h / src_h)
        new_w, new_h = int(round(src_w * ratio)), int(round(src_h * ratio))
        pad_w, pad_h = (dst_w - new_w) / 2.0, (dst_h - new_h) / 2.0

        resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((dst_h, dst_w, 3), 114, dtype=np.uint8)
        x0, y0 = int(round(pad_w - 0.1)), int(round(pad_h - 0.1))
        canvas[y0 : y0 + new_h, x0 : x0 + new_w] = resized

        blob = canvas.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)[None, ...]
        return blob, ratio, (pad_w, pad_h), src_w, src_h

    def _letterbox_to_orig(
        self,
        x1: np.ndarray,
        y1: np.ndarray,
        x2: np.ndarray,
        y2: np.ndarray,
        ratio: float,
        pad: tuple[float, float],
        orig_w: int,
        orig_h: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        pad_w, pad_h = pad
        x1 = (x1 - pad_w) / ratio
        x2 = (x2 - pad_w) / ratio
        y1 = (y1 - pad_h) / ratio
        y2 = (y2 - pad_h) / ratio
        x1 = np.clip(x1, 0, max(orig_w - 1, 1))
        y1 = np.clip(y1, 0, max(orig_h - 1, 1))
        x2 = np.clip(x2, 0, max(orig_w - 1, 1))
        y2 = np.clip(y2, 0, max(orig_h - 1, 1))
        return x1, y1, x2, y2

    def _filter_boxes(
        self,
        x1: np.ndarray,
        y1: np.ndarray,
        x2: np.ndarray,
        y2: np.ndarray,
        scores: np.ndarray,
        orig_w: int,
        orig_h: int,
    ) -> tuple[list[list[int]], list[float]]:
        frame_area = float(max(orig_w, 1) * max(orig_h, 1))
        min_area = frame_area * self.min_box_area_ratio
        max_area = frame_area * self.max_box_area_ratio

        out_boxes: list[list[int]] = []
        out_scores: list[float] = []
        for ax1, ay1, ax2, ay2, score in zip(x1, y1, x2, y2, scores):
            ix1 = int(round(float(ax1)))
            iy1 = int(round(float(ay1)))
            ix2 = int(round(float(ax2)))
            iy2 = int(round(float(ay2)))
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
            out_boxes.append([ix1, iy1, ix2, iy2])
            out_scores.append(float(score))
        return out_boxes, out_scores

    def _postprocess(
        self,
        outputs: list[np.ndarray],
        ratio: float,
        pad: tuple[float, float],
        orig_w: int,
        orig_h: int,
        conf: float,
        nms: float,
    ) -> tuple[list[list[int]], list[float]]:
        pred = outputs[0]
        if pred.ndim == 3:
            pred = pred[0]
        if pred.ndim != 2:
            return [], []

        if pred.shape[0] in (84, 85) and pred.shape[1] > pred.shape[0]:
            pred = pred.transpose(1, 0)

        # YOLO26 end2end: [x1, y1, x2, y2, score, class] in letterbox 640 space
        if pred.shape[1] == 6:
            raw_boxes = pred[:, :4].astype(np.float32)
            raw_scores = pred[:, 4].astype(np.float32)
            raw_classes = np.rint(pred[:, 5]).astype(np.int32)

            keep = (
                (raw_scores >= conf)
                & (raw_classes == int(self.person_class_idx))
                & (raw_boxes[:, 2] > raw_boxes[:, 0] + 4)
                & (raw_boxes[:, 3] > raw_boxes[:, 1] + 4)
            )
            if not np.any(keep):
                return [], []

            x1, y1, x2, y2 = raw_boxes[keep].T
            scores = raw_scores[keep]
            x1, y1, x2, y2 = self._letterbox_to_orig(x1, y1, x2, y2, ratio, pad, orig_w, orig_h)
            return self._filter_boxes(x1, y1, x2, y2, scores, orig_w, orig_h)

        if pred.shape[1] < 6:
            return [], []

        boxes_xywh = pred[:, :4]
        if pred.shape[1] >= 85:
            obj = pred[:, 4]
            cls = pred[:, 5 + self.person_class_idx]
            class_scores = obj * cls
        else:
            if pred.shape[1] <= self.person_class_idx + 4:
                return [], []
            class_scores = pred[:, 4 + self.person_class_idx]
        keep = class_scores >= conf
        if not np.any(keep):
            return [], []

        boxes_xywh = boxes_xywh[keep]
        class_scores = class_scores[keep]

        x = boxes_xywh[:, 0]
        y = boxes_xywh[:, 1]
        w = boxes_xywh[:, 2]
        h = boxes_xywh[:, 3]
        x1 = x - w / 2.0
        y1 = y - h / 2.0
        x2 = x + w / 2.0
        y2 = y + h / 2.0

        x1, y1, x2, y2 = self._letterbox_to_orig(x1, y1, x2, y2, ratio, pad, orig_w, orig_h)

        boxes_for_nms = []
        for a, b, c, d in zip(x1, y1, x2, y2):
            boxes_for_nms.append([float(a), float(b), float(c - a), float(d - b)])
        scores_list = class_scores.astype(float).tolist()

        idxs = cv2.dnn.NMSBoxes(boxes_for_nms, scores_list, score_threshold=conf, nms_threshold=nms)
        if idxs is None or len(idxs) == 0:
            return [], []
        flat_idxs = [int(i[0]) if isinstance(i, (list, tuple, np.ndarray)) else int(i) for i in idxs]

        fx1 = np.array([x1[i] for i in flat_idxs])
        fy1 = np.array([y1[i] for i in flat_idxs])
        fx2 = np.array([x2[i] for i in flat_idxs])
        fy2 = np.array([y2[i] for i in flat_idxs])
        fscores = np.array([scores_list[i] for i in flat_idxs])
        return self._filter_boxes(fx1, fy1, fx2, fy2, fscores, orig_w, orig_h)
