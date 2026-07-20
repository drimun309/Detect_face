"""Lazy-loaded rod pose detector (только камера «пакеты»)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.engine.rod_pose_engine import RodPoseEngine

log = get_logger()


class RodPoseService:
    def __init__(self, model_path: str, provider: str) -> None:
        self._model_path = model_path
        self._provider = provider
        self._lock = threading.Lock()
        self._refs = 0
        self._engine: RodPoseEngine | None = None

    def acquire(self) -> RodPoseEngine:
        from src.engine.rod_pose_engine import RodPoseEngine

        with self._lock:
            self._refs += 1
            if self._engine is None:
                log.info(f"Rod pose module loading ({self._model_path})")
                engine = RodPoseEngine(
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
                log.info("Rod pose module unloaded (no active cameras)")
                self._engine = None


_service: RodPoseService | None = None


def init_rod_pose_service(model_path: str, provider: str) -> RodPoseService:
    global _service
    if _service is None:
        _service = RodPoseService(model_path, provider)
    return _service


def get_rod_pose_service() -> RodPoseService:
    if _service is None:
        raise RuntimeError("Rod pose service not initialized")
    return _service
