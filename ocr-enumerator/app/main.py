# app/main.py
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import numpy as np
import cv2

from .ocr_engine import extract_table  # paket içi import

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="OCR Enumerator")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

MIN_CONF = 0.85

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_title": "OCR Enumerator", "min_conf": MIN_CONF},
    )

@app.post("/api/extract")
async def api_extract(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image format")

        table = extract_table(image)
        return {
            "table": {
                "headers": [f"Col {i+1}" for i in range(table["columns"])],
                "rows": table["rows"],
            },
            "min_conf": MIN_CONF,
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})
