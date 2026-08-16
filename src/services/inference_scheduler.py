"""Shared, phase-staggered inference workers.

One worker owns one model instance. Camera streams submit frames according to a
stable phase, while a process-wide execution lock prevents several GPU models
from starting inference at the same instant.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable


InferCallable = Callable[[Any, dict[str, Any]], Any]


@dataclass
class _Task:
    camera_id: int
    frame: Any
    params: dict[str, Any]
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: BaseException | None = None


class _ModelWorker:
    def __init__(
        self,
        key: str,
        infer: InferCallable,
        device_lock: threading.Lock,
        model_offset: int,
    ) -> None:
        self.key = key
        self.infer = infer
        self.device_lock = device_lock
        self.model_offset = model_offset
        self._condition = threading.Condition()
        self._pending: dict[int, _Task] = {}
        self._camera_order: list[int] = []
        self._round_robin: deque[int] = deque()
        self._latest: dict[int, Any] = {}
        self._running = True
        self.completed = 0
        self.failed = 0
        self.total_seconds = 0.0
        self.thread = threading.Thread(
            target=self._loop, name=f"infer-{key}", daemon=True
        )
        self.thread.start()

    def attach(self, camera_id: int) -> None:
        with self._condition:
            if camera_id not in self._camera_order:
                self._camera_order.append(camera_id)
                self._camera_order.sort()

    def detach(self, camera_id: int) -> None:
        with self._condition:
            self._camera_order = [item for item in self._camera_order if item != camera_id]
            task = self._pending.pop(camera_id, None)
            if task:
                task.error = RuntimeError("camera detached")
                task.done.set()
            self._latest.pop(camera_id, None)
            self._round_robin = deque(
                item for item in self._round_robin if item != camera_id
            )

    def phase(self, camera_id: int, interval: int) -> int:
        interval = max(1, int(interval))
        with self._condition:
            try:
                camera_offset = self._camera_order.index(camera_id)
            except ValueError:
                self._camera_order.append(camera_id)
                self._camera_order.sort()
                camera_offset = self._camera_order.index(camera_id)
        return (camera_offset + self.model_offset) % interval

    def submit(
        self,
        camera_id: int,
        frame_index: int,
        interval: int,
        frame: Any,
        params: dict[str, Any],
        timeout: float,
    ) -> tuple[Any, bool]:
        self.attach(camera_id)
        if int(frame_index) % max(1, int(interval)) != self.phase(camera_id, interval):
            return self._latest.get(camera_id), False

        task = _Task(camera_id=camera_id, frame=frame, params=params)
        with self._condition:
            previous = self._pending.get(camera_id)
            if previous is not None:
                previous.error = RuntimeError("superseded by a newer frame")
                previous.done.set()
            self._pending[camera_id] = task
            if camera_id not in self._round_robin:
                self._round_robin.append(camera_id)
            self._condition.notify()

        if not task.done.wait(timeout=max(0.1, timeout)):
            return self._latest.get(camera_id), False
        if task.error is not None:
            raise task.error
        return task.result, True

    def _next_task(self) -> _Task | None:
        while self._round_robin:
            camera_id = self._round_robin.popleft()
            task = self._pending.pop(camera_id, None)
            if task is not None:
                return task
        return None

    def _loop(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: not self._running or bool(self._pending))
                if not self._running and not self._pending:
                    return
                task = self._next_task()
            if task is None:
                continue
            started = time.perf_counter()
            try:
                with self.device_lock:
                    task.result = self.infer(task.frame, task.params)
                self._latest[task.camera_id] = task.result
                self.completed += 1
            except BaseException as exc:
                task.error = exc
                self.failed += 1
            finally:
                self.total_seconds += time.perf_counter() - started
                task.done.set()

    def stop(self) -> None:
        with self._condition:
            self._running = False
            self._condition.notify_all()
        self.thread.join(timeout=5.0)

    def metrics(self) -> dict[str, Any]:
        avg_ms = self.total_seconds * 1000.0 / self.completed if self.completed else 0.0
        return {
            "key": self.key,
            "cameras": list(self._camera_order),
            "completed": self.completed,
            "failed": self.failed,
            "pending": len(self._pending),
            "average_inference_ms": round(avg_ms, 2),
        }


class SharedInferenceScheduler:
    """Registry of unique model workers with deterministic camera/model phases."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._device_lock = threading.Lock()
        self._workers: dict[str, _ModelWorker] = {}

    def register(self, key: str, infer: InferCallable) -> None:
        with self._lock:
            if key in self._workers:
                return
            self._workers[key] = _ModelWorker(
                key, infer, self._device_lock, model_offset=len(self._workers)
            )

    def attach(self, key: str, camera_id: int) -> None:
        self._workers[key].attach(camera_id)

    def infer(
        self,
        key: str,
        camera_id: int,
        frame_index: int,
        interval: int,
        frame: Any,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> tuple[Any, bool]:
        worker = self._workers.get(key)
        if worker is None:
            raise KeyError(f"Inference model is not registered: {key}")
        return worker.submit(
            camera_id, frame_index, interval, frame, params or {}, timeout
        )

    def detach_camera(self, camera_id: int) -> None:
        with self._lock:
            for worker in self._workers.values():
                worker.detach(camera_id)

    def metrics(self) -> list[dict[str, Any]]:
        with self._lock:
            return [worker.metrics() for worker in self._workers.values()]

    def camera_schedule(
        self, camera_id: int, interval: int, keys: list[str]
    ) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "model": key,
                    "interval": max(1, int(interval)),
                    "phase": self._workers[key].phase(camera_id, interval),
                }
                for key in keys
                if key in self._workers
            ]

    def stop(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()
        for worker in workers:
            worker.stop()
