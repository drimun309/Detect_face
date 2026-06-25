"""Persistent people-hours counter for a whole workshop zone."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
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
class PeopleCounterState:
    camera_id: int
    current_workers: int = 0
    max_workers: int = 3
    seconds_0_workers: float = 0.0
    seconds_1_worker: float = 0.0
    seconds_2_workers: float = 0.0
    seconds_3_workers: float = 0.0
    person_seconds: float = 0.0
    day_date: str = ""
    last_tick: float = 0.0
    updated_at: float = 0.0


class PeopleCounterStore:
    """Accumulates occupancy duration and person-seconds per camera."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = Lock()
        self._cache: dict[int, PeopleCounterState] = {}
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
                    CREATE TABLE IF NOT EXISTS people_zone_counters (
                        camera_id INTEGER PRIMARY KEY,
                        current_workers INTEGER NOT NULL DEFAULT 0,
                        max_workers INTEGER NOT NULL DEFAULT 3,
                        day_date DATE NOT NULL DEFAULT CURRENT_DATE,
                        seconds_0_workers DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seconds_1_worker DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seconds_2_workers DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seconds_3_workers DOUBLE PRECISION NOT NULL DEFAULT 0,
                        person_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        last_tick DOUBLE PRECISION NOT NULL DEFAULT 0,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS people_zone_events (
                        id BIGSERIAL PRIMARY KEY,
                        camera_id INTEGER NOT NULL,
                        event_type VARCHAR(32) NOT NULL,
                        workers_before INTEGER NOT NULL,
                        workers_after INTEGER NOT NULL,
                        ts DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_people_zone_events_cam_ts "
                    "ON people_zone_events (camera_id, ts)"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"people zone tables migration skipped: {exc}")

    def _today(self, ts: float) -> str:
        return datetime.fromtimestamp(ts, TZ).date().isoformat()

    def _shift_active(self, ts: float) -> bool:
        dt = datetime.fromtimestamp(ts, TZ)
        start = dt.replace(hour=VIEW_START_HOUR, minute=0, second=0, microsecond=0)
        end = dt.replace(hour=VIEW_END_HOUR, minute=0, second=0, microsecond=0)
        return start <= dt < end

    def _load_state(self, camera_id: int, max_workers: int, ts: float) -> PeopleCounterState:
        row = self.pg.session.exec(
            text(
                """
                SELECT current_workers, max_workers, day_date::text,
                       seconds_0_workers, seconds_1_worker, seconds_2_workers,
                       seconds_3_workers, person_seconds, last_tick, updated_at
                FROM people_zone_counters
                WHERE camera_id = :camera_id
                """
            ).bindparams(camera_id=camera_id)
        ).first()
        if not row:
            return PeopleCounterState(
                camera_id=camera_id,
                max_workers=max_workers,
                day_date=self._today(ts),
                last_tick=ts,
                updated_at=ts,
            )
        return PeopleCounterState(
            camera_id=camera_id,
            current_workers=min(max_workers, max(0, int(row[0] or 0))),
            max_workers=max_workers,
            day_date=str(row[2] or self._today(ts)),
            seconds_0_workers=float(row[3] or 0),
            seconds_1_worker=float(row[4] or 0),
            seconds_2_workers=float(row[5] or 0),
            seconds_3_workers=float(row[6] or 0),
            person_seconds=float(row[7] or 0),
            last_tick=float(row[8] or ts),
            updated_at=float(row[9] or ts),
        )

    def _upsert_state(self, state: PeopleCounterState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO people_zone_counters (
                    camera_id, current_workers, max_workers, day_date,
                    seconds_0_workers, seconds_1_worker, seconds_2_workers,
                    seconds_3_workers, person_seconds, last_tick, updated_at
                )
                VALUES (
                    :camera_id, :current_workers, :max_workers, :day_date,
                    :seconds_0_workers, :seconds_1_worker, :seconds_2_workers,
                    :seconds_3_workers, :person_seconds, :last_tick, :updated_at
                )
                ON CONFLICT (camera_id) DO UPDATE SET
                    current_workers = EXCLUDED.current_workers,
                    max_workers = EXCLUDED.max_workers,
                    day_date = EXCLUDED.day_date,
                    seconds_0_workers = EXCLUDED.seconds_0_workers,
                    seconds_1_worker = EXCLUDED.seconds_1_worker,
                    seconds_2_workers = EXCLUDED.seconds_2_workers,
                    seconds_3_workers = EXCLUDED.seconds_3_workers,
                    person_seconds = EXCLUDED.person_seconds,
                    last_tick = EXCLUDED.last_tick,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(**state.__dict__)
        )

    def _log_event(
        self,
        camera_id: int,
        event_type: str,
        before: int,
        after: int,
        ts: float,
    ) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO people_zone_events (
                    camera_id, event_type, workers_before, workers_after, ts
                )
                VALUES (:camera_id, :event_type, :before, :after, :ts)
                """
            ).bindparams(
                camera_id=camera_id,
                event_type=event_type,
                before=before,
                after=after,
                ts=ts,
            )
        )

    def _reset_day_if_needed(self, state: PeopleCounterState, ts: float) -> None:
        today = self._today(ts)
        if state.day_date == today:
            return
        state.day_date = today
        state.seconds_0_workers = 0.0
        state.seconds_1_worker = 0.0
        state.seconds_2_workers = 0.0
        state.seconds_3_workers = 0.0
        state.person_seconds = 0.0
        state.last_tick = ts

    def _accumulate(self, state: PeopleCounterState, ts: float) -> None:
        prev_ts = state.last_tick or ts
        if ts <= prev_ts:
            return
        if self._shift_active(prev_ts):
            dt = ts - prev_ts
            workers = min(state.max_workers, max(0, state.current_workers))
            if workers == 0:
                state.seconds_0_workers += dt
            elif workers == 1:
                state.seconds_1_worker += dt
            elif workers == 2:
                state.seconds_2_workers += dt
            else:
                state.seconds_3_workers += dt
            state.person_seconds += workers * dt

    def tick(
        self,
        camera_id: int,
        delta_workers: int = 0,
        max_workers: int = 3,
        target_workers: int | None = None,
        now: float | None = None,
    ) -> PeopleCounterState:
        ts = now or time.time()
        max_workers = min(3, max(1, int(max_workers or 3)))
        with self._lock:
            state = self._cache.get(camera_id)
            if state is None:
                state = self._load_state(camera_id, max_workers, ts)
                self._cache[camera_id] = state
            state.max_workers = max_workers
            try:
                self._reset_day_if_needed(state, ts)
                self._accumulate(state, ts)
                before = state.current_workers
                if target_workers is not None:
                    after = min(max_workers, max(0, int(target_workers)))
                elif delta_workers:
                    after = min(max_workers, max(0, before + int(delta_workers)))
                else:
                    after = before
                if after != before:
                    event_type = "enter" if after > before else "exit"
                    self._log_event(camera_id, event_type, before, after, ts)
                state.current_workers = after
                state.last_tick = ts
                state.updated_at = ts
                self._upsert_state(state)
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"people zone tick failed (camera={camera_id}): {exc}")
        return state

    def get_state(self, camera_id: int, max_workers: int = 3) -> PeopleCounterState:
        ts = time.time()
        with self._lock:
            state = self._cache.get(camera_id)
            if state is None:
                state = self._load_state(camera_id, max_workers, ts)
                self._cache[camera_id] = state
            return state

    def get_state_live(self, camera_id: int, max_workers: int = 3) -> PeopleCounterState:
        """Актуальные счётчики с доначислением времени до текущего момента."""
        ts = time.time()
        max_workers = min(3, max(1, int(max_workers or 3)))
        with self._lock:
            state = self._cache.get(camera_id)
            if state is None:
                state = self._load_state(camera_id, max_workers, ts)
                self._cache[camera_id] = state
            state.max_workers = max_workers
            try:
                self._reset_day_if_needed(state, ts)
                self._accumulate(state, ts)
                state.last_tick = ts
                state.updated_at = ts
                self._upsert_state(state)
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"people zone live state failed (camera={camera_id}): {exc}")
            return state

    def reset_camera(self, camera_id: int) -> None:
        with self._lock:
            self._cache.pop(camera_id, None)
