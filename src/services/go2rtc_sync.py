"""Helpers to sync go2rtc streams from camera configs."""

import os
from pathlib import Path

import yaml

from src.schema.camera_schema import CameraSchema


def _webrtc_candidates() -> list[str]:
    """ICE для браузера на хосте (Chrome): порт 8556 снаружи Docker."""
    candidates = ["127.0.0.1:8556", "stun:stun.l.google.com:19302"]
    extra = os.environ.get("GO2RTC_WEBRTC_CANDIDATE", "").strip()
    if extra and extra not in candidates:
        candidates.insert(0, extra)
    return candidates


def _default_config() -> dict:
    return {
        "streams": {},
        "api": {"listen": ":1984", "origin": "*"},
        "webrtc": {
            "listen": ":8555/tcp",
            "candidates": _webrtc_candidates(),
        },
        "rtsp": {"listen": ":8554"},
        "log": {"level": "info", "format": "text"},
    }


def _build_rtsp_url(camera: CameraSchema) -> str:
    if camera.username and camera.password:
        return (
            f"{camera.protocol}://{camera.username}:{camera.password}@"
            f"{camera.ip}:{camera.port}{camera.path}"
        )
    return f"{camera.protocol}://{camera.ip}:{camera.port}{camera.path}"


def sync_go2rtc_config(
    cameras: list[CameraSchema],
    config_path: str,
    mediamtx_url: str = "rtsp://mediamtx:8554",
) -> None:
    """Rewrite go2rtc config with raw + annotated streams."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        config = _default_config()

    webrtc = config.setdefault("webrtc", {})
    webrtc.setdefault("listen", ":8555/tcp")
    webrtc["candidates"] = _webrtc_candidates()

    streams = config.setdefault("streams", {})
    to_remove = [key for key in streams if key.startswith("cam")]
    for key in to_remove:
        del streams[key]

    base = mediamtx_url.rstrip("/")
    for camera in cameras:
        if not camera.enabled:
            continue
        raw_name = f"cam{camera.id}"
        annot_name = f"{raw_name}_annot"
        streams[raw_name] = [
            _build_rtsp_url(camera),
            f"ffmpeg:{raw_name}#video=h264#hardware",
        ]
        streams[annot_name] = [f"{base}/annot_cam_{camera.id}"]

    path.write_text(
        yaml.dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
