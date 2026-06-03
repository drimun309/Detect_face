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

log = get_logger()

# Запас до начала интервала: последняя смена режима из БД
TIMELINE_HEAD_MAX_SEC = 86400.0
# Запас по умолчанию, если switch_sec не передан (см. get_timeline)
TIMELINE_DEFAULT_SWITCH_SEC = 60.0


@dataclass
class RoiTimerState:
    camera_id: int
    roi_key: str
    roi_index: int
    polygon_json: str
    mode: str = "standby"  # standby | work | idle
    work_seconds: float = 0.0
    idle_seconds: float = 0.0
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
        day_str, hour = self._local_day_hour(ts)
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
                           last_tick, presence_since, absence_since, updated_at
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
        return RoiTimerState(
            camera_id=camera_id,
            roi_key=roi_key,
            roi_index=int(row[0] or roi_index),
            polygon_json=str(row[1] or polygon_json),
            mode=str(row[2] or "standby"),
            work_seconds=float(row[3] or 0),
            idle_seconds=float(row[4] or 0),
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
        state = RoiTimerState(
            camera_id=camera_id,
            roi_key=roi_key,
            roi_index=roi_index,
            polygon_json=polygon_json,
            mode="standby",
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
                    camera_id, roi_key, roi_index, polygon_json, mode,
                    work_seconds, idle_seconds, last_tick,
                    presence_since, absence_since, updated_at
                )
                VALUES (
                    :camera_id, :roi_key, :roi_index, :polygon_json, :mode,
                    :work_seconds, :idle_seconds, :last_tick,
                    :presence_since, :absence_since, :updated_at
                )
                ON CONFLICT (camera_id, roi_key) DO UPDATE SET
                    roi_index = EXCLUDED.roi_index,
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
        polygons: list[list[tuple[float, float]]],
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
                # cleanup cache for removed ROIs
                for cache_key in list(self._cache.keys()):
                    cid, roi_key = cache_key
                    if cid == camera_id and roi_key not in keys_set:
                        del self._cache[cache_key]
                        self._last_present_ts.pop(cache_key, None)

                for idx, poly in enumerate(polygons, start=1):
                    roi_key = keys[idx - 1]
                    poly_json = self._polygon_to_json(poly)
                    state, is_new = self._get_or_load_state(
                        camera_id, roi_key, idx, poly_json
                    )
                    state.roi_index = idx
                    state.polygon_json = poly_json
                    state.updated_at = now
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
                    dt = max(0.0, ts - (state.last_tick or ts))
                    interval_mode = state.mode
                    if interval_mode == "work":
                        state.work_seconds += dt
                    elif interval_mode == "idle":
                        state.idle_seconds += dt
                    if dt > 0:
                        self._accumulate_period(
                            camera_id,
                            roi_key,
                            state.roi_index,
                            interval_mode,
                            dt,
                            ts,
                        )

                    prev_mode = state.mode
                    if effective_present:
                        state.absence_since = None
                        if state.mode in ("standby", "idle"):
                            if state.presence_since is None:
                                state.presence_since = ts
                            elif (ts - state.presence_since) >= switch_seconds:
                                state.mode = "work"
                                state.presence_since = None
                    else:
                        state.presence_since = None
                        if state.mode in ("standby", "work"):
                            if state.absence_since is None:
                                state.absence_since = ts
                            elif (ts - state.absence_since) >= switch_seconds:
                                state.mode = "idle"
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

    def get_overlay_labels(
        self,
        camera_id: int,
        roi_keys: list[str],
        switch_seconds: float,
        now: float | None = None,
    ) -> list[str]:
        ts = now or time.time()
        labels: list[str] = []
        with self._lock:
            for roi_key in roi_keys:
                state = self._cache.get((camera_id, roi_key))
                idx = int(state.roi_index) if state and state.roi_index else 0
                if state is None:
                    labels.append(f"ROI {idx or '?'}: ожидание")
                    continue
                work_txt = self._fmt_hhmmss(state.work_seconds)
                idle_txt = self._fmt_hhmmss(state.idle_seconds)
                roi_lbl = f"ROI {state.roi_index}"
                if state.mode == "work":
                    if state.absence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.absence_since)))
                        labels.append(
                            f"{roi_lbl} работа {work_txt} | простой {idle_txt} (простой через {left}с)"
                        )
                    else:
                        labels.append(f"{roi_lbl} работа {work_txt} | простой {idle_txt}")
                elif state.mode == "idle":
                    if state.presence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.presence_since)))
                        labels.append(
                            f"{roi_lbl} работа {work_txt} | простой {idle_txt} (работа через {left}с)"
                        )
                    else:
                        labels.append(f"{roi_lbl} работа {work_txt} | простой {idle_txt}")
                else:
                    if state.presence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.presence_since)))
                        labels.append(
                            f"{roi_lbl} работа {work_txt} | простой {idle_txt} (работа через {left}с)"
                        )
                    elif state.absence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.absence_since)))
                        labels.append(
                            f"{roi_lbl} работа {work_txt} | простой {idle_txt} (простой через {left}с)"
                        )
                    else:
                        labels.append(f"{roi_lbl} работа {work_txt} | простой {idle_txt}")
        return labels

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
        rs = range_start if range_start is not None else day_start
        re = range_end if range_end is not None else day_end
        rs = max(rs, day_start)
        re = min(re, day_end)
        now = time.time()
        if range_end is None and day_start <= now < day_end:
            re = min(re, now)
        if re <= rs:
            re = min(day_end, now) if day_start <= now < day_end else day_end

        span = max(1.0, re - rs)
        explicit_range = range_start is not None and range_end is not None
        head_before = min(
            TIMELINE_HEAD_MAX_SEC,
            max(120.0, span + 60.0) if explicit_range else max(3600.0, span * 2),
        )

        index_by_key: dict[str, int] = {}
        zones_out: list[dict] = []
        with self._lock:
            try:
                index_rows = self.pg.session.exec(
                    text(
                        """
                        SELECT roi_key, roi_index
                        FROM roi_timers
                        WHERE camera_id = :camera_id
                        ORDER BY roi_index
                        """
                    ).bindparams(camera_id=camera_id)
                ).all()
                for row in index_rows:
                    index_by_key[str(row[0])] = int(row[1] or 0)
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

            daily_by_key: dict[str, tuple[float, float]] = {}
            try:
                daily_rows = self.pg.session.exec(
                    text(
                        """
                        SELECT roi_key, work_seconds, idle_seconds
                        FROM roi_timer_daily
                        WHERE camera_id = :camera_id AND day_date = :day_date
                        """
                    ).bindparams(camera_id=camera_id, day_date=date_str)
                ).all()
                for row in daily_rows:
                    daily_by_key[str(row[0])] = (
                        float(row[1] or 0),
                        float(row[2] or 0),
                    )
            except SQLAlchemyError:
                self._rollback()

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
                daily = daily_by_key.get(roi_key, (0.0, 0.0))
                zones_out.append(
                    {
                        "roi_index": roi_index,
                        "roi_key": roi_key,
                        "segments": segments,
                        "daily_work_seconds": daily[0],
                        "daily_idle_seconds": daily[1],
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
