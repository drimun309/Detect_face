"""Скачивание ONNX-моделей в assets/ (лица + YOLO26 + buffalo_l)."""

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
YOLO26_PT_URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"
YOLOV8S_PT_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"Уже есть: {dest} ({dest.stat().st_size // 1024 // 1024} MB)")
        return
    print(f"Скачивание {dest.name}...")
    urllib.request.urlretrieve(url, dest)
    print(f"  готово: {dest} ({dest.stat().st_size // 1024 // 1024} MB)")


def export_yolo26_onnx(dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"Уже есть: {dest} ({dest.stat().st_size // 1024 // 1024} MB)")
        return
    pt_path = dest.with_suffix(".pt")
    download(YOLO26_PT_URL, pt_path)
    try:
        from ultralytics import YOLO
    except Exception as exc:
        raise RuntimeError(
            "Для экспорта YOLO26 нужен ultralytics: py -3.12 -m pip install ultralytics"
        ) from exc

    print("Экспорт YOLO26n в ONNX...")
    model = YOLO(str(pt_path))
    model.export(format="onnx", opset=12, simplify=False, dynamic=False, imgsz=640)
    exported = pt_path.with_suffix(".onnx")
    if exported.exists() and exported.resolve() != dest.resolve():
        dest.write_bytes(exported.read_bytes())
    if not dest.exists():
        raise RuntimeError(f"Не удалось получить {dest}")
    print(f"  готово: {dest} ({dest.stat().st_size // 1024 // 1024} MB)")


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    download(YOLOX_URL, ASSETS / "yoloxs_face.onnx")
    download(MBF_URL, ASSETS / "w600k_mbf.onnx")
    download(YOLOV8S_PT_URL, ASSETS / "yolov8s.pt")
    export_yolo26_onnx(ASSETS / "yolo26n.onnx")

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
