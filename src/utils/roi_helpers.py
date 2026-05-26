"""ROI polygons: parse, hit-test, scale (как в analiz)."""

from __future__ import annotations

import json
from typing import Optional

from src.utils.logger import get_logger

log = get_logger()


def parse_rois_from_json(rois_json: Optional[str]) -> list[list[tuple[float, float]]]:
    if not rois_json:
        return []
    try:
        data = json.loads(rois_json) if isinstance(rois_json, str) else rois_json
        if not isinstance(data, list):
            return []
        polygons: list[list[tuple[float, float]]] = []
        for poly_data in data:
            if not isinstance(poly_data, list) or len(poly_data) < 3:
                continue
            points: list[tuple[float, float]] = []
            for point in poly_data:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    x, y = float(point[0]), float(point[1])
                    if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                        points.append((x, y))
            if len(points) >= 3:
                polygons.append(points)
        return polygons
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        log.warning(f"ROI JSON parse error: {exc}")
        return []


def serialize_rois_to_json(polygons: list[list[tuple[float, float]]]) -> str:
    if not polygons:
        return "[]"
    data = [[[float(x), float(y)] for x, y in poly] for poly in polygons]
    return json.dumps(data, ensure_ascii=False)


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


def scale_polygons_to_pixels(
    polygons: list[list[tuple[float, float]]], width: int, height: int
) -> list[list[tuple[int, int]]]:
    return [[(int(x * width), int(y * height)) for x, y in poly] for poly in polygons]
