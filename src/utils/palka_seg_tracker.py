"""Авто-ROI + события E-out/angle для seg-палки."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import cv2
import numpy as np


HOLD_NEED_SEC = 1.0
ANG_NEED_SEC = 0.25
ANG_ENTER_DEG = 6.0
ANG_EXIT_DEG = 4.0
ANG_REF_ALPHA = 0.02
# длинная ось — меньше pad (не тянуть ROI вниз за кончиком), поперёк — чуть больше
ROI_PAD_LONG = 0.10
ROI_PAD_SHORT = 0.28
REST_SETTLE_SEC = 1.0
ROI_FOLLOW_DT = 5.0  # в покое подстраивать ROI не чаще раза в 5 секунд
ANG_EMA = 0.4
ROI_FREEZE_DEG = 3.0  # раньше freeze, чтобы ROI не ехал за нажатием


def ang_diff_abs(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def ang_lerp(a: float, b: float, t: float) -> float:
    d = (b - a + 180.0) % 360.0 - 180.0
    return a + d * t


def se_angle_deg(s: tuple[float, float], e: tuple[float, float]) -> float:
    return math.degrees(math.atan2(e[1] - s[1], e[0] - s[0]))


def axis_ends(
    poly: np.ndarray,
    prev_se: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    if poly is None or len(poly) < 2:
        return None
    pts = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
    if len(pts) < 2:
        return None
    box = cv2.boxPoints(cv2.minAreaRect(pts))
    diags: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for i, j in ((0, 2), (1, 3)):
        a = (float(box[i][0]), float(box[i][1]))
        b = (float(box[j][0]), float(box[j][1]))
        diags.append((a, b))
        diags.append((b, a))
    if prev_se is not None:
        ps, pe = prev_se
        return min(
            diags,
            key=lambda se: (se[0][0] - ps[0]) ** 2
            + (se[0][1] - ps[1]) ** 2
            + (se[1][0] - pe[0]) ** 2
            + (se[1][1] - pe[1]) ** 2,
        )
    upright = [se if se[0][1] <= se[1][1] else (se[1], se[0]) for se in diags[::2]]
    return max(upright, key=lambda se: abs(se[0][1] - se[1][1]))


def roi_from_stick(
    poly: np.ndarray,
    w: int,
    h: int,
    pad_long: float = ROI_PAD_LONG,
    pad_short: float = ROI_PAD_SHORT,
) -> list[list[float]]:
    """OBB палки: вдоль длины pad меньше — ROI не уезжает вниз за E."""
    pts = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
    (cx, cy), (bw, bh), angle = cv2.minAreaRect(pts)
    if bw >= bh:
        bw = max(bw * (1.0 + pad_long), 1.0)
        bh = max(bh * (1.0 + pad_short), 1.0)
    else:
        bw = max(bw * (1.0 + pad_short), 1.0)
        bh = max(bh * (1.0 + pad_long), 1.0)
    box = cv2.boxPoints(((cx, cy), (bw, bh), angle))
    return [
        [float(np.clip(x / w, 0, 1)), float(np.clip(y / h, 0, 1))]
        for x, y in box
    ]


def point_in_roi(cx: float, cy: float, w: int, h: int, roi: list[list[float]]) -> bool:
    if not roi or len(roi) < 3:
        return False
    pts = np.array([[p[0] * w, p[1] * h] for p in roi], dtype=np.float32)
    return cv2.pointPolygonTest(pts, (cx, cy), False) >= 0


def tip_along_axis(
    poly: np.ndarray,
    s: tuple[float, float],
    e: tuple[float, float],
) -> tuple[float, float]:
    """Кончик маски вдоль S→E (OBB-угол часто ещё внутри ROI, когда маска уже вышла)."""
    pts = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
    if len(pts) < 1:
        return e
    vx, vy = e[0] - s[0], e[1] - s[1]
    if vx * vx + vy * vy < 1e-6:
        return e
    dots = (pts[:, 0] - s[0]) * vx + (pts[:, 1] - s[1]) * vy
    i = int(np.argmax(dots))
    return (float(pts[i, 0]), float(pts[i, 1]))


@dataclass
class RelativeAngleTracker:
    """UP -> confirmed DOWN (one event) -> confirmed UP by relative angle."""

    enter_deg: float = ANG_ENTER_DEG
    exit_deg: float = ANG_EXIT_DEG
    dwell_sec: float = ANG_NEED_SEC
    ref_alpha: float = ANG_REF_ALPHA
    state: str = "UP"
    ref_angle: float | None = None
    delta_deg: float = 0.0
    hold_sec: float = 0.0

    def reset(self) -> None:
        self.state = "UP"
        self.ref_angle = None
        self.delta_deg = 0.0
        self.hold_sec = 0.0

    def update(self, angle: float, dt: float) -> bool:
        dt = max(0.0, min(float(dt), 1.0))
        if self.ref_angle is None:
            self.ref_angle = angle
            self.delta_deg = 0.0
            self.hold_sec = 0.0
            return False

        self.delta_deg = ang_diff_abs(angle, self.ref_angle)
        if self.state == "UP":
            if self.delta_deg >= self.enter_deg:
                self.hold_sec = min(self.dwell_sec, self.hold_sec + dt)
                if self.hold_sec >= self.dwell_sec:
                    self.state = "DOWN"
                    self.hold_sec = 0.0
                    return True
            else:
                self.hold_sec = 0.0
                if self.delta_deg <= self.exit_deg:
                    self.ref_angle = ang_lerp(self.ref_angle, angle, self.ref_alpha)
        else:
            if self.delta_deg <= self.exit_deg:
                self.hold_sec = min(self.dwell_sec, self.hold_sec + dt)
                if self.hold_sec >= self.dwell_sec:
                    self.state = "UP"
                    self.ref_angle = angle
                    self.delta_deg = 0.0
                    self.hold_sec = 0.0
            else:
                self.hold_sec = 0.0
        return False


@dataclass
class PalkaSegUpdate:
    s: tuple[float, float]
    e: tuple[float, float]
    angle_deg: float
    ref_dA: float
    e_in_roi: bool | None
    event_e: bool
    event_angle: bool
    roi: list[list[float]] | None
    hold_sec: float
    ang_hold_sec: float
    roi_idle_sec: float
    armed: bool
    roi_created: bool = False
    roi_retuned: bool = False
    roi_rescued: bool = False
    roi_shift: float = 0.0


@dataclass
class PalkaSegTracker:
    """
    Покой: ROI следует за палкой, ang_ref подстраивается как в RelativeCycleTracker.
    Угол: подтверждённый UP -> DOWN по относительному углу даёт event_angle.
    ROI: кончик вне ROI при движении (dA≥3° или pressing) → event_e за 1с
    (не ждём полного enter — иначе при dA~5–6 E-out молчал).
    """

    hold_need_sec: float = HOLD_NEED_SEC
    ang_need_sec: float = ANG_NEED_SEC
    ang_enter_deg: float = ANG_ENTER_DEG
    ang_exit_deg: float = ANG_EXIT_DEG
    rest_settle_sec: float = REST_SETTLE_SEC

    roi: list[list[float]] | None = None
    prev_se: tuple[tuple[float, float], tuple[float, float]] | None = None
    ang_ref: float | None = None
    ang_smooth: float | None = None
    angle_cycle: RelativeAngleTracker = field(default_factory=RelativeAngleTracker)
    hold_armed: bool = True
    ang_armed: bool = True
    hold_sec: float = 0.0
    ang_hold_sec: float = 0.0
    calm_sec: float = 0.0
    pressing: bool = False
    _last_ts: float | None = None
    _roi_follow_ts: float = 0.0

    def reset(self) -> None:
        self.roi = None
        self.prev_se = None
        self.ang_ref = None
        self.ang_smooth = None
        self.angle_cycle.reset()
        self.hold_armed = True
        self.ang_armed = True
        self.hold_sec = 0.0
        self.ang_hold_sec = 0.0
        self.calm_sec = 0.0
        self.pressing = False
        self._last_ts = None
        self._roi_follow_ts = 0.0

    def update(
        self,
        contour: list[tuple[float, float]],
        width: int,
        height: int,
        frame_dt: float,
    ) -> PalkaSegUpdate | None:
        if width <= 0 or height <= 0 or len(contour) < 2:
            return None
        now = time.time()
        if self._last_ts is not None:
            dt = max(0.0, min(now - self._last_ts, 1.0))
        else:
            dt = max(frame_dt, 1e-3)
        self._last_ts = now

        poly = np.asarray(contour, dtype=np.float32).reshape(-1, 2)
        ends = axis_ends(poly, self.prev_se)
        if ends is None:
            return None
        s_pt, e_pt = ends
        raw_ang = se_angle_deg(s_pt, e_pt)
        if self.ang_smooth is not None and ang_diff_abs(raw_ang, self.ang_smooth) > 90.0:
            s_pt, e_pt = e_pt, s_pt
            ends = (s_pt, e_pt)
            raw_ang = se_angle_deg(s_pt, e_pt)
        self.prev_se = ends
        tip = tip_along_axis(poly, s_pt, e_pt)

        if self.ang_smooth is None:
            self.ang_smooth = raw_ang
        else:
            self.ang_smooth = ang_lerp(self.ang_smooth, raw_ang, ANG_EMA)
        cur_ang = self.ang_smooth

        roi_created = not self.roi or len(self.roi) < 3
        if roi_created:
            self.roi = roi_from_stick(poly, width, height)
            self._roi_follow_ts = now

        event_ang = self.angle_cycle.update(cur_ang, dt)
        self.ang_ref = self.angle_cycle.ref_angle
        ref_da = self.angle_cycle.delta_deg
        self.pressing = self.angle_cycle.state == "DOWN"
        self.ang_armed = self.angle_cycle.state == "UP"

        # ROI follow только в покое и редко; при dA≥3° уже freeze
        roi_follow = (
            (not self.pressing)
            and (ref_da < ROI_FREEZE_DEG)
            and (roi_created or (now - self._roi_follow_ts) >= ROI_FOLLOW_DT)
        )

        if roi_follow:
            self.roi = roi_from_stick(poly, width, height)
            self._roi_follow_ts = now

        e_in = (
            point_in_roi(tip[0], tip[1], width, height, self.roi)
            if self.roi and len(self.roi) >= 3
            else None
        )

        event_e = False
        # E-out: при движении (как в оригинале не ждём полный enter угла).
        # ponytail: dA≥freeze — потолок ложных E при дрожании ROI в покое; ужесточить до pressing если шум.
        e_motion = self.pressing or ref_da >= ROI_FREEZE_DEG
        if e_in is False and self.hold_armed and e_motion:
            self.hold_sec = min(self.hold_need_sec, self.hold_sec + dt)
            if self.hold_sec >= self.hold_need_sec:
                event_e = True
                self.hold_sec = 0.0
                self.hold_armed = False
        elif e_in is True:
            self.hold_sec = 0.0
            self.hold_armed = True
        elif not e_motion:
            self.hold_sec = 0.0

        self.ang_hold_sec = self.angle_cycle.hold_sec

        return PalkaSegUpdate(
            s=s_pt,
            e=tip,
            angle_deg=cur_ang,
            ref_dA=ref_da,
            e_in_roi=e_in,
            event_e=event_e,
            event_angle=event_ang,
            roi=list(self.roi) if self.roi else None,
            hold_sec=self.hold_sec,
            ang_hold_sec=self.ang_hold_sec,
            roi_idle_sec=0.0,
            armed=bool(self.hold_armed and self.angle_cycle.state == "UP"),
            roi_created=roi_created,
        )
