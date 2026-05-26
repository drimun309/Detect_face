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
from src.schema.camera_schema import CameraCreateSchema, CameraSchema, CameraUpdateSchema
from src.schema.camera_sql_schema import CameraSqlSchema
from src.schema.roi_schema import RoiPoint, RoiPolygon, RoiResponse, RoiUpdate
from src.utils.logger import get_logger
from src.utils.roi_helpers import parse_rois_from_json, serialize_rois_to_json

log = get_logger()

LEGACY_JSON_PATHS = (
    Path("data/backend/cameras.json"),
    Path("data/cameras.json"),
)


class CameraStore:
    """CRUD для камер в PostgreSQL."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = Lock()
        self._ensure_roi_columns()
        self._migrate_legacy_json_once()
        self._sync_id_sequence()

    def _ensure_roi_columns(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "roi_enabled BOOLEAN DEFAULT FALSE"
                )
            )
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "rois TEXT DEFAULT '[]'"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"ROI columns migration: {exc}")

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
            roi_enabled=bool(getattr(row, "roi_enabled", False)),
        )

    def _polygons_to_response(
        self, polygons: list[list[tuple[float, float]]]
    ) -> list[RoiPolygon]:
        return [
            RoiPolygon(points=[RoiPoint(x=x, y=y) for x, y in poly]) for poly in polygons
        ]

    def get_roi(self, camera_id: int) -> Optional[RoiResponse]:
        row = self.pg.session.get(CameraSqlSchema, camera_id)
        if not row:
            return None
        polygons = parse_rois_from_json(getattr(row, "rois", "[]"))
        return RoiResponse(
            enabled=bool(getattr(row, "roi_enabled", False)),
            polygons=self._polygons_to_response(polygons),
        )

    def update_roi(self, camera_id: int, payload: RoiUpdate) -> Optional[RoiResponse]:
        polygons_list: list[list[tuple[float, float]]] = []
        if payload.enabled and payload.polygons:
            for poly in payload.polygons:
                polygons_list.append([(p.x, p.y) for p in poly.points])
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                row.roi_enabled = payload.enabled and len(polygons_list) > 0
                row.rois = serialize_rois_to_json(polygons_list) if row.roi_enabled else "[]"
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self.get_roi(camera_id)

    def delete_roi(self, camera_id: int) -> Optional[RoiResponse]:
        return self.update_roi(
            camera_id, RoiUpdate(enabled=False, polygons=[])
        )

    def get_roi_polygons(self, camera_id: int) -> tuple[bool, list[list[tuple[float, float]]]]:
        row = self.pg.session.get(CameraSqlSchema, camera_id)
        if not row:
            return False, []
        enabled = bool(getattr(row, "roi_enabled", False))
        polygons = parse_rois_from_json(getattr(row, "rois", "[]"))
        if not enabled:
            return False, []
        return True, polygons

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
