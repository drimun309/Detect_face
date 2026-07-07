"""ROI polygons: parse, hit-test, scale (как в analiz)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from src.utils.logger import get_logger

log = get_logger()


@dataclass
class RoiPolygonData:
    points: list[tuple[float, float]]
    name: str = ""


def default_roi_name(index: int) -> str:
    return f"Зона {index}"


def roi_display_name(name: str | None, index: int) -> str:
    trimmed = (name or "").strip()
    return trimmed if trimmed else default_roi_name(index)


def parse_rois_from_json(rois_json: Optional[str]) -> list[RoiPolygonData]:
    if not rois_json:
        return []
    try:
        data = json.loads(rois_json) if isinstance(rois_json, str) else rois_json
        if not isinstance(data, list):
            return []
        polygons: list[RoiPolygonData] = []
        for idx, poly_data in enumerate(data, start=1):
            name = ""
            raw_points = poly_data
            if isinstance(poly_data, dict):
                name = str(poly_data.get("name") or "").strip()
                raw_points = poly_data.get("points", [])
            points: list[tuple[float, float]] = []
            if isinstance(raw_points, list):
                for point in raw_points:
                    if isinstance(point, (list, tuple)) and len(point) >= 2:
                        x, y = float(point[0]), float(point[1])
                        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                            points.append((x, y))
            if len(points) >= 3:
                polygons.append(
                    RoiPolygonData(
                        points=points,
                        name=name or default_roi_name(idx),
                    )
                )
        return polygons
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        log.warning(f"ROI JSON parse error: {exc}")
        return []


def serialize_rois_to_json(polygons: list[RoiPolygonData]) -> str:
    if not polygons:
        return "[]"
    data = [
        {
            "name": (poly.name or default_roi_name(idx)).strip(),
            "points": [[float(x), float(y)] for x, y in poly.points],
        }
        for idx, poly in enumerate(polygons, start=1)
    ]
    return json.dumps(data, ensure_ascii=False)


def polygons_points(polygons: list[RoiPolygonData]) -> list[list[tuple[float, float]]]:
    return [poly.points for poly in polygons]


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    p1x, p1y = polygon[0]
    for i in range(1, len(polygon) + 1):
        p2x, p2y = polygon[i % len(polygon)]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def point_in_any_polygon(
    point: tuple[float, float], polygons: list[list[tuple[float, float]]]
) -> bool:
    if not polygons:
        return True
    return any(point_in_polygon(point, poly) for poly in polygons)


def polygon_area(polygon: list[tuple[float, float]]) -> float:
    """Площадь полигона в нормализованных координатах (0–1)."""
    if len(polygon) < 3:
        return 0.0
    area = 0.0
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) * 0.5


def assign_detection_to_roi(
    point: tuple[float, float],
    polygons: list[list[tuple[float, float]]],
) -> int | None:
    """Индекс наименьшего полигона, содержащего точку (при перекрытии зон)."""
    best_idx: int | None = None
    best_area = float("inf")
    for idx, poly in enumerate(polygons):
        if point_in_polygon(point, poly):
            area = polygon_area(poly)
            if area < best_area:
                best_area = area
                best_idx = idx
    return best_idx


def scale_polygons_to_pixels(
    polygons: list[list[tuple[float, float]]], width: int, height: int
) -> list[list[tuple[int, int]]]:
    return [[(int(x * width), int(y * height)) for x, y in poly] for poly in polygons]


def box_intersects_polygon(
    box: list[int] | tuple[int, int, int, int],
    polygon: list[tuple[float, float]],
    width: int,
    height: int,
) -> bool:
    """Пересечение bbox (пиксели) с ROI-полигоном (нормализованные 0–1)."""
    if len(polygon) < 3 or width <= 0 or height <= 0:
        return False
    x1, y1, x2, y2 = box
    norm_points = (
        ((x1 + x2) / 2.0 / width, (y1 + y2) / 2.0 / height),
        (x1 / width, y1 / height),
        (x2 / width, y1 / height),
        (x2 / width, y2 / height),
        (x1 / width, y2 / height),
    )
    return any(point_in_polygon(p, polygon) for p in norm_points)
