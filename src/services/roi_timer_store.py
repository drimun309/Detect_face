"""Persistent per-ROI work/idle timers."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import time as dt_time
from threading import Lock
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.db.pg_db import PgSyncDb
from src.utils.logger import get_logger
from src.utils.roi_helpers import RoiPolygonData, default_roi_name, roi_display_name

# Запас до начала интервала: последняя смена режима из БД
TIMELINE_HEAD_MAX_SEC = 86400.0
# Запас по умолчанию, если switch_sec не передан (см. get_timeline)
TIMELINE_DEFAULT_SWITCH_SEC = 60.0
# Окно отображения статистики: часы [start, end) в локальной TZ сервера
VIEW_START_HOUR = 7
VIEW_END_HOUR = 19

log = get_logger()


@dataclass
class RoiTimerState:
    camera_id: int
    roi_key: str
    roi_index: int
    polygon_json: str
    roi_name: str = ""
    mode: str = "standby"  # standby | work | idle
    work_seconds: float = 0.0  # накоплено за текущий день в окне смены 07:00–19:00
    idle_seconds: float = 0.0
    shift_date: str = ""  # календарная дата (YYYY-MM-DD) для work_seconds/idle_seconds
    last_tick: float = 0.0
    presence_since: float | None = None
    absence_since: float | None = None
    updated_at: float = 0.0


class RoiTimerStore:
    """Stores and updates per-ROI timers in PostgreSQL."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = Lock()
        self._cache: dict[tuple[int, str], RoiTimerState] = {}
        self._last_present_ts: dict[tuple[int, str], float] = {}
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
            self.pg.session.exec(
                text(
                    "ALTER TABLE roi_timers ADD COLUMN IF NOT EXISTS "
                    "roi_name VARCHAR(128) NOT NULL DEFAULT ''"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"ROI timers table migration skipped: {exc}")
        self._ensure_events_table()
        self._ensure_history_tables()

    def _ensure_history_tables(self) -> None:
        """Поминутная история по дням и часам для диаграмм за прошлые даты."""
        try:
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS roi_timer_daily (
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        roi_index INTEGER NOT NULL,
                        day_date DATE NOT NULL,
                        work_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        idle_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        standby_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, roi_key, day_date)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS roi_timer_hourly (
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        roi_index INTEGER NOT NULL,
                        day_date DATE NOT NULL,
                        hour SMALLINT NOT NULL,
                        work_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        idle_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, roi_key, day_date, hour)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_roi_timer_hourly_cam_day "
                    "ON roi_timer_hourly (camera_id, day_date)"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"ROI history tables migration skipped: {exc}")

    def _ensure_events_table(self) -> None:
        try:
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS roi_timer_events (
                        id SERIAL PRIMARY KEY,
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        roi_index INTEGER NOT NULL,
                        mode VARCHAR(16) NOT NULL,
                        ts DOUBLE PRECISION NOT NULL
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_roi_timer_events_cam_ts "
                    "ON roi_timer_events (camera_id, ts)"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"ROI timer events table migration skipped: {exc}")

    @staticmethod
    def _local_tz() -> ZoneInfo:
        name = os.environ.get("TZ", "UTC")
        try:
            return ZoneInfo(name)
        except Exception:
            return ZoneInfo("UTC")

    @staticmethod
    def day_range_unix(date_str: str) -> tuple[float, float]:
        """Локальные границы календарного дня [start, end)."""
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
        tz = RoiTimerStore._local_tz()
        start = datetime.combine(day, dt_time.min, tzinfo=tz).timestamp()
        end = datetime.combine(day + timedelta(days=1), dt_time.min, tzinfo=tz).timestamp()
        return start, end

    def _local_day_hour(self, ts: float) -> tuple[str, int]:
        tz = self._local_tz()
        dt = datetime.fromtimestamp(ts, tz=tz)
        return dt.date().isoformat(), dt.hour

    def _shift_bounds_for_date(self, day) -> tuple[float, float]:
        """Границы рабочей смены [07:00, 19:00) для календарной даты."""
        tz = self._local_tz()
        start = datetime.combine(day, dt_time(VIEW_START_HOUR, 0), tzinfo=tz).timestamp()
        end = datetime.combine(day, dt_time(VIEW_END_HOUR, 0), tzinfo=tz).timestamp()
        return start, end

    def _shift_status(self, ts: float) -> str:
        """before | active | after — относительно смены 07:00–19:00 текущего дня."""
        tz = self._local_tz()
        day = datetime.fromtimestamp(ts, tz=tz).date()
        shift_start, shift_end = self._shift_bounds_for_date(day)
        if ts < shift_start:
            return "before"
        if ts >= shift_end:
            return "after"
        return "active"

    @staticmethod
    def _iter_shift_slices(t0: float, t1: float, shift_start: float, shift_end: float):
        """Части [t0, t1), попадающие в [shift_start, shift_end)."""
        if t1 <= t0:
            return
        seg_start = max(t0, shift_start)
        seg_end = min(t1, shift_end)
        if seg_end > seg_start:
            yield seg_start, seg_end

    def _iter_shift_slices_for_interval(self, t0: float, t1: float):
        """Части интервала, попадающие в смену 07:00–19:00 (один или два дня)."""
        if t1 <= t0:
            return
        tz = self._local_tz()
        day = datetime.fromtimestamp(t0, tz=tz).date()
        end_day = datetime.fromtimestamp(t1 - 1e-6, tz=tz).date()
        while day <= end_day:
            shift_start, shift_end = self._shift_bounds_for_date(day)
            yield from self._iter_shift_slices(t0, t1, shift_start, shift_end)
            day += timedelta(days=1)

    def _get_shift_totals_from_db(
        self, camera_id: int, roi_key: str, day_str: str
    ) -> tuple[float, float]:
        """Сумма work/idle за день в окне смены (из почасовых накоплений)."""
        try:
            row = self.pg.session.exec(
                text(
                    """
                    SELECT COALESCE(SUM(work_seconds), 0), COALESCE(SUM(idle_seconds), 0)
                    FROM roi_timer_hourly
                    WHERE camera_id = :camera_id
                      AND roi_key = :roi_key
                      AND day_date = :day_date
                      AND hour >= :view_start AND hour < :view_end
                    """
                ).bindparams(
                    camera_id=camera_id,
                    roi_key=roi_key,
                    day_date=day_str,
                    view_start=VIEW_START_HOUR,
                    view_end=VIEW_END_HOUR,
                )
            ).first()
        except SQLAlchemyError:
            self._rollback()
            return 0.0, 0.0
        if row is None:
            return 0.0, 0.0
        return float(row[0] or 0), float(row[1] or 0)

    def _accumulate_shift_segment(
        self,
        camera_id: int,
        roi_key: str,
        roi_index: int,
        mode: str,
        seg_start: float,
        seg_end: float,
    ) -> None:
        """Накопить work/idle за отрезок внутри смены, разбивая по часам."""
        if mode not in ("work", "idle") or seg_end <= seg_start:
            return
        tz = self._local_tz()
        cur = seg_start
        while cur < seg_end:
            dt_loc = datetime.fromtimestamp(cur, tz=tz)
            hour = dt_loc.hour
            next_hour = datetime.combine(
                dt_loc.date(),
                dt_time(hour + 1 if hour < 23 else 0, 0),
                tzinfo=tz,
            )
            if hour == 23:
                next_hour = datetime.combine(
                    dt_loc.date() + timedelta(days=1),
                    dt_time(0, 0),
                    tzinfo=tz,
                )
            next_ts = next_hour.timestamp()
            chunk_end = min(seg_end, next_ts)
            dt = chunk_end - cur
            if dt > 0:
                self._accumulate_period(
                    camera_id, roi_key, roi_index, mode, dt, chunk_end
                )
            cur = chunk_end

    def _sync_shift_day_state(
        self,
        state: RoiTimerState,
        camera_id: int,
        roi_key: str,
        ts: float,
        prev_ts: float,
    ) -> None:
        """Сброс/загрузка счётчиков при смене дня или входе в окно 07:00."""
        day_str, _ = self._local_day_hour(ts)
        status = self._shift_status(ts)
        prev_status = self._shift_status(prev_ts) if prev_ts else status

        if state.shift_date != day_str:
            state.shift_date = day_str
            state.work_seconds = 0.0
            state.idle_seconds = 0.0
            state.mode = "standby"
            state.presence_since = None
            state.absence_since = None
            if status == "active":
                w, i = self._get_shift_totals_from_db(camera_id, roi_key, day_str)
                state.work_seconds = w
                state.idle_seconds = i
        elif status == "active" and prev_status == "before":
            state.mode = "standby"
            state.presence_since = None
            state.absence_since = None

    def _accumulate_period(
        self,
        camera_id: int,
        roi_key: str,
        roi_index: int,
        mode: str,
        dt: float,
        ts: float,
    ) -> None:
        """Накопить секунды за интервал в сутки и час (локальный TZ)."""
        if dt <= 0:
            return
        # Храним секунды в "час, к которому относится начало интервала".
        # В противном случае при разбиении по границам (cur..next_hour)
        # всё будет приписываться следующему часу.
        day_str, hour = self._local_day_hour(ts - 1e-6)
        work_d = idle_d = standby_d = 0.0
        work_h = idle_h = 0.0
        if mode == "work":
            work_d = dt
            work_h = dt
        elif mode == "idle":
            idle_d = dt
            idle_h = dt
        else:
            standby_d = dt

        self.pg.session.exec(
            text(
                """
                INSERT INTO roi_timer_daily (
                    camera_id, roi_key, roi_index, day_date,
                    work_seconds, idle_seconds, standby_seconds, updated_at
                )
                VALUES (
                    :camera_id, :roi_key, :roi_index, :day_date,
                    :work_seconds, :idle_seconds, :standby_seconds, :updated_at
                )
                ON CONFLICT (camera_id, roi_key, day_date) DO UPDATE SET
                    roi_index = EXCLUDED.roi_index,
                    work_seconds = roi_timer_daily.work_seconds + EXCLUDED.work_seconds,
                    idle_seconds = roi_timer_daily.idle_seconds + EXCLUDED.idle_seconds,
                    standby_seconds = roi_timer_daily.standby_seconds + EXCLUDED.standby_seconds,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(
                camera_id=camera_id,
                roi_key=roi_key,
                roi_index=roi_index,
                day_date=day_str,
                work_seconds=work_d,
                idle_seconds=idle_d,
                standby_seconds=standby_d,
                updated_at=ts,
            )
        )
        self.pg.session.exec(
            text(
                """
                INSERT INTO roi_timer_hourly (
                    camera_id, roi_key, roi_index, day_date, hour,
                    work_seconds, idle_seconds
                )
                VALUES (
                    :camera_id, :roi_key, :roi_index, :day_date, :hour,
                    :work_seconds, :idle_seconds
                )
                ON CONFLICT (camera_id, roi_key, day_date, hour) DO UPDATE SET
                    roi_index = EXCLUDED.roi_index,
                    work_seconds = roi_timer_hourly.work_seconds + EXCLUDED.work_seconds,
                    idle_seconds = roi_timer_hourly.idle_seconds + EXCLUDED.idle_seconds
                """
            ).bindparams(
                camera_id=camera_id,
                roi_key=roi_key,
                roi_index=roi_index,
                day_date=day_str,
                hour=hour,
                work_seconds=work_h,
                idle_seconds=idle_h,
            )
        )

    def _log_mode_event(
        self,
        camera_id: int,
        roi_key: str,
        roi_index: int,
        mode: str,
        ts: float,
    ) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO roi_timer_events (camera_id, roi_key, roi_index, mode, ts)
                VALUES (:camera_id, :roi_key, :roi_index, :mode, :ts)
                """
            ).bindparams(
                camera_id=camera_id,
                roi_key=roi_key,
                roi_index=roi_index,
                mode=mode,
                ts=ts,
            )
        )

    @staticmethod
    def _polygon_to_json(polygon: list[tuple[float, float]]) -> str:
        return json.dumps(
            [[float(x), float(y)] for x, y in polygon],
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @staticmethod
    def _fmt_hhmmss(seconds: float) -> str:
        total = max(0, int(seconds))
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _load_state_from_db(
        self, camera_id: int, roi_key: str, roi_index: int, polygon_json: str
    ) -> RoiTimerState | None:
        """Восстановить накопленное время и режим из PostgreSQL после перезапуска."""
        try:
            row = self.pg.session.exec(
                text(
                    """
                    SELECT roi_index, polygon_json, mode, work_seconds, idle_seconds,
                           last_tick, presence_since, absence_since, updated_at,
                           COALESCE(roi_name, '') AS roi_name
                    FROM roi_timers
                    WHERE camera_id = :camera_id AND roi_key = :roi_key
                    """
                ).bindparams(camera_id=camera_id, roi_key=roi_key)
            ).first()
        except SQLAlchemyError:
            self._rollback()
            return None
        if row is None:
            return None

        now = time.time()
        day_str, _ = self._local_day_hour(now)
        work, idle = self._get_shift_totals_from_db(camera_id, roi_key, day_str)
        return RoiTimerState(
            camera_id=camera_id,
            roi_key=roi_key,
            roi_index=int(row[0] or roi_index),
            polygon_json=str(row[1] or polygon_json),
            roi_name=str(row[9] or ""),
            mode=str(row[2] or "standby"),
            work_seconds=work,
            idle_seconds=idle,
            shift_date=day_str,
            # Не начисляем простой/работу за время, пока сервис был выключен
            last_tick=now,
            presence_since=None,
            absence_since=None,
            updated_at=now,
        )

    def _get_or_load_state(
        self,
        camera_id: int,
        roi_key: str,
        roi_index: int,
        polygon_json: str,
    ) -> tuple[RoiTimerState, bool]:
        """Вернуть состояние из кэша/БД. bool = создана новая зона."""
        cache_key = (camera_id, roi_key)
        state = self._cache.get(cache_key)
        if state is not None:
            return state, False

        restored = self._load_state_from_db(
            camera_id, roi_key, roi_index, polygon_json
        )
        if restored is not None:
            restored.roi_index = roi_index
            restored.polygon_json = polygon_json
            self._cache[cache_key] = restored
            log.info(
                f"ROI timer restored cam={camera_id} {roi_key}: "
                f"work={restored.work_seconds:.0f}s idle={restored.idle_seconds:.0f}s "
                f"mode={restored.mode}"
            )
            return restored, False

        now = time.time()
        day_str, _ = self._local_day_hour(now)
        state = RoiTimerState(
            camera_id=camera_id,
            roi_key=roi_key,
            roi_index=roi_index,
            polygon_json=polygon_json,
            mode="standby",
            shift_date=day_str,
            last_tick=now,
            updated_at=now,
        )
        self._cache[cache_key] = state
        return state, True

    def _upsert_state(self, st: RoiTimerState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO roi_timers (
                    camera_id, roi_key, roi_index, roi_name, polygon_json, mode,
                    work_seconds, idle_seconds, last_tick,
                    presence_since, absence_since, updated_at
                )
                VALUES (
                    :camera_id, :roi_key, :roi_index, :roi_name, :polygon_json, :mode,
                    :work_seconds, :idle_seconds, :last_tick,
                    :presence_since, :absence_since, :updated_at
                )
                ON CONFLICT (camera_id, roi_key) DO UPDATE SET
                    roi_index = EXCLUDED.roi_index,
                    roi_name = EXCLUDED.roi_name,
                    polygon_json = EXCLUDED.polygon_json,
                    mode = EXCLUDED.mode,
                    work_seconds = EXCLUDED.work_seconds,
                    idle_seconds = EXCLUDED.idle_seconds,
                    last_tick = EXCLUDED.last_tick,
                    presence_since = EXCLUDED.presence_since,
                    absence_since = EXCLUDED.absence_since,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(
                camera_id=st.camera_id,
                roi_key=st.roi_key,
                roi_index=st.roi_index,
                roi_name=st.roi_name or default_roi_name(st.roi_index),
                polygon_json=st.polygon_json,
                mode=st.mode,
                work_seconds=st.work_seconds,
                idle_seconds=st.idle_seconds,
                last_tick=st.last_tick,
                presence_since=st.presence_since,
                absence_since=st.absence_since,
                updated_at=st.updated_at,
            )
        )

    def sync_camera_rois(
        self,
        camera_id: int,
        polygons: list[RoiPolygonData],
    ) -> list[str]:
        """Create/update rows for active ROIs and delete removed ROIs data.

        ROI keys stay stable by roi_index, so point edits do not reset timers.
        """
        now = time.time()
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        "SELECT roi_key, roi_index FROM roi_timers "
                        "WHERE camera_id = :camera_id ORDER BY roi_index"
                    ).bindparams(camera_id=camera_id)
                ).all()
                existing_by_index: dict[int, str] = {}
                existing_keys: list[str] = []
                max_suffix = 0
                for row in rows:
                    roi_key = str(row[0])
                    roi_index = int(row[1] or 0)
                    existing_by_index[roi_index] = roi_key
                    existing_keys.append(roi_key)
                    if roi_key.startswith("roi"):
                        try:
                            max_suffix = max(max_suffix, int(roi_key[3:]))
                        except ValueError:
                            pass

                keys: list[str] = []
                for idx, _poly in enumerate(polygons, start=1):
                    roi_key = existing_by_index.get(idx)
                    if roi_key is None:
                        max_suffix += 1
                        roi_key = f"roi{max_suffix:03d}"
                    keys.append(roi_key)

                keys_set = set(keys)
                for roi_key in existing_keys:
                    if roi_key not in keys_set:
                        self.pg.session.exec(
                            text(
                                "DELETE FROM roi_timers WHERE camera_id = :camera_id "
                                "AND roi_key = :roi_key"
                            ).bindparams(camera_id=camera_id, roi_key=roi_key)
                        )
                        self.pg.session.exec(
                            text(
                                "DELETE FROM roi_timer_events WHERE camera_id = :camera_id "
                                "AND roi_key = :roi_key"
                            ).bindparams(camera_id=camera_id, roi_key=roi_key)
                        )
                        self.pg.session.exec(
                            text(
                                "DELETE FROM roi_timer_daily WHERE camera_id = :camera_id "
                                "AND roi_key = :roi_key"
                            ).bindparams(camera_id=camera_id, roi_key=roi_key)
                        )
                        self.pg.session.exec(
                            text(
                                "DELETE FROM roi_timer_hourly WHERE camera_id = :camera_id "
                                "AND roi_key = :roi_key"
                            ).bindparams(camera_id=camera_id, roi_key=roi_key)
                        )
                for cache_key in list(self._cache.keys()):
                    cid, roi_key = cache_key
                    if cid == camera_id and roi_key not in keys_set:
                        del self._cache[cache_key]
                        self._last_present_ts.pop(cache_key, None)

                for idx, poly_data in enumerate(polygons, start=1):
                    roi_key = keys[idx - 1]
                    poly_json = self._polygon_to_json(poly_data.points)
                    roi_name = (poly_data.name or "").strip() or default_roi_name(idx)
                    state, is_new = self._get_or_load_state(
                        camera_id, roi_key, idx, poly_json
                    )
                    state.roi_index = idx
                    state.polygon_json = poly_json
                    state.roi_name = roi_name
                    state.updated_at = now
                    self._cache[(camera_id, roi_key)] = state
                    self.pg.session.exec(
                        text(
                            """
                            UPDATE roi_timer_events
                            SET roi_index = :roi_index
                            WHERE camera_id = :camera_id AND roi_key = :roi_key
                            """
                        ).bindparams(
                            camera_id=camera_id,
                            roi_key=roi_key,
                            roi_index=idx,
                        )
                    )
                    if is_new:
                        self._log_mode_event(
                            camera_id, roi_key, idx, state.mode, now
                        )
                    self._upsert_state(state)
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"ROI timers sync failed (camera={camera_id}): {exc}")
        return keys

    def _roi_names_for_camera(self, camera_id: int) -> dict[str, str]:
        names: dict[str, str] = {}
        try:
            rows = self.pg.session.exec(
                text(
                    """
                    SELECT roi_key, roi_index, COALESCE(roi_name, '') AS roi_name
                    FROM roi_timers
                    WHERE camera_id = :camera_id
                    """
                ).bindparams(camera_id=camera_id)
            ).all()
            for row in rows:
                roi_key = str(row[0])
                roi_index = int(row[1] or 0)
                names[roi_key] = roi_display_name(str(row[2] or ""), roi_index)
        except SQLAlchemyError:
            self._rollback()
        return names

    def delete_camera(self, camera_id: int) -> None:
        with self._lock:
            try:
                for table in (
                    "roi_timer_hourly",
                    "roi_timer_daily",
                    "roi_timer_events",
                    "roi_timers",
                ):
                    self.pg.session.exec(
                        text(
                            f"DELETE FROM {table} WHERE camera_id = :camera_id"
                        ).bindparams(camera_id=camera_id)
                    )
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"ROI timers camera delete failed (camera={camera_id}): {exc}")
            for cache_key in list(self._cache.keys()):
                if cache_key[0] == camera_id:
                    del self._cache[cache_key]
                    self._last_present_ts.pop(cache_key, None)

    def tick(
        self,
        camera_id: int,
        roi_keys: list[str],
        presence_flags: list[bool],
        switch_seconds: float,
        reset_grace_seconds: float = 0.0,
        now: float | None = None,
    ) -> None:
        if not roi_keys or len(roi_keys) != len(presence_flags):
            return
        ts = now or time.time()
        with self._lock:
            try:
                for roi_key, present in zip(roi_keys, presence_flags):
                    cache_key = (camera_id, roi_key)
                    state = self._cache.get(cache_key)
                    if state is None:
                        state = self._load_state_from_db(
                            camera_id, roi_key, 0, "[]"
                        )
                        if state is None:
                            continue
                        self._cache[cache_key] = state

                    prev_ts = state.last_tick or ts
                    self._sync_shift_day_state(
                        state, camera_id, roi_key, ts, prev_ts
                    )
                    shift_status = self._shift_status(ts)

                    if present:
                        self._last_present_ts[cache_key] = ts
                        effective_present = True
                    else:
                        last_seen = self._last_present_ts.get(cache_key)
                        effective_present = bool(
                            last_seen is not None
                            and reset_grace_seconds > 0
                            and (ts - last_seen) <= reset_grace_seconds
                        )

                    interval_mode = state.mode
                    if (
                        shift_status == "active"
                        and state.last_tick
                        and ts > state.last_tick
                    ):
                        for seg_start, seg_end in self._iter_shift_slices_for_interval(
                            state.last_tick, ts
                        ):
                            seg_dt = seg_end - seg_start
                            if interval_mode == "work":
                                state.work_seconds += seg_dt
                            elif interval_mode == "idle":
                                state.idle_seconds += seg_dt
                            if seg_dt > 0 and interval_mode in ("work", "idle"):
                                self._accumulate_shift_segment(
                                    camera_id,
                                    roi_key,
                                    state.roi_index,
                                    interval_mode,
                                    seg_start,
                                    seg_end,
                                )

                    # Таймеры перехода для оверлея — по фактическому присутствию
                    if present:
                        state.absence_since = None
                        if state.mode in ("standby", "idle") and state.presence_since is None:
                            state.presence_since = ts
                    else:
                        state.presence_since = None
                        if state.mode in ("standby", "work") and state.absence_since is None:
                            state.absence_since = ts

                    prev_mode = state.mode
                    if shift_status == "active":
                        if effective_present:
                            if state.mode in ("standby", "idle"):
                                if state.presence_since is None:
                                    state.presence_since = ts
                                elif (ts - state.presence_since) >= switch_seconds:
                                    state.mode = "work"
                                    state.presence_since = None
                                    state.absence_since = None
                        else:
                            if state.mode in ("standby", "work"):
                                if state.absence_since is None:
                                    state.absence_since = ts
                                elif (ts - state.absence_since) >= switch_seconds:
                                    state.mode = "idle"
                                    state.presence_since = None
                                    state.absence_since = None

                        if state.mode != prev_mode:
                            self._log_mode_event(
                                camera_id,
                                roi_key,
                                state.roi_index,
                                state.mode,
                                ts,
                            )

                    state.last_tick = ts
                    state.updated_at = ts
                    self._upsert_state(state)

                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"ROI timers tick failed (camera={camera_id}): {exc}")

    def _countdown_to_idle(
        self,
        cache_key: tuple[int, str],
        state: RoiTimerState,
        ts: float,
        switch_seconds: float,
        reset_grace_seconds: float,
        raw_present: bool | None,
    ) -> int | None:
        """Секунды до простоя (с учётом grace после ухода человека)."""
        if state.mode != "work" or raw_present is True:
            return None
        last_seen = self._last_present_ts.get(cache_key)
        if last_seen is None and state.absence_since is not None:
            last_seen = state.absence_since - reset_grace_seconds
        if last_seen is None:
            return None
        deadline = last_seen + reset_grace_seconds + switch_seconds
        return max(0, int(deadline - ts))

    def _countdown_to_work(
        self,
        state: RoiTimerState,
        ts: float,
        switch_seconds: float,
        raw_present: bool | None,
    ) -> int | None:
        """Секунды до работы."""
        if state.mode not in ("standby", "idle"):
            return None
        if raw_present is False:
            return None
        if state.presence_since is None:
            return None
        return max(0, int(switch_seconds - (ts - state.presence_since)))

    def get_overlay_labels(
        self,
        camera_id: int,
        roi_keys: list[str],
        switch_seconds: float,
        now: float | None = None,
        presence_flags: list[bool] | None = None,
        reset_grace_seconds: float = 0.0,
    ) -> list[str]:
        ts = now or time.time()
        shift_lbl = f"смена {VIEW_START_HOUR:02d}:00–{VIEW_END_HOUR:02d}:00"
        labels: list[str] = []
        with self._lock:
            for idx, roi_key in enumerate(roi_keys):
                state = self._cache.get((camera_id, roi_key))
                cache_key = (camera_id, roi_key)
                raw_present = (
                    presence_flags[idx]
                    if presence_flags is not None and idx < len(presence_flags)
                    else None
                )
                roi_lbl = roi_display_name(
                    state.roi_name if state else "",
                    state.roi_index if state else (idx + 1),
                )
                shift_status = self._shift_status(ts)

                if state is None:
                    labels.append(f"{roi_lbl}: ожидание | {shift_lbl}")
                    continue

                work_txt = self._fmt_hhmmss(state.work_seconds)
                idle_txt = self._fmt_hhmmss(state.idle_seconds)

                if shift_status == "before":
                    labels.append(
                        f"{roi_lbl} работа {work_txt} | {shift_lbl} (старт в {VIEW_START_HOUR:02d}:00)"
                    )
                    continue
                if shift_status == "after":
                    labels.append(
                        f"{roi_lbl} работа {work_txt} | простой {idle_txt} | {shift_lbl} (завершена)"
                    )
                    continue

                to_idle = self._countdown_to_idle(
                    cache_key, state, ts, switch_seconds, reset_grace_seconds, raw_present
                )
                to_work = self._countdown_to_work(state, ts, switch_seconds, raw_present)

                if to_idle is not None:
                    labels.append(
                        f"{roi_lbl} работа {work_txt} | простой {idle_txt} (простой через {to_idle}с)"
                    )
                elif to_work is not None:
                    labels.append(
                        f"{roi_lbl} работа {work_txt} | простой {idle_txt} (работа через {to_work}с)"
                    )
                else:
                    labels.append(f"{roi_lbl} работа {work_txt} | простой {idle_txt}")
        return labels

    @staticmethod
    def _sum_hourly_window(
        hourly_rows: list[tuple[int, float, float]],
        start_hour: int,
        end_hour: int,
    ) -> tuple[float, float]:
        work = idle = 0.0
        for hour, w, i in hourly_rows:
            if start_hour <= hour < end_hour:
                work += w
                idle += i
        return work, idle

    def get_timeline(
        self,
        camera_id: int,
        date_str: str,
        range_start: float | None = None,
        range_end: float | None = None,
        switch_sec: float | None = None,
    ) -> dict:
        """Сегменты work/idle/standby по зонам за день или интервал."""
        sw = float(switch_sec or TIMELINE_DEFAULT_SWITCH_SEC)
        max_extrapolate = max(sw * 2.0, sw + 30.0)
        day_start, day_end = self.day_range_unix(date_str)
        explicit_range = range_start is not None and range_end is not None
        if explicit_range:
            rs = max(float(range_start), day_start)
            re = min(float(range_end), day_end)
        else:
            rs = day_start + VIEW_START_HOUR * 3600
            re = day_start + VIEW_END_HOUR * 3600
            rs = max(rs, day_start)
            re = min(re, day_end)
        now = time.time()
        if not explicit_range and day_start <= now < day_end:
            re = min(re, now)
        if re <= rs:
            re = min(day_end, now) if day_start <= now < day_end else day_end

        span = max(1.0, re - rs)
        head_before = min(
            TIMELINE_HEAD_MAX_SEC,
            max(120.0, span + 60.0) if explicit_range else max(3600.0, span * 2),
        )

        index_by_key: dict[str, int] = {}
        name_by_key: dict[str, str] = {}
        zones_out: list[dict] = []
        with self._lock:
            try:
                index_rows = self.pg.session.exec(
                    text(
                        """
                        SELECT roi_key, roi_index, COALESCE(roi_name, '') AS roi_name
                        FROM roi_timers
                        WHERE camera_id = :camera_id
                        ORDER BY roi_index
                        """
                    ).bindparams(camera_id=camera_id)
                ).all()
                for row in index_rows:
                    roi_key = str(row[0])
                    roi_index = int(row[1] or 0)
                    index_by_key[roi_key] = roi_index
                    name_by_key[roi_key] = roi_display_name(str(row[2] or ""), roi_index)
            except SQLAlchemyError:
                self._rollback()

            by_key: dict[str, list[tuple[float, str, int]]] = {
                k: [] for k in index_by_key
            }
            try:
                rows = self.pg.session.exec(
                    text(
                        """
                        SELECT roi_key, roi_index, mode, ts
                        FROM roi_timer_events
                        WHERE camera_id = :camera_id
                          AND ts >= :range_start - :head_before
                          AND ts <= :range_end
                        ORDER BY roi_key, ts
                        """
                    ).bindparams(
                        camera_id=camera_id,
                        range_start=rs,
                        range_end=re,
                        head_before=head_before,
                    )
                ).all()
                for row in rows:
                    roi_key = str(row[0])
                    roi_index = int(row[1] or 0)
                    mode = str(row[2] or "standby")
                    ts = float(row[3] or 0)
                    by_key.setdefault(roi_key, []).append((ts, mode, roi_index))
                    if roi_key not in index_by_key:
                        index_by_key[roi_key] = roi_index
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"ROI timeline query failed: {exc}")

            hourly_by_key: dict[str, list[tuple[int, float, float]]] = {}
            try:
                hourly_rows = self.pg.session.exec(
                    text(
                        """
                        SELECT roi_key, hour, work_seconds, idle_seconds
                        FROM roi_timer_hourly
                        WHERE camera_id = :camera_id AND day_date = :day_date
                        ORDER BY roi_key, hour
                        """
                    ).bindparams(camera_id=camera_id, day_date=date_str)
                ).all()
                for row in hourly_rows:
                    roi_key = str(row[0])
                    hourly_by_key.setdefault(roi_key, []).append(
                        (int(row[1] or 0), float(row[2] or 0), float(row[3] or 0))
                    )
            except SQLAlchemyError:
                self._rollback()

            for roi_key in sorted(
                index_by_key.keys(),
                key=lambda k: (index_by_key[k], k),
            ):
                roi_index = index_by_key[roi_key]
                events = by_key.get(roi_key, [])
                segments = self._events_to_segments(
                    events,
                    rs,
                    re,
                    switch_sec=sw,
                    max_extrapolate_sec=max_extrapolate,
                )
                source = "events"
                if not self._segments_have_activity(segments):
                    hourly = hourly_by_key.get(roi_key, [])
                    if hourly:
                        segments = self._hourly_to_segments(
                            hourly, day_start, rs, re
                        )
                        source = "hourly"
                if explicit_range:
                    tz = self._local_tz()
                    start_h = datetime.fromtimestamp(rs, tz=tz).hour
                    end_h = datetime.fromtimestamp(max(rs, re - 1), tz=tz).hour + 1
                    totals = self._sum_hourly_window(
                        hourly_by_key.get(roi_key, []),
                        start_h,
                        end_h,
                    )
                else:
                    totals = self._sum_hourly_window(
                        hourly_by_key.get(roi_key, []),
                        VIEW_START_HOUR,
                        VIEW_END_HOUR,
                    )
                zones_out.append(
                    {
                        "roi_index": roi_index,
                        "roi_key": roi_key,
                        "roi_name": name_by_key.get(
                            roi_key, roi_display_name("", roi_index)
                        ),
                        "segments": segments,
                        "daily_work_seconds": totals[0],
                        "daily_idle_seconds": totals[1],
                        "timeline_source": source,
                    }
                )

        events_in_range = sum(
            1
            for evts in by_key.values()
            for ts, _mode, _idx in evts
            if rs < ts <= re
        )

        return {
            "camera_id": camera_id,
            "date": date_str,
            "range_start": rs,
            "range_end": re,
            "day_end": day_end,
            "zones": zones_out,
            "events_in_range": events_in_range,
            "timezone": str(self._local_tz()),
        }

    @staticmethod
    def _segments_have_activity(segments: list[dict]) -> bool:
        for seg in segments:
            if seg.get("mode") in ("work", "idle") and seg["end"] > seg["start"]:
                return True
        return False

    @staticmethod
    def _hourly_to_segments(
        hours: list[tuple[int, float, float]],
        day_start: float,
        range_start: float,
        range_end: float,
    ) -> list[dict]:
        """Полоса дня из почасовых накоплений (если нет журнала смен)."""
        raw: list[dict] = []
        for hour, work, idle in sorted(hours, key=lambda x: x[0]):
            t0 = day_start + hour * 3600
            t1 = t0 + 3600
            seg_start = max(range_start, t0)
            seg_end = min(range_end, t1)
            if seg_end <= seg_start:
                continue
            if work <= 0 and idle <= 0:
                mode = "standby"
            elif work >= idle:
                mode = "work"
            else:
                mode = "idle"
            raw.append({"start": seg_start, "end": seg_end, "mode": mode})

        merged: list[dict] = []
        for seg in raw:
            if merged and merged[-1]["mode"] == seg["mode"]:
                merged[-1]["end"] = seg["end"]
            else:
                merged.append(seg)
        return merged or [
            {"start": range_start, "end": range_end, "mode": "standby"}
        ]

    @staticmethod
    def _compress_mode_events(
        events: list[tuple[float, str, int]],
        *,
        min_hold_sec: float = 60.0,
    ) -> list[tuple[float, str, int]]:
        """Смены режима из БД: без повторов и без дребезга короче min_hold_sec."""
        out: list[tuple[float, str, int]] = []
        for ts, mode, idx in sorted(events, key=lambda x: x[0]):
            if not out or out[-1][1] != mode:
                out.append((ts, mode, idx))
        if len(out) < 2 or min_hold_sec <= 0:
            return out
        stable: list[tuple[float, str, int]] = [out[0]]
        for ts, mode, idx in out[1:]:
            prev_ts, prev_mode, _ = stable[-1]
            if mode != prev_mode and (ts - prev_ts) < min_hold_sec:
                continue
            stable.append((ts, mode, idx))
        return stable

    @staticmethod
    def _events_to_segments(
        events: list[tuple[float, str, int]],
        range_start: float,
        range_end: float,
        switch_sec: float = TIMELINE_DEFAULT_SWITCH_SEC,
        max_extrapolate_sec: float | None = None,
    ) -> list[dict]:
        """Полоса по roi_timer_events: режим между сменами из журнала."""
        if range_end <= range_start:
            return []

        extrap = max_extrapolate_sec if max_extrapolate_sec is not None else max(
            switch_sec * 2.0, switch_sec + 30.0
        )
        compressed = RoiTimerStore._compress_mode_events(
            events, min_hold_sec=switch_sec
        )
        if not compressed:
            return [
                {
                    "start": range_start,
                    "end": range_end,
                    "mode": "standby",
                }
            ]

        last_before: tuple[float, str] | None = None
        for ts, mode, _idx in compressed:
            if ts <= range_start:
                last_before = (ts, mode)
            else:
                break

        mode_at_start = "standby"
        if last_before is not None:
            gap = range_start - last_before[0]
            if gap <= extrap:
                mode_at_start = last_before[1]

        segments: list[dict] = []
        cursor = range_start
        current_mode = mode_at_start

        for ts, mode, _idx in compressed:
            if ts <= range_start:
                current_mode = mode
                continue
            if ts > range_end:
                break
            if ts > cursor:
                segments.append(
                    {"start": cursor, "end": ts, "mode": current_mode}
                )
                cursor = ts
            current_mode = mode

        if cursor < range_end:
            segments.append(
                {"start": cursor, "end": range_end, "mode": current_mode}
            )

        merged: list[dict] = []
        for seg in segments:
            if seg["end"] <= seg["start"]:
                continue
            if merged and merged[-1]["mode"] == seg["mode"]:
                merged[-1]["end"] = seg["end"]
            else:
                merged.append(seg)

        return merged or [
            {"start": range_start, "end": range_end, "mode": "standby"}
        ]

    def get_stat_dates(self, camera_id: int) -> list[str]:
        """Даты с накопленной статистикой ROI для камеры."""
        try:
            rows = self.pg.session.exec(
                text(
                    """
                    SELECT DISTINCT day_date
                    FROM roi_timer_daily
                    WHERE camera_id = :camera_id
                    ORDER BY day_date
                    """
                ).bindparams(camera_id=camera_id)
            ).all()
            return [str(row[0]) for row in rows]
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"ROI stat dates query failed: {exc}")
            return []

    def get_daily_stats_range(
        self, camera_id: int, from_date: str, to_date: str
    ) -> dict:
        """Статистика work/idle по ROI за диапазон дат (окно VIEW_START–VIEW_END)."""
        days_map: dict[str, dict] = {}
        name_by_key = self._roi_names_for_camera(camera_id)
        try:
            rows = self.pg.session.exec(
                text(
                    """
                    SELECT day_date, roi_key, MAX(roi_index) AS roi_index,
                           SUM(work_seconds) AS work_seconds,
                           SUM(idle_seconds) AS idle_seconds
                    FROM roi_timer_hourly
                    WHERE camera_id = :camera_id
                      AND day_date BETWEEN :from_date AND :to_date
                      AND hour >= :view_start AND hour < :view_end
                    GROUP BY day_date, roi_key
                    ORDER BY day_date, roi_index, roi_key
                    """
                ).bindparams(
                    camera_id=camera_id,
                    from_date=from_date,
                    to_date=to_date,
                    view_start=VIEW_START_HOUR,
                    view_end=VIEW_END_HOUR,
                )
            ).all()
            for row in rows:
                day_str = str(row[0])
                zone = {
                    "roi_key": str(row[1]),
                    "roi_index": int(row[2] or 0),
                    "roi_name": name_by_key.get(
                        str(row[1]),
                        roi_display_name("", int(row[2] or 0)),
                    ),
                    "work_seconds": float(row[3] or 0),
                    "idle_seconds": float(row[4] or 0),
                    "standby_seconds": 0.0,
                }
                entry = days_map.setdefault(
                    day_str,
                    {
                        "date": day_str,
                        "work_seconds": 0.0,
                        "idle_seconds": 0.0,
                        "standby_seconds": 0.0,
                        "zones": [],
                    },
                )
                entry["work_seconds"] += zone["work_seconds"]
                entry["idle_seconds"] += zone["idle_seconds"]
                entry["standby_seconds"] += zone["standby_seconds"]
                entry["zones"].append(zone)
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"ROI daily stats range query failed: {exc}")

        days = [days_map[k] for k in sorted(days_map.keys())]
        return {
            "camera_id": camera_id,
            "from": from_date,
            "to": to_date,
            "timezone": str(self._local_tz()),
            "view_start_hour": VIEW_START_HOUR,
            "view_end_hour": VIEW_END_HOUR,
            "days": days,
        }
