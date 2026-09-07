# TableAI Web

A FastAPI prototype that detects table regions with a YOLO checkpoint, applies
EasyOCR to the detected crops, reconstructs rows/columns, and offers a CSV download
with an annotated image showing the detected boxes.

## Run locally

Run these commands from `table-ai-web/` using a Python environment supported by
Ultralytics and EasyOCR/PyTorch. The verified environment uses Python 3.12 on macOS ARM64.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8001
```

On Windows, activate using `.venv\Scripts\activate`.
Open http://127.0.0.1:8001, upload a clear table image, select **Extract table**,
and review the detected regions and downloaded CSV.

The checkpoint must be at `model/best.pt`; it is included in this repository.
EasyOCR runs in English on CPU and may download its own weights at startup.
The application uses EasyOCR for text recognition; Tesseract is not required.
Startup, model loading, image upload and CSV generation were checked on macOS
ARM64 with Python 3.12. Following the isolated-digit recognition fix, a six-row,
three-column reference table produced all 18 expected cells. Synthetic digit and
blank-cell regression tests passed. These checks are not an accuracy benchmark.
Package versions are recorded in `requirements-tested-macos-arm64.txt`.

## Example input

The sibling application includes `../ocr-enumerator/examples/generate_sample.py`.
Run it in the Enumerator environment, then upload the generated PNG here.
The example is synthetic and is intended for exploration; the generated enum
reference belongs to Enumerator. It is not an expected CSV output or an accuracy benchmark.

## Processing

1. Decode the uploaded image with OpenCV.
2. Run `model/best.pt` at a detection confidence threshold of 0.45.
3. Filter small boxes and merge overlapping detections (threshold 0.30).
4. Group detections into rows and infer column positions.
5. Read each crop with EasyOCR and save an overlay and CSV in `static/tmp/`.

`POST /predict` takes a multipart field named `file` and returns the results page.
Generated files are served through `/static/tmp/` and excluded from Git. Delete
that directory when you no longer need its outputs; it is recreated at startup.

## Known limitations

- The original grid algorithm can fail when all detected rows contain fewer
  than two cells, and uses the first row to determine reference positions.
  Incomplete or merged rows can cause incorrect alignment.
- Recognized text segments are joined. If text detection misses an isolated
  character, the cell interior is recognized directly with a confidence filter.
  This improves isolated digits but does not guarantee recognition accuracy.
- No accuracy benchmark, cross-platform compatibility matrix or training
  reproduction is included. See [MODEL.md](MODEL.md).
- Upload size is not bounded at the application layer. Processing is synchronous;
  there is no authentication, output expiry, or multi-user isolation. Use locally.
- CSV contains recognized text without spreadsheet formula neutralization.
  Review the data before opening untrusted input in spreadsheet software.

The portfolio copy removes an unused Tesseract configuration and an unused
download route; the UI uses static output links. File locations are resolved
relative to the application file rather than the shell's working directory.
