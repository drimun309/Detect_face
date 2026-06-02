"""Persistent per-ROI work/idle timers."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from threading import Lock

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.db.pg_db import PgSyncDb
from src.utils.logger import get_logger

log = get_logger()


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

    @staticmethod
    def make_roi_key(polygon: list[tuple[float, float]]) -> str:
        stable = [[round(float(x), 6), round(float(y), 6)] for x, y in polygon]
        data = json.dumps(stable, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha1(data.encode("utf-8")).hexdigest()[:24]

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
        """Create rows for active ROIs and delete removed ROIs data."""
        now = time.time()
        keys: list[str] = [self.make_roi_key(poly) for poly in polygons]
        keys_set = set(keys)
        with self._lock:
            try:
                rows = self.pg.session.exec(
                    text(
                        "SELECT roi_key FROM roi_timers WHERE camera_id = :camera_id"
                    ).bindparams(camera_id=camera_id)
                ).all()
                for row in rows:
                    roi_key = row[0]
                    if roi_key not in keys_set:
                        self.pg.session.exec(
                            text(
                                "DELETE FROM roi_timers WHERE camera_id = :camera_id "
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
                    cache_key = (camera_id, roi_key)
                    state = self._cache.get(cache_key)
                    if state is None:
                        state = RoiTimerState(
                            camera_id=camera_id,
                            roi_key=roi_key,
                            roi_index=idx,
                            polygon_json=self._polygon_to_json(poly),
                            mode="standby",
                            updated_at=now,
                        )
                        self._cache[cache_key] = state
                    else:
                        state.roi_index = idx
                        state.polygon_json = self._polygon_to_json(poly)
                        state.updated_at = now
                    self._upsert_state(state)
                self.pg.session.commit()
            except SQLAlchemyError as exc:
                self._rollback()
                log.warning(f"ROI timers sync failed (camera={camera_id}): {exc}")
        return keys

    def delete_camera(self, camera_id: int) -> None:
        with self._lock:
            try:
                self.pg.session.exec(
                    text("DELETE FROM roi_timers WHERE camera_id = :camera_id").bindparams(
                        camera_id=camera_id
                    )
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
                    state = self._cache.get((camera_id, roi_key))
                    if state is None:
                        # missed sync, skip this frame
                        continue
                    cache_key = (camera_id, roi_key)
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
                    if state.mode == "work":
                        state.work_seconds += dt
                    elif state.mode == "idle":
                        state.idle_seconds += dt

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
            for idx, roi_key in enumerate(roi_keys, start=1):
                state = self._cache.get((camera_id, roi_key))
                if state is None:
                    labels.append(f"ROI {idx}: ожидание")
                    continue
                work_txt = self._fmt_hhmmss(state.work_seconds)
                idle_txt = self._fmt_hhmmss(state.idle_seconds)
                if state.mode == "work":
                    if state.absence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.absence_since)))
                        labels.append(
                            f"ROI {idx} работа {work_txt} | простой {idle_txt} (простой через {left}с)"
                        )
                    else:
                        labels.append(f"ROI {idx} работа {work_txt} | простой {idle_txt}")
                elif state.mode == "idle":
                    if state.presence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.presence_since)))
                        labels.append(
                            f"ROI {idx} работа {work_txt} | простой {idle_txt} (работа через {left}с)"
                        )
                    else:
                        labels.append(f"ROI {idx} работа {work_txt} | простой {idle_txt}")
                else:
                    if state.presence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.presence_since)))
                        labels.append(
                            f"ROI {idx} работа {work_txt} | простой {idle_txt} (работа через {left}с)"
                        )
                    elif state.absence_since is not None:
                        left = max(0, int(switch_seconds - (ts - state.absence_since)))
                        labels.append(
                            f"ROI {idx} работа {work_txt} | простой {idle_txt} (простой через {left}с)"
                        )
                    else:
                        labels.append(f"ROI {idx} работа {work_txt} | простой {idle_txt}")
        return labels
