"""Трекер людей: ByteTrack / BoT-SORT (Ultralytics) + SORT с Kalman (предсказание при пропадании)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

PersonTrackerType = Literal["off", "bytetrack", "botsort", "sort"]

# Трекер только по телу (person). Головы (head) не сопровождаются.
_CAT_TO_CLS = {"person": 0}
_CLS_TO_CAT = {0: "person"}


@dataclass
class TrackedPerson:
    track_id: int
    box: list[int]  # xyxy
    score: float
    category: str
    predicted: bool = False  # True = детекции нет, бокс из Kalman


class _DetResults:
    """Минимальный Results-like объект для BYTETracker / BOTSORT."""

    def __init__(
        self,
        xyxy: np.ndarray,
        conf: np.ndarray,
        cls: np.ndarray,
    ) -> None:
        self.xyxy = np.asarray(xyxy, dtype=np.float32).reshape(-1, 4)
        self.conf = np.asarray(conf, dtype=np.float32).reshape(-1)
        self.cls = np.asarray(cls, dtype=np.float32).reshape(-1)
        if len(self.xyxy):
            w = self.xyxy[:, 2] - self.xyxy[:, 0]
            h = self.xyxy[:, 3] - self.xyxy[:, 1]
            cx = self.xyxy[:, 0] + w / 2.0
            cy = self.xyxy[:, 1] + h / 2.0
            self.xywh = np.stack([cx, cy, w, h], axis=1).astype(np.float32)
        else:
            self.xywh = np.zeros((0, 4), dtype=np.float32)

    def __len__(self) -> int:
        return int(len(self.conf))

    def __getitem__(self, idx) -> "_DetResults":
        return _DetResults(self.xyxy[idx], self.conf[idx], self.cls[idx])


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    x1 = max(float(a[0]), float(b[0]))
    y1 = max(float(a[1]), float(b[1]))
    x2 = min(float(a[2]), float(b[2]))
    y2 = min(float(a[3]), float(b[3]))
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, float(a[2] - a[0])) * max(0.0, float(a[3] - a[1]))
    area_b = max(0.0, float(b[2] - b[0])) * max(0.0, float(b[3] - b[1]))
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


@dataclass
class _SortTrack:
    track_id: int
    box: np.ndarray  # xyxy float
    score: float
    category: str
    hits: int = 1
    age: int = 1
    time_since_update: int = 0
    velocity: np.ndarray | None = None  # dx, dy, dw, dh per frame

    def predict(self) -> None:
        if self.velocity is None:
            self.velocity = np.zeros(4, dtype=np.float32)
        # Слабое смещение + затухание скорости — бокс не убегает вперёд
        damp = 0.25
        self.box = self.box + self.velocity * damp
        self.velocity = self.velocity * 0.7
        self.age += 1
        self.time_since_update += 1

    def update(self, box: np.ndarray, score: float, category: str) -> None:
        new_vel = box - self.box
        if self.velocity is None:
            self.velocity = (0.4 * new_vel).astype(np.float32)
        else:
            self.velocity = (0.5 * self.velocity + 0.2 * new_vel).astype(np.float32)
        # Ограничение скорости (пикс/кадр), чтобы не разгонялось
        self.velocity = np.clip(self.velocity, -12.0, 12.0)
        self.box = box.astype(np.float32)
        self.score = float(score)
        self.category = category
        self.hits += 1
        self.time_since_update = 0


class SortKalmanTracker:
    """Простой SORT: IoU-матчинг + скорость бокса (предсказание при пропадании)."""

    def __init__(
        self,
        max_age: int = 45,
        min_hits: int = 1,
        iou_thresh: float = 0.3,
    ) -> None:
        self.max_age = max(1, int(max_age))
        self.min_hits = max(1, int(min_hits))
        self.iou_thresh = float(iou_thresh)
        self._tracks: list[_SortTrack] = []
        self._next_id = 1

    def reset(self) -> None:
        self._tracks = []
        self._next_id = 1

    def update(
        self,
        boxes: list[list[int]],
        scores: list[float],
        categories: list[str],
    ) -> list[TrackedPerson]:
        dets = [
            (
                np.array(box, dtype=np.float32),
                float(score),
                (cat or "person").lower(),
            )
            for box, score, cat in zip(boxes, scores, categories)
            if (cat or "").lower() == "person"
        ]

        for tr in self._tracks:
            tr.predict()

        matched_t: set[int] = set()
        matched_d: set[int] = set()
        pairs: list[tuple[float, int, int]] = []
        for ti, tr in enumerate(self._tracks):
            for di, (dbox, _, _) in enumerate(dets):
                pairs.append((_iou(tr.box, dbox), ti, di))
        pairs.sort(reverse=True)
        for iou, ti, di in pairs:
            if iou < self.iou_thresh:
                break
            if ti in matched_t or di in matched_d:
                continue
            dbox, score, cat = dets[di]
            self._tracks[ti].update(dbox, score, cat)
            matched_t.add(ti)
            matched_d.add(di)

        for di, (dbox, score, cat) in enumerate(dets):
            if di in matched_d:
                continue
            self._tracks.append(
                _SortTrack(
                    track_id=self._next_id,
                    box=dbox.astype(np.float32),
                    score=score,
                    category=cat,
                )
            )
            self._next_id += 1

        alive: list[_SortTrack] = []
        out: list[TrackedPerson] = []
        for tr in self._tracks:
            if tr.time_since_update > self.max_age:
                continue
            alive.append(tr)
            if tr.hits < self.min_hits and tr.time_since_update > 0:
                continue
            if tr.time_since_update > 0:
                # Не рисуем «тень» без детекции — только держим ID внутри max_age.
                continue
            x1, y1, x2, y2 = [int(round(v)) for v in tr.box.tolist()]
            if x2 <= x1 or y2 <= y1:
                continue
            out.append(
                TrackedPerson(
                    track_id=tr.track_id,
                    box=[x1, y1, x2, y2],
                    score=tr.score,
                    category=tr.category,
                    predicted=False,
                )
            )
        self._tracks = alive
        return out


class UltralyticsMotionTracker:
    """ByteTrack / BoT-SORT из Ultralytics + вывод lost-треков (предсказание)."""

    def __init__(
        self,
        tracker_type: Literal["bytetrack", "botsort"] = "bytetrack",
        track_buffer: int = 45,
    ) -> None:
        self.tracker_type = tracker_type
        self.track_buffer = track_buffer
        self._tracker = None
        self._init_error: str | None = None
        self._build()

    def _build(self) -> None:
        try:
            from pathlib import Path

            import ultralytics
            from ultralytics.utils import IterableSimpleNamespace, YAML

            name = "botsort.yaml" if self.tracker_type == "botsort" else "bytetrack.yaml"
            path = Path(ultralytics.__file__).parent / "cfg" / "trackers" / name
            cfg = YAML.load(path)
            cfg["track_buffer"] = int(self.track_buffer)
            # Soften association so a lean/partial box can re-attach to the same ID.
            cfg["match_thresh"] = min(float(cfg.get("match_thresh", 0.8)), 0.7)
            args = IterableSimpleNamespace(**cfg)
            if self.tracker_type == "botsort":
                from ultralytics.trackers.bot_sort import BOTSORT

                self._tracker = BOTSORT(args)
            else:
                from ultralytics.trackers.byte_tracker import BYTETracker

                self._tracker = BYTETracker(args)
            self._init_error = None
        except Exception as exc:
            self._tracker = None
            self._init_error = str(exc)

    def reset(self) -> None:
        self._build()

    @property
    def available(self) -> bool:
        return self._tracker is not None

    def update(
        self,
        boxes: list[list[int]],
        scores: list[float],
        categories: list[str],
        frame_bgr: np.ndarray | None = None,
    ) -> list[TrackedPerson]:
        if self._tracker is None:
            return []

        keep_boxes: list[list[int]] = []
        keep_scores: list[float] = []
        keep_cls: list[int] = []
        for box, score, cat in zip(boxes, scores, categories):
            c = (cat or "").lower()
            if c not in _CAT_TO_CLS:
                continue
            keep_boxes.append(box)
            keep_scores.append(float(score))
            keep_cls.append(_CAT_TO_CLS[c])

        dets = _DetResults(
            np.array(keep_boxes, dtype=np.float32).reshape(-1, 4)
            if keep_boxes
            else np.zeros((0, 4), dtype=np.float32),
            np.array(keep_scores, dtype=np.float32),
            np.array(keep_cls, dtype=np.float32),
        )
        img = frame_bgr
        if img is None:
            img = np.zeros((480, 640, 3), dtype=np.uint8)

        online = self._tracker.update(dets, img)
        out: list[TrackedPerson] = []

        # Сырые детекции — показываем трек только при матче с детекцией.
        # Иначе Kalman «тень» летит по экрану и считается лишним человеком.
        det_xyxy = dets.xyxy

        if online is not None and len(online):
            arr = np.asarray(online)
            for row in arr:
                x1, y1, x2, y2 = [float(v) for v in row[:4]]
                tid = int(row[4])
                score = float(row[5]) if len(row) > 5 else 0.5
                cls_i = int(row[6]) if len(row) > 6 else 0
                track_box = np.array([x1, y1, x2, y2], dtype=np.float32)
                best_iou = 0.0
                best_det = track_box
                for dbox in det_xyxy:
                    iou = _iou(track_box, dbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_det = dbox
                if best_iou < 0.3:
                    continue
                x1, y1, x2, y2 = [float(v) for v in best_det.tolist()]
                ix1, iy1, ix2, iy2 = [int(round(v)) for v in (x1, y1, x2, y2)]
                if ix2 <= ix1 or iy2 <= iy1:
                    continue
                out.append(
                    TrackedPerson(
                        track_id=tid,
                        box=[ix1, iy1, ix2, iy2],
                        score=score,
                        category=_CLS_TO_CAT.get(cls_i, "person"),
                        predicted=False,
                    )
                )

        # Lost-треки не рисуем и не считаем: ID внутри BOTSORT живёт по track_buffer.
        return out


class PersonTracker:
    """Фасад: off / bytetrack / botsort / sort. На экземпляр камеры."""

    def __init__(
        self,
        tracker_type: PersonTrackerType = "bytetrack",
        track_buffer: int = 45,
    ) -> None:
        self.tracker_type: PersonTrackerType = "off"
        self.track_buffer = track_buffer
        self._ultra: UltralyticsMotionTracker | None = None
        self._sort: SortKalmanTracker | None = None
        self.set_type(tracker_type)

    def set_type(self, tracker_type: str, track_buffer: int | None = None) -> None:
        raw = (tracker_type or "off").lower().strip()
        if raw in ("strongsort", "bot-sort", "bot_sort"):
            raw = "botsort"
        if raw not in ("off", "bytetrack", "botsort", "sort"):
            raw = "off"
        if track_buffer is not None:
            self.track_buffer = max(5, int(track_buffer))
        self.tracker_type = raw  # type: ignore[assignment]
        self._ultra = None
        self._sort = None
        if raw == "off":
            return
        if raw in ("bytetrack", "botsort"):
            self._ultra = UltralyticsMotionTracker(
                tracker_type=raw,  # type: ignore[arg-type]
                track_buffer=self.track_buffer,
            )
            if not self._ultra.available:
                self._sort = SortKalmanTracker(max_age=self.track_buffer)
        else:
            self._sort = SortKalmanTracker(max_age=self.track_buffer)

    def reset(self) -> None:
        if self._ultra is not None:
            self._ultra.reset()
        if self._sort is not None:
            self._sort.reset()

    def update(
        self,
        boxes: list[list[int]],
        scores: list[float],
        categories: list[str],
        frame_bgr: np.ndarray | None = None,
    ) -> list[TrackedPerson] | None:
        """None = трекер выключен (использовать сырые детекции)."""
        if self.tracker_type == "off":
            return None
        if self._ultra is not None and self._ultra.available:
            return self._ultra.update(boxes, scores, categories, frame_bgr)
        if self._sort is not None:
            return self._sort.update(boxes, scores, categories)
        return None
