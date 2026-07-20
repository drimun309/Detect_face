# 🎯 Вариант 3: Фиксированный ROI + Трекер

Это самый быстрый путь. Никакого обучения нейросети, работает за 10 минут.

---

## 📦 Установка

```bash
pip install opencv-python numpy
```

Больше ничего не нужно! Никакой YOLO, никаких GPU.

---

## 🛠 Скрипт 1: Калибровка (запускаем один раз)

Этот скрипт поможет вам:
1. Выбрать область трекинга (верхняя ручка)
2. Настроить пороги срабатывания в реальном времени на слайдерах

Создайте `1_calibrate.py`:

```python
import cv2
import numpy as np

VIDEO_PATH = 'sealer_video.mp4'  # ← ваше видео

cap = cv2.VideoCapture(VIDEO_PATH)
ret, first_frame = cap.read()
if not ret:
    print("❌ Не удалось открыть видео")
    exit()

# ========================================
# ЭТАП 1: Выбор ROI (области для трекинга)
# ========================================
print("=" * 50)
print("ЭТАП 1: Выбор области трекинга")
print("Выделите мышкой ВЕРХНЮЮ подвижную часть запайщика")
print("Нажмите ENTER для подтверждения")
print("=" * 50)

roi = cv2.selectROI("Выберите верхнюю часть запайщика", first_frame, fromCenter=False)
cv2.destroyWindow("Выберите верхнюю часть запайщика")

x_roi, y_roi, w_roi, h_roi = [int(v) for v in roi]
print(f"✅ ROI выбран: x={x_roi}, y={y_roi}, w={w_roi}, h={h_roi}")

# ========================================
# ЭТАП 2: Трекинг + настройка порогов
# ========================================
print("\n" + "=" * 50)
print("ЭТАП 2: Настройка порогов")
print("Перемещайте слайдеры чтобы поймать момент срабатывания")
print("q = выйти и сохранить настройки")
print("=" * 50)

# Создаем окно с ползунками
cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Calibration", 900, 600)
cv2.createTrackbar("THRESH_CLOSED", "Calibration", 200, 500, lambda x: None)
cv2.createTrackbar("THRESH_OPEN",   "Calibration", 150, 500, lambda x: None)

# Инициализируем трекер
tracker = cv2.TrackerCSRT_create()
tracker.init(first_frame, (x_roi, y_roi, w_roi, h_roi))

# Записываем историю Y-координат для графика
y_history = []
max_history = 200

frame_idx = 0
events = []
state = "OPEN"  # OPEN / CLOSED

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        # Если видео кончилось — начинаем сначала
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        tracker = cv2.TrackerCSRT_create()
        ret, frame = cap.read()
        if not ret:
            break
        tracker.init(frame, (x_roi, y_roi, w_roi, h_roi))
        y_history.clear()
        continue

    # Обновляем трекер
    success, bbox = tracker.update(frame)
    
    # Если трекер слетел — пытаемся переинициализировать
    if not success:
        tracker = cv2.TrackerCSRT_create()
        tracker.init(frame, (x_roi, y_roi, w_roi, h_roi))
        success, bbox = tracker.update(frame)
    
    # Получаем текущие пороги с ползунков
    thresh_closed = cv2.getTrackbarPos("THRESH_CLOSED", "Calibration")
    thresh_open = cv2.getTrackbarPos("THRESH_OPEN", "Calibration")
    
    # Рисуем ROI
    cv2.rectangle(frame, (x_roi, y_roi), (x_roi + w_roi, y_roi + h_roi), (255, 0, 0), 2)
    
    if success:
        bx, by, bw, bh = [int(v) for v in bbox]
        center_x = bx + bw // 2
        center_y = by + bh // 2
        
        # Рисуем трекируемую область
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
        
        # Y-координата центра
        y_history.append(center_y)
        if len(y_history) > max_history:
            y_history.pop(0)
        
        # Логика срабатывания
        if state == "OPEN" and center_y > thresh_closed:
            state = "CLOSED"
            events.append(frame_idx)
            print(f"  🎯 [{frame_idx}] СРАБАТЫВАНИЕ! Y={center_y}")
        elif state == "CLOSED" and center_y < thresh_open:
            state = "OPEN"
            print(f"  🔓 [{frame_idx}] Открыто. Y={center_y}")
        
        # Текст
        color = (0, 255, 0) if state == "CLOSED" else (200, 200, 200)
        cv2.putText(frame, f"Y: {center_y}  State: {state}  Events: {len(events)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Горизонтальные линии порогов
        cv2.line(frame, (0, thresh_closed), (frame.shape[1], thresh_closed), (0, 0, 255), 1)
        cv2.line(frame, (0, thresh_open), (frame.shape[1], thresh_open), (255, 255, 0), 1)
        
        # Мини-график внизу экрана
        graph_h = 100
        graph_y = frame.shape[0] - graph_h - 10
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, graph_y), (max_history * 3, graph_y + graph_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        if len(y_history) > 1:
            min_y = min(y_history) - 10
            max_y = max(y_history) + 10
            if max_y == min_y:
                max_y += 1
            
            for i in range(len(y_history) - 1):
                px1 = i * 3
                py1 = graph_y + graph_h - int((y_history[i] - min_y) / (max_y - min_y) * graph_h)
                px2 = (i + 1) * 3
                py2 = graph_y + graph_h - int((y_history[i + 1] - min_y) / (max_y - min_y) * graph_h)
                cv2.line(frame, (px1, py1), (px2, py2), (0, 255, 255), 2)
    else:
        cv2.putText(frame, "TRACKER LOST - reinit...", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    cv2.imshow("Calibration", frame)
    frame_idx += 1
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        # Переинициализация трекера вручную
        tracker = cv2.TrackerCSRT_create()
        tracker.init(frame, (x_roi, y_roi, w_roi, h_roi))
        print("  🔄 Трекер переинициализирован")

cap.release()
cv2.destroyAllWindows()

# ========================================
# Сохраняем настройки
# ========================================
final_closed = cv2.getTrackbarPos("THRESH_CLOSED", "Calibration") if frame_idx > 0 else 200
final_open = cv2.getTrackbarPos("THRESH_OPEN", "Calibration") if frame_idx > 0 else 150

config = f"""# Настройки калибровки (скопируйте в 2_detect.py)
ROI_X = {x_roi}
ROI_Y = {y_roi}
ROI_W = {w_roi}
ROI_H = {h_roi}
THRESH_CLOSED = {final_closed}
THRESH_OPEN = {final_open}
"""

print("\n" + "=" * 50)
print("📋 СОХРАНИТЕ ЭТИ НАСТРОЙКИ:")
print("=" * 50)
print(config)

with open('calibration.txt', 'w') as f:
    f.write(config)
print("💾 Также сохранено в calibration.txt")
```

