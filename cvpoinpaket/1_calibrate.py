import cv2
from pathlib import Path

from handle_detector import (
    FixedRoiDetector,
    MotionDetector,
    draw_fixed_roi,
    draw_score_graph,
    probe_thresholds,
    warn_if_roi_too_large,
)

VIDEO_PATH = Path(__file__).parent / "video" / "130906.mp4"
CONFIG_PATH = Path(__file__).parent / "calibration.txt"
DEFAULT_SLOWMO = 5  # во сколько раз медленнее реального времени

cap = cv2.VideoCapture(str(VIDEO_PATH))
ret, first_frame = cap.read()
if not ret:
    print("Не удалось открыть видео:", VIDEO_PATH)
    exit(1)

print("=" * 50)
print("ЭТАП 1: Выбор области на ручке В ПОКОЕ")
print("Выделите небольшой участок ручки в исходном положении")
print("Нажмите ENTER")
print("=" * 50)

roi = cv2.selectROI("Выделите ручку в покое (маленький прямоугольник)", first_frame, fromCenter=False)
cv2.destroyWindow("Выделите ручку в покое (маленький прямоугольник)")

x_roi, y_roi, w_roi, h_roi = [int(v) for v in roi]
if w_roi == 0 or h_roi == 0:
    print("ROI не выбран. Завершение.")
    cap.release()
    exit(1)

roi = (x_roi, y_roi, w_roi, h_roi)
warn_if_roi_too_large(roi)
print(f"ROI: x={x_roi}, y={y_roi}, w={w_roi}, h={h_roi}")

handle = FixedRoiDetector(roi)
handle.set_reference(first_frame)

print("\nАвтоопределение порогов...")
init_spike, init_rest = probe_thresholds(cap, roi)
print(f"Пороги ~ spike>{init_spike}, rest<{init_rest}")

print("\n" + "=" * 50)
print("ЭТАП 2: Настройка")
print("Жёлтая линия на графике = всплеск (spike), не общий diff")
print("Красная = порог срабатывания")
print("Пробел = пауза | + / - = быстрее / медленнее")
print("q = сохранить")
print("=" * 50)

video_fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
base_delay_ms = max(1, int(1000 / video_fps))

cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Calibration", 900, 600)
cv2.createTrackbar("SPIKE_THRESH", "Calibration", init_spike, 60, lambda x: None)
cv2.createTrackbar("REST_THRESH", "Calibration", init_rest, 30, lambda x: None)
cv2.createTrackbar("SLOWMO x", "Calibration", DEFAULT_SLOWMO, 20, lambda x: None)

motion = MotionDetector(init_spike, init_rest)
diff_history = []
activity_history = []
max_history = 200
frame_idx = 0
events = []
final_spike = init_spike
final_rest = init_rest
paused = False

while cap.isOpened():
    if not paused:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            diff_history.clear()
            activity_history.clear()
            motion.reset()
            handle.set_reference(first_frame)
            frame_idx = 0
            continue

        score = handle.measure(frame)
        spike_thresh = cv2.getTrackbarPos("SPIKE_THRESH", "Calibration")
        rest_thresh = cv2.getTrackbarPos("REST_THRESH", "Calibration")
        final_spike = spike_thresh
        final_rest = rest_thresh
        motion.set_thresholds(spike_thresh, rest_thresh)

        if motion.update(score, frame_idx):
            events.append(frame_idx)
            print(f"  [{frame_idx}] СРАБАТЫВАНИЕ! spike={motion.activity:.1f} diff={score:.1f}")

        handle.adapt_reference_if_resting(frame, motion.activity, rest_thresh)

        diff_history.append(score)
        activity_history.append(motion.activity)
        if len(diff_history) > max_history:
            diff_history.pop(0)
            activity_history.pop(0)

        frame_idx += 1

    slowmo = max(1, cv2.getTrackbarPos("SLOWMO x", "Calibration"))
    spike_thresh = cv2.getTrackbarPos("SPIKE_THRESH", "Calibration")
    rest_thresh = cv2.getTrackbarPos("REST_THRESH", "Calibration")
    delay_ms = base_delay_ms * slowmo

    armed = "ARMED" if motion.armed else "wait"
    color = (0, 255, 0) if motion.state == "CLOSED" else (200, 200, 200)
    pause_label = "PAUSE" if paused else f"{slowmo}x"
    cv2.putText(
        frame,
        f"spike: {motion.activity:.1f}  diff: {score:.1f}  Events: {len(events)}  {armed}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        color,
        2,
    )
    cv2.putText(
        frame,
        f"fire>{spike_thresh}  rest<{rest_thresh}  [{pause_label}]  frame {frame_idx}",
        (10, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (180, 180, 180),
        1,
    )

    draw_fixed_roi(frame, roi, motion.state)
    draw_score_graph(frame, diff_history, activity_history, spike_thresh, rest_thresh, max_history)

    cv2.imshow("Calibration", frame)

    key = cv2.waitKey(50 if paused else delay_ms) & 0xFF
    if key == ord("q"):
        break
    if key == ord(" "):
        paused = not paused
    elif key in (ord("+"), ord("=")):
        pos = min(20, cv2.getTrackbarPos("SLOWMO x", "Calibration") + 1)
        cv2.setTrackbarPos("SLOWMO x", "Calibration", pos)
    elif key in (ord("-"), ord("_")):
        pos = max(1, cv2.getTrackbarPos("SLOWMO x", "Calibration") - 1)
        cv2.setTrackbarPos("SLOWMO x", "Calibration", pos)

cap.release()
cv2.destroyAllWindows()

config = f"""# Настройки калибровки (автоматически читаются в 2_detect.py)
ROI_X = {x_roi}
ROI_Y = {y_roi}
ROI_W = {w_roi}
ROI_H = {h_roi}
SPIKE_THRESH = {final_spike}
REST_THRESH = {final_rest}
COOLDOWN_FRAMES = 8
"""

print("\n" + "=" * 50)
print("СОХРАНЁННЫЕ НАСТРОЙКИ:")
print("=" * 50)
print(config)

CONFIG_PATH.write_text(config, encoding="utf-8")
print(f"Сохранено в {CONFIG_PATH}")
