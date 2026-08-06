"""Application settings."""

import rootutils

ROOT = rootutils.autosetup()

from typing import Any, List, Literal, Union

from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> Union[List[str], str]:
    """Parse CORS origins."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, Union[list, str]):
        return v
    raise ValueError(v)


class Configs(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # api settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 6090
    API_WORKERS: int = 1
    SERVER: Literal["uvicorn", "gunicorn"] = "uvicorn"

    # postgres settings
    POSTGRES_HOST: str = "vision-fr-pg"
    POSTGRES_PORT: int = 7031
    POSTGRES_USER: str = "didi"
    POSTGRES_PASSWORD: str = "didi123"
    POSTGRES_DB: str = "vision-fr"

    # fr engine (YOLOX + MobileFaceNet)
    FR_DET_ENGINE_PATH: str = "assets/yoloxs_face.onnx"
    FR_REC_ENGINE_PATH: str = "assets/w600k_mbf.onnx"
    PERSON_DET_ENGINE_PATH: str = "assets/yolov8s.pt"
    FR_DET_MAX_END2END: int = 100
    FR_PROVIDER: Literal["cpu", "gpu"] = "cpu"

    # streaming stack (go2rtc + mediamtx)
    GO2RTC_CONFIG_PATH: str = "go2rtc/go2rtc.yaml"
    GO2RTC_RTSP_URL: str = "rtsp://go2rtc:8554"
    MEDIAMTX_URL: str = "rtsp://mediamtx:8554"
    ENABLE_ANNOTATED_STREAM: bool = True
    STREAM_WIDTH: int = 1280
    STREAM_HEIGHT: int = 720
    STREAM_FPS: int = 10
    STREAM_FRAME_INTERVAL: int = 1
    STREAM_SHOW_UNKNOWN_DISTANCE: bool = False
    ROI_TIMER_SWITCH_SEC: float = 60.0
    ROI_TIMER_RESET_GRACE_SEC: float = 7.0
    PACKAGE_DET_MODEL_PATH: str = "assets/package_label_stage2.pt"
    PACKAGE_DET_CONF: float = 0.25
    PACKAGE_DET_IMGSZ: int = 960
    PACKAGE_COUNT_DWELL_SEC: float = 1.0
    ROD_POSE_MODEL_PATH: str = "assets/best_pala_roi.pt"
    ROD_POSE_CONF: float = 0.25
    ROD_POSE_IMGSZ: int = 640
    SEALER_CYCLE_DWELL_SEC: float = 1.0
    DETECTION_MODE: Literal["off", "face", "person", "face_person"] = "off"
    FR_DET_CONF: float = 0.25
    FR_DET_NMS: float = 0.45
    FR_DISTANCE: float = 0.5
    FR_MIN_DET_SCORE: float = 0.5
    EMBEDDING_REFRESH_SEC: float = 30.0
    DETECTION_SETTINGS_PATH: str = "data/backend/detection_settings.json"


cfg = Configs()
