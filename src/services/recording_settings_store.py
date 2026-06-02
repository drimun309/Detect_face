"""Persist recording settings to JSON."""

import json
from pathlib import Path

from src.schema.settings_schema import RecordingSettingsSchema


class RecordingSettingsStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._defaults = RecordingSettingsSchema()

    def get(self) -> RecordingSettingsSchema:
        if not self.path.exists():
            return self._defaults.model_copy()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return RecordingSettingsSchema.model_validate(
                {**self._defaults.model_dump(), **(data or {})}
            )
        except Exception:
            return self._defaults.model_copy()

    def save(self, settings: RecordingSettingsSchema) -> RecordingSettingsSchema:
        self.path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        return settings

