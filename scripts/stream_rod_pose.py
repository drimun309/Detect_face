"""Тестовый стрим: видео → best_pose.pt + RodTracker → браузер с перемоткой.

    py -3.12 scripts/stream_rod_pose.py
    py -3.12 scripts/stream_rod_pose.py "C:\\path\\to\\video.mp4"

Откройте http://127.0.0.1:8767
Управление: play/pause, скорость, слайдер перемотки.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import cv2
from flask import Flask, Response, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from src.engine.rod_pose_engine import RodPoseEngine  # noqa: E402
from src.utils.face_draw import draw_rod_pose_overlay, get_cyrillic_font  # noqa: E402
from src.utils.rod_metrics import RodTracker  # noqa: E402


def draw_events_badge(frame: np.ndarray, count: int) -> np.ndarray:
    """Крупный бейдж числа событий только для тестового стрима."""
    text = f"События: {int(count)}"
    font_size = 36
    padding = 12
    margin = 16
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil)
    font = get_cyrillic_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = pil.width - tw - padding * 2 - margin
    y = margin
    draw.rectangle(
        [x, y, x + tw + padding * 2, y + th + padding * 2],
        fill=(16, 40, 28),
        outline=(61, 214, 140),
        width=2,
    )
    draw.text((x + padding, y + padding), text, font=font, fill=(120, 255, 180))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

DEFAULT_VIDEO = Path(r"C:\Users\Dudu\Desktop\датасет пакеты\videopaket\142959.mp4")
DEFAULT_MODEL = ROOT / "assets" / "best_pose.pt"
WEB_PORT = 8767

app = Flask(__name__)
state = {
    "frame_jpeg": None,
    "fps": 0.0,
    "errors": 0,
    "frame_idx": 0,
    "total_frames": 0,
    "duration_sec": 0.0,
    "file_fps": 25.0,
    "source": "",
    "playing": True,
    "speed": 1.0,
    "seek_to": None,  # float seconds or None
    "reset_tracker": False,
    "rod_angle": 0.0,
    "rod_ref_dA": 0.0,
    "rod_press_count": 0,
    "rod_armed": True,
    "rod_post_event": False,
    "detected": False,
    "lock": threading.Lock(),
}


def mjpeg_stream():
    while True:
        with state["lock"]:
            frame = state["frame_jpeg"]
        if frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(0.03)


@app.route("/")
def index():
    name = Path(state["source"]).name if state["source"] else "rod pose"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Rod pose — {name}</title>
<style>
  :root {{
    --bg: #111;
    --panel: #1c1c1c;
    --text: #eee;
    --muted: #9a9a9a;
    --accent: #3dd68c;
  }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font-family: Segoe UI, sans-serif; text-align: center;
  }}
  h2 {{ margin: 12px; font-weight: 600; }}
  img {{
    max-width: 96vw; max-height: 72vh; border: 2px solid #333;
    background: #000;
  }}
  .panel {{
    margin: 12px auto 20px; max-width: 920px; padding: 12px 16px;
    background: var(--panel); border-radius: 10px; text-align: left;
  }}
  .row {{
    display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
    margin: 8px 0;
  }}
  button, select {{
    background: #2a2a2a; color: var(--text); border: 1px solid #444;
    border-radius: 6px; padding: 8px 12px; cursor: pointer;
  }}
  button:hover {{ border-color: var(--accent); }}
  #seek {{ width: 100%; accent-color: var(--accent); }}
  #stats, #time {{ color: var(--muted); font-size: 14px; }}
  .ok {{ color: var(--accent); }}
  .events-box {{
    display: inline-flex; align-items: baseline; gap: 10px;
    margin: 8px 0 4px; padding: 10px 18px;
    background: #12261c; border: 1px solid #2f8f5b; border-radius: 10px;
  }}
  .events-box .label {{ color: #9fd9b8; font-size: 15px; }}
  .events-box .count {{
    color: var(--accent); font-size: 42px; font-weight: 700; line-height: 1;
    min-width: 1.4em; text-align: right;
  }}
  .events-box.flash {{
    border-color: #7dffb3; box-shadow: 0 0 0 2px rgba(61, 214, 140, 0.35);
  }}
</style></head><body>
  <h2>Rod pose — {name}</h2>
  <div class="events-box" id="eventsBox">
    <span class="label">События (нажатия)</span>
    <span class="count" id="eventsCount">0</span>
  </div>
  <img id="video" src="/video_feed" alt="stream">
  <div class="panel">
    <div class="row">
      <button id="play">⏸ Pause</button>
      <button id="reset">Reset tracker</button>
      <label>Скорость
        <select id="speed">
          <option value="0.25">0.25×</option>
          <option value="0.5">0.5×</option>
          <option value="1" selected>1×</option>
          <option value="1.5">1.5×</option>
          <option value="2">2×</option>
        </select>
      </label>
      <span id="time">00:00 / 00:00</span>
    </div>
    <input id="seek" type="range" min="0" max="1000" value="0" step="1">
    <p id="stats">загрузка…</p>
  </div>
  <script>
    const seek = document.getElementById('seek');
    const playBtn = document.getElementById('play');
    const resetBtn = document.getElementById('reset');
    const speedSel = document.getElementById('speed');
    const timeEl = document.getElementById('time');
    const statsEl = document.getElementById('stats');
    const eventsCountEl = document.getElementById('eventsCount');
    const eventsBox = document.getElementById('eventsBox');
    let dragging = false;
    let playing = true;
    let lastEvents = 0;

    function fmt(sec) {{
      sec = Math.max(0, Math.floor(sec || 0));
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
    }}

    async function post(path, body) {{
      await fetch(path, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(body || {{}})
      }});
    }}

    playBtn.onclick = async () => {{
      playing = !playing;
      playBtn.textContent = playing ? '⏸ Pause' : '▶ Play';
      await post('/api/play', {{ playing }});
    }};
    resetBtn.onclick = () => post('/api/reset', {{}});
    speedSel.onchange = () => post('/api/speed', {{ speed: Number(speedSel.value) }});

    seek.addEventListener('mousedown', () => {{ dragging = true; }});
    seek.addEventListener('touchstart', () => {{ dragging = true; }});
    seek.addEventListener('mouseup', async () => {{
      dragging = false;
      const t = Number(seek.value) / 1000 * (window._dur || 0);
      await post('/api/seek', {{ t }});
    }});
    seek.addEventListener('touchend', async () => {{
      dragging = false;
      const t = Number(seek.value) / 1000 * (window._dur || 0);
      await post('/api/seek', {{ t }});
    }});

    setInterval(async () => {{
      const s = await fetch('/stats').then(r => r.json());
      window._dur = s.duration_sec || 0;
      if (!dragging && s.duration_sec > 0) {{
        seek.value = Math.round(1000 * s.frame_idx / Math.max(1, s.total_frames));
      }}
      timeEl.textContent = fmt(s.frame_idx / Math.max(1, s.file_fps))
        + ' / ' + fmt(s.duration_sec);
      const events = Number(s.rod_press_count || 0);
      eventsCountEl.textContent = String(events);
      if (events > lastEvents) {{
        eventsBox.classList.add('flash');
        setTimeout(() => eventsBox.classList.remove('flash'), 700);
      }}
      lastEvents = events;
      let t = 'FPS ~ ' + Number(s.fps || 0).toFixed(1);
      t += ' · угол ' + Number(s.rod_angle || 0).toFixed(1) + '°';
      t += ' · dA ' + Number(s.rod_ref_dA || 0).toFixed(1) + '°';
      t += ' · <b>событий ' + events + '</b>';
      t += ' · ' + (s.rod_armed ? 'ARMED' : (s.rod_post_event ? 'COOLDOWN' : 'DISARM'));
      t += s.detected ? ' · <span class="ok">палка найдена</span>' : ' · палка не найдена';
      if (s.errors) t += ' · ошибки: ' + s.errors;
      statsEl.innerHTML = t;
      if (s.playing !== playing) {{
        playing = !!s.playing;
        playBtn.textContent = playing ? '⏸ Pause' : '▶ Play';
      }}
    }}, 400);
  </script>
</body></html>"""


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/stats")
def stats():
    with state["lock"]:
        return jsonify(
            {
                "fps": state["fps"],
                "errors": state["errors"],
                "frame_idx": state["frame_idx"],
                "total_frames": state["total_frames"],
                "duration_sec": state["duration_sec"],
                "file_fps": state["file_fps"],
                "source": state["source"],
                "playing": state["playing"],
                "speed": state["speed"],
                "rod_angle": state["rod_angle"],
                "rod_ref_dA": state["rod_ref_dA"],
                "rod_press_count": state["rod_press_count"],
                "rod_armed": state["rod_armed"],
                "rod_post_event": state["rod_post_event"],
                "detected": state["detected"],
            }
        )


