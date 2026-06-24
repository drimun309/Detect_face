"""Detection settings API."""

from fastapi import APIRouter, HTTPException

from src.schema.person_model_catalog import list_person_models
from src.schema.settings_schema import DetectionSettingsSchema
from src.services.settings_store import SettingsStore
from src.streaming.stream_manager import get_stream_manager


class SettingsApi:
    def __init__(self, store: SettingsStore) -> None:
        self.store = store
        self.router = APIRouter()
        self.setup()

    def setup(self) -> None:
        @self.router.get("/settings/person-models")
        async def get_person_models() -> dict:
            return {"items": list_person_models()}

        @self.router.get("/settings/detection", response_model=DetectionSettingsSchema)
        async def get_detection_settings() -> DetectionSettingsSchema:
            return self.store.get()

        @self.router.put("/settings/detection", response_model=DetectionSettingsSchema)
        async def update_detection_settings(
            payload: DetectionSettingsSchema,
        ) -> DetectionSettingsSchema:
            saved = self.store.save(payload)
            try:
                manager = get_stream_manager()
                manager.apply_detection_settings(saved)
            except RuntimeError:
                pass
            return saved
