"""Разрешение annotated-потока: пресеты и расчёт effective size."""

from __future__ import annotations

MAX_STREAM_WIDTH = 2560
MAX_STREAM_HEIGHT = 1440

STREAM_QUALITY_PRESETS: dict[str, tuple[int | None, int | None]] = {
    "global": (None, None),
    "640x360": (640, 360),
    "960x540": (960, 540),
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
    "2560x1440": (2560, 1440),
}


def clamp_stream_size(width: int, height: int) -> tuple[int, int]:
    w = max(320, min(MAX_STREAM_WIDTH, int(width)))
    h = max(240, min(MAX_STREAM_HEIGHT, int(height)))
    return w, h


def preset_to_size(preset: str) -> tuple[int | None, int | None]:
    key = (preset or "global").strip().lower()
    if key in ("global", "default", ""):
        return None, None
    if key in STREAM_QUALITY_PRESETS:
        return STREAM_QUALITY_PRESETS[key]
    if "x" in key:
        w_str, h_str = key.split("x", 1)
        return clamp_stream_size(int(w_str), int(h_str))
    raise ValueError(f"Неизвестный пресет качества: {preset}")


def size_to_preset(width: int | None, height: int | None) -> str:
    if width is None or height is None:
        return "global"
    w, h = int(width), int(height)
    for preset, (pw, ph) in STREAM_QUALITY_PRESETS.items():
        if preset != "global" and pw == w and ph == h:
            return preset
    return f"{w}x{h}"


def resolve_stream_output_size(
    camera_width: int | None,
    camera_height: int | None,
    global_width: int,
    global_height: int,
    session_override: tuple[int, int] | None = None,
) -> tuple[int, int, bool]:
    """Вернуть (width, height, max_quality_flag)."""
    if session_override:
        w, h = clamp_stream_size(*session_override)
    elif camera_width is not None and camera_height is not None:
        w, h = clamp_stream_size(camera_width, camera_height)
    else:
        w, h = clamp_stream_size(global_width, global_height)
    is_max = w >= MAX_STREAM_WIDTH and h >= MAX_STREAM_HEIGHT
    return w, h, is_max
