"""Скачивание моделей InsightFace buffalo_l."""

from pathlib import Path

from huggingface_hub import hf_hub_download

FILES = ("det_10g.onnx", "w600k_r50.onnx")
REPO = "public-data/insightface"
OUT = Path("assets/buffalo_l")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = OUT / name
        if target.exists() and target.stat().st_size > 1000:
            print(f"Уже есть: {target}")
            continue
        print(f"Скачивание {name}...")
        path = hf_hub_download(
            repo_id=REPO,
            filename=f"models/buffalo_l/{name}",
            local_dir=str(OUT),
        )
        downloaded = Path(path)
        if downloaded.resolve() != target.resolve() and downloaded.exists():
            target.write_bytes(downloaded.read_bytes())
        print(f"  сохранено: {target} ({target.stat().st_size // 1024 // 1024} MB)")


if __name__ == "__main__":
    main()