@app.route("/api/play", methods=["POST"])
def api_play():
    data = request.get_json(silent=True) or {}
    with state["lock"]:
        state["playing"] = bool(data.get("playing", True))
    return jsonify({"ok": True, "playing": state["playing"]})


@app.route("/api/speed", methods=["POST"])
def api_speed():
    data = request.get_json(silent=True) or {}
    speed = float(data.get("speed", 1.0))
    speed = max(0.1, min(4.0, speed))
    with state["lock"]:
        state["speed"] = speed
    return jsonify({"ok": True, "speed": speed})


@app.route("/api/seek", methods=["POST"])
def api_seek():
    data = request.get_json(silent=True) or {}
    t = float(data.get("t", 0.0))
    with state["lock"]:
        state["seek_to"] = max(0.0, t)
    return jsonify({"ok": True, "t": t})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    with state["lock"]:
        state["reset_tracker"] = True
    return jsonify({"ok": True})


def capture_loop(video_path: Path, model_path: Path, conf: float, imgsz: int) -> None:
    engine = RodPoseEngine(str(model_path), device="gpu")
    engine.setup()
    tracker = RodTracker()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Не удалось открыть видео: {video_path}")
        with state["lock"]:
            state["errors"] += 1
        return

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    file_fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    if file_fps <= 1e-3:
        file_fps = 25.0
    duration = total / file_fps if total > 0 else 0.0

    with state["lock"]:
        state["source"] = str(video_path)
        state["total_frames"] = total
        state["file_fps"] = file_fps
        state["duration_sec"] = duration

    print(f"Видео: {video_path}")
    print(f"Кадров: {total}, FPS файла: {file_fps:.2f}, длительность: {duration:.1f}s")
    print(f"Модель: {model_path}")

    frames = 0
    t0 = time.time()
    idx = 0

    while True:
        with state["lock"]:
            playing = state["playing"]
            speed = state["speed"]
            seek_to = state["seek_to"]
            do_reset = state["reset_tracker"]
            state["seek_to"] = None
            state["reset_tracker"] = False

        if do_reset:
            presses = tracker.change_count
            tracker.reset()
            tracker.change_count = presses
            print("RodTracker reset (счётчик нажатий сохранён)")

        if seek_to is not None:
            frame_no = int(round(seek_to * file_fps))
            frame_no = max(0, min(max(total - 1, 0), frame_no))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            idx = frame_no

        if not playing:
            time.sleep(0.05)
            continue

        ok, frame = cap.read()
        if not ok or frame is None:
            if total > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                idx = 0
                continue
            with state["lock"]:
                state["errors"] += 1
            time.sleep(0.2)
            continue

        now = time.time()
        det = engine.predict(frame, conf=conf, imgsz=imgsz)
        annotated = frame
        press_count = 0
        with state["lock"]:
            press_count = int(state["rod_press_count"])

        if det is not None:
            upd = tracker.update(det.angle_deg, ts=now)
            press_count = int(upd.change_count)
            annotated = draw_rod_pose_overlay(
                frame,
                det.top,
                det.bottom,
                ema_angle=float(upd.ema_angle or det.angle_deg),
                ref_dA=float(upd.ref_dA),
                press_count=press_count,
                armed=bool(upd.armed),
            )
            with state["lock"]:
                state["detected"] = True
                state["rod_angle"] = float(upd.ema_angle or det.angle_deg)
                state["rod_ref_dA"] = float(upd.ref_dA)
                state["rod_press_count"] = press_count
                state["rod_armed"] = bool(upd.armed)
                state["rod_post_event"] = bool(upd.post_event)
            if upd.event_fired:
                print(
                    f"[EVENT] press #{upd.change_count} "
                    f"dA={upd.ref_dA:.1f}° t={idx / file_fps:.1f}s"
                )
        else:
            with state["lock"]:
                state["detected"] = False

        annotated = draw_events_badge(annotated, press_count)

        ok_enc, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ok_enc:
            with state["lock"]:
                state["frame_jpeg"] = jpeg.tobytes()
                state["frame_idx"] = idx

        idx += 1
        frames += 1
        elapsed = time.time() - t0
        if elapsed >= 1.0:
            with state["lock"]:
                state["fps"] = frames / elapsed
            frames = 0
            t0 = time.time()

        delay = (1.0 / file_fps) / max(speed, 0.1)
        time.sleep(max(0.0, delay))


def main() -> int:
    video = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_VIDEO
    if not video.is_absolute():
        video = ROOT / video
    if not video.exists():
        print(f"Видео не найдено: {video}")
        return 1
    if not DEFAULT_MODEL.exists():
        print(f"Модель не найдена: {DEFAULT_MODEL}")
        return 1

    conf = float(os.environ.get("ROD_POSE_CONF", "0.25"))
    imgsz = int(os.environ.get("ROD_POSE_IMGSZ", "640"))
    port = int(os.environ.get("ROD_POSE_PORT", str(WEB_PORT)))

    threading.Thread(
        target=capture_loop,
        args=(video, DEFAULT_MODEL, conf, imgsz),
        daemon=True,
    ).start()

    print(f"Стрим: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
