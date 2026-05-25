import rootutils

ROOT = rootutils.setup_root(__file__, indicator=".project-root", pythonpath=True)

import numpy as np

from src.engine.arcface_onnx_engine import ArcfaceOnnxEngine
from src.engine.fr_onnx_engine import FrOnnxEngine

engine = FrOnnxEngine(
    det_engine_path="assets/buffalo_l/det_10g.onnx",
    rec_engine_path="assets/buffalo_l/w600k_r50.onnx",
    provider="cpu",
)
engine.setup()

img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
result = engine.predict([img], det_conf=0.3, det_nms=0.4)[0]
print(f"boxes={len(result.boxes)} embeddings={len(result.embeddings)}")
