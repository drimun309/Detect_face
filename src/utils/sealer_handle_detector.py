"""Детектор циклов запайщика: фиксированный ROI + всплеск diff (cvpoinpaket)."""

from __future__ import annotations

import time

import cv2
import numpy as np

DEFAULT_COOLDOWN_FRAMES = 8
DEFAULT_EMA_ALPHA = 0.08
DEFAULT_MIN_HYSTERESIS = 2.0
DEFAULT_MIN_ACTIVE_SEC = 1.0
DEFAULT_SPIKE_THRESHOLD = 80.0
DEFAULT_REST_THRESHOLD = -50.0


def norm_rect_to_pixels(
    x: float,
    y: float,
    w: float,
    h: float,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    if width <= 0 or height <= 0:
        return 0, 0, 1, 1
    px = max(0, min(width - 1, int(round(x * width))))
    py = max(0, min(height - 1, int(round(y * height))))
    pw = max(1, int(round(w * width)))
    ph = max(1, int(round(h * height)))
    if px + pw > width:
        pw = width - px
    if py + ph > height:
        ph = height - py
    return px, py, max(1, pw), max(1, ph)


class FixedRoiDetector:
    """Сравнивает фиксированную область с эталоном (ручка в покое)."""

    def __init__(self, roi_pixels: tuple[int, int, int, int]) -> None:
        self.roi = tuple(int(v) for v in roi_pixels)
        self.reference_gray: np.ndarray | None = None
        self._rest_frames = 0

    def set_reference(self, frame: np.ndarray) -> None:
        x, y, w, h = self.roi
        patch = frame[y : y + h, x : x + w]
        if patch.size == 0:
            raise ValueError("Пустой ROI — проверьте координаты")
        self.reference_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY).astype(np.float32)
        self._rest_frames = 0

    def _patch_gray(self, frame: np.ndarray) -> np.ndarray:
        x, y, w, h = self.roi
        gray = cv2.cvtColor(frame[y : y + h, x : x + w], cv2.COLOR_BGR2GRAY)
        return gray.astype(np.float32)

    def measure(self, frame: np.ndarray) -> float:
        if self.reference_gray is None:
            raise RuntimeError("Эталон не задан — вызовите set_reference()")
        gray = self._patch_gray(frame)
        return float(np.mean(np.abs(gray - self.reference_gray)))

    def adapt_reference_if_resting(
        self,
        frame: np.ndarray,
        activity: float,
        rest_threshold: float,
        rest_frames: int = 6,
    ) -> None:
        if activity < rest_threshold:
            self._rest_frames += 1
            if self._rest_frames >= rest_frames and self.reference_gray is not None:
                gray = self._patch_gray(frame)
                self.reference_gray = 0.9 * self.reference_gray + 0.1 * gray
                self._rest_frames = 0
        else:
            self._rest_frames = 0


class SealerMotionDetector:
    """Ловит всплеск diff относительно плавной базовой линии (EMA)."""

    def __init__(
        self,
        spike_threshold: float,
        rest_threshold: float = DEFAULT_REST_THRESHOLD,
        cooldown_frames: int = DEFAULT_COOLDOWN_FRAMES,
        ema_alpha: float = DEFAULT_EMA_ALPHA,
        min_active_sec: float = DEFAULT_MIN_ACTIVE_SEC,
    ) -> None:
        self.spike_threshold = float(spike_threshold)
        self.rest_threshold = float(rest_threshold)
        self.cooldown_frames = cooldown_frames
        self.ema_alpha = ema_alpha
        self.min_active_sec = max(0.1, float(min_active_sec))
        self.ema: float | None = None
        self.activity = 0.0
        self._last_activity = 0.0
        self.armed = True
        self.state = "OPEN"
        self._cooldown_until = 0
        self._active_since: float | None = None
        self._counted_episode = False

    def set_thresholds(self, spike_threshold: float, rest_threshold: float = DEFAULT_REST_THRESHOLD) -> None:
        if spike_threshold - rest_threshold < DEFAULT_MIN_HYSTERESIS:
            rest_threshold = spike_threshold - DEFAULT_MIN_HYSTERESIS
        self.spike_threshold = float(spike_threshold)
        self.rest_threshold = float(rest_threshold)

    def reset(self) -> None:
        self.ema = None
        self.activity = 0.0
        self._last_activity = 0.0
        self.armed = True
        self.state = "OPEN"
        self._cooldown_until = 0
        self._active_since = None
        self._counted_episode = False

    def update(self, score: float, frame_idx: int) -> bool:
        if self.ema is None:
            self.ema = score
            self._last_activity = 0.0
            return False

        now = time.time()
        self.activity = score - self.ema
        self.ema = (1 - self.ema_alpha) * self.ema + self.ema_alpha * score

        crossed_up = self._last_activity <= self.spike_threshold < self.activity
        fired = False
        if crossed_up and self.armed and frame_idx >= self._cooldown_until:
            self.armed = False
            self.state = "CLOSED"
            self._active_since = now
            self._counted_episode = False
            self._cooldown_until = frame_idx + self.cooldown_frames

        if (
            self.state == "CLOSED"
            and self._active_since is not None
            and self.activity >= self.rest_threshold
            and not self._counted_episode
            and (now - self._active_since) >= self.min_active_sec
        ):
            fired = True
            self._counted_episode = True

        if self.activity < self.rest_threshold:
            self.armed = True
            self.state = "OPEN"
            self._active_since = None
            self._counted_episode = False

        self._last_activity = self.activity
        return fired


def probe_thresholds_from_scores(scores: list[float], activities: list[float]) -> tuple[float, float]:
    if len(activities) < 20:
        return DEFAULT_SPIKE_THRESHOLD, DEFAULT_REST_THRESHOLD
    arr = np.array(activities)
    peak = float(np.max(arr))
    if peak < 60.0:
        return DEFAULT_SPIKE_THRESHOLD, DEFAULT_REST_THRESHOLD
    noise = float(np.percentile(arr, 60))
    spike = float(np.percentile(arr, 95))
    thresh = max(DEFAULT_SPIKE_THRESHOLD, noise + (spike - noise) * 0.65)
    return float(round(thresh, 1)), DEFAULT_REST_THRESHOLD
