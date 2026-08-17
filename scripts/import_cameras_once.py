"""One-off import of cameras from JSON file via local API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

DEFAULT_PATH = "/ISAPI/Streaming/Channels/101"
API_URL = "http://127.0.0.1:7030/api/v1/cameras"


def normalize_camera(item: dict) -> dict:
    path = (item.get("path") or "").strip()
    if not path:
        path = DEFAULT_PATH
    return {
        "name": str(item["name"]),
        "ip": str(item["ip"]),
        "port": int(item.get("port", 554)),
        "username": item.get("username"),
        "password": item.get("password"),
        "protocol": item.get("protocol", "rtsp"),
        "path": path if path.startswith("/") else f"/{path}",
        "enabled": bool(item.get("enabled", True)),
    }


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if src is None or not src.is_file():
        print("Usage: import_cameras_once.py <cameras.json>", file=sys.stderr)
        return 1

    raw = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("Expected JSON array", file=sys.stderr)
        return 1

    existing = {c["name"] for c in requests.get(API_URL, timeout=15).json().get("items", [])}
    added = 0
    for item in raw:
        if not isinstance(item, dict) or "name" not in item:
            continue
        payload = normalize_camera(item)
        if payload["name"] in existing:
            print(f"skip existing: {payload['name']}")
            continue
        resp = requests.post(API_URL, json=payload, timeout=30)
        if not resp.ok:
            print(f"fail {payload['name']}: {resp.status_code} {resp.text}", file=sys.stderr)
            return 1
        body = resp.json()
        print(f"added {payload['name']} -> id={body['id']} ip={payload['ip']}")
        existing.add(payload["name"])
        added += 1

    total = len(requests.get(API_URL, timeout=15).json().get("items", []))
    print(f"done: added={added}, total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
