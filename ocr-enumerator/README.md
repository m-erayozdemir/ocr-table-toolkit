# OCR Enumerator

A local web prototype that turns a table image into an editable table, then
generates a C enum and plain-text mappings from two selected columns.
Developed as an internship project by Mehmet Eray Ozdemir.

## Features

- English and Turkish text recognition with EasyOCR on CPU.
- OpenCV preprocessing and heuristic row/column reconstruction.
- Editable recognized cells; confidence below 0.85 is highlighted for review.
- User-selected right-to-left column mapping for C enum and text generation.
- Browser clipboard buttons for both outputs.

## Run locally

Run the following commands from the `ocr-enumerator/` directory.

Use a Python environment supported by EasyOCR/PyTorch (Python 3.11 is a starting
point, not a verified compatibility guarantee for this repository).

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows, activate with `.venv\Scripts\activate` instead.
Open http://127.0.0.1:8000. EasyOCR initializes at startup and may download model
weights on first use, requiring internet access. Subsequent OCR runs use the
local model. No API key or external OCR service is configured.

Dependencies are unpinned. The complete OCR and editing workflow has not been
revalidated for this release.

## Synthetic example

With the environment activated:

```sh
python examples/generate_sample.py
```

1. Upload `examples/sample-table.png` and select **Extract**.
2. Review every cell and correct recognition or column placement errors.
3. Choose the numeric column as **Left** and the state-name column as **Right**.
4. Select **Generate outputs** and copy the C enum or text.

`examples/expected-enum.c` is the intended result after manual review, not a
measured OCR output. The sample uses fictional state names and no company data.

## How it works

`app/main.py` serves the page and receives images at `POST /api/extract`.
`app/ocr_engine.py` preprocesses images, recognizes text, groups rows, and infers
columns from header hints, vertical lines, text positions, and clustering.
`app/static/script.js` renders the editable table and creates output in the browser.

The API accepts a multipart field named `file` and returns `table.headers`,
`table.rows` (cells with `text` and `conf`), and `min_conf`.

## Limitations

- Prototype for a single, reasonably clear table in a PNG/JPEG image; no PDF input.
- Column inference is heuristic. Merged cells, skew, sparse text, and complex
  layouts can produce missing or incorrectly assigned cells.
- Original header rows are not automatically removed. Clear both selected cells
  on any unwanted row before generating output.
- Enum generation does not validate C identifiers or numeric values. Duplicate
  names overwrite earlier entries in the enum mapping. Review before compiling.
- Confidence is a review aid, not a correctness guarantee. No accuracy benchmark
  or safety-standard compliance claim is made.
- Image processing is synchronous, and uploads have no application-level size
  limit. Run locally; authentication and public-service hardening are not included.

## Publication status

Shared by the author as part of the OCR Table Toolkit portfolio project.
No license grant is included.
Company documents, caches, and runtime outputs are not needed for this example.
