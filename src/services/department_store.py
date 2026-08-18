"""Department storage in PostgreSQL."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from src.db.pg_db import PgSyncDb
from src.schema.department_schema import (
    DashboardDepartmentSchema,
    DashboardSummarySchema,
    DashboardZoneSchema,
    DepartmentCreateSchema,
    DepartmentSchema,
    DepartmentUpdateSchema,
)
from src.schema.department_sql_schema import DepartmentSqlSchema
from src.utils.logger import get_logger

log = get_logger()


class DepartmentStore:
    """CRUD для отделов."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._ensure_table()

    def _rollback(self) -> None:
        try:
            self.pg.session.rollback()
        except SQLAlchemyError:
            pass

    def _ensure_table(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS departments (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(128) NOT NULL UNIQUE
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS "
                    "department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"departments migration: {exc}")

    def _camera_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        try:
            rows = self.pg.session.exec(
                text(
                    """
                    SELECT department_id, COUNT(*)::int
                    FROM cameras
                    WHERE department_id IS NOT NULL
                    GROUP BY department_id
                    """
                )
            ).all()
            for row in rows:
                counts[int(row[0])] = int(row[1])
        except SQLAlchemyError:
            self._rollback()
        return counts

    def _to_schema(self, row: DepartmentSqlSchema, counts: dict[int, int]) -> DepartmentSchema:
        return DepartmentSchema(
            id=row.id,
            name=row.name,
            camera_count=counts.get(row.id or 0, 0),
        )

    def list(self) -> list[DepartmentSchema]:
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    select(DepartmentSqlSchema).order_by(DepartmentSqlSchema.name)
                ).all()
            except SQLAlchemyError:
                self._rollback()
                raise
        counts = self._camera_counts()
        return [self._to_schema(r, counts) for r in rows]

    def dashboard_summary(self) -> DashboardSummarySchema:
        """Одна сводка по всем цехам и ROI-зонам за сегодня."""
        today = date.today().isoformat()
        query = text(
            """
            WITH department_cameras AS (
                SELECT d.id AS department_id, d.name AS department_name,
                       c.id AS camera_id, c.name AS camera_name, c.enabled
                FROM departments d
                LEFT JOIN cameras c ON c.department_id = d.id
                UNION ALL
                SELECT NULL, 'Без цеха', c.id, c.name, c.enabled
                FROM cameras c
                WHERE c.department_id IS NULL
            ),
            roi_work AS (
                SELECT camera_id, roi_key,
                       SUM(work_seconds) AS work_seconds,
                       SUM(idle_seconds) AS idle_seconds
                FROM roi_timer_hourly
                WHERE day_date = :today AND hour >= 7 AND hour < 19
                GROUP BY camera_id, roi_key
            )
            SELECT dc.department_id, dc.department_name, dc.camera_id,
                   dc.camera_name, dc.enabled,
                   rt.roi_key, rt.roi_index, COALESCE(rt.roi_name, ''),
                   COALESCE(rw.work_seconds, 0),
                   COALESCE(rw.idle_seconds, 0),
                   COALESCE(rpd.person_seconds, 0),
                   COALESCE(sd.cycle_count, 0),
                   COALESCE(pd.packed_count, 0),
                   COALESCE(
                     CASE WHEN pzc.day_date = CAST(:today AS date)
                          THEN pzc.current_workers END,
                     0
                   ),
                   COALESCE(
                     CASE WHEN pzc.day_date = CAST(:today AS date)
                          THEN pzc.person_seconds END,
                     pzd.person_seconds,
                     0
                   )
            FROM department_cameras dc
            LEFT JOIN roi_timers rt ON rt.camera_id = dc.camera_id
            LEFT JOIN roi_work rw
              ON rw.camera_id = rt.camera_id AND rw.roi_key = rt.roi_key
            LEFT JOIN roi_people_daily rpd
              ON rpd.camera_id = rt.camera_id
             AND rpd.roi_key = rt.roi_key
             AND rpd.day_date = :today
            LEFT JOIN sealer_daily sd
              ON sd.camera_id = dc.camera_id
             AND sd.day_date = :today
            LEFT JOIN package_roi_daily pd
              ON pd.camera_id = dc.camera_id
             AND pd.day_date = :today
            LEFT JOIN people_zone_counters pzc ON pzc.camera_id = dc.camera_id
            LEFT JOIN people_zone_daily pzd
              ON pzd.camera_id = dc.camera_id
             AND pzd.day_date = :today
            ORDER BY dc.department_name, dc.camera_name, rt.roi_index
            """
        ).bindparams(today=today)

        with self._lock:
            try:
                rows = self.pg.session.exec(query).all()
            except SQLAlchemyError:
                self._rollback()
                raise

        departments: dict[int | None, DashboardDepartmentSchema] = {}
        cameras: dict[int | None, set[int]] = {}
        enabled_cameras: dict[int | None, set[int]] = {}
        counted_cameras: set[int] = set()

        for row in rows:
            department_id = int(row[0]) if row[0] is not None else None
            department = departments.setdefault(
                department_id,
                DashboardDepartmentSchema(id=department_id, name=str(row[1])),
            )
            cameras.setdefault(department_id, set())
            enabled_cameras.setdefault(department_id, set())

            if row[2] is None:
                continue
            camera_id = int(row[2])
            cameras[department_id].add(camera_id)
            if row[4]:
                enabled_cameras[department_id].add(camera_id)
            pz_workers = int(row[13] or 0)
            pz_person_seconds = float(row[14] or 0)
            if camera_id not in counted_cameras:
                department.cycles += int(row[11] or 0)
                department.packages += int(row[12] or 0)
                department.people_zone_workers += pz_workers
                department.people_zone_person_seconds += pz_person_seconds
                counted_cameras.add(camera_id)

            if row[5] is None:
                continue
            work_seconds = float(row[8] or 0)
            idle_seconds = float(row[9] or 0)
            person_seconds = float(row[10] or 0)
            department.zones.append(
                DashboardZoneSchema(
                    camera_id=camera_id,
                    camera_name=str(row[3]),
                    roi_index=int(row[6] or 0),
                    name=str(row[7]).strip() or f"Зона {int(row[6] or 0)}",
                    work_seconds=work_seconds,
                    idle_seconds=idle_seconds,
                    person_seconds=person_seconds,
                    people_zone_workers=pz_workers,
                    people_zone_person_seconds=pz_person_seconds,
                )
            )
            department.work_seconds += work_seconds
            department.idle_seconds += idle_seconds
            department.person_seconds += person_seconds

        items = list(departments.values())
        for department in items:
            department.camera_count = len(cameras.get(department.id, set()))
            department.enabled_camera_count = len(enabled_cameras.get(department.id, set()))
            department.zone_count = len(department.zones)

        return DashboardSummarySchema(
            date=today,
            department_count=sum(item.id is not None for item in items),
            camera_count=sum(item.camera_count for item in items),
            enabled_camera_count=sum(item.enabled_camera_count for item in items),
            zone_count=sum(item.zone_count for item in items),
            work_seconds=sum(item.work_seconds for item in items),
            idle_seconds=sum(item.idle_seconds for item in items),
            person_seconds=sum(item.person_seconds for item in items),
            people_zone_workers=sum(item.people_zone_workers for item in items),
            people_zone_person_seconds=sum(
                item.people_zone_person_seconds for item in items
            ),
            cycles=sum(item.cycles for item in items),
            packages=sum(item.packages for item in items),
            departments=items,
        )

    def create(self, payload: DepartmentCreateSchema) -> DepartmentSchema:
        with self._lock:
            row = DepartmentSqlSchema(name=payload.name.strip())
            try:
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except IntegrityError:
                self._rollback()
                raise ValueError("Отдел с таким именем уже существует")
            except SQLAlchemyError:
                self._rollback()
                raise
        return DepartmentSchema(id=row.id, name=row.name, camera_count=0)

    def update(
        self, department_id: int, payload: DepartmentUpdateSchema
    ) -> DepartmentSchema | None:
        name = payload.name.strip()
        if not name:
            raise ValueError("Название отдела не может быть пустым")
        with self._lock:
            try:
                row = self.pg.session.get(DepartmentSqlSchema, department_id)
                if not row:
                    return None
                row.name = name
                self.pg.session.add(row)
                self.pg.session.commit()
                self.pg.session.refresh(row)
            except IntegrityError:
                self._rollback()
                raise ValueError("Отдел с таким именем уже существует")
            except SQLAlchemyError:
                self._rollback()
                raise
        counts = self._camera_counts()
        return self._to_schema(row, counts)

    def get(self, department_id: int) -> DepartmentSchema | None:
        with self._lock:
            try:
                row = self.pg.session.get(DepartmentSqlSchema, department_id)
            except SQLAlchemyError:
                self._rollback()
                raise
        if not row:
            return None
        counts = self._camera_counts()
        return self._to_schema(row, counts)

    def delete(self, department_id: int) -> bool:
        with self._lock:
            try:
                row = self.pg.session.get(DepartmentSqlSchema, department_id)
                if not row:
                    return False
                self.pg.session.exec(
                    text(
                        "UPDATE cameras SET department_id = NULL "
                        "WHERE department_id = :dept_id"
                    ).bindparams(dept_id=department_id)
                )
                self.pg.session.delete(row)
                self.pg.session.commit()
            except SQLAlchemyError:
                self._rollback()
                raise
        return True
