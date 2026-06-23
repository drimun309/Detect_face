"""Build director analytics from ceh1_roi_stats.json."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATS = ROOT / "ceh1_roi_stats.json"
OUT_JSON = ROOT / "ceh1_roi_analytics.json"
OUT_MD = ROOT / "ceh1_roi_analytics.md"

HOLIDAYS = {"2026-06-12"}  # День России
PARTIAL_DAYS = {"2026-06-03", "2026-06-17"}
WEEKDAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def fmt_sec(s: float) -> str:
    s = int(round(float(s or 0)))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}"


def pct(a: float, b: float) -> float:
    return round(100 * a / b, 1) if b else 0.0


def weekday_ru(d: datetime) -> str:
    return WEEKDAYS_RU[d.weekday()]


def is_weekend(d: datetime) -> bool:
    return d.weekday() >= 5


def is_analyzable_day(date_str: str, for_averages: bool = False) -> bool:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if is_weekend(dt) or date_str in HOLIDAYS:
        return False
    if for_averages and date_str in PARTIAL_DAYS:
        return False
    return True


def week_label(dt: datetime) -> str:
    iso = dt.isocalendar()
    year = iso[0] if isinstance(iso, tuple) else iso.year
    week = iso[1] if isinstance(iso, tuple) else iso.week
    return f"{year}-W{week:02d}"


def week_period_label(days: list[str]) -> str:
    if not days:
        return ""
    return f"{days[0][8:10]}.{days[0][5:7]} – {days[-1][8:10]}.{days[-1][5:7]}"


def month_label(dt: datetime) -> str:
    names = {
        1: "январь",
        2: "февраль",
        3: "март",
        4: "апрель",
        5: "май",
        6: "июнь",
        7: "июль",
        8: "август",
        9: "сентябрь",
        10: "октябрь",
        11: "ноябрь",
        12: "декабрь",
    }
    return f"{names[dt.month]} {dt.year}"


def zone_stats(series: list[dict]) -> dict | None:
    if not series:
        return None
    work_vals = [x["work_seconds"] for x in series]
    idle_vals = [x["idle_seconds"] for x in series]
    util_vals = [x["utilization_pct"] for x in series]
    avg_work = statistics.mean(work_vals)
    return {
        "days_count": len(series),
        "avg_work_seconds": avg_work,
        "avg_idle_seconds": statistics.mean(idle_vals),
        "avg_work_time": fmt_sec(avg_work),
        "avg_idle_time": fmt_sec(statistics.mean(idle_vals)),
        "avg_utilization_pct": round(statistics.mean(util_vals), 1),
        "min_work_time": fmt_sec(min(work_vals)),
        "max_work_time": fmt_sec(max(work_vals)),
        "min_idle_time": fmt_sec(min(idle_vals)),
        "max_idle_time": fmt_sec(max(idle_vals)),
        "stdev_work_seconds": statistics.pstdev(work_vals) if len(work_vals) > 1 else 0.0,
    }


def pick_extreme(rows: list[dict], key: str, mode: str) -> dict | None:
    if not rows:
        return None
    if mode == "max":
        return max(rows, key=lambda x: x[key])
    return min(rows, key=lambda x: x[key])


def build_daily_rows(src: dict) -> tuple[list[dict], dict[int, list[dict]]]:
    days: list[dict] = []
    zones: dict[int, list[dict]] = {1: [], 2: [], 3: []}

    for d in src["days"]:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        partial = d["date"] in PARTIAL_DAYS
        weekend = is_weekend(dt)
        holiday = d["date"] in HOLIDAYS

        zone_map = {z["roi_index"]: z for z in d["shift_7_19"]["zones"]}
        t_work = t_idle = 0.0
        for z in d["shift_7_19"]["zones"]:
            t_work += z["work_seconds"]
            t_idle += z["idle_seconds"]

        day_row = {
            "date": d["date"],
            "weekday": weekday_ru(dt),
            "week": week_label(dt),
            "month": month_label(dt),
            "is_weekend": weekend,
            "is_holiday": holiday,
            "partial_day": partial,
            "analyzable": is_analyzable_day(d["date"]),
            "analyzable_for_avg": is_analyzable_day(d["date"], for_averages=True),
            "total_work_seconds": t_work,
            "total_idle_seconds": t_idle,
            "total_work_time": fmt_sec(t_work),
            "total_idle_time": fmt_sec(t_idle),
            "total_utilization_pct": pct(t_work, t_work + t_idle),
        }
        days.append(day_row)

        for roi in (1, 2, 3):
            z = zone_map[roi]
            work = z["work_seconds"]
            idle = z["idle_seconds"]
            row = {
                **day_row,
                "roi_index": roi,
                "work_seconds": work,
                "idle_seconds": idle,
                "work_time": fmt_sec(work),
                "idle_time": fmt_sec(idle),
                "utilization_pct": pct(work, work + idle),
            }
            zones[roi].append(row)

    return days, zones


def aggregate_period(
    rows: list[dict],
    group_key: str,
    for_averages: bool = True,
) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if for_averages and not row["analyzable_for_avg"]:
            continue
        if not for_averages and not row["analyzable"]:
            continue
        buckets[row[group_key]].append(row)

    result: list[dict] = []
    for key in sorted(buckets.keys()):
        items = buckets[key]
        work_vals = [x["work_seconds"] for x in items]
        idle_vals = [x["idle_seconds"] for x in items]
        util_vals = [x["utilization_pct"] for x in items]
        dates = sorted(x["date"] for x in items)
        result.append(
            {
                "period": key,
                "period_dates": dates,
                "period_range": week_period_label(dates) if group_key == "week" else key,
                "days_count": len(items),
                "avg_work_seconds": statistics.mean(work_vals),
                "avg_idle_seconds": statistics.mean(idle_vals),
                "avg_work_time": fmt_sec(statistics.mean(work_vals)),
                "avg_idle_time": fmt_sec(statistics.mean(idle_vals)),
                "avg_utilization_pct": round(statistics.mean(util_vals), 1),
                "total_work_time": fmt_sec(sum(work_vals)),
                "total_idle_time": fmt_sec(sum(idle_vals)),
            }
        )
    return result


def build_min_max_table(rows: list[dict], group_key: str, label: str) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if not row["analyzable_for_avg"]:
            continue
        buckets[row[group_key]].append(row)

    table: list[dict] = []
    for key in sorted(buckets.keys()):
        items = buckets[key]
        dates = sorted(x["date"] for x in items)
        max_row = pick_extreme(items, "utilization_pct", "max")
        min_row = pick_extreme(items, "utilization_pct", "min")
        if not max_row or not min_row:
            continue
        table.append(
            {
                "period_label": label,
                "period": key,
                "period_range": week_period_label(dates) if group_key == "week" else key,
                "days_in_period": len(items),
                "max_date": max_row["date"],
                "max_weekday": max_row["weekday"],
                "max_utilization_pct": max_row["utilization_pct"],
                "max_work_time": max_row["work_time"],
                "max_idle_time": max_row["idle_time"],
                "min_date": min_row["date"],
                "min_weekday": min_row["weekday"],
                "min_utilization_pct": min_row["utilization_pct"],
                "min_work_time": min_row["work_time"],
                "min_idle_time": min_row["idle_time"],
            }
        )
    return table


def build_anomalies(zones: dict[int, list[dict]], zone_analytics: dict) -> list[dict]:
    anomalies: list[dict] = []
    for roi in (1, 2, 3):
        s = zone_analytics[str(roi)]["stats_full_workdays"]
        if not s:
            continue
        mean_w = s["avg_work_seconds"]
        mean_i = s["avg_idle_seconds"]
        sd_w = s["stdev_work_seconds"] or 1.0
        full_rows = [x for x in zones[roi] if x["analyzable_for_avg"]]
        idle_sd = statistics.pstdev([x["idle_seconds"] for x in full_rows]) if len(full_rows) > 1 else 1.0

        for row in full_rows:
            flags: list[str] = []
            if abs(row["work_seconds"] - mean_w) > 1.5 * sd_w:
                direction = "выше" if row["work_seconds"] > mean_w else "ниже"
                flags.append(f"работа {direction} среднего на {pct(abs(row['work_seconds'] - mean_w), mean_w)}%")
            if abs(row["idle_seconds"] - mean_i) > 1.5 * idle_sd:
                direction = "выше" if row["idle_seconds"] > mean_i else "ниже"
                flags.append(f"простой {direction} среднего на {pct(abs(row['idle_seconds'] - mean_i), mean_i)}%")
            if row["utilization_pct"] < 15 and roi in (1, 2):
                flags.append(f"критически низкая загрузка ({row['utilization_pct']}%)")
            if row["utilization_pct"] > 35 and roi == 3:
                flags.append(f"необычно высокая загрузка ({row['utilization_pct']}%)")
            if flags:
                anomalies.append(
                    {
                        "date": row["date"],
                        "weekday": row["weekday"],
                        "zone": roi,
                        "work_time": row["work_time"],
                        "idle_time": row["idle_time"],
                        "utilization_pct": row["utilization_pct"],
                        "notes": flags,
                    }
                )
    return sorted(anomalies, key=lambda x: (x["date"], x["zone"]))


def render_md(report: dict) -> str:
    lines: list[str] = [
        "# Аналитический отчёт: цех 1",
        "",
        "**Для:** директор  ",
        f"**Период данных:** {report['period']['from']} – {report['period']['to']}  ",
        "**Окно анализа:** 07:00–19:00  ",
        f"**Сформирован:** {report['generated_at']}",
        "",
        "---",
        "",
        "## Краткая выжимка",
        "",
    ]
    for i, bullet in enumerate(report["executive_summary"], 1):
        lines.append(f"{i}. {bullet}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Сводка по зонам (только будни, без неполных дней)",
            "",
            "| Зона | Ср. работа | Ср. простой | Загрузка | Мин. работа | Макс. работа |",
            "|------|------------|-------------|----------|-------------|--------------|",
        ]
    )
    for roi in ("1", "2", "3"):
        s = report["zones"][roi]["stats_full_workdays"]
        lines.append(
            f"| Зона {roi} | {s['avg_work_time']} | {s['avg_idle_time']} | **{s['avg_utilization_pct']}%** | {s['min_work_time']} | {s['max_work_time']} |"
        )

    lines.extend(["", "---", "", "## Сводка по неделям", ""])
    lines.append(
        "| Неделя | Период | Зона | Дней | Ср. работа | Ср. простой | Загрузка | Итого работа |"
    )
    lines.append("|--------|--------|------|------|------------|-------------|----------|--------------|")
    for block in report["weekly"]["by_zone"]:
        for row in block["periods"]:
            lines.append(
                f"| {row['period']} | {row['period_range']} | Зона {block['zone']} | {row['days_count']} | "
                f"{row['avg_work_time']} | {row['avg_idle_time']} | **{row['avg_utilization_pct']}%** | {row['total_work_time']} |"
            )

    lines.extend(["", "### Цех целиком по неделям", ""])
    lines.append("| Неделя | Период | Дней | Ср. загрузка | Итого работа | Итого простой |")
    lines.append("|--------|--------|------|--------------|--------------|---------------|")
    for row in report["weekly"]["shop"]:
        lines.append(
            f"| {row['period']} | {row['period_range']} | {row['days_count']} | **{row['avg_utilization_pct']}%** | {row['total_work_time']} | {row['total_idle_time']} |"
        )

    lines.extend(
        [
            "",
            "### Минимальная и максимальная загрузка по неделям",
            "",
            "| Неделя | Период | Зона | Макс. день | Загрузка | Работа | Простой | Мин. день | Загрузка | Работа | Простой |",
            "|--------|--------|------|------------|----------|--------|---------|-----------|----------|--------|---------|",
        ]
    )
    for block in report["weekly"]["min_max_by_zone"]:
        for row in block["rows"]:
            lines.append(
                f"| {row['period']} | {row['period_range']} | Зона {block['zone']} | "
                f"{row['max_date']} ({row['max_weekday']}) | **{row['max_utilization_pct']}%** | {row['max_work_time']} | {row['max_idle_time']} | "
                f"{row['min_date']} ({row['min_weekday']}) | **{row['min_utilization_pct']}%** | {row['min_work_time']} | {row['min_idle_time']} |"
            )

    lines.extend(
        [
            "",
            "### Минимальная и максимальная загрузка цеха по неделям",
            "",
            "| Неделя | Период | Макс. день | Загрузка | Работа | Простой | Мин. день | Загрузка | Работа | Простой |",
            "|--------|--------|------------|----------|--------|---------|-----------|----------|--------|---------|",
        ]
    )
    for row in report["weekly"]["min_max_shop"]:
        lines.append(
            f"| {row['period']} | {row['period_range']} | "
            f"{row['max_date']} ({row['max_weekday']}) | **{row['max_utilization_pct']}%** | {row['max_work_time']} | {row['max_idle_time']} | "
            f"{row['min_date']} ({row['min_weekday']}) | **{row['min_utilization_pct']}%** | {row['min_work_time']} | {row['min_idle_time']} |"
        )

    lines.extend(["", "---", "", "## Сводка по месяцам", ""])
    lines.append(
        "| Месяц | Зона | Дней | Ср. работа | Ср. простой | Загрузка | Итого работа |"
    )
    lines.append("|-------|------|------|------------|-------------|----------|--------------|")
    for block in report["monthly"]["by_zone"]:
        for row in block["periods"]:
            lines.append(
                f"| {row['period']} | Зона {block['zone']} | {row['days_count']} | "
                f"{row['avg_work_time']} | {row['avg_idle_time']} | **{row['avg_utilization_pct']}%** | {row['total_work_time']} |"
            )

    lines.extend(["", "### Цех целиком по месяцам", ""])
    lines.append("| Месяц | Дней | Ср. загрузка | Итого работа | Итого простой |")
    lines.append("|-------|------|--------------|--------------|---------------|")
    for row in report["monthly"]["shop"]:
        lines.append(
            f"| {row['period']} | {row['days_count']} | **{row['avg_utilization_pct']}%** | {row['total_work_time']} | {row['total_idle_time']} |"
        )

    lines.extend(
        [
            "",
            "### Минимальная и максимальная загрузка по месяцам",
            "",
            "| Месяц | Зона | Макс. день | Загрузка | Работа | Простой | Мин. день | Загрузка | Работа | Простой |",
            "|-------|------|------------|----------|--------|---------|-----------|----------|--------|---------|",
        ]
    )
    for block in report["monthly"]["min_max_by_zone"]:
        for row in block["rows"]:
            lines.append(
                f"| {row['period']} | Зона {block['zone']} | "
                f"{row['max_date']} ({row['max_weekday']}) | **{row['max_utilization_pct']}%** | {row['max_work_time']} | {row['max_idle_time']} | "
                f"{row['min_date']} ({row['min_weekday']}) | **{row['min_utilization_pct']}%** | {row['min_work_time']} | {row['min_idle_time']} |"
            )

    lines.extend(
        [
            "",
            "### Минимальная и максимальная загрузка цеха по месяцам",
            "",
            "| Месяц | Макс. день | Загрузка | Работа | Простой | Мин. день | Загрузка | Работа | Простой |",
            "|-------|------------|----------|--------|---------|-----------|----------|--------|---------|",
        ]
    )
    for row in report["monthly"]["min_max_shop"]:
        lines.append(
            f"| {row['period']} | "
            f"{row['max_date']} ({row['max_weekday']}) | **{row['max_utilization_pct']}%** | {row['max_work_time']} | {row['max_idle_time']} | "
            f"{row['min_date']} ({row['min_weekday']}) | **{row['min_utilization_pct']}%** | {row['min_work_time']} | {row['min_idle_time']} |"
        )

    lines.extend(["", "---", "", "## Рейтинг зон по загрузке", ""])
    for i, r in enumerate(report["zone_ranking_by_utilization"], 1):
        lines.append(f"{i}. Зона {r['zone']} — **{r['avg_utilization_pct']}%**")

    lines.extend(["", "---", "", "## Лучшие и худшие дни по зонам (за весь период)", ""])
    for roi in ("1", "2", "3"):
        h = report["zone_highlights"][roi]
        lines.extend(
            [
                f"### Зона {roi}",
                f"- **Лучший день:** {h['best_day']['date']} ({h['best_day']['weekday']}) — работа {h['best_day']['work_time']} (загрузка {h['best_day']['utilization_pct']}%)",
                f"- **Худший день:** {h['worst_day']['date']} ({h['worst_day']['weekday']}) — работа {h['worst_day']['work_time']} (загрузка {h['worst_day']['utilization_pct']}%)",
                "",
            ]
        )

    lines.extend(["---", "", "## Отклонения от среднего (требуют внимания)", ""])
    if not report["anomalies"]:
        lines.append("Существенных отклонений не выявлено.")
    else:
        for a in report["anomalies"]:
            lines.append(
                f"- **{a['date']} ({a['weekday']}), зона {a['zone']}** — работа {a['work_time']}, простой {a['idle_time']}, загрузка {a['utilization_pct']}%. {'; '.join(a['notes'])}."
            )

    lines.extend(["", "---", "", "## Ключевые наблюдения для решений", ""])
    for i, note in enumerate(report["key_observations"], 1):
        lines.append(f"{i}. {note}")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Исключённые дни",
            "",
            "**Выходные:** " + ", ".join(report["period"]["weekends_excluded"] or ["—"]),
            "",
            "**Праздники:** " + ", ".join(report["period"]["holidays_excluded"] or ["—"]),
            "",
            "**Неполные будни (исключены из средних):** " + ", ".join(report["period"]["partial_excluded"] or ["—"]),
            "",
            "---",
            "",
            "*Данные: видеоаналитика ROI, камера «цех1». Загрузка = доля времени «работа» от суммы «работа + простой» в окне 07:00–19:00.*",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    src = json.loads(STATS.read_text(encoding="utf-8"))
    all_days, zones = build_daily_rows(src)

    zone_analytics: dict[str, dict] = {}
    for roi in (1, 2, 3):
        full = [x for x in zones[roi] if x["analyzable_for_avg"]]
        zone_analytics[str(roi)] = {
            "label": f"Зона {roi}",
            "stats_full_workdays": zone_stats(full),
            "daily": zones[roi],
        }

    shop_rows = [x for x in all_days if x["analyzable_for_avg"]]
    shop_full_analyzable = [x for x in all_days if x["analyzable"]]

    weekly_by_zone = [
        {"zone": roi, "periods": aggregate_period(zones[roi], "week", for_averages=True)}
        for roi in (1, 2, 3)
    ]
    monthly_by_zone = [
        {"zone": roi, "periods": aggregate_period(zones[roi], "month", for_averages=True)}
        for roi in (1, 2, 3)
    ]

    weekly_shop = aggregate_period(
        [
            {
                "week": x["week"],
                "month": x["month"],
                "date": x["date"],
                "analyzable": x["analyzable"],
                "analyzable_for_avg": x["analyzable_for_avg"],
                "work_seconds": x["total_work_seconds"],
                "idle_seconds": x["total_idle_seconds"],
                "utilization_pct": x["total_utilization_pct"],
            }
            for x in all_days
        ],
        "week",
        for_averages=True,
    )
    monthly_shop = aggregate_period(
        [
            {
                "week": x["week"],
                "month": x["month"],
                "date": x["date"],
                "analyzable": x["analyzable"],
                "analyzable_for_avg": x["analyzable_for_avg"],
                "work_seconds": x["total_work_seconds"],
                "idle_seconds": x["total_idle_seconds"],
                "utilization_pct": x["total_utilization_pct"],
            }
            for x in all_days
        ],
        "month",
        for_averages=True,
    )

    weekly_min_max_zone = [
        {"zone": roi, "rows": build_min_max_table(zones[roi], "week", "Неделя")}
        for roi in (1, 2, 3)
    ]
    monthly_min_max_zone = [
        {"zone": roi, "rows": build_min_max_table(zones[roi], "month", "Месяц")}
        for roi in (1, 2, 3)
    ]

    shop_period_rows = [
        {
            "week": x["week"],
            "month": x["month"],
            "date": x["date"],
            "weekday": x["weekday"],
            "analyzable": x["analyzable"],
            "analyzable_for_avg": x["analyzable_for_avg"],
            "work_time": x["total_work_time"],
            "idle_time": x["total_idle_time"],
            "work_seconds": x["total_work_seconds"],
            "idle_seconds": x["total_idle_seconds"],
            "utilization_pct": x["total_utilization_pct"],
        }
        for x in all_days
    ]
    weekly_min_max_shop = build_min_max_table(shop_period_rows, "week", "Неделя")
    monthly_min_max_shop = build_min_max_table(shop_period_rows, "month", "Месяц")

    ranking = sorted(
        [(roi, zone_analytics[str(roi)]["stats_full_workdays"]["avg_utilization_pct"]) for roi in (1, 2, 3)],
        key=lambda x: x[1],
        reverse=True,
    )

    highlights: dict[str, dict] = {}
    for roi in (1, 2, 3):
        full = [x for x in zones[roi] if x["analyzable_for_avg"]]
        best = max(full, key=lambda x: x["utilization_pct"])
        worst = min(full, key=lambda x: x["utilization_pct"])
        highlights[str(roi)] = {
            "best_day": {
                "date": best["date"],
                "weekday": best["weekday"],
                "work_time": best["work_time"],
                "utilization_pct": best["utilization_pct"],
            },
            "worst_day": {
                "date": worst["date"],
                "weekday": worst["weekday"],
                "work_time": worst["work_time"],
                "utilization_pct": worst["utilization_pct"],
            },
        }

    anomalies = build_anomalies(zones, zone_analytics)
    z1 = zone_analytics["1"]["stats_full_workdays"]
    z2 = zone_analytics["2"]["stats_full_workdays"]
    z3 = zone_analytics["3"]["stats_full_workdays"]

    best_shop = max(shop_rows, key=lambda x: x["total_utilization_pct"])
    worst_shop = min(shop_rows, key=lambda x: x["total_utilization_pct"])

    partial_in_data = sorted(d["date"] for d in all_days if d["partial_day"])
    weekends = sorted(f"{d['date']} ({d['weekday']})" for d in all_days if d["is_weekend"])
    holidays = sorted(f"{d} (праздник)" for d in HOLIDAYS if any(x["date"] == d for x in all_days))

    report = {
        "title": "Аналитический отчёт: цех 1",
        "audience": "директор",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_file": STATS.name,
        "methodology": {
            "window": "07:00–19:00 (рабочая смена)",
            "excluded": "суббота, воскресенье, праздники, неполные дни",
            "partial_days_excluded_from_averages": sorted(partial_in_data),
            "holidays_excluded": sorted(HOLIDAYS),
        },
        "period": {
            "from": all_days[0]["date"],
            "to": all_days[-1]["date"],
            "all_days": [d["date"] for d in all_days],
            "workdays_analyzed": [d["date"] for d in all_days if d["analyzable_for_avg"]],
            "weekends_excluded": weekends,
            "holidays_excluded": holidays,
            "partial_excluded": partial_in_data,
        },
        "executive_summary": [
            f"Проанализировано {z1['days_count']} полных рабочих дней (будни без неполных: {', '.join(partial_in_data) or '—'}).",
            f"Зона 1 — лидер: {z1['avg_work_time']} работы, загрузка {z1['avg_utilization_pct']}%.",
            f"Зона 2 — аутсайдер: {z2['avg_work_time']} работы, загрузка {z2['avg_utilization_pct']}%. Требует внимания.",
            f"Зона 3 — разброс от {z3['min_work_time']} до {z3['max_work_time']} работы в день.",
            f"Лучший день цеха: {best_shop['date']} ({best_shop['weekday']}) — загрузка {best_shop['total_utilization_pct']}%.",
            f"Слабый день цеха: {worst_shop['date']} ({worst_shop['weekday']}) — загрузка {worst_shop['total_utilization_pct']}%.",
            f"Добавлены разрезы по неделям ({len(weekly_shop)}) и месяцам ({len(monthly_shop)}) с таблицами мин/макс загрузки.",
            f"Выявлено {len(anomalies)} отклонений от нормы.",
        ],
        "zones": zone_analytics,
        "weekly": {
            "by_zone": weekly_by_zone,
            "shop": weekly_shop,
            "min_max_by_zone": weekly_min_max_zone,
            "min_max_shop": weekly_min_max_shop,
        },
        "monthly": {
            "by_zone": monthly_by_zone,
            "shop": monthly_shop,
            "min_max_by_zone": monthly_min_max_zone,
            "min_max_shop": monthly_min_max_shop,
        },
        "zone_ranking_by_utilization": [{"zone": r[0], "avg_utilization_pct": r[1]} for r in ranking],
        "zone_highlights": highlights,
        "shop_daily_totals": shop_full_analyzable,
        "anomalies": anomalies,
        "key_observations": [
            f"Дисбаланс зон: зона 1 — {z1['avg_utilization_pct']}%, зона 2 — {z2['avg_utilization_pct']}%, зона 3 — {z3['avg_utilization_pct']}%.",
            "В таблицах по неделям и месяцам зафиксированы конкретные дни с максимальной и минимальной загрузкой по каждой зоне.",
            f"Лучший день цеха ({best_shop['date']}) стоит сопоставить с планом производства и составом смены.",
            f"Слабый день ({worst_shop['date']}) — проверить причину просадки (простой, отсутствие персонала, сбой детекции).",
            "Зона 2 стабильно ниже 12% загрузки — рекомендуется проверить геометрию ROI и фактическое использование рабочего места.",
            "Для управленческих решений использовать недельные таблицы мин/макс — они показывают разброс внутри короткого периода.",
        ],
    }

    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_md(report), encoding="utf-8")
    print(OUT_JSON)
    print(OUT_MD)


if __name__ == "__main__":
    main()
