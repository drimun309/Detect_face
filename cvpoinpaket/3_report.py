import json
from pathlib import Path

import matplotlib.pyplot as plt

EVENTS_PATH = Path(__file__).parent / "events.json"
REPORT_PATH = Path(__file__).parent / "report.png"

if not EVENTS_PATH.exists():
    print(f"Файл {EVENTS_PATH} не найден. Сначала запустите: python 2_detect.py")
    exit(1)

with EVENTS_PATH.open(encoding="utf-8") as f:
    events = json.load(f)

print(f"Всего срабатываний: {len(events)}")

if len(events) == 0:
    print("Нет событий для отображения")
    exit(0)

times = [e["time_sec"] for e in events]
positions = [e.get("diff_score", e.get("position", e.get("y_position"))) for e in events]

print("\nСобытия:")
for i, event in enumerate(events, 1):
    print(
        f"  #{i}: кадр {event['frame']}, "
        f"время {event['time_sec']:.2f}с, "
        f"diff={positions[i - 1]}"
    )

if len(times) > 1:
    intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    avg_interval = sum(intervals) / len(intervals)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    axes[0].eventplot([times], orientation="horizontal", colors="green")
    axes[0].set_xlabel("Время (сек)")
    axes[0].set_title("Таймлайн срабатываний")
    axes[0].set_yticks([])

    axes[1].bar(range(len(intervals)), intervals, color="steelblue")
    axes[1].axhline(
        y=avg_interval,
        color="red",
        linestyle="--",
        label=f"Среднее: {avg_interval:.1f}с",
    )
    axes[1].set_xlabel("Номер срабатывания")
    axes[1].set_ylabel("Интервал (сек)")
    axes[1].set_title("Время между срабатываниями")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(REPORT_PATH, dpi=150)
    print(f"\nГрафик сохранён: {REPORT_PATH}")

    print("\nСтатистика:")
    print(f"  Средний интервал: {avg_interval:.2f}с")
    print(f"  Мин. интервал: {min(intervals):.2f}с")
    print(f"  Макс. интервал: {max(intervals):.2f}с")
    duration = times[-1] - times[0]
    if duration > 0:
        print(f"  Срабатываний в минуту: {len(events) / duration * 60:.1f}")
else:
    print("\nТолько одно срабатывание — для интервалов нужно минимум два.")
