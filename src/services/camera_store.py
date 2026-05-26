"""Camera storage in PostgreSQL (с миграцией из legacy JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from src.db.pg_db import PgSyncDb
from src.utils.logger import get_logger

log = get_logger()
from src.schema.camera_schema import CameraCreateSchema, CameraSchema, CameraUpdateSchema
from src.schema.camera_sql_schema import CameraSqlSchema

LEGACY_JSON_PATHS = (
    Path("data/backend/cameras.json"),
    Path("data/cameras.json"),
)


class CameraStore:
    """CRUD для камер в PostgreSQL."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = Lock()
        self._migrate_legacy_json_once()
        self._sync_id_sequence()

    def _rollback(self) -> None:
        try:
            self.pg.session.rollback()
        except SQLAlchemyError:
            pass

    def _sync_id_sequence(self) -> None:
        """После импорта с явным id — выровнять SERIAL, иначе duplicate key на id=1."""
        try:
            self.pg.session.exec(
                text(
                    "SELECT setval("
                    "pg_get_serial_sequence('cameras', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM cameras), 1)"
                    ")"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"cameras id sequence sync skipped: {exc}")

    def _migrate_legacy_json_once(self) -> None:
        with self._lock:
            existing = self.pg.session.exec(select(CameraSqlSchema)).first()
            if existing is not None:
                return
            for path in LEGACY_JSON_PATHS:
                if not path.is_file():
                    continue
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if not isinstance(raw, list) or not raw:
                    continue
                for item in raw:
                    row_kw = dict(
                        name=item["name"],
                        ip=item["ip"],
                        port=int(item.get("port", 554)),
                        username=item.get("username"),
                        password=item.get("password"),
                        protocol=item.get("protocol", "rtsp"),
                        path=item.get("path", "/Streaming/Channels/101"),
                        enabled=bool(item.get("enabled", True)),
                    )
                    if item.get("id") is not None:
                        row_kw["id"] = int(item["id"])
                    row = CameraSqlSchema(**row_kw)
                    self.pg.session.add(row)
                self.pg.session.commit()
                self._sync_id_sequence()
                return

    def _to_schema(self, row: CameraSqlSchema) -> CameraSchema:
        return CameraSchema(
            id=row.id,
            name=row.name,
            ip=row.ip,
            port=row.port,
            username=row.username,
            password=row.password,
            protocol=row.protocol,
            path=row.path,
            enabled=row.enabled,
        )

    def list(self) -> list[CameraSchema]:
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    select(CameraSqlSchema).order_by(CameraSqlSchema.id)
                ).all()
            except SQLAlchemyError:
                self._rollback()
                raise
        return [self._to_schema(r) for r in rows]

    def create(self, payload: CameraCreateSchema) -> CameraSchema:
        with self._lock:
            row = CameraSqlSchema(**payload.model_dump())
            try:
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except IntegrityError:
                self._rollback()
                self._sync_id_sequence()
                row = CameraSqlSchema(**payload.model_dump())
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
            self._sync_id_sequence()
        return self._to_schema(row)

    def get(self, camera_id: int) -> Optional[CameraSchema]:
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self._to_schema(row) if row else None

    def update(self, camera_id: int, payload: CameraUpdateSchema) -> Optional[CameraSchema]:
        updates = payload.model_dump(exclude_unset=True)
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                for key, value in updates.items():
                    setattr(row, key, value)
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self._to_schema(row)

    def delete(self, camera_id: int) -> bool:
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return False
                self.pg.session.delete(row)
                self.pg.session.commit()
                self._sync_id_sequence()
            except SQLAlchemyError:
                self._rollback()
                raise
        return True
