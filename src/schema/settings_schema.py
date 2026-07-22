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
    auto_enabled: bool = Field(
        False, description="Автоматически записывать все камеры по расписанию"
    )
    retention_days: int = Field(3, ge=1, le=30, description="Сколько дней хранить записи")
    chunk_duration_min: int = Field(10, ge=1, le=60, description="Длительность ролика в минутах")
    # качество: уменьшаем размер записи отдельным перекодированием
    record_width: int = Field(
        1280, ge=320, le=2560, description="Ширина записи (масштабирование)"
    )
    record_height: int = Field(
        720, ge=240, le=1440, description="Высота записи (масштабирование)"
    )
    record_crf: int = Field(
        28, ge=18, le=40, description="CRF (качество H264): ниже — лучше, выше — меньше размер"
    )
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
    person_det_model: Literal[
        "yolov8s", "crowdhuman_yolov5m", "yolo26n", "package_label_stage2"
    ] = Field(
        "yolov8s",
        description="Модель детекции человека",
    )
    crowdhuman_det_type: Literal["both", "body", "head"] = Field(
        "both",
        description="CrowdHuman: детектировать тело, голову или оба класса",
    )
    person_tracker: Literal["off", "bytetrack", "botsort", "sort"] = Field(
        "bytetrack",
        description="Трекер людей: off / bytetrack / botsort / sort (Kalman)",
    )
    person_track_buffer: int = Field(
        45,
        ge=5,
        le=120,
        description="Сколько кадров держать трек без детекции (предсказание движения)",
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
        1,
        ge=1,
        le=30,
        description="Детекция каждый N-й кадр: 1 = каждый (боксы синхронны), 2/4/... = меньше CPU",
    )
    stream_fps: int = Field(
        10, ge=1, le=30, description="FPS исходящего потока (ffmpeg / веб)"
    )
    stream_width: int = Field(1280, ge=320, le=2560)
    stream_height: int = Field(720, ge=240, le=1440)
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
    roi_timer_switch_sec: float = Field(
        60.0,
        ge=5.0,
        le=300.0,
        description="Секунд подряд «человек в зоне» / «нет» для смены работа↔простой",
    )
    roi_timer_reset_grace_sec: float = Field(
        7.0,
        ge=0.0,
        le=60.0,
        description="Секунд: краткое пропадание детекции не сбрасывает присутствие",
    )