**Как пользоваться:**
1. Запустите `python 1_calibrate.py`
2. Выделите мышкой **верхнюю ручку** запайщика
3. Смотрите на график и двигайте ползунки:
   - `THRESH_CLOSED` — когда Y пересекает эту линию → срабатывание
   - `THRESH_OPEN` — когда Y возвращается выше → открыто
4. Нажимайте `q` когда довольны результатом

---

## 🚀 Скрипт 2: Продакшн-детекция

Создайте `2_detect.py`:

```python
import cv2
import json
import time
from datetime import datetime

# === НАСТРОЙКИ ИЗ КАЛИБРОВКИ (скопируйте из calibration.txt) ===
VIDEO_PATH = 'sealer_video.mp4'
OUTPUT_VIDEO = 'output.mp4'

ROI_X = 300       # ← замените на свои значения!
ROI_Y = 100
ROI_W = 80
ROI_H = 60
THRESH_CLOSED = 200
THRESH_OPEN = 150

# === ИНИЦИАЛИЗАЦИЯ ===
cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)

# Если нужно сохранить видео с отрисовкой:
save_video = True
if save_video:
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (w, h))

# Трекер
tracker = cv2.TrackerCSRT_create()
ret, first_frame = cap.read()
tracker.init(first_frame, (ROI_X, ROI_Y, ROI_W, ROI_H))

# Состояние
state = "OPEN"
events = []
frame_idx = 1  # начинаем с 1, т.к. первый кадр уже прочитан

# === ОБРАБОТКА ===
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    timestamp = frame_idx / fps
    
    # Обновляем трекер
    success, bbox = tracker.update(frame)
    
    if not success:
        # Переинициализация
        tracker = cv2.TrackerCSRT_create()
        tracker.init(frame, (ROI_X, ROI_Y, ROI_W, ROI_H))
        success, bbox = tracker.update(frame)
    
    if success:
        bx, by, bw, bh = [int(v) for v in bbox]
        center_y = by + bh // 2
        
        # --- ЛОГИКА СРАБАТЫВАНИЯ ---
        if state == "OPEN" and center_y > THRESH_CLOSED:
            state = "CLOSED"
            event = {
                "frame": frame_idx,
                "time_sec": round(timestamp, 3),
                "time_str": str(datetime.now()),
                "y_position": center_y
            }
            events.append(event)
            print(f"🎯 СРАБАТЫВАНИЕ #{len(events)} | "
                  f"кадр={frame_idx} | время={timestamp:.2f}с | Y={center_y}")
            
            # >>> ЗДЕСЬ МОЖНО ДОБАВИТЬ ВАШЕ ДЕЙСТВИЕ <<<
            # Например: requests.post("http://your-api/count")
            # Или: mqtt.publish("sealer/events", json.dumps(event))
        
        elif state == "CLOSED" and center_y < THRESH_OPEN:
            state = "OPEN"
    
    # --- ОТРИСОВКА ---
    cv2.rectangle(frame, (ROI_X, ROI_Y), (ROI_X + ROI_W, ROI_Y + ROI_H), (255, 0, 0), 2)
    cv2.line(frame, (0, THRESH_CLOSED), (frame.shape[1], THRESH_CLOSED), (0, 0, 255), 1)
    
    if success:
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        color = (0, 255, 0) if state == "CLOSED" else (200, 200, 200)
        cv2.putText(frame, f"Events: {len(events)} | {state}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    if save_video:
        out.write(frame)
    
    frame_idx += 1

# === ФИНАЛ ===
cap.release()
if save_video:
    out.release()

with open('events.json', 'w', encoding='utf-8') as f:
    json.dump(events, f, indent=2, ensure_ascii=False)

print(f"\n✅ Готово! Всего срабатываний: {len(events)}")
print(f"📄 events.json сохранен")
if save_video:
    print(f"📹 {OUTPUT_VIDEO} сохранен")
```

