# OCR Table Toolkit

Two internship prototypes by Mehmet Eray Ozdemir for extracting structured
information from table images: an editable OCR-to-enum tool and a web application
that combines a trained detection model with OCR to export CSV files.

| Application | Approach | Output |
| --- | --- | --- |
| [OCR Enumerator](ocr-enumerator/README.md) | EasyOCR, image preprocessing, heuristic row/column reconstruction, manual editing | C enum and text mappings |
| [TableAI Web](table-ai-web/README.md) | YOLO detection checkpoint, EasyOCR on detected regions, grid reconstruction | Detection overlay and CSV |

These are separate applications within the same body of OCR work. The available
Enumerator implementation does not train or load the YOLO checkpoint.

## Project structure

```text
ocr-enumerator/
  app/                 # API, OCR engine, editable browser interface
  examples/            # Synthetic table generator and reference enum
  requirements.txt
table-ai-web/
  app.py               # Detection, OCR, table reconstruction and web interface
  model/best.pt        # Preserved checkpoint
  requirements.txt
  MODEL.md             # Provenance and missing training artifacts
```

## Getting started

Follow the README for the application you want to run. Each has its own virtual
environment and dependency list; use ports 8000 and 8001 to run both together.
Both are intended for local use. EasyOCR may download recognition weights on its
first startup. No hosted demonstration or external OCR API is provided.

## Model training and available evidence

The author reports training a model during the OCR project and using it in
TableAI Web. The preserved checkpoint contains references to `yolov8n.pt`,
`dataset/data.yaml`, and a historical `TableAI/runs/detect/train` directory.
These were inspected as archive metadata without loading/executing the model.

The training script/notebook, dataset, annotations and evaluation report are not
available in this archive. Training cannot be reproduced from this repository,
and no accuracy figures or verified training hyperparameters are claimed.
See [model notes](table-ai-web/MODEL.md).

## Portfolio preparation status

- Setup paths and documentation have been cleaned up. A fallback OCR step
  recovers isolated digits missed by text detection.
- Existing sample documents and generated image/CSV outputs were excluded.
  A synthetic example generator is provided instead.
- TableAI Web startup, checkpoint loading, image upload and CSV generation were
  checked on macOS ARM64 / Python 3.12 on 2026-09-07. The synthetic image produced
  incomplete cell recognition; this is an operation check, not an accuracy benchmark.
- Installed TableAI versions are recorded in its `requirements-tested-macos-arm64.txt`.
  OCR Enumerator itself still awaits an end-to-end check.
- A six-row, three-column reference table produced all 18 expected cells after
  the isolated-digit fix. Synthetic digit and empty-cell regression tests pass.

## Attribution and release

Developed during an internship and shared by the author as a portfolio project.
No project license is assigned;
third-party dependencies retain their own licenses. No safety-standard
compliance or production-readiness claim is made.
