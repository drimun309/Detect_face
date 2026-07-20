"""Счётчик нажатий палки по pose-модели (смена 07:00–19:00)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.db.pg_db import PgSyncDb
from src.utils.logger import get_logger

log = get_logger()
TZ = ZoneInfo("Asia/Tbilisi")
VIEW_START_HOUR = 7
VIEW_END_HOUR = 19


@dataclass
class RodCounterState:
    camera_id: int
    presses_today: int = 0
    day_date: str = ""
    updated_at: float = 0.0


class RodCounterStore:
    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._cache: dict[int, RodCounterState] = {}
        self._ensure_tables()

    def _rollback(self) -> None:
        try:
            self.pg.session.rollback()
        except SQLAlchemyError:
            pass

    def _ensure_tables(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS rod_counters (
                        camera_id INTEGER NOT NULL PRIMARY KEY,
                        presses_today INTEGER NOT NULL DEFAULT 0,
                        day_date DATE NOT NULL DEFAULT CURRENT_DATE,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS rod_daily (
                        camera_id INTEGER NOT NULL,
                        day_date DATE NOT NULL,
                        press_count INTEGER NOT NULL DEFAULT 0,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, day_date)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS rod_events (
                        id BIGSERIAL PRIMARY KEY,
                        camera_id INTEGER NOT NULL,
                        ref_dA DOUBLE PRECISION NOT NULL DEFAULT 0,
                        ts DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rod_events_cam_ts "
                    "ON rod_events (camera_id, ts)"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"rod counter tables migration skipped: {exc}")

    def _today(self, ts: float) -> str:
        return datetime.fromtimestamp(ts, TZ).date().isoformat()

    def _shift_active(self, ts: float) -> bool:
        dt = datetime.fromtimestamp(ts, TZ)
        start = dt.replace(hour=VIEW_START_HOUR, minute=0, second=0, microsecond=0)
        end = dt.replace(hour=VIEW_END_HOUR, minute=0, second=0, microsecond=0)
        return start <= dt < end

    def _load_state(self, camera_id: int, ts: float) -> RodCounterState:
        row = self.pg.session.exec(
            text(
                """
                SELECT presses_today, day_date::text, updated_at
                FROM rod_counters
                WHERE camera_id = :camera_id
                """
            ).bindparams(camera_id=camera_id)
        ).first()
        today = self._today(ts)
        if row is None:
            return RodCounterState(camera_id=camera_id, presses_today=0, day_date=today, updated_at=ts)
        presses_today = int(row[0] or 0)
        day_date = str(row[1] or today)
        if day_date != today:
            presses_today = 0
            day_date = today
        return RodCounterState(
            camera_id=camera_id,
            presses_today=presses_today,
            day_date=day_date,
            updated_at=float(row[2] or ts),
        )

    def record_press(
        self,
        camera_id: int,
        ref_dA: float = 0.0,
        now: float | None = None,
    ) -> int:
        ts = now or time.time()
        if not self._shift_active(ts):
            return self.get_presses_today(camera_id)

        with self._lock:
            try:
                state = self._cache.get(camera_id)
                if state is None:
                    state = self._load_state(camera_id, ts)
                today = self._today(ts)
                if state.day_date != today:
                    state.presses_today = 0
                    state.day_date = today
                state.presses_today += 1
                state.updated_at = ts
                self.pg.session.exec(
                    text(
                        """
                        INSERT INTO rod_counters (camera_id, presses_today, day_date, updated_at)
                        VALUES (:camera_id, :presses_today, :day_date, :updated_at)
                        ON CONFLICT (camera_id) DO UPDATE SET
                            presses_today = EXCLUDED.presses_today,
                            day_date = EXCLUDED.day_date,
                            updated_at = EXCLUDED.updated_at
                        """
                    ).bindparams(**state.__dict__)
                )
                self.pg.session.exec(
                    text(
                        """
                        INSERT INTO rod_daily (camera_id, day_date, press_count, updated_at)
                        VALUES (:camera_id, :day_date, :presses_today, :updated_at)
                        ON CONFLICT (camera_id, day_date) DO UPDATE SET
                            press_count = EXCLUDED.press_count,
                            updated_at = EXCLUDED.updated_at
                        """
                    ).bindparams(
                        camera_id=state.camera_id,
                        day_date=state.day_date,
                        presses_today=state.presses_today,
                        updated_at=state.updated_at,
                    )
                )
                self.pg.session.exec(
                    text(
                        """
                        INSERT INTO rod_events (camera_id, ref_dA, ts)
                        VALUES (:camera_id, :ref_dA, :ts)
                        """
                    ).bindparams(camera_id=camera_id, ref_dA=float(ref_dA), ts=ts)
                )
                self.pg.session.commit()
                self._cache[camera_id] = state
                log.info(
                    f"Rod press cam{camera_id}: total today {state.presses_today} "
                    f"(ref_dA={ref_dA:.1f})"
                )
                return state.presses_today
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"rod record_press failed (camera={camera_id}): {exc}")
                cached = self._cache.get(camera_id)
                if cached and cached.day_date == self._today(ts):
                    return int(cached.presses_today)
                return 0

    def get_presses_today(self, camera_id: int) -> int:
        ts = time.time()
        with self._lock:
            cached = self._cache.get(camera_id)
            if cached and cached.day_date == self._today(ts):
                return int(cached.presses_today)
            try:
                state = self._load_state(camera_id, ts)
                self._cache[camera_id] = state
                return int(state.presses_today)
            except SQLAlchemyError:
                self._rollback()
                return 0

    def delete_camera(self, camera_id: int) -> None:
        with self._lock:
            self._cache.pop(camera_id, None)
            try:
                for table in ("rod_events", "rod_daily", "rod_counters"):
                    self.pg.session.exec(
                        text(f"DELETE FROM {table} WHERE camera_id = :camera_id").bindparams(
                            camera_id=camera_id
                        )
                    )
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"rod counter camera delete failed (camera={camera_id}): {exc}")
