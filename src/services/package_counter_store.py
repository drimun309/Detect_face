"""Счётчик упакованных изделий по ROI-зонам камеры «пакеты»."""

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
class PackageCounterState:
    camera_id: int
    roi_key: str
    packed_today: int = 0
    day_date: str = ""
    updated_at: float = 0.0


@dataclass
class _PresenceTrack:
    stable_count: int = 0
    presence_since: float | None = None
    recorded_count: int = 0


class PackageCounterStore:
    """Считает упаковку, когда пакет ≥ dwell_sec в ROI-зоне."""

    def __init__(self, pg: PgSyncDb) -> None:
        self.pg = pg
        self._lock = pg.lock
        self._cache: dict[tuple[int, str], PackageCounterState] = {}
        self._tracks: dict[tuple[int, str], _PresenceTrack] = {}
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
                    CREATE TABLE IF NOT EXISTS package_roi_counters (
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        packed_today INTEGER NOT NULL DEFAULT 0,
                        day_date DATE NOT NULL DEFAULT CURRENT_DATE,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, roi_key)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS package_roi_daily (
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        day_date DATE NOT NULL,
                        packed_count INTEGER NOT NULL DEFAULT 0,
                        updated_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                        PRIMARY KEY (camera_id, roi_key, day_date)
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS package_roi_events (
                        id BIGSERIAL PRIMARY KEY,
                        camera_id INTEGER NOT NULL,
                        roi_key VARCHAR(64) NOT NULL,
                        count_delta INTEGER NOT NULL,
                        packages_in_zone INTEGER NOT NULL,
                        ts DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            self.pg.session.exec(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_package_roi_events_cam_key_ts "
                    "ON package_roi_events (camera_id, roi_key, ts)"
                )
            )
            self.pg.session.commit()
        except SQLAlchemyError as exc:
            self._rollback()
            log.warning(f"package counter tables migration skipped: {exc}")

    def _today(self, ts: float) -> str:
        return datetime.fromtimestamp(ts, TZ).date().isoformat()

    def _shift_active(self, ts: float) -> bool:
        dt = datetime.fromtimestamp(ts, TZ)
        start = dt.replace(hour=VIEW_START_HOUR, minute=0, second=0, microsecond=0)
        end = dt.replace(hour=VIEW_END_HOUR, minute=0, second=0, microsecond=0)
        return start <= dt < end

    def _load_state(self, camera_id: int, roi_key: str, ts: float) -> PackageCounterState:
        row = self.pg.session.exec(
            text(
                """
                SELECT packed_today, day_date::text, updated_at
                FROM package_roi_counters
                WHERE camera_id = :camera_id AND roi_key = :roi_key
                """
            ).bindparams(camera_id=camera_id, roi_key=roi_key)
        ).first()
        today = self._today(ts)
        if row is None:
            return PackageCounterState(
                camera_id=camera_id,
                roi_key=roi_key,
                packed_today=0,
                day_date=today,
                updated_at=ts,
            )
        packed_today = int(row[0] or 0)
        day_date = str(row[1] or today)
        if day_date != today:
            packed_today = 0
            day_date = today
        return PackageCounterState(
            camera_id=camera_id,
            roi_key=roi_key,
            packed_today=packed_today,
            day_date=day_date,
            updated_at=float(row[2] or ts),
        )

    def _upsert_state(self, state: PackageCounterState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO package_roi_counters (
                    camera_id, roi_key, packed_today, day_date, updated_at
                )
                VALUES (:camera_id, :roi_key, :packed_today, :day_date, :updated_at)
                ON CONFLICT (camera_id, roi_key) DO UPDATE SET
                    packed_today = EXCLUDED.packed_today,
                    day_date = EXCLUDED.day_date,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(**state.__dict__)
        )

    def _flush_daily(self, state: PackageCounterState) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO package_roi_daily (
                    camera_id, roi_key, day_date, packed_count, updated_at
                )
                VALUES (:camera_id, :roi_key, :day_date, :packed_today, :updated_at)
                ON CONFLICT (camera_id, roi_key, day_date) DO UPDATE SET
                    packed_count = EXCLUDED.packed_count,
                    updated_at = EXCLUDED.updated_at
                """
            ).bindparams(
                camera_id=state.camera_id,
                roi_key=state.roi_key,
                day_date=state.day_date,
                packed_today=state.packed_today,
                updated_at=state.updated_at,
            )
        )

    def _log_event(
        self,
        camera_id: int,
        roi_key: str,
        count_delta: int,
        packages_in_zone: int,
        ts: float,
    ) -> None:
        self.pg.session.exec(
            text(
                """
                INSERT INTO package_roi_events (
                    camera_id, roi_key, count_delta, packages_in_zone, ts
                )
                VALUES (:camera_id, :roi_key, :count_delta, :packages_in_zone, :ts)
                """
            ).bindparams(
                camera_id=camera_id,
                roi_key=roi_key,
                count_delta=count_delta,
                packages_in_zone=packages_in_zone,
                ts=ts,
            )
        )

    def sync_camera_rois(self, camera_id: int, roi_keys: list[str]) -> None:
        keys_set = set(roi_keys)
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        "SELECT roi_key FROM package_roi_counters WHERE camera_id = :camera_id"
                    ).bindparams(camera_id=camera_id)
                ).all()
                for row in rows:
                    roi_key = str(row[0])
                    if roi_key in keys_set:
                        continue
                    for table in (
                        "package_roi_events",
                        "package_roi_daily",
                        "package_roi_counters",
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
                for track_key in list(self._tracks.keys()):
                    cid, rk = track_key
                    if cid == camera_id and rk not in keys_set:
                        del self._tracks[track_key]
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"package counter sync failed (camera={camera_id}): {exc}")

    def tick(
        self,
        camera_id: int,
        roi_key: str,
        packages_in_zone: int,
        dwell_seconds: float = 1.0,
        now: float | None = None,
    ) -> PackageCounterState:
        ts = now or time.time()
        packages_in_zone = max(0, int(packages_in_zone))
        cache_key = (camera_id, roi_key)
        track = self._tracks.get(cache_key) or _PresenceTrack()

        if packages_in_zone <= 0:
            track = _PresenceTrack()
            self._tracks[cache_key] = track
            with self._lock:
                state = self._cache.get(cache_key)
                if state is None:
                    state = self._load_state(camera_id, roi_key, ts)
                    self._cache[cache_key] = state
            return state

        if packages_in_zone != track.stable_count:
            track.stable_count = packages_in_zone
            track.presence_since = ts
        elif (
            track.presence_since is not None
            and ts - track.presence_since >= dwell_seconds
        ):
            delta = packages_in_zone - track.recorded_count
            if delta > 0:
                with self._lock:
                    state = self._cache.get(cache_key)
                    if state is None:
                        state = self._load_state(camera_id, roi_key, ts)
                        self._cache[cache_key] = state
                    today = self._today(ts)
                    if state.day_date != today:
                        state.packed_today = 0
                        state.day_date = today
                    if self._shift_active(ts):
                        try:
                            state.packed_today += delta
                            state.updated_at = ts
                            self._log_event(
                                camera_id, roi_key, delta, packages_in_zone, ts
                            )
                            self._upsert_state(state)
                            self._flush_daily(state)
                            self.pg.session.commit()
                            log.info(
                                f"Package packed cam{camera_id} {roi_key}: "
                                f"+{delta} (total today {state.packed_today})"
                            )
                        except SQLAlchemyError as exc:
                            self._rollback()
                            log.warning(
                                f"package counter tick failed "
                                f"(camera={camera_id}, roi={roi_key}): {exc}"
                            )
                    track.recorded_count = packages_in_zone

        self._tracks[cache_key] = track
        with self._lock:
            state = self._cache.get(cache_key)
            if state is None:
                state = self._load_state(camera_id, roi_key, ts)
                self._cache[cache_key] = state
        return state

    def delete_camera(self, camera_id: int) -> None:
        with self._lock:
            try:
                for table in (
                    "package_roi_events",
                    "package_roi_daily",
                    "package_roi_counters",
                ):
                    self.pg.session.exec(
                        text(
                            f"DELETE FROM {table} WHERE camera_id = :camera_id"
                        ).bindparams(camera_id=camera_id)
                    )
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(
                    f"package counter camera delete failed (camera={camera_id}): {exc}"
                )
            for cache_key in list(self._cache.keys()):
                if cache_key[0] == camera_id:
                    del self._cache[cache_key]
            for track_key in list(self._tracks.keys()):
                if track_key[0] == camera_id:
                    del self._tracks[track_key]

    def get_states(self, camera_id: int) -> list[PackageCounterState]:
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        """
                        SELECT roi_key, packed_today, day_date::text, updated_at
                        FROM package_roi_counters
                        WHERE camera_id = :camera_id
                        ORDER BY roi_key
                        """
                    ).bindparams(camera_id=camera_id)
                ).all()
            except SQLAlchemyError:
                self._rollback()
                return []
        today = self._today(time.time())
        states: list[PackageCounterState] = []
        for row in rows:
            day_date = str(row[2] or today)
            packed = int(row[1] or 0)
            if day_date != today:
                packed = 0
            states.append(
                PackageCounterState(
                    camera_id=camera_id,
                    roi_key=str(row[0]),
                    packed_today=packed,
                    day_date=day_date,
                    updated_at=float(row[3] or 0),
                )
            )
        return states

    def get_total_today(self, camera_id: int) -> int:
        return sum(s.packed_today for s in self.get_states(camera_id))
