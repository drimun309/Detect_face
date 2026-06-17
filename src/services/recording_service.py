"""Recording service for saving annotated video.

Сохраняет RTSP-потоки в mp4-ролики сегментами и чистит старые записи.
"""

import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.schema.settings_schema import RecordingSettingsSchema
from src.utils.logger import get_logger

log = get_logger()


class RecordingService:
    """Service for recording annotated streams."""

    def __init__(self, settings: RecordingSettingsSchema) -> None:
        self.settings = settings
        self._active_recordings: Dict[int, subprocess.Popen] = {}  # camera_id -> ffmpeg process
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._camera_provider = None

    def update_settings(self, settings: RecordingSettingsSchema) -> None:
        self.settings = settings

    def set_camera_provider(self, provider) -> None:
        """provider: callable returning list of CameraSchema."""
        self._camera_provider = provider

    def _reap_recording(self, camera_id: int) -> None:
        """Убрать завершившийся ffmpeg из активных."""
        with self._lock:
            proc = self._active_recordings.get(camera_id)
            if proc is None:
                return
            try:
                dead = proc.poll() is not None
            except Exception:
                dead = True
            if dead:
                self._active_recordings.pop(camera_id, None)

    def is_recording(self, camera_id: int) -> bool:
        self._reap_recording(camera_id)
        with self._lock:
            proc = self._active_recordings.get(camera_id)
        if proc is None:
            return False
        try:
            return proc.poll() is None
        except Exception:
            return True

    def is_shift_active(self) -> bool:
        """Check if current time is within shift hours."""
        if not self.settings.shift.enabled:
            return True  # Record all the time if not using shift
        try:
            now = datetime.now().time()
            start = datetime.strptime(self.settings.shift.start_time, "%H:%M").time()
            end = datetime.strptime(self.settings.shift.end_time, "%H:%M").time()
            if start <= end:
                return start <= now <= end
            else:
                return now >= start or now <= end
        except ValueError:
            return True

    @staticmethod
    def _camera_dir_name(camera_id: int, camera_name: str) -> str:
        return f"cam{camera_id}_{camera_name}"

    def _recordings_base(self) -> Path:
        return Path(self.settings.recordings_path)

    def _camera_dirs(self, camera_id: int, camera_name: str) -> list[Path]:
        """Все папки cam{id}_* (после переименования камеры их может быть несколько)."""
        base = self._recordings_base()
        if not base.is_dir():
            return []
        prefix = f"cam{camera_id}_"
        dirs = [p for p in base.iterdir() if p.is_dir() and p.name.startswith(prefix)]
        exact = base / self._camera_dir_name(camera_id, camera_name)
        if exact.is_dir() and exact not in dirs:
            dirs.append(exact)
        if not dirs:
            return [exact]
        return sorted(dirs, key=lambda p: p.name)

    def _primary_camera_dir(self, camera_id: int, camera_name: str) -> Path:
        base = self._recordings_base()
        exact = base / self._camera_dir_name(camera_id, camera_name)
        dirs = self._camera_dirs(camera_id, camera_name)
        if exact.is_dir():
            return exact
        if len(dirs) == 1:
            return dirs[0]
        if dirs:
            return max(dirs, key=lambda p: sum(1 for _ in p.rglob("*.mp4")))
        return exact

    def rename_camera_folder(self, camera_id: int, old_name: str, new_name: str) -> None:
        """Переименовать/объединить папку записей при смене имени камеры."""
        if not old_name or not new_name or old_name == new_name:
            return
        base = self._recordings_base()
        old_dir = base / self._camera_dir_name(camera_id, old_name)
        new_dir = base / self._camera_dir_name(camera_id, new_name)
        if not old_dir.is_dir():
            return
        try:
            if new_dir.is_dir() and new_dir != old_dir:
                for day_dir in old_dir.iterdir():
                    if not day_dir.is_dir():
                        continue
                    target_day = new_dir / day_dir.name
                    target_day.mkdir(parents=True, exist_ok=True)
                    for f in day_dir.glob("*.mp4"):
                        dest = target_day / f.name
                        if not dest.exists():
                            f.rename(dest)
                    try:
                        day_dir.rmdir()
                    except OSError:
                        pass
                try:
                    old_dir.rmdir()
                except OSError:
                    pass
                log.info(f"[cam {camera_id}] Merged recordings {old_dir.name} -> {new_dir.name}")
            elif not new_dir.exists():
                old_dir.rename(new_dir)
                log.info(f"[cam {camera_id}] Renamed recordings folder to {new_dir.name}")
        except OSError as exc:
            log.warning(f"[cam {camera_id}] Recordings folder rename failed: {exc}")

    def get_output_path(self, camera_id: int, camera_name: str) -> Path:
        """Get the output path for today's recordings."""
        today = datetime.now().strftime("%Y-%m-%d")
        cam_dir = self._primary_camera_dir(camera_id, camera_name) / today
        cam_dir.mkdir(parents=True, exist_ok=True)
        return cam_dir

    def get_file_path(self, camera_id: int, camera_name: str, date: str, filename: str) -> Path:
        for cam_dir in self._camera_dirs(camera_id, camera_name):
            path = cam_dir / date / filename
            if path.is_file():
                return path
        return self._primary_camera_dir(camera_id, camera_name) / date / filename

    def start_recording(
        self,
        camera_id: int,
        camera_name: str,
        rtsp_url: str,
        *,
        manual: bool = False,
    ) -> bool:
        """Start recording for a camera."""
        self._reap_recording(camera_id)
        if not self.settings.enabled:
            return False
        if (
            not manual
            and self.settings.shift.enabled
            and not self.is_shift_active()
        ):
            return False
        with self._lock:
            if camera_id in self._active_recordings:
                return True  # Already recording

        output_dir = self.get_output_path(camera_id, camera_name)
        segment_sec = int(self.settings.chunk_duration_min) * 60
        # сегменты будут называться по времени начала (strftime)
        output_pattern = str(output_dir / "%H%M%S.mp4")

        # ffmpeg: RTSP -> H264 mp4 segments
        vf = f"scale={self.settings.record_width}:{self.settings.record_height}"
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-rtsp_transport",
            "tcp",
            "-i",
            rtsp_url,
            "-an",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(int(self.settings.record_crf)),
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "segment",
            "-segment_format_options",
            "movflags=+faststart",
            "-segment_time",
            str(segment_sec),
            "-reset_timestamps",
            "1",
            "-strftime",
            "1",
            output_pattern,
        ]

        try:
            log.info(f"[cam {camera_id}] Starting recording segments -> {output_dir}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with self._lock:
                self._active_recordings[camera_id] = process
            return True
        except Exception as e:
            log.error(f"[cam {camera_id}] Failed to start recording: {e}")
            return False

    def stop_recording(self, camera_id: int) -> None:
        """Stop recording for a camera."""
        with self._lock:
            process = self._active_recordings.pop(camera_id, None)
        if process is None:
            return
        log.info(f"[cam {camera_id}] Stopping recording")
        try:
            process.terminate()
        except Exception:
            pass

    def get_recordings_list(self, camera_id: int, camera_name: str, date: str) -> list[dict]:
        """Get list of recordings for a specific date."""
        by_name: dict[str, Path] = {}
        for cam_dir in self._camera_dirs(camera_id, camera_name):
            day_dir = cam_dir / date
            if not day_dir.is_dir():
                continue
            for f in day_dir.glob("*.mp4"):
                by_name.setdefault(f.name, f)
        if not by_name:
            return []
        files = sorted(by_name.values(), key=lambda p: p.name)
        chunk_sec = int(self.settings.chunk_duration_min) * 60
        recordings = []
        for i, f in enumerate(files):
            stat = f.stat()
            start_ts, end_ts = self._clip_range_unix(
                f.name, date, files, i, chunk_sec, stat.st_mtime
            )
            recordings.append({
                "filename": f.name,
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
                "start_ts": start_ts,
                "end_ts": end_ts,
            })
        return recordings

    @staticmethod
    def _clip_range_unix(
        filename: str,
        date_str: str,
        files: list[Path],
        index: int,
        chunk_sec: int,
        mtime: float,
    ) -> tuple[float | None, float | None]:
        m = re.match(r"^(\d{2})(\d{2})(\d{2})\.mp4$", filename)
        if not m:
            return None, None
        try:
            from src.services.roi_timer_store import RoiTimerStore

            day_start, _ = RoiTimerStore.day_range_unix(date_str)
            hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
            start = day_start + hh * 3600 + mm * 60 + ss
            end = start + chunk_sec
            if index + 1 < len(files):
                nxt = files[index + 1].name
                nm = re.match(r"^(\d{2})(\d{2})(\d{2})\.mp4$", nxt)
                if nm:
                    nh, nmi, ns = int(nm.group(1)), int(nm.group(2)), int(nm.group(3))
                    next_start = day_start + nh * 3600 + nmi * 60 + ns
                    if next_start > start:
                        end = min(end, next_start)
            if mtime and mtime > start:
                end = min(end, mtime + 1)
            return start, end
        except Exception:
            return None, None

    def build_clips_for_timeline(
        self, camera_id: int, camera_name: str, date: str
    ) -> list[dict]:
        items = self.get_recordings_list(camera_id, camera_name, date)
        clips = []
        for it in items:
            if it.get("start_ts") is None or it.get("end_ts") is None:
                continue
            clips.append(
                {
                    "filename": it["filename"],
                    "start": float(it["start_ts"]),
                    "end": float(it["end_ts"]),
                }
            )
        return clips

    def get_available_dates(self, camera_id: int, camera_name: str) -> list[str]:
        """Get list of dates with recordings."""
        dates: set[str] = set()
        for cam_dir in self._camera_dirs(camera_id, camera_name):
            if not cam_dir.is_dir():
                continue
            for d in cam_dir.iterdir():
                if d.is_dir():
                    dates.add(d.name)
        return sorted(dates, reverse=True)

    def delete_recording(self, camera_id: int, camera_name: str, date: str, filename: str) -> bool:
        """Delete a specific recording."""
        file_path = self.get_file_path(camera_id, camera_name, date, filename)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def cleanup_old_recordings(self) -> int:
        """Remove recordings older than retention_days. Returns count of deleted files."""
        if self.settings.retention_days <= 0:
            return 0
        cutoff = datetime.now().timestamp() - (self.settings.retention_days * 86400)
        deleted = 0
        base = Path(self.settings.recordings_path)
        if not base.exists():
            return 0
        for cam_dir in base.iterdir():
            if not cam_dir.is_dir():
                continue
            for date_dir in cam_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                try:
                    dir_time = datetime.strptime(date_dir.name, "%Y-%m-%d").timestamp()
                    if dir_time < cutoff:
                        for f in date_dir.glob("*"):
                            f.unlink()
                        date_dir.rmdir()
                        deleted += 1
                        log.info(f"Deleted old recording: {date_dir}")
                except ValueError:
                    continue
        return deleted

    def start(self) -> None:
        """Start the cleanup background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the cleanup thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _cleanup_loop(self) -> None:
        """Background loop to cleanup old recordings."""
        while self._running:
            try:
                # auto-record loop every 5 seconds
                self._sync_auto_recording()
            except Exception as e:
                log.error(f"Cleanup error: {e}")
            # cleanup old recordings hourly
            if int(time.time()) % 3600 < 5:
                try:
                    deleted = self.cleanup_old_recordings()
                    if deleted > 0:
                        log.info(f"Cleaned up {deleted} old recording directories")
                except Exception:
                    pass
            time.sleep(5)

    def _sync_auto_recording(self) -> None:
        if not self.settings.enabled or not self.settings.auto_enabled:
            return
        if not self._camera_provider:
            return
        active = self.is_shift_active() if self.settings.shift.enabled else True
        cams = [c for c in (self._camera_provider() or []) if getattr(c, "enabled", False)]
        if not active:
            # stop all
            for cam in cams:
                if self.is_recording(cam.id):
                    self.stop_recording(cam.id)
            return
        # start for all enabled cams
        for cam in cams:
            self._reap_recording(cam.id)
            if not self.is_recording(cam.id):
                # annotated stream in MediaMTX
                rtsp = f"rtsp://mediamtx:8554/annot_cam_{cam.id}"
                self.start_recording(cam.id, cam.name, rtsp, manual=False)


_recording_service: Optional[RecordingService] = None


def init_recording_service(settings: RecordingSettingsSchema) -> RecordingService:
    global _recording_service
    _recording_service = RecordingService(settings)
    _recording_service.start()
    return _recording_service


def get_recording_service() -> Optional[RecordingService]:
    return _recording_service