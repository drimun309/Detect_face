"""Счётчик циклов запайщика по камере (смена 07:00–19:00)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
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
class SealerCounterState:
    camera_id: int
    cycles_today: int = 0
    day_date: str = ""
    updated_at: float = 0.0


class SealerCounterStore:
    """Пишет циклы запайщика в БД только в рабочую смену."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._cache: dict[int, SealerCounterState] = {}
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
                    CREATE TABLE IF NOT EXISTS sealer_counters (
                        camera_id INTEGER NOT NULL PRIMARY KEY,
                        cycles_today INTEGER NOT NULL DEFAULT 0,
                        day_date DATE NOT NULL DEFAULT CURRENT_DATE,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS sealer_daily (
                        camera_id INTEGER NOT NULL,
                        day_date DATE NOT NULL,
                        cycle_count INTEGER NOT NULL DEFAULT 0,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, day_date)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS sealer_events (
                        id BIGSERIAL PRIMARY KEY,
                        camera_id INTEGER NOT NULL,
                        activity DOUBLE PRECISION NOT NULL DEFAULT 0,
                        ts DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_sealer_events_cam_ts "
                    "ON sealer_events (camera_id, ts)"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"sealer counter tables migration skipped: {exc}")

    def _today(self, ts: float) -> str:
        """Дата смены Asia/Tbilisi: с 07:00 до 07:00 следующего календарного дня."""
        dt = datetime.fromtimestamp(ts, TZ)
        if dt.hour < VIEW_START_HOUR:
            dt = dt - timedelta(days=1)
        return dt.date().isoformat()

    def _shift_active(self, ts: float) -> bool:
        dt = datetime.fromtimestamp(ts, TZ)
        start = dt.replace(hour=VIEW_START_HOUR, minute=0, second=0, microsecond=0)
        end = dt.replace(hour=VIEW_END_HOUR, minute=0, second=0, microsecond=0)
        return start <= dt < end

    def _persist_rollover_if_needed(
        self, state: SealerCounterState, previous_day: str | None
    ) -> None:
        """При смене смены (07:00) зафиксировать нулевой день в counters."""
        if previous_day is None or previous_day == state.day_date:
            return
        self._upsert_state(state)
        self._flush_daily(state)
        self.pg.session.commit()
        log.info(
            f"Sealer shift rollover cam{state.camera_id}: "
            f"{previous_day} -> {state.day_date} (count=0)"
        )

    def _load_state(self, camera_id: int, ts: float) -> SealerCounterState:
        row = self.pg.session.exec(
            text(
                """
                SELECT cycles_today, day_date::text, updated_at
                FROM sealer_counters
                WHERE camera_id = :camera_id
                """
            ).bindparams(camera_id=camera_id)
        ).first()
        today = self._today(ts)
        if row is None:
            return SealerCounterState(
                camera_id=camera_id,
                cycles_today=0,
                day_date=today,
                updated_at=ts,
            )
        cycles_today = int(row[0] or 0)
        day_date = str(row[1] or today)
        if day_date != today:
            cycles_today = 0
            day_date = today
        return SealerCounterState(
            camera_id=camera_id,
            cycles_today=cycles_today,
            day_date=day_date,
            updated_at=float(row[2] or ts),
        )

    def _upsert_state(self, state: SealerCounterState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO sealer_counters (
                    camera_id, cycles_today, day_date, updated_at
                )
                VALUES (:camera_id, :cycles_today, :day_date, :updated_at)
                ON CONFLICT (camera_id) DO UPDATE SET
                    cycles_today = EXCLUDED.cycles_today,
                    day_date = EXCLUDED.day_date,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(**state.__dict__)
        )

    def _flush_daily(self, state: SealerCounterState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO sealer_daily (
                    camera_id, day_date, cycle_count, updated_at
                )
                VALUES (:camera_id, :day_date, :cycles_today, :updated_at)
                ON CONFLICT (camera_id, day_date) DO UPDATE SET
                    cycle_count = EXCLUDED.cycle_count,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(
                camera_id=state.camera_id,
                day_date=state.day_date,
                cycles_today=state.cycles_today,
                updated_at=state.updated_at,
            )
        )

    def _log_event(self, camera_id: int, activity: float, ts: float) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO sealer_events (camera_id, activity, ts)
                VALUES (:camera_id, :activity, :ts)
                """
            ).bindparams(camera_id=camera_id, activity=float(activity), ts=ts)
        )

    def record_cycle(
        self,
        camera_id: int,
        activity: float = 0.0,
        now: float | None = None,
    ) -> int:
        ts = now or time.time()
        if not self._shift_active(ts):
            return self.get_cycles_today(camera_id)

        with self._lock:
            try:
                state = self._cache.get(camera_id)
                if state is None:
                    state = self._load_state(camera_id, ts)
                today = self._today(ts)
                if state.day_date != today:
                    state.cycles_today = 0
                    state.day_date = today
                state.cycles_today += 1
                state.updated_at = ts
                self._log_event(camera_id, activity, ts)
                self._upsert_state(state)
                self._flush_daily(state)
                self.pg.session.commit()
                self._cache[camera_id] = state
                log.info(
                    f"Sealer cycle cam{camera_id}: "
                    f"total today {state.cycles_today} (activity={activity:.2f})"
                )
                return state.cycles_today
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"sealer record_cycle failed (camera={camera_id}): {exc}")
                cached = self._cache.get(camera_id)
                if cached and cached.day_date == self._today(ts):
                    return int(cached.cycles_today)
                return 0

    def get_cycles_today(self, camera_id: int) -> int:
        ts = time.time()
        with self._lock:
            cached = self._cache.get(camera_id)
            today = self._today(ts)
            if cached and cached.day_date == today:
                return int(cached.cycles_today)
            try:
                row = self.pg.session.exec(
                    text(
                        """
                        SELECT cycles_today, day_date::text, updated_at
                        FROM sealer_counters
                        WHERE camera_id = :camera_id
                        """
                    ).bindparams(camera_id=camera_id)
                ).first()
                if row is None:
                    state = SealerCounterState(
                        camera_id=camera_id,
                        cycles_today=0,
                        day_date=today,
                        updated_at=ts,
                    )
                else:
                    db_day = str(row[1] or today)
                    cycles = int(row[0] or 0)
                    if db_day != today:
                        cycles = 0
                        state = SealerCounterState(
                            camera_id=camera_id,
                            cycles_today=0,
                            day_date=today,
                            updated_at=ts,
                        )
                        self._persist_rollover_if_needed(state, db_day)
                    else:
                        state = SealerCounterState(
                            camera_id=camera_id,
                            cycles_today=cycles,
                            day_date=today,
                            updated_at=float(row[2] or ts),
                        )
                self._cache[camera_id] = state
                return int(state.cycles_today)
            except SQLAlchemyError:
                self._rollback()
                return 0

    def get_cycle_count_for_date(self, camera_id: int, day_date: str) -> int:
        today = self._today(time.time())
        if day_date == today:
            return self.get_cycles_today(camera_id)
        with self._lock:
            try:
                row = self.pg.session.exec(
                    text(
                        """
                        SELECT cycle_count
                        FROM sealer_daily
                        WHERE camera_id = :camera_id AND day_date = :day_date
                        """
                    ).bindparams(camera_id=camera_id, day_date=day_date)
                ).first()
                return int(row[0] or 0) if row else 0
            except SQLAlchemyError:
                self._rollback()
                return 0

    def delete_camera(self, camera_id: int) -> None:
        with self._lock:
            try:
                for table in ("sealer_events", "sealer_daily", "sealer_counters"):
                    self.pg.session.exec(
                        text(
                            f"DELETE FROM {table} WHERE camera_id = :camera_id"
                        ).bindparams(camera_id=camera_id)
                    )
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(
                    f"sealer counter camera delete failed (camera={camera_id}): {exc}"
                )
            self._cache.pop(camera_id, None)

    def get_stat_dates(self, camera_id: int) -> list[str]:
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        """
                        SELECT DISTINCT day_date
                        FROM sealer_daily
                        WHERE camera_id = :camera_id
                        ORDER BY day_date
                        """
                    ).bindparams(camera_id=camera_id)
                ).all()
                return [str(row[0]) for row in rows]
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"sealer stat dates query failed: {exc}")
                return []

    def get_stat_dates_meta(self, camera_id: int) -> dict:
        return {
            "camera_id": camera_id,
            "dates": self.get_stat_dates(camera_id),
            "server_today": self._today(time.time()),
            "timezone": str(TZ),
        }

    def get_daily_stats_range(
        self, camera_id: int, from_date: str, to_date: str
    ) -> dict:
        days_map: dict[str, dict] = {}
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        """
                        SELECT day_date, cycle_count
                        FROM sealer_daily
                        WHERE camera_id = :camera_id
                          AND day_date BETWEEN :from_date AND :to_date
                        ORDER BY day_date
                        """
                    ).bindparams(
                        camera_id=camera_id,
                        from_date=from_date,
                        to_date=to_date,
                    )
                ).all()
                for row in rows:
                    day_str = str(row[0])
                    days_map[day_str] = {
                        "date": day_str,
                        "cycle_count": int(row[1] or 0),
                    }
                today = self._today(time.time())
                if from_date <= today <= to_date:
                    live_state = self._load_state(camera_id, time.time())
                    self._cache[camera_id] = live_state
                    live_count = int(live_state.cycles_today)
                    if live_count > 0 or today in days_map:
                        days_map[today] = {
                            "date": today,
                            "cycle_count": live_count,
                        }
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"sealer daily stats query failed: {exc}")

        days = [days_map[k] for k in sorted(days_map.keys())]
        return {
            "camera_id": camera_id,
            "from": from_date,
            "to": to_date,
            "timezone": str(TZ),
            "server_today": self._today(time.time()),
            "view_start_hour": VIEW_START_HOUR,
            "view_end_hour": VIEW_END_HOUR,
            "days": days,
        }


def _shift_day_selfcheck() -> None:
    """Дата смены: до 07:00 — вчера, с 07:00 — сегодня."""
    store = SealerCounterStore.__new__(SealerCounterStore)
    before = datetime(2026, 7, 23, 6, 59, 0, tzinfo=TZ).timestamp()
    at = datetime(2026, 7, 23, 7, 0, 0, tzinfo=TZ).timestamp()
    assert store._today(before) == "2026-07-22", store._today(before)
    assert store._today(at) == "2026-07-23", store._today(at)
    assert not store._shift_active(before)
    assert store._shift_active(at)


if __name__ == "__main__":
    _shift_day_selfcheck()
    print("sealer shift-day ok")
