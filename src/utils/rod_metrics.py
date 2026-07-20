"""Метрики угла палки и логика событий RodTracker."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass


def rod_angle_deg(
    top: tuple[float, float],
    bottom: tuple[float, float],
) -> float:
    """Угол палки от вертикали (градусы): 0 = вертикально, + вправо."""
    dx = float(bottom[0] - top[0])
    dy = float(bottom[1] - top[1])
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 0.0
    return math.degrees(math.atan2(dx, dy))


def base_d_angle_deg(raw_angle: float, ref_angle: float) -> float:
    """Кратчайшее угловое отклонение |raw - ref| с учётом wrap-around."""
    delta = (float(raw_angle) - float(ref_angle) + 180.0) % 360.0 - 180.0
    return abs(delta)


@dataclass
class RodTrackerUpdate:
    raw_angle: float
    ref_angle: float | None
    ema_angle: float | None
    ref_dA: float
    change_count: int
    armed: bool
    post_event: bool
    deviation_active: bool
    event_fired: bool


@dataclass
class RodTracker:
    """Считает «нажатия» палки по углу относительно REF."""

    angle_thresh_deg: float = 8.0
    min_deviation_sec: float = 1.0
    release_thresh_deg: float = 6.0
    normal_thresh_deg: float = 4.0
    post_event_cooldown_sec: float = 2.0
    stability_frame_d_angle_deg: float = 2.0
    stability_min_sec: float = 0.3
    ema_alpha: float = 0.75

    ref_angle: float | None = None
    change_count: int = 0
    armed: bool = True
    post_event: bool = False
    deviation_active: bool = False
    deviation_above_thresh_since: float | None = None
    normal_since: float | None = None
    stability_since: float | None = None
    last_raw_angle: float | None = None
    ema_angle: float | None = None

    def reset(self) -> None:
        self.ref_angle = None
        self.change_count = 0
        self.armed = True
        self.post_event = False
        self.deviation_active = False
        self.deviation_above_thresh_since = None
        self.normal_since = None
        self.stability_since = None
        self.last_raw_angle = None
        self.ema_angle = None

    def _update_ref(self, raw_angle: float, ref_dA: float, ts: float) -> None:
        if self.post_event or self.deviation_active:
            self.stability_since = None
            return
        if self.deviation_above_thresh_since is not None:
            self.stability_since = None
            return
        if ref_dA >= self.normal_thresh_deg:
            self.stability_since = None
            return

        if self.last_raw_angle is not None:
            frame_d = base_d_angle_deg(raw_angle, self.last_raw_angle)
            if frame_d > self.stability_frame_d_angle_deg:
                self.stability_since = None
                return

        if self.stability_since is None:
            self.stability_since = ts
        elif ts - self.stability_since >= self.stability_min_sec:
            self.ref_angle = raw_angle

    def update(self, raw_angle: float, ts: float | None = None) -> RodTrackerUpdate:
        now = time.time() if ts is None else float(ts)
        event_fired = False

        if self.ref_angle is None:
            self.ref_angle = raw_angle
            self.ema_angle = raw_angle
            self.last_raw_angle = raw_angle
            return RodTrackerUpdate(
                raw_angle=raw_angle,
                ref_angle=self.ref_angle,
                ema_angle=self.ema_angle,
                ref_dA=0.0,
                change_count=self.change_count,
                armed=self.armed,
                post_event=self.post_event,
                deviation_active=self.deviation_active,
                event_fired=False,
            )

        ref_dA = base_d_angle_deg(raw_angle, self.ref_angle)

        if self.ema_angle is None:
            self.ema_angle = raw_angle
        else:
            a = self.ema_alpha
            self.ema_angle = a * raw_angle + (1.0 - a) * self.ema_angle

        if self.post_event:
            if ref_dA < self.normal_thresh_deg:
                if self.normal_since is None:
                    self.normal_since = now
                elif now - self.normal_since >= self.post_event_cooldown_sec:
                    self.post_event = False
                    self.armed = True
                    self.normal_since = None
                    self.deviation_active = False
                    self.deviation_above_thresh_since = None
            else:
                self.normal_since = None
        elif self.armed:
            if ref_dA >= self.angle_thresh_deg:
                if self.deviation_above_thresh_since is None:
                    self.deviation_above_thresh_since = now
                elif now - self.deviation_above_thresh_since >= self.min_deviation_sec:
                    self.change_count += 1
                    event_fired = True
                    self.armed = False
                    self.post_event = True
                    self.normal_since = None
                    self.deviation_above_thresh_since = None
                    self.deviation_active = True
            else:
                self.deviation_above_thresh_since = None

            if self.deviation_active and ref_dA < self.release_thresh_deg:
                self.deviation_active = False

        self._update_ref(raw_angle, ref_dA, now)
        self.last_raw_angle = raw_angle

        return RodTrackerUpdate(
            raw_angle=raw_angle,
            ref_angle=self.ref_angle,
            ema_angle=self.ema_angle,
            ref_dA=ref_dA,
            change_count=self.change_count,
            armed=self.armed,
            post_event=self.post_event,
            deviation_active=self.deviation_active,
            event_fired=event_fired,
        )