---

## 📊 Скрипт 3: Красивый отчет

Создайте `3_report.py`:

```python
import json
import matplotlib.pyplot as plt

with open('events.json', 'r') as f:
    events = json.load(f)

print(f"Всего срабатываний: {len(events)}")

if len(events) == 0:
    print("Нет событий для отображения")
    exit()

times = [e['time_sec'] for e in events]
y_positions = [e['y_position'] for e in events]

# --- График времени между срабатываниями ---
if len(times) > 1:
    intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    # Верхний: таймлайн событий
    axes[0].eventplot([times], orientation='horizontal', colors='green')
    axes[0].set_xlabel('Время (сек)')
    axes[0].set_title('Таймлайн срабатываний')
    axes[0].set_yticks([])
    
    # Нижний: интервалы между срабатываниями
    axes[1].bar(range(len(intervals)), intervals, color='steelblue')
    axes[1].axhline(y=sum(intervals)/len(intervals), color='red', 
                    linestyle='--', label=f'Среднее: {sum(intervals)/len(intervals):.1f}с')
    axes[1].set_xlabel('Номер срабатывания')
    axes[1].set_ylabel('Интервал (сек)')
    axes[1].set_title('Время между срабатываниями')
    axes[1].legend()
    
    plt.tight_layout()
    plt.savefig('report.png', dpi=150)
    plt.show()
    
    print(f"\n📊 Статистика:")
    print(f"  Средний интервал: {sum(intervals)/len(intervals):.2f}с")
    print(f"  Мин. интервал: {min(intervals):.2f}с")
    print(f"  Макс. интервал: {max(intervals):.2f}с")
    print(f"  Срабатываний в минуту: {len(events) / (times[-1] - times[0]) * 60:.1f}")
```

Для этого скрипта нужен matplotlib:
```bash
pip install matplotlib
```

---

## 🔄 Полный рабочий цикл

```
1. python 1_calibrate.py     → выбрать ROI, настроить пороги
2. Скопировать значения из calibration.txt в 2_detect.py
3. python 2_detect.py         → обработать видео, получить events.json
4. python 3_report.py         → посмотреть статистику и график
```

---

## ⚠️ Что делать если трекер слетает

| Проблема | Решение |
|----------|---------|
| Рука закрывает ручку | Увеличьте ROI чтобы захватить больше ручки |
| Пакет перекрывает | Сдвиньте ROI на часть ручки, которая видна всегда |
| Освещение меняется | В калибровке выберите ROI на самой контрастной части |
| Трекер "уплывает" | В `1_calibrate.py` нажимайте `r` для ручной переинициализации |
| Срабатывания дублируются | Увеличьте разницу между `THRESH_CLOSED` и `THRESH_OPEN` (гистерезис) |

**Совет по гистерезису:** Разница между `THRESH_CLOSED` и `THRESH_OPEN` — это ваша защита от дребезга. Если `CLOSED=200` а `OPEN=150`, то после срабатывания ручка должна подняться на 50 пикселей прежде чем система снова сможет зафиксировать срабатывание. Чем больше разница — тем меньше ложных срабатываний.

---

Попробуйте запустить калибровку и пришлите результат — если что-то не работает, разберем!