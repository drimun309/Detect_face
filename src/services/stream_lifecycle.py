"""Auto-start annotated streams for enabled cameras."""

import asyncio
import threading

from src.schema.configs import Configs
from src.services.camera_store import CameraStore
from src.streaming.stream_manager import get_stream_manager
from src.utils.logger import get_logger

log = get_logger()


def _start_enabled_cameras(cfg: Configs, store: CameraStore) -> None:
    if not cfg.ENABLE_ANNOTATED_STREAM:
        return
    manager = get_stream_manager()
    cameras = [c for c in store.list() if c.enabled]
    if not cameras:
        log.info("No enabled cameras for auto-start")
        return
    log.info(f"Auto-starting face streams for {len(cameras)} camera(s)")
    for camera in cameras:
        if manager.start_stream(camera):
            log.info(f"  cam{camera.id} ({camera.name}) started")
        else:
            log.warning(f"  cam{camera.id} ({camera.name}) failed to start")


async def schedule_auto_start(cfg: Configs, store: CameraStore, delay_sec: float = 4.0) -> None:
    await asyncio.sleep(delay_sec)
    thread = threading.Thread(
        target=_start_enabled_cameras,
        args=(cfg, store),
        daemon=True,
        name="auto-start-streams",
    )
    thread.start()
