"""Smoke tests for people-zone polygon counting."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.streaming.face_annotated_stream import FaceAnnotatedStreamer, FaceStreamerConfig


def _streamer(polygon: list[tuple[float, float]]) -> FaceAnnotatedStreamer:
    cfg = FaceStreamerConfig(
        camera_id=99,
        camera_name="test",
        rtsp_input_url="rtsp://test",
        people_zone_enabled=True,
        people_zone_polygon=polygon,
    )
    streamer = FaceAnnotatedStreamer.__new__(FaceAnnotatedStreamer)
    streamer.config = cfg
    streamer._people_tracks = {}
    return streamer


def test_inside_polygon_count() -> None:
    polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    s = _streamer(polygon)
    boxes = [[400, 300, 500, 450], [700, 320, 820, 470]]
    centers = s._people_zone_track_centers(boxes, ["person", "person"], 1280, 720)
    assert len(centers) == 2


def test_outside_polygon_ignored() -> None:
    polygon = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]
    s = _streamer(polygon)
    boxes = [[900, 300, 1000, 450]]
    centers = s._people_zone_track_centers(boxes, ["person"], 1280, 720)
    assert len(centers) == 0


def test_live_inside_count() -> None:
    polygon = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    cfg = FaceStreamerConfig(
        camera_id=2,
        camera_name="test",
        rtsp_input_url="rtsp://test",
        people_zone_enabled=True,
        people_zone_polygon=polygon,
    )
    store = MagicMock()
    store.tick.return_value = MagicMock(current_workers=2, person_seconds=0.0)

    streamer = FaceAnnotatedStreamer.__new__(FaceAnnotatedStreamer)
    streamer.config = cfg
    streamer.people_counter_store = store
    streamer._people_tracks = {}
    streamer.metrics = {}

    w, h = 1280, 720

    def box_at(nx: float, ny: float) -> list[int]:
        cx = int(nx * w)
        cy = int(ny * h)
        return [cx - 40, cy - 80, cx + 40, cy + 80]

    streamer._update_people_counter(
        [box_at(0.4, 0.5), box_at(0.6, 0.55)],
        ["person", "person"],
        w,
        h,
    )

    assert store.tick.call_args.kwargs.get("target_workers") == 2


if __name__ == "__main__":
    test_inside_polygon_count()
    test_outside_polygon_ignored()
    test_live_inside_count()
    print("OK: people zone tests passed")
