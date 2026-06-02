"""Debug YOLO26 ONNX output format."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from src.engine.person_yolo_onnx_engine import PersonYoloOnnxEngine

eng = PersonYoloOnnxEngine(str(ROOT / "assets/yolo26n.onnx"), provider="cpu")
eng.setup()

h, w = 720, 1280
blank = np.full((h, w, 3), 114, dtype=np.uint8)
blob, ratio, pad, ow, oh = eng._preprocess(blank)
out = eng.engine.run(None, {eng.metadata[0].input_name: blob})[0][0]
print("ratio", ratio, "pad", pad, "orig", ow, oh, "input", eng.img_shape)
print("out shape", out.shape, "max score", float(out[:, 4].max()))

for thr in (0.01, 0.25, 0.51):
    rows = out[out[:, 4] >= thr]
    print(f"thr={thr} count={len(rows)}")
    if len(rows):
        print(rows[:5])

r = eng.predict([blank], conf=0.51, nms=0.45)[0]
print("parsed blank:", len(r.boxes), r.boxes, r.scores)

# synthetic person-like blob center
img = np.full((720, 1280, 3), 114, dtype=np.uint8)
cv2 = __import__("cv2")
cv2.rectangle(img, (500, 200), (780, 620), (80, 80, 80), -1)
blob, ratio, pad, ow, oh = eng._preprocess(img)
out = eng.engine.run(None, {eng.metadata[0].input_name: blob})[0][0]
pos = out[out[:, 4] >= 0.25]
print("synthetic rows>=0.25", len(pos))
if len(pos):
    print(pos[:5])
r2 = eng.predict([img], conf=0.25, nms=0.45)[0]
print("parsed synthetic:", len(r2.boxes), r2.boxes, r2.scores)

# letterbox sanity: fake detection in model space
ratio, pad = 0.5, (0.0, 140.0)
x1, y1, x2, y2 = eng._letterbox_to_orig(
    np.array([320.0]),
    np.array([300.0]),
    np.array([400.0]),
    np.array([520.0]),
    ratio,
    pad,
    1280,
    720,
)
print("letterbox test center box:", int(x1[0]), int(y1[0]), int(x2[0]), int(y2[0]))
