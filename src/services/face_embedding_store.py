"""Кэш эмбеддингов лиц из PostgreSQL для сравнения на потоке."""

import time
from dataclasses import dataclass

import numpy as np
from sqlmodel import select

from src.db.pg_db import PgSyncDb
from src.schema.fr_schema import FacesFrSqlSchema
from src.utils.logger import get_logger

log = get_logger()


def _to_numpy(embedding) -> np.ndarray:
    """pgvector / list / ndarray → float32 вектор."""
    if embedding is None:
        return np.array([], dtype=np.float32)
    if isinstance(embedding, np.ndarray):
        arr = embedding.astype(np.float32, copy=False)
    else:
        arr = np.array(embedding, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm > 1e-6:
        arr = arr / norm
    return arr


@dataclass
class KnownFace:
    id: int
    name: str
    embedding: np.ndarray


class FaceEmbeddingStore:
    """Загружает таблицу faces и сравнивает эмбеддинги кадра с БД."""

    def __init__(self, db: PgSyncDb, refresh_interval_sec: float = 30.0) -> None:
        self.db = db
        self.refresh_interval_sec = refresh_interval_sec
        self._lock = db.lock
        self._faces: list[KnownFace] = []
        self._loaded_at = 0.0

    @property
    def count(self) -> int:
        return len(self._faces)

    def reload(self) -> int:
        """Полная перезагрузка из PostgreSQL."""
        with self._lock:
            rows = self.db.session.exec(select(FacesFrSqlSchema)).all()
            loaded: list[KnownFace] = []
            for row in rows:
                emb = _to_numpy(row.embedding)
                if emb.size == 0:
                    log.warning(f"Skip face id={row.id} name={row.name}: empty embedding")
                    continue
                loaded.append(KnownFace(id=row.id, name=row.name, embedding=emb))
            self._faces = loaded
            self._loaded_at = time.time()

        log.info(f"Loaded {len(loaded)} face embedding(s) from PostgreSQL")
        return len(loaded)

    def ensure_fresh(self) -> None:
        if time.time() - self._loaded_at >= self.refresh_interval_sec:
            self.reload()

    def invalidate(self) -> None:
        """Сброс TTL — следующий кадр перечитает БД."""
        with self._lock:
            self._loaded_at = 0.0

    def match_one(
        self,
        embedding: list[float],
        distance_threshold: float,
        min_det_score: float = 0.0,
        det_score: float = 1.0,
    ) -> tuple[str | None, float | None]:
        if det_score < min_det_score:
            return None, None

        query = _to_numpy(embedding)
        if query.size == 0:
            return None, None

        with self._lock:
            faces = list(self._faces)

        if not faces:
            return None, None

        best_name: str | None = None
        best_dist = float("inf")
        for face in faces:
            dist = 1.0 - float(np.dot(query, face.embedding))
            if dist < best_dist:
                best_dist = dist
                best_name = face.name

        if best_name is not None and best_dist < distance_threshold:
            return best_name, best_dist
        return None, best_dist if best_dist != float("inf") else None

    def match_batch(
        self,
        embeddings: list[list[float]],
        scores: list[float],
        distance_threshold: float,
        min_det_score: float = 0.5,
    ) -> tuple[list[str | None], list[float | None]]:
        self.ensure_fresh()
        names: list[str | None] = []
        distances: list[float | None] = []
        for embd, score in zip(embeddings, scores):
            name, dist = self.match_one(
                embd,
                distance_threshold,
                min_det_score=min_det_score,
                det_score=score,
            )
            names.append(name)
            distances.append(dist)
        return names, distances

    def match_via_pgvector(
        self,
        embedding: list[float],
        distance_threshold: float,
    ) -> tuple[str | None, float | None]:
        """Один запрос в БД через pgvector (как в FrApi)."""
        with self.db.lock:
            rows = self.db.session.exec(
                select(FacesFrSqlSchema)
                .filter(FacesFrSqlSchema.embedding.cosine_distance(embedding) < distance_threshold)
                .order_by(FacesFrSqlSchema.embedding.cosine_distance(embedding))
                .limit(1)
            ).all()
        if not rows:
            return None, None
        face = rows[0]
        query = _to_numpy(embedding)
        ref = _to_numpy(face.embedding)
        dist = 1.0 - float(np.dot(query, ref))
        return face.name, dist


_store: FaceEmbeddingStore | None = None


def init_face_embedding_store(db: PgSyncDb, refresh_interval_sec: float = 30.0) -> FaceEmbeddingStore:
    global _store
    _store = FaceEmbeddingStore(db, refresh_interval_sec=refresh_interval_sec)
    _store.reload()
    return _store


def get_face_embedding_store() -> FaceEmbeddingStore | None:
    return _store
