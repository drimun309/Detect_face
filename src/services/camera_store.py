"""Simple JSON-backed camera storage."""

import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from src.schema.camera_schema import CameraCreateSchema, CameraSchema, CameraUpdateSchema


class CameraStore:
    """CRUD operations for camera configs persisted in a JSON file."""

    def __init__(self, storage_path: str = "data/cameras.json") -> None:
        self.storage_path = Path(storage_path)
        self._lock = Lock()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write([])

    def _read(self) -> List[Dict[str, Any]]:
        raw = self.storage_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def _write(self, data: List[Dict[str, Any]]) -> None:
        self.storage_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list(self) -> List[CameraSchema]:
        with self._lock:
            data = self._read()
        return [CameraSchema(**item) for item in data]

    def _next_id(self, data: List[Dict[str, Any]]) -> int:
        return max((int(item["id"]) for item in data), default=0) + 1

    def create(self, payload: CameraCreateSchema) -> CameraSchema:
        with self._lock:
            data = self._read()
            item = payload.model_dump()
            item["id"] = self._next_id(data)
            data.append(item)
            self._write(data)
        return CameraSchema(**item)

    def get(self, camera_id: int) -> Optional[CameraSchema]:
        with self._lock:
            data = self._read()
        for item in data:
            if int(item["id"]) == camera_id:
                return CameraSchema(**item)
        return None

    def update(self, camera_id: int, payload: CameraUpdateSchema) -> Optional[CameraSchema]:
        updates = payload.model_dump(exclude_unset=True)
        with self._lock:
            data = self._read()
            for idx, item in enumerate(data):
                if int(item["id"]) != camera_id:
                    continue
                item.update(updates)
                data[idx] = item
                self._write(data)
                return CameraSchema(**item)
        return None

    def delete(self, camera_id: int) -> bool:
        with self._lock:
            data = self._read()
            new_data = [item for item in data if int(item["id"]) != camera_id]
            if len(new_data) == len(data):
                return False
            self._write(new_data)
        return True
