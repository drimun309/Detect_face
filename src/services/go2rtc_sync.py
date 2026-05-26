"""Helpers to sync go2rtc streams from camera configs."""

import os
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

from src.schema.camera_schema import CameraSchema
from src.utils.logger import get_logger

log = get_logger()


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
        user = quote(camera.username, safe="")
        password = quote(camera.password, safe="")
        return (
            f"{camera.protocol}://{user}:{password}@"
            f"{camera.ip}:{camera.port}{camera.path}"
        )
    return f"{camera.protocol}://{camera.ip}:{camera.port}{camera.path}"


def reload_go2rtc(api_base: str | None = None) -> None:
    """go2rtc не подхватывает yaml без рестарта — нужен POST /api/restart."""
    base = (api_base or os.environ.get("GO2RTC_API_URL", "http://go2rtc:1984")).rstrip("/")
    try:
        resp = requests.post(f"{base}/api/restart", timeout=15)
        resp.raise_for_status()
        log.info("go2rtc restarted after config sync")
    except requests.RequestException as exc:
        log.warning(f"go2rtc restart failed ({base}): {exc}")


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
    reload_go2rtc()
