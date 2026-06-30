"""Department storage in PostgreSQL."""

from __future__ import annotations


from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from src.db.pg_db import PgSyncDb
from src.schema.department_schema import DepartmentCreateSchema, DepartmentSchema, DepartmentUpdateSchema
from src.schema.department_sql_schema import DepartmentSqlSchema
from src.utils.logger import get_logger

log = get_logger()

SEED_DEPARTMENTS = (
    ("сборка затворов", ("IP Camera 3",)),
    ("програмисты", ("123",)),
)


class DepartmentStore:
    """CRUD для отделов."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._ensure_table()
        self._seed_defaults()

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

    def _seed_defaults(self) -> None:
        with self._lock:
            try:
                for dept_name, camera_names in SEED_DEPARTMENTS:
                    row = self.pg.session.exec(
                        select(DepartmentSqlSchema).where(
                            DepartmentSqlSchema.name == dept_name
                        )
                    ).first()
                    if row is None:
                        row = DepartmentSqlSchema(name=dept_name)
                        self.pg.session.add(row)
                        self.pg.session.commit()
                        self.pg.session.refresh(row)
                    dept_id = row.id
                    for cam_name in camera_names:
                        self.pg.session.exec(
                            text(
                                """
                                UPDATE cameras
                                SET department_id = :dept_id
                                WHERE name = :cam_name
                                  AND (department_id IS NULL OR department_id = :dept_id)
                                """
                            ).bindparams(dept_id=dept_id, cam_name=cam_name)
                        )
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"departments seed skipped: {exc}")

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
