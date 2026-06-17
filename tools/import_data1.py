"""Импорт статистики ROI и видеозаписей из data1 (другой ПК) в камеру IP Camera 3."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PG = dict(
    host="127.0.0.1",
    port=7040,
    user="didi",
    password="didi123",
    dbname="vision-fr",
)
TARGET_PG = dict(
    host="127.0.0.1",
    port=7032,
    user="didi",
    password="didi123",
    dbname="vision-fr",
)

SRC_CAMERA_ID = 2
DST_CAMERA_ID = 3
DST_CAMERA_NAME = "IP Camera 3"

ROI_KEY_BY_INDEX = {
    1: "d49cdb984d23b4591cd0d936",
    2: "4e75cfe1a95586a5679b015d",
    3: "fb668e01c338cdf9f1124603",
}


def find_source_recordings_dir() -> Path:
    base = ROOT / "data1" / "backend" / "recordings"
    if not base.is_dir():
        raise FileNotFoundError(f"Нет папки {base}")
    matches = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("cam2_")]
    if not matches:
        raise FileNotFoundError(f"Не найдена папка cam2_* в {base}")
    return matches[0]


def wipe_camera_data(dst_rec: Path) -> None:
    """Удалить все видео и статистику ROI для IP Camera 3."""
    if dst_rec.exists():
        shutil.rmtree(dst_rec)
        print(f"Удалена папка записей: {dst_rec.name}")

    conn = psycopg2.connect(**TARGET_PG)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM roi_timer_events WHERE camera_id = %s", (DST_CAMERA_ID,))
            events = cur.rowcount
            cur.execute("DELETE FROM roi_timer_hourly WHERE camera_id = %s", (DST_CAMERA_ID,))
            hourly = cur.rowcount
            cur.execute("DELETE FROM roi_timer_daily WHERE camera_id = %s", (DST_CAMERA_ID,))
            daily = cur.rowcount
            cur.execute(
                """
                UPDATE roi_timers SET
                    mode = 'standby',
                    work_seconds = 0,
                    idle_seconds = 0,
                    last_tick = 0,
                    presence_since = NULL,
                    absence_since = NULL,
                    updated_at = 0
                WHERE camera_id = %s
                """,
                (DST_CAMERA_ID,),
            )
            timers = cur.rowcount
        conn.commit()
        print(
            f"Очищена БД camera_id={DST_CAMERA_ID}: "
            f"events={events}, hourly={hourly}, daily={daily}, timers_reset={timers}"
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def copy_recordings(src_dir: Path, dst_dir: Path) -> int:
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for day_dir in sorted(src_dir.iterdir()):
        if not day_dir.is_dir():
            continue
        out_day = dst_dir / day_dir.name
        out_day.mkdir(parents=True, exist_ok=True)
        for mp4 in day_dir.glob("*.mp4"):
            shutil.copy2(mp4, out_day / mp4.name)
            copied += 1
    return copied


def import_stats() -> None:
    src = psycopg2.connect(**SOURCE_PG)
    dst = psycopg2.connect(**TARGET_PG)
    try:
        with src.cursor() as sc, dst.cursor() as dc:
            sc.execute(
                """
                SELECT DISTINCT day_date::text
                FROM roi_timer_daily
                WHERE camera_id = %s
                ORDER BY 1
                """,
                (SRC_CAMERA_ID,),
            )
            dates = [r[0] for r in sc.fetchall()]
            if not dates:
                print("В источнике нет roi_timer_daily для camera_id=2")
                return

            print(f"Даты статистики для импорта: {dates[0]} .. {dates[-1]} ({len(dates)} дн.)")

            sc.execute(
                """
                SELECT day_date::text, roi_index,
                       work_seconds, idle_seconds, standby_seconds, updated_at
                FROM roi_timer_daily
                WHERE camera_id = %s
                ORDER BY day_date, roi_index
                """,
                (SRC_CAMERA_ID,),
            )
            daily_rows = []
            for day_date, roi_index, work, idle, standby, updated_at in sc.fetchall():
                roi_key = ROI_KEY_BY_INDEX.get(int(roi_index))
                if not roi_key:
                    continue
                daily_rows.append(
                    (DST_CAMERA_ID, roi_key, int(roi_index), day_date, work, idle, standby, updated_at)
                )
            execute_batch(
                dc,
                """
                INSERT INTO roi_timer_daily (
                    camera_id, roi_key, roi_index, day_date,
                    work_seconds, idle_seconds, standby_seconds, updated_at
                ) VALUES (%s, %s, %s, %s::date, %s, %s, %s, %s)
                """,
                daily_rows,
            )

            sc.execute(
                """
                SELECT day_date::text, roi_index, hour,
                       work_seconds, idle_seconds
                FROM roi_timer_hourly
                WHERE camera_id = %s
                ORDER BY day_date, roi_index, hour
                """,
                (SRC_CAMERA_ID,),
            )
            hourly_rows = []
            for day_date, roi_index, hour, work, idle in sc.fetchall():
                roi_key = ROI_KEY_BY_INDEX.get(int(roi_index))
                if not roi_key:
                    continue
                hourly_rows.append(
                    (DST_CAMERA_ID, roi_key, int(roi_index), day_date, int(hour), work, idle)
                )
            execute_batch(
                dc,
                """
                INSERT INTO roi_timer_hourly (
                    camera_id, roi_key, roi_index, day_date, hour,
                    work_seconds, idle_seconds
                ) VALUES (%s, %s, %s, %s::date, %s, %s, %s)
                """,
                hourly_rows,
            )

            sc.execute(
                """
                SELECT roi_index, mode, ts
                FROM roi_timer_events
                WHERE camera_id = %s
                ORDER BY ts
                """,
                (SRC_CAMERA_ID,),
            )
            event_rows = []
            for roi_index, mode, ts in sc.fetchall():
                dst_key = ROI_KEY_BY_INDEX.get(int(roi_index))
                if not dst_key:
                    continue
                event_rows.append((DST_CAMERA_ID, dst_key, int(roi_index), str(mode), float(ts)))

            execute_batch(
                dc,
                """
                INSERT INTO roi_timer_events (camera_id, roi_key, roi_index, mode, ts)
                VALUES (%s, %s, %s, %s, %s)
                """,
                event_rows,
            )

            sc.execute(
                """
                SELECT roi_index, mode, work_seconds, idle_seconds, last_tick,
                       presence_since, absence_since, updated_at
                FROM roi_timers
                WHERE camera_id = %s
                ORDER BY roi_index
                """,
                (SRC_CAMERA_ID,),
            )
            for row in sc.fetchall():
                roi_index, mode, work, idle, last_tick, ps, ab, updated_at = row
                dst_key = ROI_KEY_BY_INDEX.get(int(roi_index))
                if not dst_key:
                    continue
                dc.execute(
                    """
                    UPDATE roi_timers SET
                        roi_index = %s,
                        mode = %s,
                        work_seconds = %s,
                        idle_seconds = %s,
                        last_tick = %s,
                        presence_since = %s,
                        absence_since = %s,
                        updated_at = %s
                    WHERE camera_id = %s AND roi_key = %s
                    """,
                    (
                        int(roi_index),
                        mode,
                        work,
                        idle,
                        last_tick,
                        ps,
                        ab,
                        updated_at,
                        DST_CAMERA_ID,
                        dst_key,
                    ),
                )

            dst.commit()
            print(
                f"Импорт БД: daily={len(daily_rows)}, hourly={len(hourly_rows)}, "
                f"events={len(event_rows)}"
            )
    except Exception:
        dst.rollback()
        raise
    finally:
        src.close()
        dst.close()


def main() -> int:
    src_rec = find_source_recordings_dir()
    dst_rec = ROOT / "data" / "backend" / "recordings" / f"cam{DST_CAMERA_ID}_{DST_CAMERA_NAME}"
    print(f"Источник видео: {src_rec.name}")
    print(f"Цель: IP Camera 3 (id={DST_CAMERA_ID})")

    wipe_camera_data(dst_rec)
    import_stats()
    copied = copy_recordings(src_rec, dst_rec)
    print(f"Видео: скопировано {copied} файлов")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        raise SystemExit(1)
