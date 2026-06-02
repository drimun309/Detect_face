"""Runtime detection / recognition settings."""

from typing import Literal

from pydantic import BaseModel, Field


class ShiftSchedule(BaseModel):
    """Время начала и конца смены."""

    enabled: bool = Field(False, description="Включить запись по расписанию")
    start_time: str = Field("09:00", description="Время начала смены HH:MM")
    end_time: str = Field("18:00", description="Время окончания смены HH:MM")


class RecordingSettingsSchema(BaseModel):
    """Настройки записи видео."""

    enabled: bool = Field(False, description="Включить запись")
    retention_days: int = Field(3, ge=1, le=30, description="Сколько дней хранить записи")
    chunk_duration_min: int = Field(10, ge=1, le=60, description="Длительность ролика в минутах")
    shift: ShiftSchedule = Field(default_factory=ShiftSchedule)
    recordings_path: str = Field(
        "data/recordings", description="Путь для хранения записей"
    )


class DetectionSettingsSchema(BaseModel):
    """Параметры точности детекции и распознавания лиц."""

    detection_mode: Literal["face", "person", "face_person"] = Field(
        "face",
        description="Режим детекции: только лица, только люди или вместе",
    )

    fr_det_conf: float = Field(0.25, ge=0.01, le=1.0, description="Порог уверенности детектора YOLOX")
    fr_det_nms: float = Field(0.45, ge=0.01, le=1.0, description="NMS детектора")
    fr_distance: float = Field(
        0.5,
        ge=0.01,
        le=1.5,
        description="Макс. cosine distance для совпадения с БД (меньше — строже)",
    )
    min_det_score: float = Field(
        0.5,
        ge=0.01,
        le=1.0,
        description="Мин. score детекции для сравнения эмбеддинга",
    )
    stream_frame_interval: int = Field(
        2,
        ge=1,
        le=30,
        description="Обрабатывать каждый N-й кадр",
    )
    stream_fps: int = Field(10, ge=1, le=30, description="FPS исходящего потока")
    stream_width: int = Field(1280, ge=320, le=1920)
    stream_height: int = Field(720, ge=240, le=1080)
    stream_show_unknown_distance: bool = Field(
        False,
        description="Показывать расстояние для нераспознанных лиц",
    )
    embedding_refresh_sec: float = Field(
        30.0,
        ge=5.0,
        le=600.0,
        description="Интервал перезагрузки эмбеддингов из PostgreSQL",
    )
