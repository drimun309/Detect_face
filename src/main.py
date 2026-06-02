"""Main function."""

import rootutils

ROOT = rootutils.autosetup()

from contextlib import asynccontextmanager

from src.schema.configs import Configs, cfg
from src.utils.logger import get_logger

log = get_logger()


def create_lifespan(app_cfg: Configs, camera_store):
    @asynccontextmanager
    async def lifespan(app):
        from src.services.stream_lifecycle import schedule_auto_start
        from src.streaming.stream_manager import shutdown_stream_manager

        await schedule_auto_start(app_cfg, camera_store)
        yield
        shutdown_stream_manager()

    return lifespan


def main_api(cfg: Configs) -> None:
    """Main API function."""
    from fastapi import FastAPI

    from src.api.base_api import BaseApi
    from src.api.camera_api import CameraApi
    from src.api.fr_api import FrApi
    from src.api.server import GunicornServer, UvicornServer
    from src.api.enroll_api import EnrollApi
    from src.api.settings_api import SettingsApi
    from src.api.stream_api import StreamApi
    from src.db.pg_db import PgSyncDb
    from src.schema.camera_sql_schema import CameraSqlSchema  # noqa: F401 — register table
    from src.schema.fr_schema import FacesFrSqlSchema  # noqa: F401
    from src.services.camera_store import CameraStore
    from src.services.settings_store import SettingsStore
    from src.streaming.stream_manager import init_stream_manager

    log.info(f"Starting API server on {cfg.API_HOST}:{cfg.API_PORT}")

    pg = PgSyncDb(
        host=cfg.POSTGRES_HOST,
        port=cfg.POSTGRES_PORT,
        user=cfg.POSTGRES_USER,
        password=cfg.POSTGRES_PASSWORD,
        db=cfg.POSTGRES_DB,
    )
    pg.setup()
    pg.create_all()

    camera_store = CameraStore(pg)
    settings_store = SettingsStore(cfg.DETECTION_SETTINGS_PATH, cfg)
    stream_manager = init_stream_manager(cfg, camera_store=camera_store)
    stream_manager.apply_detection_settings(settings_store.get())
    from src.services.go2rtc_sync import sync_go2rtc_config

    sync_go2rtc_config(
        cameras=camera_store.list(),
        config_path=cfg.GO2RTC_CONFIG_PATH,
        mediamtx_url=cfg.MEDIAMTX_URL,
    )

    camera_api = CameraApi(
        camera_store,
        go2rtc_config_path=cfg.GO2RTC_CONFIG_PATH,
        mediamtx_url=cfg.MEDIAMTX_URL,
    )

    app = FastAPI(
        title="Face Recognition API",
        description="API for face recognition and camera streaming",
        version="1.0.0",
        docs_url="/",
        lifespan=create_lifespan(cfg, camera_store),
    )

    base_api = BaseApi(cfg)
    app.include_router(base_api.router)

    fr_api = FrApi(cfg, engine=stream_manager.engine)
    app.include_router(fr_api.router, prefix="/api/v1/engine", tags=["face-recognition"])

    app.include_router(camera_api.router, prefix="/api/v1", tags=["cameras"])

    stream_api = StreamApi(camera_store)
    app.include_router(stream_api.router, prefix="/api/v1", tags=["streams"])

    settings_api = SettingsApi(settings_store)
    app.include_router(settings_api.router, prefix="/api/v1", tags=["settings"])

    enroll_api = EnrollApi(cfg, settings_store)
    app.include_router(enroll_api.router, prefix="/api/v1", tags=["enrollment"])

    from src.api.recording_api import RecordingApi
    from src.services.recording_service import init_recording_service
    from src.schema.settings_schema import RecordingSettingsSchema

    recording_service = init_recording_service(RecordingSettingsSchema())
    recording_api = RecordingApi()
    app.include_router(recording_api.router, prefix="/api/v1", tags=["recordings"])

    if cfg.SERVER == "gunicorn":
        server = GunicornServer(
            app=app,
            host=cfg.API_HOST,
            port=cfg.API_PORT,
            workers=cfg.API_WORKERS,
        )
    elif cfg.SERVER == "uvicorn":
        server = UvicornServer(
            app=app,
            host=cfg.API_HOST,
            port=cfg.API_PORT,
            workers=cfg.API_WORKERS,
        )
    else:
        raise ValueError(f"Invalid server: {cfg.SERVER}")

    server.run()


if __name__ == "__main__":
    main_api(cfg)
