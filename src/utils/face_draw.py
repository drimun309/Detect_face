"""Draw face boxes and Cyrillic labels on BGR frames."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]
_font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def get_cyrillic_font(size: int = 20) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size in _font_cache:
        return _font_cache[size]
    for path in FONT_CANDIDATES:
        if path.exists():
            _font_cache[size] = ImageFont.truetype(str(path), size)
            return _font_cache[size]
    _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def measure_cyrillic_text(text: str, font_size: int = 20) -> tuple[int, int]:
    font = get_cyrillic_font(font_size)
    x0, y0, x1, y1 = font.getbbox(text)
    return x1 - x0, y1 - y0


def name_match_confidence_percent(distance: float | None) -> int | None:
    """Уверенность совпадения с БД: cosine similarity × 100 (distance = 1 − sim)."""
    if distance is None:
        return None
    sim = max(0.0, min(1.0, 1.0 - float(distance)))
    return int(round(sim * 100))


def format_face_label(
    name: str | None,
    score: float,
    distance: float | None,
    show_unknown_distance: bool,
) -> str:
    if name:
        label = name.strip().capitalize()
        pct = name_match_confidence_percent(distance)
        if pct is not None:
            label = f"{label} {pct}%"
        return label
    if show_unknown_distance and distance is not None:
        pct = name_match_confidence_percent(distance)
        if pct is not None:
            return f"лицо {score:.2f} ({pct}%)"
        return f"лицо {score:.2f} (расст. {distance:.2f})"
    return f"лицо {score:.2f}"


def format_person_label(score: float) -> str:
    return f"работник {score:.2f}"


def format_head_label(score: float) -> str:
    return f"работник {score:.2f}"


def worker_count_word(n: int) -> str:
    n_abs = abs(int(n)) % 100
    n1 = n_abs % 10
    if 11 <= n_abs <= 19:
        return "работников"
    if n1 == 1:
        return "работник"
    if 2 <= n1 <= 4:
        return "работника"
    return "работников"


def worker_count_text(n: int) -> str:
    count = max(0, int(n))
    if count == 0:
        return "Работников в кадре: нет"
    return f"В кадре: {count} {worker_count_word(count)}"


def count_workers(
    boxes: list[list[int]],
    categories: list[str],
) -> int:
    if not boxes:
        return 0
    persons = sum(1 for c in categories if (c or "").lower() == "person")
    if persons:
        return persons
    heads = sum(1 for c in categories if (c or "").lower() == "head")
    if heads:
        return heads
    return len(boxes)


def draw_worker_count_badge(frame: np.ndarray, count: int) -> np.ndarray:
    text = worker_count_text(count)
    font_size = 22
    padding = 10
    margin = 12
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil)
    font = get_cyrillic_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    box_w = tw + padding * 2
    box_h = th + padding * 2
    frame_w = pil.width
    x = frame_w - box_w - margin
    y = margin
    draw.rectangle([x, y, x + box_w, y + box_h], fill=(20, 20, 20))
    draw.text((x + padding, y + padding), text, font=font, fill=(255, 220, 80))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def draw_roi_polygons(
    frame: np.ndarray,
    polygons: list[list[tuple[float, float]]],
    color: tuple[int, int, int] = (0, 255, 255),
    thickness: int = 2,
    labels: list[str] | None = None,
) -> np.ndarray:
    if not polygons:
        return frame
    from src.utils.roi_helpers import scale_polygons_to_pixels

    h, w = frame.shape[:2]
    output = frame.copy()
    scaled = scale_polygons_to_pixels(polygons, w, h)
    for poly in scaled:
        if len(poly) < 3:
            continue
        pts = np.array(poly, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(output, [pts], isClosed=True, color=color, thickness=thickness)
    if labels:
        rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        draw = ImageDraw.Draw(pil)
        font = get_cyrillic_font(18)
        for idx, poly in enumerate(scaled):
            if idx >= len(labels) or len(poly) < 3:
                continue
            label = labels[idx]
            cx = int(sum(p[0] for p in poly) / len(poly))
            cy = int(sum(p[1] for p in poly) / len(poly))
            tw, th = measure_cyrillic_text(label, 18)
            x = max(0, min(output.shape[1] - tw - 8, cx - tw // 2))
            y = max(0, min(output.shape[0] - th - 8, cy - th - 12))
            draw.rectangle([x, y, x + tw + 8, y + th + 8], fill=(30, 30, 30))
            draw.text((x + 4, y + 4), label, font=font, fill=(255, 255, 0))
        output = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return output


def draw_detections(
    frame: np.ndarray,
    boxes: list[list[int]],
    scores: list[float],
    categories: list[str],
    names: list[str | None],
    match_distances: list[float | None] | None = None,
    show_unknown_distance: bool = False,
    font_size: int = 20,
) -> np.ndarray:
    if not boxes:
        return frame

    output = frame.copy()
    labels: list[tuple[int, int, tuple[int, int, int], str]] = []

    for i, (box, score, category, name) in enumerate(zip(boxes, scores, categories, names)):
        x1, y1, x2, y2 = box
        cat = (category or "face").lower()
        if cat == "person":
            color = (255, 170, 0)
        elif cat == "head":
            color = (68, 68, 255)
        else:
            color = (0, 200, 0) if name else (0, 140, 255)
        dist = None
        if match_distances and i < len(match_distances):
            dist = match_distances[i]
        if cat == "person":
            label = format_person_label(score)
        elif cat == "head":
            label = format_head_label(score)
        else:
            label = format_face_label(name, score, dist, show_unknown_distance)
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        tw, th = measure_cyrillic_text(label, font_size)
        label_y = max(y1 - th - 12, 0)
        labels.append((x1, label_y, color, label))

    rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil)
    font = get_cyrillic_font(font_size)
    padding = 4

    for x1, label_y, color, label in labels:
        color_rgb = (color[2], color[1], color[0])
        tw, th = measure_cyrillic_text(label, font_size)
        draw.rectangle(
            [x1, label_y, x1 + tw + padding * 2, label_y + th + padding * 2],
            fill=color_rgb,
        )
        draw.text((x1 + padding, label_y + padding), label, font=font, fill=(255, 255, 255))

    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def draw_face_results(
    frame: np.ndarray,
    boxes: list[list[int]],
    scores: list[float],
    names: list[str | None],
    match_distances: list[float | None] | None = None,
    show_unknown_distance: bool = False,
    font_size: int = 20,
) -> np.ndarray:
    return draw_detections(
        frame=frame,
        boxes=boxes,
        scores=scores,
        categories=["face"] * len(boxes),
        names=names,
        match_distances=match_distances,
        show_unknown_distance=show_unknown_distance,
        font_size=font_size,
    )
