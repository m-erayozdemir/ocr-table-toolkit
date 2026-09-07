# OCR Table Toolkit

Two Python applications for converting table images into structured data and C
enumerations. Developed by Mehmet Eray Ozdemir during an internship, the project
explores both OCR-based table reconstruction and custom model-assisted cell detection.

## Applications

| Application | Workflow | Output |
| --- | --- | --- |
| [OCR Enumerator](ocr-enumerator/README.md) | Recognize text, reconstruct a table, review cells and select columns | C enum and text mappings |
| [TableAI Web](table-ai-web/README.md) | Detect cells with YOLO, read their contents with EasyOCR and reconstruct a grid | Annotated image and CSV |

**Technologies:** Python, FastAPI, OpenCV, EasyOCR, Ultralytics YOLO, NumPy,
JavaScript and HTML/CSS.

## Key capabilities

- Image preprocessing and geometric row/column reconstruction.
- Editable OCR results with low-confidence cells highlighted for review.
- Custom-trained detection checkpoint integrated into a web upload workflow.
- Direct cell recognition fallback for isolated characters missed by text detection.
- Synthetic input generation and regression checks for isolated digits and blank cells.

## Getting started

Each application has its own dependencies and launch instructions:

- [Run OCR Enumerator](ocr-enumerator/README.md#run-locally)
- [Run TableAI Web](table-ai-web/README.md#run-locally)

Both run locally. EasyOCR may download recognition weights on first startup.
The applications are independent; OCR Enumerator does not require the YOLO model.

## Model and repository contents

The YOLO checkpoint trained during the OCR project is included at
`table-ai-web/model/best.pt`. The training code, dataset and evaluation report
are no longer available, so this repository supports inference rather than
reproducing training. See [model documentation](table-ai-web/MODEL.md).

```text
ocr-enumerator/
  app/          API, OCR engine and editable web interface
  examples/     Synthetic input generator and reference enum
table-ai-web/
  app.py        Detection, OCR, grid reconstruction and CSV export
  model/        Trained detection checkpoint
  tests/        OCR regression checks
```

## Validation and limitations

TableAI Web was checked on macOS ARM64 with Python 3.12: model loading, image
upload and CSV generation worked. A six-row, three-column reference table
produced all 18 expected cells after the isolated-digit fix. Synthetic digit and
blank-cell regression tests passed. The installed package versions are recorded
in `table-ai-web/requirements-tested-macos-arm64.txt`.

These checks are not an accuracy benchmark. Complex layouts, merged cells and
poor image quality can affect extraction. OCR Enumerator's complete UI workflow
has not been revalidated in this release. Review extracted values before use;
the application READMEs describe component-specific limitations.

## Author

Mehmet Eray Ozdemir. Published as an internship portfolio project.
Third-party components retain their respective licenses; no project-wide license
has been assigned.
