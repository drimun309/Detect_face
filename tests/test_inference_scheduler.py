import threading
import time
import unittest

from src.services.inference_scheduler import SharedInferenceScheduler


class SharedInferenceSchedulerTest(unittest.TestCase):
    def test_staggers_cameras_and_serializes_models(self) -> None:
        scheduler = SharedInferenceScheduler()
        calls: list[tuple[str, tuple[int, int]]] = []
        active = 0
        max_active = 0
        lock = threading.Lock()

        def factory(model: str):
            def infer(frame, _params):
                nonlocal active, max_active
                with lock:
                    active += 1
                    max_active = max(max_active, active)
                    calls.append((model, frame))
                time.sleep(0.002)
                with lock:
                    active -= 1
                return frame

            return infer

        scheduler.register("model-a", factory("a"))
        scheduler.register("model-b", factory("b"))
        for key in ("model-a", "model-b"):
            scheduler.attach(key, 1)
            scheduler.attach(key, 2)

        def feed(camera_id: int) -> None:
            for frame_index in range(1, 18):
                for key in ("model-a", "model-b"):
                    scheduler.infer(
                        key,
                        camera_id,
                        frame_index,
                        interval=4,
                        frame=(camera_id, frame_index),
                        timeout=2.0,
                    )

        threads = [threading.Thread(target=feed, args=(camera_id,)) for camera_id in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        scheduler.stop()

        camera_1 = [
            frame_index
            for model, (camera_id, frame_index) in calls
            if model == "a" and camera_id == 1
        ]
        camera_2 = [
            frame_index
            for model, (camera_id, frame_index) in calls
            if model == "a" and camera_id == 2
        ]
        self.assertEqual(camera_1, [4, 8, 12, 16])
        self.assertEqual(camera_2, [1, 5, 9, 13, 17])
        self.assertEqual(max_active, 1)


if __name__ == "__main__":
    unittest.main()
