import json
import re
from datetime import datetime
from pathlib import Path

import cv2

from handle_detector import FixedRoiDetector, MotionDetector, draw_fixed_roi

BASE_DIR = Path(__file__).parent
VIDEO_PATH = BASE_DIR / "video" / "130906.mp4"
OUTPUT_VIDEO = BASE_DIR / "output.mp4"
EVENTS_PATH = BASE_DIR / "events.json"
CONFIG_PATH = BASE_DIR / "calibration.txt"

ROI_X, ROI_Y, ROI_W, ROI_H = 300, 100, 40, 40
SPIKE_THRESH, REST_THRESH = 8, 2
COOLDOWN_FRAMES = 8


def load_calibration(path: Path) -> None:
    global ROI_X, ROI_Y, ROI_W, ROI_H, SPIKE_THRESH, REST_THRESH, COOLDOWN_FRAMES

    if not path.exists():
        print(f"Файл {path} не найден — сначала запустите: python 1_calibrate.py")
        return

    text = path.read_text(encoding="utf-8")
    for name in ("ROI_X", "ROI_Y", "ROI_W", "ROI_H", "COOLDOWN_FRAMES"):
        match = re.search(rf"^{name}\s*=\s*(\S+)", text, re.MULTILINE)
        if match:
            globals()[name] = int(match.group(1))

    spike = re.search(r"^SPIKE_THRESH\s*=\s*(\S+)", text, re.MULTILINE)
    rest = re.search(r"^REST_THRESH\s*=\s*(\S+)", text, re.MULTILINE)
    if spike:
        SPIKE_THRESH = int(spike.group(1))
    else:
        for legacy in ("THRESH_CLOSED",):
            match = re.search(rf"^{legacy}\s*=\s*(\S+)", text, re.MULTILINE)
            if match:
                SPIKE_THRESH = int(match.group(1))
    if rest:
        REST_THRESH = int(rest.group(1))
    else:
        for legacy in ("THRESH_OPEN",):
            match = re.search(rf"^{legacy}\s*=\s*(\S+)", text, re.MULTILINE)
            if match:
                REST_THRESH = int(match.group(1))

    print(f"Настройки загружены из {path}")


load_calibration(CONFIG_PATH)

cap = cv2.VideoCapture(str(VIDEO_PATH))
if not cap.isOpened():
    print("Не удалось открыть видео:", VIDEO_PATH)
    exit(1)

fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
ret, first_frame = cap.read()
if not ret:
    print("Не удалось прочитать первый кадр")
    exit(1)

roi = (ROI_X, ROI_Y, ROI_W, ROI_H)
handle = FixedRoiDetector(roi)
handle.set_reference(first_frame)
motion = MotionDetector(SPIKE_THRESH, REST_THRESH, COOLDOWN_FRAMES)

out = cv2.VideoWriter(
    str(OUTPUT_VIDEO),
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))),
)

events = []
frame_idx = 1

while True:
    ret, frame = cap.read()
    if not ret:
        break

    score = handle.measure(frame)
    if motion.update(score, frame_idx):
        events.append(
            {
                "frame": frame_idx,
                "time_sec": round(frame_idx / fps, 3),
                "time_str": datetime.now().isoformat(timespec="seconds"),
                "spike": round(motion.activity, 2),
                "diff_score": round(score, 2),
            }
        )
        print(f"СРАБАТЫВАНИЕ #{len(events)} | кадр={frame_idx} | spike={motion.activity:.1f}")

    handle.adapt_reference_if_resting(frame, motion.activity, REST_THRESH)

    state = motion.state or "OPEN"
    draw_fixed_roi(frame, roi, state)
    color = (0, 255, 0) if state == "CLOSED" else (200, 200, 200)
    cv2.putText(
        frame,
        f"Events: {len(events)} | spike={motion.activity:.1f}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
    )
    out.write(frame)
    frame_idx += 1

cap.release()
out.release()

EVENTS_PATH.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nГотово! Срабатываний: {len(events)}")
print(f"events.json → {EVENTS_PATH}")
print(f"output.mp4 → {OUTPUT_VIDEO}")
