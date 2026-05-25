"""Скачивание ONNX-моделей в assets/ (YOLOX + MobileFaceNet + buffalo_l)."""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

YOLOX_URL = (
    "https://github.com/ruhyadi/vision-fr/releases/download/v1.0.0/yoloxs_face.onnx"
)
MBF_URL = (
    "https://github.com/ruhyadi/vision-fr/releases/download/v1.0.0/w600k_mbf.onnx"
)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"Уже есть: {dest} ({dest.stat().st_size // 1024 // 1024} MB)")
        return
    print(f"Скачивание {dest.name}...")
    urllib.request.urlretrieve(url, dest)
    print(f"  готово: {dest} ({dest.stat().st_size // 1024 // 1024} MB)")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    download(YOLOX_URL, ASSETS / "yoloxs_face.onnx")
    download(MBF_URL, ASSETS / "w600k_mbf.onnx")

    print("buffalo_l...")
    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "download_buffalo_l.py")],
        check=True,
        cwd=str(ROOT),
    )
    print("Все модели в assets/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
