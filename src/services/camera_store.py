"""Camera storage in PostgreSQL (с миграцией из legacy JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from src.db.pg_db import PgSyncDb
from src.schema.camera_schema import CameraCreateSchema, CameraSchema, CameraUpdateSchema
from src.schema.camera_sql_schema import CameraSqlSchema
from src.schema.sealer_roi_schema import SealerRoiConfig, SealerRoiResponse
from src.schema.people_zone_schema import (
    PeopleZoneConfig,
    PeopleZoneResponse,
)
from src.schema.roi_schema import RoiPoint, RoiPolygon, RoiResponse, RoiUpdate
from src.utils.logger import get_logger
from src.utils.roi_helpers import (
    RoiPolygonData,
    default_roi_name,
    parse_rois_from_json,
    polygons_points,
    serialize_rois_to_json,
)

log = get_logger()

LEGACY_JSON_PATHS = (
    Path("data/backend/cameras.json"),
    Path("data/cameras.json"),
)


class CameraStore:
    """CRUD для камер в PostgreSQL."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._ensure_roi_columns()
        self._ensure_people_zone_columns()
        self._ensure_department_column()
        self._ensure_package_detection_column()
        self._ensure_rod_pose_column()
        self._ensure_sealer_roi_columns()
        self._ensure_stream_quality_columns()
        self._ensure_inference_interval_column()
        self._ensure_roi_timer_table()
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

    def _ensure_people_zone_columns(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "people_zone_enabled BOOLEAN DEFAULT FALSE"
                )
            )
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "people_zone_config TEXT DEFAULT '{}'"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"people zone columns migration: {exc}")

    def _ensure_department_column(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"department_id column migration: {exc}")

    def _ensure_package_detection_column(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "package_detection_enabled BOOLEAN DEFAULT FALSE"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"package_detection column migration: {exc}")

    def _ensure_rod_pose_column(self) -> None:
        try:
            exists = self.pg.session.exec(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'cameras' "
                    "AND column_name = 'rod_pose_enabled' "
                    "LIMIT 1"
                )
            ).first()
            if exists:
                return
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN "
                    "rod_pose_enabled BOOLEAN DEFAULT FALSE"
                )
            )
            # Первый запуск: раньше YOLO-ручка включалась вместе с пакетами
            self.pg.session.exec(
                text(
                    "UPDATE cameras SET rod_pose_enabled = package_detection_enabled"
                )
            )
            self.pg.session.commit()
            log.info("Migrated cameras.rod_pose_enabled from package_detection_enabled")
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"rod_pose column migration: {exc}")

    def _ensure_sealer_roi_columns(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "sealer_roi_enabled BOOLEAN DEFAULT FALSE"
                )
            )
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "sealer_roi_config TEXT DEFAULT '{}'"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"sealer_roi columns migration: {exc}")

    def _ensure_stream_quality_columns(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "stream_width INTEGER NULL"
                )
            )
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "stream_height INTEGER NULL"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"stream quality columns migration: {exc}")

    def _ensure_inference_interval_column(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "inference_interval INTEGER NULL"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"inference interval column migration: {exc}")

    def _ensure_roi_timer_table(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS roi_timers (
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        roi_index INTEGER NOT NULL,
                        polygon_json TEXT NOT NULL DEFAULT '[]',
                        mode VARCHAR(16) NOT NULL DEFAULT 'standby',
                        work_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        idle_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        last_tick DOUBLE PRECISION NOT NULL DEFAULT 0,
                        presence_since DOUBLE PRECISION NULL,
                        absence_since DOUBLE PRECISION NULL,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, roi_key)
                    )
                    """
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"ROI timers table migration: {exc}")

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

    def _department_names(self) -> dict[int, str]:
        names: dict[int, str] = {}
        try:
            rows = self.pg.session.exec(
                text("SELECT id, name FROM departments")
            ).all()
            for row in rows:
                names[int(row[0])] = str(row[1])
        except SQLAlchemyError:
            self._rollback()
        return names

    def _to_schema(
        self, row: CameraSqlSchema, dept_names: dict[int, str] | None = None
    ) -> CameraSchema:
        dept_id = getattr(row, "department_id", None)
        if dept_names is None:
            dept_names = self._department_names()
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
            department_id=dept_id,
            department_name=dept_names.get(dept_id) if dept_id else None,
            package_detection_enabled=bool(
                getattr(row, "package_detection_enabled", False)
            ),
            rod_pose_enabled=bool(getattr(row, "rod_pose_enabled", False)),
            stream_width=getattr(row, "stream_width", None),
            stream_height=getattr(row, "stream_height", None),
            inference_interval=getattr(row, "inference_interval", None),
        )

    def _polygons_to_response(
        self, polygons: list[RoiPolygonData]
    ) -> list[RoiPolygon]:
        return [
            RoiPolygon(
                name=poly.name or default_roi_name(idx),
                points=[RoiPoint(x=x, y=y) for x, y in poly.points],
            )
            for idx, poly in enumerate(polygons, start=1)
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
        polygons_list: list[RoiPolygonData] = []
        if payload.enabled and payload.polygons:
            for idx, poly in enumerate(payload.polygons, start=1):
                name = (poly.name or "").strip() or default_roi_name(idx)
                polygons_list.append(
                    RoiPolygonData(
                        name=name,
                        points=[(p.x, p.y) for p in poly.points],
                    )
                )
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

    def _parse_people_zone_config(self, row: CameraSqlSchema) -> PeopleZoneConfig:
        raw = getattr(row, "people_zone_config", "{}") or "{}"
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(data, dict):
                data = {}
        except (json.JSONDecodeError, TypeError):
            data = {}
        data["enabled"] = bool(getattr(row, "people_zone_enabled", False))
        data["max_workers"] = min(3, max(1, int(data.get("max_workers") or 3)))
        data.pop("line", None)
        try:
            return PeopleZoneConfig(**data)
        except ValueError:
            return PeopleZoneConfig(enabled=False, max_workers=3)

    def get_people_zone(self, camera_id: int) -> Optional[PeopleZoneResponse]:
        row = self.pg.session.get(CameraSqlSchema, camera_id)
        if not row:
            return None
        cfg = self._parse_people_zone_config(row)
        return PeopleZoneResponse(**cfg.model_dump())

    def update_people_zone(
        self, camera_id: int, payload: PeopleZoneConfig
    ) -> Optional[PeopleZoneResponse]:
        enabled = payload.enabled and len(payload.polygon) >= 3
        cfg = PeopleZoneConfig(
            enabled=enabled,
            polygon=list(payload.polygon),
            max_workers=3,
        )
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                row.people_zone_enabled = enabled
                row.people_zone_config = json.dumps(
                    cfg.model_dump(exclude={"enabled"}), ensure_ascii=False
                )
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self.get_people_zone(camera_id)

    def get_people_zone_runtime(
        self, camera_id: int
    ) -> tuple[bool, list[tuple[float, float]], int]:
        row = self.pg.session.get(CameraSqlSchema, camera_id)
        if not row:
            return False, [], 3
        cfg = self._parse_people_zone_config(row)
        if not cfg.enabled or len(cfg.polygon) < 3:
            return False, [], 3
        polygon = [(p.x, p.y) for p in cfg.polygon]
        return True, polygon, min(3, max(1, cfg.max_workers))

    def _parse_sealer_roi_config(self, row: CameraSqlSchema) -> SealerRoiConfig:
        raw = getattr(row, "sealer_roi_config", "{}") or "{}"
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(data, dict):
                data = {}
        except (json.JSONDecodeError, TypeError):
            data = {}
        data["enabled"] = bool(getattr(row, "sealer_roi_enabled", False))
        try:
            return SealerRoiConfig(**data)
        except ValueError:
            return SealerRoiConfig(enabled=False)

    def get_sealer_roi(self, camera_id: int) -> Optional[SealerRoiResponse]:
        row = self.pg.session.get(CameraSqlSchema, camera_id)
        if not row:
            return None
        return SealerRoiResponse(**self._parse_sealer_roi_config(row).model_dump())

    def update_sealer_roi(
        self, camera_id: int, payload: SealerRoiConfig
    ) -> Optional[SealerRoiResponse]:
        enabled = bool(
            payload.enabled
            and payload.w > 0
            and payload.h > 0
        )
        cfg = SealerRoiConfig(
            enabled=enabled,
            x=max(0.0, min(1.0, float(payload.x))),
            y=max(0.0, min(1.0, float(payload.y))),
            w=max(0.0, min(1.0, float(payload.w))),
            h=max(0.0, min(1.0, float(payload.h))),
            spike_thresh=float(payload.spike_thresh),
            rest_thresh=float(payload.rest_thresh),
            cooldown_frames=int(payload.cooldown_frames),
        )
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                row.sealer_roi_enabled = enabled
                row.sealer_roi_config = json.dumps(
                    cfg.model_dump(exclude={"enabled"}), ensure_ascii=False
                )
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self.get_sealer_roi(camera_id)

    def delete_sealer_roi(self, camera_id: int) -> Optional[SealerRoiResponse]:
        return self.update_sealer_roi(camera_id, SealerRoiConfig(enabled=False))

    def get_sealer_roi_runtime(
        self, camera_id: int
    ) -> tuple[bool, float, float, float, float, float, float, int]:
        row = self.pg.session.get(CameraSqlSchema, camera_id)
        if not row:
            return False, 0.0, 0.0, 0.0, 0.0, 80.0, -50.0, 8
        cfg = self._parse_sealer_roi_config(row)
        if not cfg.enabled or cfg.w <= 0 or cfg.h <= 0:
            return False, 0.0, 0.0, 0.0, 0.0, cfg.spike_thresh, cfg.rest_thresh, cfg.cooldown_frames
        return (
            True,
            cfg.x,
            cfg.y,
            cfg.w,
            cfg.h,
            cfg.spike_thresh,
            cfg.rest_thresh,
            cfg.cooldown_frames,
        )

    def set_package_detection(
        self, camera_id: int, enabled: bool
    ) -> Optional[CameraSchema]:
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                row.package_detection_enabled = bool(enabled)
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self._to_schema(row)

    def set_rod_pose(self, camera_id: int, enabled: bool) -> Optional[CameraSchema]:
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                row.rod_pose_enabled = bool(enabled)
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self._to_schema(row)

    def set_stream_quality(
        self,
        camera_id: int,
        stream_width: int | None,
        stream_height: int | None,
    ) -> Optional[CameraSchema]:
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                row.stream_width = stream_width
                row.stream_height = stream_height
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        return self._to_schema(row)

    def get_roi_polygons(self, camera_id: int) -> tuple[bool, list[RoiPolygonData]]:
        row = self.pg.session.get(CameraSqlSchema, camera_id)
        if not row:
            return False, []
        enabled = bool(getattr(row, "roi_enabled", False))
        polygons = parse_rois_from_json(getattr(row, "rois", "[]"))
        if not enabled:
            return False, []
        return True, polygons

    def get_roi_points(self, camera_id: int) -> tuple[bool, list[list[tuple[float, float]]]]:
        enabled, polygons = self.get_roi_polygons(camera_id)
        return enabled, polygons_points(polygons)

    def list(self) -> list[CameraSchema]:
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    select(CameraSqlSchema).order_by(CameraSqlSchema.id)
                ).all()
            except SQLAlchemyError:
                self._rollback()
                raise
        dept_names = self._department_names()
        return [self._to_schema(r, dept_names) for r in rows]

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
        if "department_id" in updates and updates["department_id"] is not None:
            dept_id = int(updates["department_id"])
            exists = self.pg.session.exec(
                text("SELECT 1 FROM departments WHERE id = :id").bindparams(id=dept_id)
            ).first()
            if not exists:
                raise ValueError("Отдел не найден")
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return None
                old_name = row.name
                for key, value in updates.items():
                    setattr(row, key, value)
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except SQLAlchemyError:
                self._rollback()
                raise
        if "name" in updates and updates["name"] and updates["name"] != old_name:
            try:
                from src.services.recording_service import get_recording_service

                svc = get_recording_service()
                if svc:
                    svc.rename_camera_folder(camera_id, old_name, updates["name"])
            except Exception as exc:
                log.warning(f"Recordings folder rename skipped: {exc}")
        return self._to_schema(row)

    def delete(self, camera_id: int) -> bool:
        with self._lock:
            try:
                row = self.pg.session.get(CameraSqlSchema, camera_id)
                if not row:
                    return False
                self.pg.session.delete(row)
                self.pg.session.exec(
                    text("DELETE FROM camera_models WHERE camera_id = :camera_id").bindparams(
                        camera_id=camera_id
                    )
                )
                self.pg.session.exec(
                    text("DELETE FROM roi_timers WHERE camera_id = :camera_id").bindparams(
                        camera_id=camera_id
                    )
                )
                self.pg.session.commit()
                self._sync_id_sequence()
            except SQLAlchemyError:
                self._rollback()
                raise
        return True
