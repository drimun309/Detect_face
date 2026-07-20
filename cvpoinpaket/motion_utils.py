import cv2

AXIS_X = "X"
AXIS_Y = "Y"

DEFAULT_CONFIRM_FRAMES = 3
DEFAULT_COOLDOWN_FRAMES = 15
DEFAULT_MIN_HYSTERESIS = 15


def get_center(bbox):
    bx, by, bw, bh = [int(v) for v in bbox]
    return bx + bw // 2, by + bh // 2


def get_position(bbox, axis: str) -> int:
    center_x, center_y = get_center(bbox)
    return center_x if axis == AXIS_X else center_y


def is_past_closed(position: int, thresh_closed: int, closed_is_greater: bool) -> bool:
    if closed_is_greater:
        return position > thresh_closed
    return position < thresh_closed


def is_past_open(position: int, thresh_open: int, closed_is_greater: bool) -> bool:
    if closed_is_greater:
        return position < thresh_open
    return position > thresh_open


def normalize_thresholds(
    thresh_closed: int,
    thresh_open: int,
    closed_is_greater: bool,
    min_hysteresis: int = DEFAULT_MIN_HYSTERESIS,
):
    gap = abs(thresh_closed - thresh_open)
    if gap >= min_hysteresis:
        return thresh_closed, thresh_open

    half = min_hysteresis // 2
    mid = (thresh_closed + thresh_open) // 2
    if closed_is_greater:
        return mid + half, mid - half
    return mid - half, mid + half


class MotionDetector:
    def __init__(
        self,
        closed_is_greater: bool,
        thresh_closed: int,
        thresh_open: int,
        confirm_frames: int = DEFAULT_CONFIRM_FRAMES,
        cooldown_frames: int = DEFAULT_COOLDOWN_FRAMES,
        min_hysteresis: int = DEFAULT_MIN_HYSTERESIS,
    ):
        self.closed_is_greater = closed_is_greater
        self.confirm_frames = confirm_frames
        self.cooldown_frames = cooldown_frames
        self.min_hysteresis = min_hysteresis
        self.state = None
        self._pending_state = None
        self._pending_count = 0
        self._cooldown_until = 0
        self.set_thresholds(thresh_closed, thresh_open)

    def set_thresholds(self, thresh_closed: int, thresh_open: int) -> None:
        self.thresh_closed, self.thresh_open = normalize_thresholds(
            thresh_closed,
            thresh_open,
            self.closed_is_greater,
            self.min_hysteresis,
        )

    def _infer_state(self, position: int) -> str:
        if is_past_closed(position, self.thresh_closed, self.closed_is_greater):
            return "CLOSED"
        if is_past_open(position, self.thresh_open, self.closed_is_greater):
            return "OPEN"
        return "CLOSED" if self.closed_is_greater == (position > self.thresh_open) else "OPEN"

    def update(self, position: int, frame_idx: int) -> bool:
        if self.state is None:
            self.state = self._infer_state(position)
            self._pending_state = None
            self._pending_count = 0
            return False

        target = None
        if self.state == "OPEN" and is_past_closed(position, self.thresh_closed, self.closed_is_greater):
            target = "CLOSED"
        elif self.state == "CLOSED" and is_past_open(position, self.thresh_open, self.closed_is_greater):
            target = "OPEN"

        if target is None:
            self._pending_state = None
            self._pending_count = 0
            return False

        if target != self._pending_state:
            self._pending_state = target
            self._pending_count = 1
        else:
            self._pending_count += 1

        if self._pending_count < self.confirm_frames:
            return False

        self.state = target
        self._pending_state = None
        self._pending_count = 0

        if target != "CLOSED":
            return False

        if frame_idx < self._cooldown_until:
            return False

        self._cooldown_until = frame_idx + self.cooldown_frames
        return True


def draw_threshold_lines(frame, axis: str, thresh_closed: int, thresh_open: int) -> None:
    h, w = frame.shape[:2]
    if axis == AXIS_X:
        cv2.line(frame, (thresh_closed, 0), (thresh_closed, h), (0, 0, 255), 1)
        cv2.line(frame, (thresh_open, 0), (thresh_open, h), (0, 255, 255), 1)
    else:
        cv2.line(frame, (0, thresh_closed), (w, thresh_closed), (0, 0, 255), 1)
        cv2.line(frame, (0, thresh_open), (w, thresh_open), (0, 255, 255), 1)


def draw_motion_graph(frame, history, max_history: int = 200) -> None:
    graph_h = 100
    graph_y = frame.shape[0] - graph_h - 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, graph_y), (max_history * 3, graph_y + graph_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    if len(history) <= 1:
        return

    min_v = min(history) - 10
    max_v = max(history) + 10
    if max_v == min_v:
        max_v += 1

    for i in range(len(history) - 1):
        px1 = i * 3
        py1 = graph_y + graph_h - int((history[i] - min_v) / (max_v - min_v) * graph_h)
        px2 = (i + 1) * 3
        py2 = graph_y + graph_h - int((history[i + 1] - min_v) / (max_v - min_v) * graph_h)
        cv2.line(frame, (px1, py1), (px2, py2), (0, 255, 255), 2)


def probe_motion_axis(cap, tracker, roi, frame_count: int = 400):
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()
    if not ret:
        return AXIS_X, True, 320, 280

    tracker.init(frame, roi)
    xs, ys = [], []

    for _ in range(frame_count):
        ret, frame = cap.read()
        if not ret:
            break
        success, bbox = tracker.update(frame)
        if success:
            center_x, center_y = get_center(bbox)
            xs.append(center_x)
            ys.append(center_y)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    if len(xs) < 20:
        return AXIS_X, True, 320, 280

    spread_x = max(xs) - min(xs)
    spread_y = max(ys) - min(ys)
    axis = AXIS_X if spread_x >= spread_y else AXIS_Y
    positions = xs if axis == AXIS_X else ys

    sorted_pos = sorted(positions)
    p25 = sorted_pos[len(sorted_pos) // 4]
    p75 = sorted_pos[(len(sorted_pos) * 3) // 4]
    spread = max(positions) - min(positions)
    min_gap = max(DEFAULT_MIN_HYSTERESIS, spread // 3)

    mid = (max(positions) + min(positions)) / 2
    upper_var = sum((p - mid) ** 2 for p in positions if p >= mid) / max(
        sum(1 for p in positions if p >= mid), 1
    )
    lower_var = sum((p - mid) ** 2 for p in positions if p < mid) / max(
        sum(1 for p in positions if p < mid), 1
    )
    closed_is_greater = upper_var >= lower_var

    if closed_is_greater:
        thresh_closed = p75
        thresh_open = p25
        if thresh_closed - thresh_open < min_gap:
            center = (thresh_closed + thresh_open) // 2
            thresh_closed = center + min_gap // 2
            thresh_open = center - min_gap // 2
    else:
        thresh_closed = p25
        thresh_open = p75
        if thresh_open - thresh_closed < min_gap:
            center = (thresh_closed + thresh_open) // 2
            thresh_closed = center - min_gap // 2
            thresh_open = center + min_gap // 2

    return axis, closed_is_greater, int(thresh_closed), int(thresh_open)
