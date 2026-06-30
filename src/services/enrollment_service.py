"""Регистрация лиц по фото/видео — общая логика для CLI, GUI и API."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from sqlmodel import delete, func, select

from src.db.pg_db import PgSyncDb
from src.engine.fr_onnx_engine import FrOnnxEngine
from src.schema.fr_schema import FacesFrSqlSchema

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
LogFn = Callable[[str], None]


@dataclass
class EnrollmentOptions:
    name: str
    every: int = 15
    max_embeddings: int = 30
    replace: bool = False
    conf: float = 0.25
    nms: float = 0.45
    min_score: float = 0.5


@dataclass
class EnrollmentResult:
    saved: int
    photos_ok: int = 0
    photos_skip: int = 0
    frames_ok: int = 0
    frames_skip: int = 0
    logs: list[str] = field(default_factory=list)


def _log_sink(logs: list[str]) -> LogFn:
    def _fn(message: str) -> None:
        logs.append(message)

    return _fn


def is_valid_frame(frame: np.ndarray) -> bool:
    if frame is None or frame.size == 0:
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if float(gray.std()) < 8.0:
        return False
    if float(gray.mean()) < 3.0:
        return False
    return True


def load_image_bytes(data: bytes) -> np.ndarray | None:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None or not is_valid_frame(img):
        return None
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def iter_video_frames(path: Path, every: int):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        if idx % every != 0:
            continue
        if not is_valid_frame(frame):
            continue
        yield idx, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    cap.release()


def is_duplicate(embedding: np.ndarray, collected: list[np.ndarray], threshold: float = 0.92) -> bool:
    if not collected:
        return False
    emb = embedding / max(np.linalg.norm(embedding), 1e-6)
    for existing in collected:
        ex = existing / max(np.linalg.norm(existing), 1e-6)
        if float(np.dot(emb, ex)) > threshold:
            return True
    return False


def extract_embedding(
    engine: FrOnnxEngine,
    rgb: np.ndarray,
    conf: float,
    nms: float,
    min_score: float,
) -> tuple[np.ndarray | None, str]:
    result = engine.predict([rgb], det_conf=conf, det_nms=nms)[0]
    if len(result.boxes) == 0:
        return None, "лицо не найдено"
    if len(result.boxes) > 1:
        return None, "несколько лиц в кадре"
    if result.scores[0] < min_score:
        return None, f"низкая уверенность ({result.scores[0]:.2f})"
    return np.array(result.embeddings[0], dtype=np.float32), "ok"


def save_embeddings(
    db: PgSyncDb,
    name: str,
    embeddings: list[np.ndarray],
    replace: bool,
    log: LogFn,
) -> int:
    with db.lock:
        if replace:
            db.session.exec(delete(FacesFrSqlSchema).where(FacesFrSqlSchema.name == name))
            db.session.commit()
            log(f"Удалены старые записи для «{name}»")

        now = datetime.now()
        for embd in embeddings:
            db.session.add(
                FacesFrSqlSchema(
                    name=name,
                    embedding=embd.tolist(),
                    created_at=now,
                    updated_at=now,
                )
            )
        db.session.commit()
    return len(embeddings)


def list_enrolled_summary(db: PgSyncDb) -> list[dict]:
    with db.lock:
        rows = db.session.exec(
            select(FacesFrSqlSchema.name, func.count(FacesFrSqlSchema.id)).group_by(FacesFrSqlSchema.name)
        ).all()
    return [{"name": name, "count": int(count)} for name, count in sorted(rows, key=lambda x: x[0])]


def delete_person(db: PgSyncDb, name: str) -> int:
    with db.lock:
        faces = db.session.exec(select(FacesFrSqlSchema).where(FacesFrSqlSchema.name == name)).all()
        for face in faces:
            db.session.delete(face)
        db.session.commit()
    return len(faces)


def run_enrollment_upload(
    options: EnrollmentOptions,
    photo_files: list[tuple[str, bytes]],
    video_files: list[tuple[str, bytes]],
    engine: FrOnnxEngine,
    db: PgSyncDb,
) -> EnrollmentResult:
    """Регистрация из загруженных файлов (веб/API)."""
    logs: list[str] = []
    log = _log_sink(logs)
    name = options.name.strip()
    if not name:
        raise ValueError("Укажите имя человека")
    if not photo_files and not video_files:
        raise ValueError("Добавьте хотя бы одно фото или видео")

    collected: list[np.ndarray] = []
    stats = {"photos_ok": 0, "photos_skip": 0, "frames_ok": 0, "frames_skip": 0}

    log(f"Регистрация: {name}")
    log(f"Источники: {len(photo_files)} фото, {len(video_files)} видео")

    for filename, data in photo_files:
        if len(collected) >= options.max_embeddings:
            break
        ext = Path(filename).suffix.lower()
        if ext not in IMAGE_EXT:
            log(f"  [skip] {filename}: неподдерживаемый формат")
            stats["photos_skip"] += 1
            continue
        rgb = load_image_bytes(data)
        if rgb is None:
            log(f"  [skip] {filename}: битое изображение")
            stats["photos_skip"] += 1
            continue
        embd, reason = extract_embedding(engine, rgb, options.conf, options.nms, options.min_score)
        if embd is None:
            log(f"  [skip] {filename}: {reason}")
            stats["photos_skip"] += 1
            continue
        if is_duplicate(embd, collected):
            log(f"  [skip] {filename}: похожий кадр уже есть")
            stats["photos_skip"] += 1
            continue
        collected.append(embd)
        stats["photos_ok"] += 1
        log(f"  [ok]   {filename} ({len(collected)}/{options.max_embeddings})")

    for filename, data in video_files:
        ext = Path(filename).suffix.lower()
        if ext not in VIDEO_EXT:
            log(f"  [skip] {filename}: неподдерживаемый формат видео")
            continue
        log(f"Видео: {filename}")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        try:
            tmp.write(data)
            tmp.close()
            for frame_idx, rgb in iter_video_frames(Path(tmp.name), options.every):
                if len(collected) >= options.max_embeddings:
                    break
                embd, reason = extract_embedding(
                    engine, rgb, options.conf, options.nms, options.min_score
                )
                if embd is None:
                    stats["frames_skip"] += 1
                    continue
                if is_duplicate(embd, collected):
                    stats["frames_skip"] += 1
                    continue
                collected.append(embd)
                stats["frames_ok"] += 1
                log(f"  [ok]   кадр #{frame_idx} ({len(collected)}/{options.max_embeddings})")
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    if not collected:
        raise RuntimeError(
            "Не удалось собрать ни одного эмбеддинга. Проверьте фото/видео и пороги."
        )

    saved = save_embeddings(db, name, collected, options.replace, log)
    log("")
    log(f"Готово: сохранено {saved} эмбеддингов для «{name}»")
    log(
        f"Фото: +{stats['photos_ok']} / -{stats['photos_skip']}, "
        f"видео-кадры: +{stats['frames_ok']} / -{stats['frames_skip']}"
    )
    return EnrollmentResult(saved=saved, logs=logs, **stats)
