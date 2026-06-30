"""Простой стрим: RTSP или MP4 → YOLO (package + label) → браузер.

    py -3.12 scripts/stream_pakety.py
    py -3.12 scripts/stream_pakety.py data/backend/recordings/.../102545.mp4

Откройте http://127.0.0.1:8766
Настройки: config/pakety_stream.json
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote

import cv2
from flask import Flask, Response

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "pakety_stream.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"Нет файла {CONFIG_PATH}")
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def build_rtsp_url(cfg: dict) -> str:
    if cfg.get("rtsp_url"):
        return str(cfg["rtsp_url"])
    rtsp = cfg.get("rtsp") or {}
    user = rtsp.get("username") or ""
    password = rtsp.get("password") or ""
    ip = rtsp.get("ip", "127.0.0.1")
    port = int(rtsp.get("port", 554))
    path = rtsp.get("path", "/stream")
    if not path.startswith("/"):
        path = "/" + path
    if user and password:
        auth = f"{quote(user)}:{quote(password)}@"
    elif user:
        auth = f"{quote(user)}@"
    else:
        auth = ""
    return f"rtsp://{auth}{ip}:{port}{path}"


app = Flask(__name__)
state = {
    "frame_jpeg": None,
    "fps": 0.0,
    "errors": 0,
    "packages": 0,
    "labels": 0,
    "frame_idx": 0,
    "total_frames": 0,
    "source": "",
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
    name = app.config.get("camera_name", "пакеты")
    port = app.config.get("web_port", 8766)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{name}</title>
<style>
  body {{ margin:0; background:#111; color:#eee; font-family:sans-serif; text-align:center; }}
  h2 {{ margin:12px; }}
  img {{ max-width:98vw; max-height:88vh; border:2px solid #333; }}
  p {{ color:#aaa; }}
</style></head><body>
  <h2>{name} — package + label</h2>
  <p id="source" style="color:#888;font-size:14px"></p>
  <img src="/video_feed" alt="stream">
  <p id="stats">загрузка…</p>
  <script>
    setInterval(() => fetch('/stats').then(r=>r.json()).then(s=>{{
      document.getElementById('source').textContent = s.source || '';
      let t = 'FPS ~ ' + s.fps.toFixed(1);
      t += ' · пакетов ' + s.packages + ' · этикеток ' + s.labels;
      if (s.total_frames) t += ' · кадр ' + s.frame_idx + '/' + s.total_frames;
      if (s.errors) t += ' · ошибки: ' + s.errors;
      document.getElementById('stats').textContent = t;
    }}), 2000);
  </script>
</body></html>"""


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/stats")
def stats():
    with state["lock"]:
        return {
            "fps": state["fps"],
            "errors": state["errors"],
            "packages": state["packages"],
            "labels": state["labels"],
            "frame_idx": state["frame_idx"],
            "total_frames": state["total_frames"],
            "source": state["source"],
        }


def _count_detections(result) -> tuple[int, int]:
    packages = labels = 0
    if result.boxes is None or len(result.boxes) == 0:
        return packages, labels
    names = result.names or {}
    for box in result.boxes:
        cls_idx = int(box.cls[0].item()) if box.cls is not None else -1
        name = str(names.get(cls_idx, "")).lower()
        if name == "package":
            packages += 1
        elif name == "label":
            labels += 1
    return packages, labels


def _open_capture(source: str) -> cv2.VideoCapture:
    if source.lower().startswith("rtsp://"):
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap
    cap = cv2.VideoCapture(source)
    return cap


def capture_loop(source: str, model_path: Path, conf: float, imgsz: int) -> None:
    from ultralytics import YOLO

    os.chdir(ROOT)
    is_file = not source.lower().startswith("rtsp://")
    print(f"Модель: {model_path}")
    print(f"Источник: {source}")

    model = YOLO(str(model_path))
    cap = _open_capture(source)
    if not cap.isOpened():
        print("Не удалось открыть источник видео")
        with state["lock"]:
            state["errors"] += 1
        return

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) if is_file else 0
    file_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_delay = 1.0 / max(file_fps, 1.0) if is_file else 0.0

    with state["lock"]:
        state["source"] = source
        state["total_frames"] = total

    frames = 0
    t0 = time.time()
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            if is_file:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                idx = 0
                continue
            with state["lock"]:
                state["errors"] += 1
            time.sleep(0.5)
            cap.release()
            cap = _open_capture(source)
            continue

        result = model.predict(
            frame,
            conf=conf,
            imgsz=imgsz,
            verbose=False,
            device=0,
        )[0]
        annotated = result.plot()
        pkg, lbl = _count_detections(result)

        ok_enc, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ok_enc:
            with state["lock"]:
                state["frame_jpeg"] = jpeg.tobytes()
                state["packages"] = pkg
                state["labels"] = lbl
                state["frame_idx"] = idx

        idx += 1
        frames += 1
        elapsed = time.time() - t0
        if elapsed >= 2.0:
            with state["lock"]:
                state["fps"] = frames / elapsed
            frames = 0
            t0 = time.time()

        if is_file:
            time.sleep(frame_delay)


def resolve_source(cfg: dict, cli_arg: str | None) -> str:
    if cli_arg:
        p = Path(cli_arg)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            print(f"Файл не найден: {p}")
            sys.exit(1)
        return str(p)
    if cfg.get("video"):
        p = Path(cfg["video"])
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            print(f"Видео не найдено: {p}")
            sys.exit(1)
        return str(p)
    return build_rtsp_url(cfg)


def main() -> int:
    cfg = load_config()
    cli_arg = sys.argv[1] if len(sys.argv) > 1 else None
    source = resolve_source(cfg, cli_arg)
    model_path = ROOT / cfg.get("model", "assets/package_label_stage2.pt")
    if not model_path.exists():
        print(f"Модель не найдена: {model_path}")
        return 1

    conf = float(cfg.get("conf", 0.25))
    imgsz = int(cfg.get("imgsz", 960))
    web_port = int(cfg.get("web_port", 8766))

    title = cfg.get("camera_name", "пакеты")
    if not source.lower().startswith("rtsp://"):
        title = Path(source).name
    app.config["camera_name"] = title
    app.config["web_port"] = web_port

    threading.Thread(
        target=capture_loop,
        args=(source, model_path, conf, imgsz),
        daemon=True,
    ).start()

    print(f"Стрим: http://127.0.0.1:{web_port}")
    app.run(host="127.0.0.1", port=web_port, threaded=True, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
