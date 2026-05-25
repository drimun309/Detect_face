"""Persist detection settings to JSON."""

import json
from pathlib import Path

from src.schema.configs import Configs
from src.schema.settings_schema import DetectionSettingsSchema


class SettingsStore:
    def __init__(self, path: str, cfg: Configs) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._defaults = DetectionSettingsSchema(
            fr_det_conf=cfg.FR_DET_CONF,
            fr_det_nms=cfg.FR_DET_NMS,
            fr_distance=cfg.FR_DISTANCE,
            min_det_score=cfg.FR_MIN_DET_SCORE,
            stream_frame_interval=cfg.STREAM_FRAME_INTERVAL,
            stream_fps=cfg.STREAM_FPS,
            stream_width=cfg.STREAM_WIDTH,
            stream_height=cfg.STREAM_HEIGHT,
            stream_show_unknown_distance=cfg.STREAM_SHOW_UNKNOWN_DISTANCE,
            embedding_refresh_sec=cfg.EMBEDDING_REFRESH_SEC,
        )

    def get(self) -> DetectionSettingsSchema:
        if not self.path.exists():
            return self._defaults.model_copy()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return DetectionSettingsSchema.model_validate({**self._defaults.model_dump(), **data})
        except Exception:
            return self._defaults.model_copy()

    def save(self, settings: DetectionSettingsSchema) -> DetectionSettingsSchema:
        self.path.write_text(
            settings.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return settings
