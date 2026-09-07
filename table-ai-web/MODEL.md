# Preserved detection model

- File: `model/best.pt`
- File size: 6,256,426 bytes
- Used by: `app.py` via Ultralytics `YOLO`, followed by EasyOCR on detected crops.
- Trained by Mehmet Eray Ozdemir during the internship OCR project and
  integrated into TableAI Web.
- Checkpoint strings include `yolov8n.pt`, `dataset/data.yaml`, and a historical
  `TableAI/runs/detect/train` output directory. This is provenance evidence, not
  a verified reconstruction of the training environment.

## Missing artifacts

Training scripts/notebooks, source dataset, annotations, split definitions,
evaluation results are unavailable. A tested inference environment is recorded
in `requirements-tested-macos-arm64.txt`. The precise
training procedure, metrics and dataset redistribution rights cannot be
established from the current source archive.

The checkpoint was copied unchanged. Its binary metadata contains a historical
local filesystem path; the checkpoint is preserved as supplied. It was successfully loaded and used
for table extraction on macOS ARM64 / Python 3.12 in the verified inference environment.
