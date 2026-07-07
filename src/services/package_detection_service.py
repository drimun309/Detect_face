"""Lazy-loaded package/label detector shared across camera streamers."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from src.schema.person_model_catalog import resolve_person_model_path
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.engine.package_yolo_ultralytics_engine import PackageYoloUltralyticsEngine

log = get_logger()

PACKAGE_MODEL_ID = "package_label_stage2"


class PackageDetectionService:
    """Loads YOLO package model only while at least one camera uses it."""

    def __init__(self, model_path: str, provider: str) -> None:
        self._model_path = model_path
        self._provider = provider
        self._lock = threading.Lock()
        self._refs = 0
        self._engine: PackageYoloUltralyticsEngine | None = None

    @property
    def is_loaded(self) -> bool:
        return self._engine is not None

    @property
    def ref_count(self) -> int:
        return self._refs

    def acquire(self) -> PackageYoloUltralyticsEngine:
        from src.engine.package_yolo_ultralytics_engine import PackageYoloUltralyticsEngine

        with self._lock:
            self._refs += 1
            if self._engine is None:
                log.info(f"Package detection module loading ({self._model_path})")
                engine = PackageYoloUltralyticsEngine(
                    model_path=self._model_path,
                    device=self._provider,
                )
                engine.setup()
                self._engine = engine
            return self._engine

    def release(self) -> None:
        with self._lock:
            if self._refs > 0:
                self._refs -= 1
            if self._refs == 0 and self._engine is not None:
                log.info("Package detection module unloaded (no active cameras)")
                self._engine = None

    def get_engine(self) -> PackageYoloUltralyticsEngine | None:
        with self._lock:
            return self._engine


_service: PackageDetectionService | None = None


def init_package_detection_service(model_path: str, provider: str) -> PackageDetectionService:
    global _service
    if _service is None:
        path = model_path or resolve_person_model_path(PACKAGE_MODEL_ID)
        _service = PackageDetectionService(path, provider)
    return _service


def get_package_detection_service() -> PackageDetectionService:
    if _service is None:
        raise RuntimeError("Package detection service not initialized")
    return _service
