"""Person-hours counter per ROI work zone (max 2 workers)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.db.pg_db import PgSyncDb
from src.services.roi_timer_store import roi_display_name
from src.utils.logger import get_logger

log = get_logger()
TZ = ZoneInfo("Asia/Tbilisi")
VIEW_START_HOUR = 7
VIEW_END_HOUR = 19
ROI_MAX_WORKERS = 2


@dataclass
class RoiPeopleCounterState:
    camera_id: int
    roi_key: str
    current_workers: int = 0
    max_workers: int = ROI_MAX_WORKERS
    seconds_0_workers: float = 0.0
    seconds_1_worker: float = 0.0
    seconds_2_workers: float = 0.0
    person_seconds: float = 0.0
    day_date: str = ""
    last_tick: float = 0.0
    updated_at: float = 0.0


class RoiPeopleCounterStore:
    """Accumulates occupancy duration and person-seconds per ROI zone."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._cache: dict[tuple[int, str], RoiPeopleCounterState] = {}
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
                    CREATE TABLE IF NOT EXISTS roi_people_counters (
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        current_workers INTEGER NOT NULL DEFAULT 0,
                        max_workers INTEGER NOT NULL DEFAULT 2,
                        day_date DATE NOT NULL DEFAULT CURRENT_DATE,
                        seconds_0_workers DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seconds_1_worker DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seconds_2_workers DOUBLE PRECISION NOT NULL DEFAULT 0,
                        person_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        last_tick DOUBLE PRECISION NOT NULL DEFAULT 0,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, roi_key)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS roi_people_daily (
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        day_date DATE NOT NULL,
                        max_workers INTEGER NOT NULL DEFAULT 2,
                        seconds_0_workers DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seconds_1_worker DOUBLE PRECISION NOT NULL DEFAULT 0,
                        seconds_2_workers DOUBLE PRECISION NOT NULL DEFAULT 0,
                        person_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, roi_key, day_date)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS roi_people_events (
                        id BIGSERIAL PRIMARY KEY,
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
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
                    "CREATE INDEX IF NOT EXISTS idx_roi_people_events_cam_key_ts "
                    "ON roi_people_events (camera_id, roi_key, ts)"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"roi people tables migration skipped: {exc}")

    def _today(self, ts: float) -> str:
        return datetime.fromtimestamp(ts, TZ).date().isoformat()

    def _shift_active(self, ts: float) -> bool:
        dt = datetime.fromtimestamp(ts, TZ)
        start = dt.replace(hour=VIEW_START_HOUR, minute=0, second=0, microsecond=0)
        end = dt.replace(hour=VIEW_END_HOUR, minute=0, second=0, microsecond=0)
        return start <= dt < end

    def _shift_bounds_for_date(self, day_str: str) -> tuple[float, float]:
        parts = day_str.split("-")
        if len(parts) != 3:
            return 0.0, 0.0
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        start = datetime(y, m, d, VIEW_START_HOUR, 0, 0, tzinfo=TZ)
        end = datetime(y, m, d, VIEW_END_HOUR, 0, 0, tzinfo=TZ)
        return start.timestamp(), end.timestamp()

    def _load_state(
        self, camera_id: int, roi_key: str, max_workers: int, ts: float
    ) -> RoiPeopleCounterState:
        row = self.pg.session.exec(
            text(
                """
                SELECT current_workers, max_workers, day_date::text,
                       seconds_0_workers, seconds_1_worker, seconds_2_workers,
                       person_seconds, last_tick, updated_at
                FROM roi_people_counters
                WHERE camera_id = :camera_id AND roi_key = :roi_key
                """
            ).bindparams(camera_id=camera_id, roi_key=roi_key)
        ).first()
        if not row:
            return RoiPeopleCounterState(
                camera_id=camera_id,
                roi_key=roi_key,
                max_workers=max_workers,
                day_date=self._today(ts),
                last_tick=ts,
                updated_at=ts,
            )
        return RoiPeopleCounterState(
            camera_id=camera_id,
            roi_key=roi_key,
            current_workers=min(max_workers, max(0, int(row[0] or 0))),
            max_workers=max_workers,
            day_date=str(row[2] or self._today(ts)),
            seconds_0_workers=float(row[3] or 0),
            seconds_1_worker=float(row[4] or 0),
            seconds_2_workers=float(row[5] or 0),
            person_seconds=float(row[6] or 0),
            last_tick=float(row[7] or ts),
            updated_at=float(row[8] or ts),
        )

    def _upsert_state(self, state: RoiPeopleCounterState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO roi_people_counters (
                    camera_id, roi_key, current_workers, max_workers, day_date,
                    seconds_0_workers, seconds_1_worker, seconds_2_workers,
                    person_seconds, last_tick, updated_at
                )
                VALUES (
                    :camera_id, :roi_key, :current_workers, :max_workers, :day_date,
                    :seconds_0_workers, :seconds_1_worker, :seconds_2_workers,
                    :person_seconds, :last_tick, :updated_at
                )
                ON CONFLICT (camera_id, roi_key) DO UPDATE SET
                    current_workers = EXCLUDED.current_workers,
                    max_workers = EXCLUDED.max_workers,
                    day_date = EXCLUDED.day_date,
                    seconds_0_workers = EXCLUDED.seconds_0_workers,
                    seconds_1_worker = EXCLUDED.seconds_1_worker,
                    seconds_2_workers = EXCLUDED.seconds_2_workers,
                    person_seconds = EXCLUDED.person_seconds,
                    last_tick = EXCLUDED.last_tick,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(**state.__dict__)
        )

    def _log_event(
        self,
        camera_id: int,
        roi_key: str,
        event_type: str,
        before: int,
        after: int,
        ts: float,
    ) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO roi_people_events (
                    camera_id, roi_key, event_type, workers_before, workers_after, ts
                )
                VALUES (:camera_id, :roi_key, :event_type, :before, :after, :ts)
                """
            ).bindparams(
                camera_id=camera_id,
                roi_key=roi_key,
                event_type=event_type,
                before=before,
                after=after,
                ts=ts,
            )
        )

    def _flush_daily(self, state: RoiPeopleCounterState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO roi_people_daily (
                    camera_id, roi_key, day_date, max_workers,
                    seconds_0_workers, seconds_1_worker, seconds_2_workers,
                    person_seconds, updated_at
                )
                VALUES (
                    :camera_id, :roi_key, :day_date, :max_workers,
                    :seconds_0_workers, :seconds_1_worker, :seconds_2_workers,
                    :person_seconds, :updated_at
                )
                ON CONFLICT (camera_id, roi_key, day_date) DO UPDATE SET
                    max_workers = EXCLUDED.max_workers,
                    seconds_0_workers = EXCLUDED.seconds_0_workers,
                    seconds_1_worker = EXCLUDED.seconds_1_worker,
                    seconds_2_workers = EXCLUDED.seconds_2_workers,
                    person_seconds = EXCLUDED.person_seconds,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(
                camera_id=state.camera_id,
                roi_key=state.roi_key,
                day_date=state.day_date,
                max_workers=state.max_workers,
                seconds_0_workers=state.seconds_0_workers,
                seconds_1_worker=state.seconds_1_worker,
                seconds_2_workers=state.seconds_2_workers,
                person_seconds=state.person_seconds,
                updated_at=state.updated_at,
            )
        )

    def _reset_day_if_needed(self, state: RoiPeopleCounterState, ts: float) -> None:
        today = self._today(ts)
        if state.day_date == today:
            return
        try:
            self._flush_daily(state)
        except SQLAlchemyError:
            self._rollback()
        state.day_date = today
        state.seconds_0_workers = 0.0
        state.seconds_1_worker = 0.0
        state.seconds_2_workers = 0.0
        state.person_seconds = 0.0
        state.last_tick = ts

    def _accumulate(self, state: RoiPeopleCounterState, ts: float) -> None:
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
            else:
                state.seconds_2_workers += dt
            state.person_seconds += workers * dt

    def sync_camera_rois(self, camera_id: int, roi_keys: list[str]) -> None:
        keys_set = set(roi_keys)
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        "SELECT roi_key FROM roi_people_counters WHERE camera_id = :camera_id"
                    ).bindparams(camera_id=camera_id)
                ).all()
                for row in rows:
                    roi_key = str(row[0])
                    if roi_key in keys_set:
                        continue
                    for table in (
                        "roi_people_counters",
                        "roi_people_daily",
                        "roi_people_events",
                    ):
                        self.pg.session.exec(
                            text(
                                f"DELETE FROM {table} "
                                "WHERE camera_id = :camera_id AND roi_key = :roi_key"
                            ).bindparams(camera_id=camera_id, roi_key=roi_key)
                        )
                for cache_key in list(self._cache.keys()):
                    cid, rk = cache_key
                    if cid == camera_id and rk not in keys_set:
                        del self._cache[cache_key]
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"roi people sync failed (camera={camera_id}): {exc}")

    def tick(
        self,
        camera_id: int,
        roi_key: str,
        target_workers: int,
        max_workers: int = ROI_MAX_WORKERS,
        now: float | None = None,
    ) -> RoiPeopleCounterState:
        ts = now or time.time()
        max_workers = min(ROI_MAX_WORKERS, max(1, int(max_workers or ROI_MAX_WORKERS)))
        cache_key = (camera_id, roi_key)
        with self._lock:
            state = self._cache.get(cache_key)
            if state is None:
                state = self._load_state(camera_id, roi_key, max_workers, ts)
                self._cache[cache_key] = state
            state.max_workers = max_workers
            try:
                self._reset_day_if_needed(state, ts)
                self._accumulate(state, ts)
                before = state.current_workers
                after = min(max_workers, max(0, int(target_workers)))
                if after != before:
                    event_type = "enter" if after > before else "exit"
                    self._log_event(camera_id, roi_key, event_type, before, after, ts)
                state.current_workers = after
                state.last_tick = ts
                state.updated_at = ts
                self._upsert_state(state)
                self._flush_daily(state)
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(
                    f"roi people tick failed (camera={camera_id}, roi={roi_key}): {exc}"
                )
        return state

    def delete_camera(self, camera_id: int) -> None:
        with self._lock:
            try:
                for table in (
                    "roi_people_events",
                    "roi_people_daily",
                    "roi_people_counters",
                ):
                    self.pg.session.exec(
                        text(
                            f"DELETE FROM {table} WHERE camera_id = :camera_id"
                        ).bindparams(camera_id=camera_id)
                    )
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"roi people camera delete failed (camera={camera_id}): {exc}")
            for cache_key in list(self._cache.keys()):
                if cache_key[0] == camera_id:
                    del self._cache[cache_key]

    def get_stat_dates(self, camera_id: int) -> list[str]:
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        """
                        SELECT DISTINCT day_date
                        FROM roi_people_daily
                        WHERE camera_id = :camera_id
                        ORDER BY day_date
                        """
                    ).bindparams(camera_id=camera_id)
                ).all()
                return [str(row[0]) for row in rows]
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"roi people stat dates query failed: {exc}")
                return []

    def _live_counters_for_zone(
        self, camera_id: int, roi_key: str, ts: float
    ) -> dict | None:
        cache_key = (camera_id, roi_key)
        state = self._cache.get(cache_key)
        if state is None:
            state = self._load_state(camera_id, roi_key, ROI_MAX_WORKERS, ts)
        self._reset_day_if_needed(state, ts)
        self._accumulate(state, ts)
        return {
            "date": state.day_date,
            "max_workers": state.max_workers,
            "seconds_0_workers": state.seconds_0_workers,
            "seconds_1_worker": state.seconds_1_worker,
            "seconds_2_workers": state.seconds_2_workers,
            "person_seconds": state.person_seconds,
            "current_workers": state.current_workers,
        }

    def _zone_row_from_db(
        self, camera_id: int, roi_key: str, day_str: str
    ) -> dict | None:
        row = self.pg.session.exec(
            text(
                """
                SELECT max_workers, seconds_0_workers, seconds_1_worker,
                       seconds_2_workers, person_seconds
                FROM roi_people_daily
                WHERE camera_id = :camera_id AND roi_key = :roi_key
                  AND day_date = :day_date
                """
            ).bindparams(
                camera_id=camera_id, roi_key=roi_key, day_date=day_str
            )
        ).first()
        if not row:
            return None
        return {
            "max_workers": int(row[0] or ROI_MAX_WORKERS),
            "seconds_0_workers": float(row[1] or 0),
            "seconds_1_worker": float(row[2] or 0),
            "seconds_2_workers": float(row[3] or 0),
            "person_seconds": float(row[4] or 0),
        }

    def merge_into_daily_stats(self, raw: dict) -> dict:
        """Добавляет person-hours в ответ get_daily_stats_range ROI-таймера."""
        camera_id = int(raw.get("camera_id") or 0)
        from_date = str(raw.get("from") or "")
        to_date = str(raw.get("to") or "")
        if not camera_id or not from_date or not to_date:
            return raw

        zone_meta: dict[str, dict] = {}
        for day in raw.get("days") or []:
            for z in day.get("zones") or []:
                rk = str(z.get("roi_key") or "")
                if rk:
                    zone_meta[rk] = z

        person_by_day: dict[str, dict[str, dict]] = {}
        ts = time.time()
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        """
                        SELECT day_date, roi_key, max_workers, seconds_0_workers,
                               seconds_1_worker, seconds_2_workers, person_seconds
                        FROM roi_people_daily
                        WHERE camera_id = :camera_id
                          AND day_date BETWEEN :from_date AND :to_date
                        ORDER BY day_date, roi_key
                        """
                    ).bindparams(
                        camera_id=camera_id,
                        from_date=from_date,
                        to_date=to_date,
                    )
                ).all()
                for row in rows:
                    day_str = str(row[0])
                    rk = str(row[1])
                    person_by_day.setdefault(day_str, {})[rk] = {
                        "max_workers": int(row[2] or ROI_MAX_WORKERS),
                        "seconds_0_workers": float(row[3] or 0),
                        "seconds_1_worker": float(row[4] or 0),
                        "seconds_2_workers": float(row[5] or 0),
                        "person_seconds": float(row[6] or 0),
                    }
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"roi people daily merge query failed: {exc}")

        live_day = self._today(ts)
        if from_date <= live_day <= to_date:
            for rk in zone_meta:
                live = self._live_counters_for_zone(camera_id, rk, ts)
                if live and live["date"] == live_day:
                    person_by_day.setdefault(live_day, {})[rk] = {
                        k: live[k]
                        for k in (
                            "max_workers",
                            "seconds_0_workers",
                            "seconds_1_worker",
                            "seconds_2_workers",
                            "person_seconds",
                        )
                    }

        days_out: list[dict] = []
        seen_days = set()
        for day in raw.get("days") or []:
            day_str = str(day.get("date") or "")
            seen_days.add(day_str)
            pmap = person_by_day.get(day_str, {})
            p_total = 0.0
            s0 = s1 = s2 = 0.0
            zones_out = []
            for z in day.get("zones") or []:
                rk = str(z.get("roi_key") or "")
                pz = pmap.get(rk, {})
                zone = dict(z)
                zone["max_workers"] = int(pz.get("max_workers") or ROI_MAX_WORKERS)
                zone["seconds_0_workers"] = float(pz.get("seconds_0_workers") or 0)
                zone["seconds_1_worker"] = float(pz.get("seconds_1_worker") or 0)
                zone["seconds_2_workers"] = float(pz.get("seconds_2_workers") or 0)
                zone["person_seconds"] = float(pz.get("person_seconds") or 0)
                p_total += zone["person_seconds"]
                s0 += zone["seconds_0_workers"]
                s1 += zone["seconds_1_worker"]
                s2 += zone["seconds_2_workers"]
                zones_out.append(zone)
            day_out = dict(day)
            day_out["zones"] = zones_out
            day_out["person_seconds"] = p_total
            day_out["seconds_0_workers"] = s0
            day_out["seconds_1_worker"] = s1
            day_out["seconds_2_workers"] = s2
            day_out["max_workers"] = ROI_MAX_WORKERS
            days_out.append(day_out)

        for day_str in sorted(person_by_day.keys()):
            if day_str in seen_days:
                continue
            pmap = person_by_day[day_str]
            p_total = s0 = s1 = s2 = 0.0
            zones_out = []
            for rk, pz in sorted(pmap.items()):
                meta = zone_meta.get(rk, {})
                zone = {
                    "roi_key": rk,
                    "roi_index": int(meta.get("roi_index") or 0),
                    "roi_name": str(meta.get("roi_name") or ""),
                    "work_seconds": 0.0,
                    "idle_seconds": 0.0,
                    "standby_seconds": 0.0,
                    "max_workers": int(pz.get("max_workers") or ROI_MAX_WORKERS),
                    "seconds_0_workers": float(pz.get("seconds_0_workers") or 0),
                    "seconds_1_worker": float(pz.get("seconds_1_worker") or 0),
                    "seconds_2_workers": float(pz.get("seconds_2_workers") or 0),
                    "person_seconds": float(pz.get("person_seconds") or 0),
                }
                p_total += zone["person_seconds"]
                s0 += zone["seconds_0_workers"]
                s1 += zone["seconds_1_worker"]
                s2 += zone["seconds_2_workers"]
                zones_out.append(zone)
            days_out.append(
                {
                    "date": day_str,
                    "work_seconds": 0.0,
                    "idle_seconds": 0.0,
                    "standby_seconds": 0.0,
                    "person_seconds": p_total,
                    "seconds_0_workers": s0,
                    "seconds_1_worker": s1,
                    "seconds_2_workers": s2,
                    "max_workers": ROI_MAX_WORKERS,
                    "zones": zones_out,
                }
            )

        days_out.sort(key=lambda d: str(d.get("date") or ""))
        out = dict(raw)
        out["days"] = days_out
        return out

    def get_zone_timeline(
        self, camera_id: int, roi_key: str, date: str
    ) -> dict:
        range_start, range_end = self._shift_bounds_for_date(date)
        with self._lock:
            stats = self._zone_row_from_db(camera_id, roi_key, date)
            if stats is None:
                live = self._live_counters_for_zone(camera_id, roi_key, time.time())
                if live and live["date"] == date:
                    stats = {k: v for k, v in live.items() if k != "date"}
            stats = stats or {
                "max_workers": ROI_MAX_WORKERS,
                "seconds_0_workers": 0.0,
                "seconds_1_worker": 0.0,
                "seconds_2_workers": 0.0,
                "person_seconds": 0.0,
            }

            segments: list[dict] = []
            try:
                rows = self.pg.session.exec(
                    text(
                        """
                        SELECT ts, workers_after
                        FROM roi_people_events
                        WHERE camera_id = :camera_id AND roi_key = :roi_key
                          AND ts >= :range_start AND ts < :range_end
                        ORDER BY ts ASC, id ASC
                        """
                    ).bindparams(
                        camera_id=camera_id,
                        roi_key=roi_key,
                        range_start=range_start,
                        range_end=range_end,
                    )
                ).all()
                workers = 0
                cursor = range_start
                for row in rows:
                    ts = float(row[0])
                    if ts > cursor:
                        segments.append(
                            {"start": cursor, "end": ts, "workers": workers}
                        )
                    workers = min(ROI_MAX_WORKERS, max(0, int(row[1] or 0)))
                    cursor = max(cursor, ts)
                if cursor < range_end:
                    segments.append(
                        {"start": cursor, "end": range_end, "workers": workers}
                    )
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"roi people timeline query failed: {exc}")
                segments = [
                    {"start": range_start, "end": range_end, "workers": 0}
                ]

        if not segments:
            segments = [{"start": range_start, "end": range_end, "workers": 0}]

        return {
            "camera_id": camera_id,
            "roi_key": roi_key,
            "date": date,
            "range_start": range_start,
            "range_end": range_end,
            "timezone": str(TZ),
            "segments": segments,
            **stats,
        }

    def get_timelines_for_camera(self, camera_id: int, date: str) -> list[dict]:
        names = self._roi_names_for_camera(camera_id)
        try:
            rows = self.pg.session.exec(
                text(
                    """
                    SELECT roi_key, roi_index, COALESCE(roi_name, '') AS roi_name
                    FROM roi_timers
                    WHERE camera_id = :camera_id
                    ORDER BY roi_index
                    """
                ).bindparams(camera_id=camera_id)
            ).all()
        except SQLAlchemyError:
            self._rollback()
            rows = []

        range_start, range_end = self._shift_bounds_for_date(date)
        zones: list[dict] = []
        for row in rows:
            roi_key = str(row[0])
            roi_index = int(row[1] or 0)
            roi_name = roi_display_name(str(row[2] or ""), roi_index)
            tl = self.get_zone_timeline(camera_id, roi_key, date)
            zones.append(
                {
                    "roi_index": roi_index,
                    "roi_key": roi_key,
                    "roi_name": names.get(roi_key, roi_name),
                    "segments": tl.get("segments") or [],
                    "person_seconds": float(tl.get("person_seconds") or 0),
                    "seconds_0_workers": float(tl.get("seconds_0_workers") or 0),
                    "seconds_1_worker": float(tl.get("seconds_1_worker") or 0),
                    "seconds_2_workers": float(tl.get("seconds_2_workers") or 0),
                    "max_workers": ROI_MAX_WORKERS,
                }
            )
        if zones:
            return zones
        return []

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

    def get_overlay_labels(
        self,
        camera_id: int,
        roi_keys: list[str],
        roi_names: list[str] | None = None,
    ) -> list[str]:
        labels: list[str] = []
        names_map = self._roi_names_for_camera(camera_id)
        with self._lock:
            for idx, roi_key in enumerate(roi_keys):
                state = self._cache.get((camera_id, roi_key))
                workers = state.current_workers if state else 0
                person_sec = state.person_seconds if state else 0.0
                name = ""
                if roi_names and idx < len(roi_names):
                    name = (roi_names[idx] or "").strip()
                if not name:
                    name = names_map.get(roi_key, f"Зона {idx + 1}")
                h = int(person_sec) // 3600
                m = (int(person_sec) % 3600) // 60
                s = int(person_sec) % 60
                time_txt = f"{h}:{m:02d}:{s:02d}"
                labels.append(
                    f"{name}: {workers}/{ROI_MAX_WORKERS} · смена {time_txt}"
                )
        return labels
