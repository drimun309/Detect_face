"""SCRFD (buffalo_l) face detection ONNX engine."""

import rootutils

ROOT = rootutils.autosetup()

from typing import List, Tuple

import cv2
import numpy as np
import onnxruntime as ort

from src.engine.onnx_engine import CommonOnnxEngine
from src.schema.yolo_schema import YoloResultSchema
from src.utils.logger import get_logger

log = get_logger()

DEFAULT_DET_SIZES = [(128, 128), (640, 640)]


def distance2bbox(points: np.ndarray, distance: np.ndarray) -> np.ndarray:
    x1 = points[:, 0] - distance[:, 0]
    y1 = points[:, 1] - distance[:, 1]
    x2 = points[:, 0] + distance[:, 2]
    y2 = points[:, 1] + distance[:, 3]
    return np.stack([x1, y1, x2, y2], axis=-1)


class ScrfdOnnxEngine(CommonOnnxEngine):
    """InsightFace SCRFD detector (det_10g.onnx from buffalo_l)."""

    def __init__(
        self,
        engine_path: str,
        categories: List[str] | None = None,
        provider: str = "cpu",
        input_size: Tuple[int, int] = (640, 640),
        **_: object,
    ) -> None:
        super().__init__(engine_path, provider)
        self.categories = categories or ["face"]
        self.input_size = input_size
        self.center_cache: dict = {}
        self.nms_thresh = 0.4
        self.det_thresh = 0.5
        self.use_kps = False
        self.batched = False
        self.fmc = 3
        self._feat_stride_fpn = [8, 16, 32]
        self._num_anchors = 2

    def setup(self) -> None:
        log.info("Setup SCRFD ONNX engine...")
        self.engine = ort.InferenceSession(
            str(self.engine_path), providers=self.provider
        )
        self._init_scrfd_vars()
        log.info("SCRFD ONNX engine is ready!")

    def _init_scrfd_vars(self) -> None:
        input_cfg = self.engine.get_inputs()[0]
        input_shape = input_cfg.input_shape if hasattr(input_cfg, "input_shape") else input_cfg.shape
        self.input_name = input_cfg.name
        outputs = self.engine.get_outputs()
        if len(outputs[0].shape) == 3:
            self.batched = True
        self.output_names = [o.name for o in outputs]
        self.input_mean = 127.5
        self.input_std = 128.0

        if len(outputs) == 6:
            self.fmc = 3
            self._feat_stride_fpn = [8, 16, 32]
            self._num_anchors = 2
        elif len(outputs) == 9:
            self.fmc = 3
            self._feat_stride_fpn = [8, 16, 32]
            self._num_anchors = 2
            self.use_kps = True
        elif len(outputs) == 10:
            self.fmc = 5
            self._feat_stride_fpn = [8, 16, 32, 64, 128]
            self._num_anchors = 1
        elif len(outputs) == 15:
            self.fmc = 5
            self._feat_stride_fpn = [8, 16, 32, 64, 128]
            self._num_anchors = 1
            self.use_kps = True

    def predict(
        self, imgs: List[np.ndarray], conf: float = 0.25, nms: float = 0.45
    ) -> List[YoloResultSchema]:
        self.det_thresh = conf
        self.nms_thresh = nms
        results: List[YoloResultSchema] = []
        for img in imgs:
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            dets = self._detect(bgr)
            boxes: List[List[int]] = []
            scores: List[float] = []
            for x1, y1, x2, y2, score in dets:
                boxes.append([int(x1), int(y1), int(x2), int(y2)])
                scores.append(float(score))
            results.append(
                YoloResultSchema(
                    boxes=boxes,
                    scores=scores,
                    categories=["face"] * len(boxes),
                )
            )
        return results

    def _detect(self, img: np.ndarray) -> np.ndarray:
        input_size = self.input_size
        im_ratio = float(img.shape[0]) / img.shape[1]
        model_ratio = float(input_size[1]) / input_size[0]
        if im_ratio > model_ratio:
            new_height = input_size[1]
            new_width = int(new_height / im_ratio)
        else:
            new_width = input_size[0]
            new_height = int(new_width * im_ratio)
        det_scale = float(new_height) / img.shape[0]
        resized = cv2.resize(img, (new_width, new_height))
        det_img = np.zeros((input_size[1], input_size[0], 3), dtype=np.uint8)
        det_img[:new_height, :new_width, :] = resized

        scores_list, bboxes_list = self._forward(det_img)
        if not scores_list:
            return np.empty((0, 5), dtype=np.float32)

        scores = np.vstack(scores_list)
        bboxes = np.vstack(bboxes_list) / det_scale
        pre_det = np.hstack((bboxes, scores)).astype(np.float32)
        order = pre_det[:, 4].argsort()[::-1]
        pre_det = pre_det[order]
        keep = self._nms(pre_det)
        return pre_det[keep]

    def _forward(self, img: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
        input_size = tuple(img.shape[0:2][::-1])
        blob = cv2.dnn.blobFromImage(
            img,
            1.0 / self.input_std,
            input_size,
            (self.input_mean, self.input_mean, self.input_mean),
            swapRB=True,
        )
        net_outs = self.engine.run(self.output_names, {self.input_name: blob})

        input_height = blob.shape[2]
        input_width = blob.shape[3]
        scores_list: list[np.ndarray] = []
        bboxes_list: list[np.ndarray] = []

        for idx, stride in enumerate(self._feat_stride_fpn):
            if self.batched:
                scores = net_outs[idx][0]
                bbox_preds = net_outs[idx + self.fmc][0] * stride
            else:
                scores = net_outs[idx]
                bbox_preds = net_outs[idx + self.fmc] * stride

            height = input_height // stride
            width = input_width // stride
            key = (height, width, stride)
            if key in self.center_cache:
                anchor_centers = self.center_cache[key]
            else:
                anchor_centers = np.stack(
                    np.mgrid[:height, :width][::-1], axis=-1
                ).astype(np.float32)
                anchor_centers = (anchor_centers * stride).reshape((-1, 2))
                if self._num_anchors > 1:
                    anchor_centers = np.stack(
                        [anchor_centers] * self._num_anchors, axis=1
                    ).reshape((-1, 2))
                if len(self.center_cache) < 100:
                    self.center_cache[key] = anchor_centers

            pos_inds = np.where(scores >= self.det_thresh)[0]
            if pos_inds.size == 0:
                continue
            bboxes = distance2bbox(anchor_centers, bbox_preds)
            scores_list.append(scores[pos_inds])
            bboxes_list.append(bboxes[pos_inds])

        return scores_list, bboxes_list

    def _nms(self, dets: np.ndarray) -> list[int]:
        x1, y1, x2, y2, scores = (
            dets[:, 0],
            dets[:, 1],
            dets[:, 2],
            dets[:, 3],
            dets[:, 4],
        )
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]
        keep: list[int] = []
        while order.size > 0:
            i = int(order[0])
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            order = order[np.where(ovr <= self.nms_thresh)[0] + 1]
        return keep
