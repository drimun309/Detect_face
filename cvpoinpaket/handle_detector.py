import cv2
import numpy as np

DEFAULT_COOLDOWN_FRAMES = 8
DEFAULT_EMA_ALPHA = 0.08
DEFAULT_MIN_HYSTERESIS = 2


class FixedRoiDetector:
    """Сравнивает фиксированную область с эталоном (ручка в покое)."""

    def __init__(self, roi):
        self.roi = tuple(int(v) for v in roi)
        self.reference_gray = None
        self._rest_frames = 0

    def set_reference(self, frame) -> None:
        x, y, w, h = self.roi
        patch = frame[y : y + h, x : x + w]
        self.reference_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY).astype(np.float32)
        self._rest_frames = 0

    def _patch_gray(self, frame):
        x, y, w, h = self.roi
        gray = cv2.cvtColor(frame[y : y + h, x : x + w], cv2.COLOR_BGR2GRAY)
        return gray.astype(np.float32)

    def measure(self, frame) -> float:
        if self.reference_gray is None:
            raise RuntimeError("Эталон не задан — вызовите set_reference()")
        gray = self._patch_gray(frame)
        return float(np.mean(np.abs(gray - self.reference_gray)))

    def adapt_reference_if_resting(self, frame, activity: float, rest_threshold: float, rest_frames: int = 6) -> None:
        """Обновляет эталон, когда ручка снова в покое — ловит смену освещения/положения."""
        if activity < rest_threshold:
            self._rest_frames += 1
            if self._rest_frames >= rest_frames:
                gray = self._patch_gray(frame)
                self.reference_gray = 0.9 * self.reference_gray + 0.1 * gray
                self._rest_frames = 0
        else:
            self._rest_frames = 0


class MotionDetector:
    """Ловит всплеск diff относительно плавной базовой линии (EMA)."""

    def __init__(
        self,
        spike_threshold: float,
        rest_threshold: float = 2.0,
        cooldown_frames: int = DEFAULT_COOLDOWN_FRAMES,
        ema_alpha: float = DEFAULT_EMA_ALPHA,
    ):
        self.spike_threshold = float(spike_threshold)
        self.rest_threshold = float(rest_threshold)
        self.cooldown_frames = cooldown_frames
        self.ema_alpha = ema_alpha
        self.ema = None
        self.activity = 0.0
        self._last_activity = 0.0
        self.armed = True
        self.state = "OPEN"
        self._cooldown_until = 0
        self.last_block_reason = ""

    def set_thresholds(self, spike_threshold: float, rest_threshold: float = 2.0):
        if spike_threshold - rest_threshold < DEFAULT_MIN_HYSTERESIS:
            rest_threshold = max(0.5, spike_threshold - DEFAULT_MIN_HYSTERESIS)
        self.spike_threshold = float(spike_threshold)
        self.rest_threshold = float(rest_threshold)

    def reset(self) -> None:
        self.ema = None
        self.activity = 0.0
        self._last_activity = 0.0
        self.armed = True
        self.state = "OPEN"
        self._cooldown_until = 0
        self.last_block_reason = ""

    def update(self, score: float, frame_idx: int) -> bool:
        if self.ema is None:
            self.ema = score
            self._last_activity = 0.0
            return False

        self.activity = score - self.ema
        self.ema = (1 - self.ema_alpha) * self.ema + self.ema_alpha * score

        if self.activity < self.rest_threshold:
            self.armed = True
            self.state = "OPEN"

        crossed_up = (
            self._last_activity <= self.spike_threshold < self.activity
        )
        fired = False

        if crossed_up:
            if not self.armed:
                self.last_block_reason = "not armed"
            elif frame_idx < self._cooldown_until:
                self.last_block_reason = "cooldown"
            else:
                fired = True
                self.armed = False
                self.state = "CLOSED"
                self._cooldown_until = frame_idx + self.cooldown_frames
        elif self.activity > self.spike_threshold and not self.armed:
            self.last_block_reason = (
                "cooldown" if frame_idx < self._cooldown_until else "not armed"
            )
        else:
            self.last_block_reason = ""

        self._last_activity = self.activity
        return fired


def draw_fixed_roi(frame, roi, state: str) -> None:
    x, y, w, h = roi
    color = (0, 255, 0) if state == "CLOSED" else (255, 128, 0)
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)


def draw_score_graph(
    frame,
    diff_history,
    activity_history,
    spike_threshold: float,
    rest_threshold: float,
    max_history: int = 200,
) -> None:
    graph_h = 100
    graph_w = max_history * 3
    graph_y = frame.shape[0] - graph_h - 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, graph_y), (graph_w, graph_y + graph_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    series = activity_history if activity_history else diff_history
    graph_max = max(spike_threshold * 2.5, max(series) if series else spike_threshold, 8)
    graph_min = min(0.0, min(series) if series else 0.0)

    def to_y(value: float) -> int:
        if graph_max == graph_min:
            graph_max_local = graph_min + 1
        else:
            graph_max_local = graph_max
        return graph_y + graph_h - int((value - graph_min) / (graph_max_local - graph_min) * graph_h)

    for thresh, col in ((spike_threshold, (0, 0, 255)), (rest_threshold, (0, 255, 255))):
        cv2.line(frame, (0, to_y(thresh)), (graph_w, to_y(thresh)), col, 1)

    if len(series) <= 1:
        return

    for i in range(len(series) - 1):
        cv2.line(
            frame,
            (i * 3, to_y(series[i])),
            ((i + 1) * 3, to_y(series[i + 1])),
            (0, 255, 255),
            2,
        )


def probe_thresholds(cap, roi, frame_count: int = 0):
    detector = FixedRoiDetector(roi)
    motion = MotionDetector(8, 2)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()
    if not ret:
        return 8, 2

    detector.set_reference(frame)
    activities = []
    total = frame_count or int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    for idx in range(total):
        ret, frame = cap.read()
        if not ret:
            break
        score = detector.measure(frame)
        if motion.ema is not None:
            activity = score - motion.ema
            activities.append(activity)
            detector.adapt_reference_if_resting(frame, activity, motion.rest_threshold)
        motion.update(score, idx)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    if len(activities) < 20:
        return 8, 2

    arr = np.array(activities)
    noise = float(np.percentile(arr, 60))
    spike = float(np.percentile(arr, 95))
    thresh = max(4.0, noise + (spike - noise) * 0.55)
    rest = max(1.0, noise * 0.6)
    return int(round(thresh)), max(1, int(round(rest)))


def warn_if_roi_too_large(roi) -> None:
    _, _, w, h = roi
    if h > 120 or w > 120:
        print("⚠ ROI слишком большой — выделите маленький участок ручки в покое (примерно 30×60)")
    if max(w, h) / max(min(w, h), 1) > 4:
        print("⚠ ROI слишком вытянутый — лучше компактный квадрат на металлической части")
