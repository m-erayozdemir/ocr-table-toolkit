from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO
from pathlib import Path
import numpy as np
import cv2, csv, uuid
import easyocr
reader = easyocr.Reader(['en'], gpu=False)


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "static" / "tmp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="TableAI Web")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

MODEL_PATH = BASE_DIR / "model" / "best.pt"
model = YOLO(str(MODEL_PATH))

def page(html_body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>TableAI</title>"
        "<style>body{font-family:-apple-system,Arial;margin:24px;max-width:1100px}"
        "button{padding:6px 12px} img{max-width:100%}</style></head><body>"
        "<h2>TableAI</h2>"
        "<form action='/predict' method='post' enctype='multipart/form-data' style='margin:12px 0'>"
        "<input type='file' name='file' accept='image/*' required> "
        "<button type='submit'>Extract table</button></form>"
        f"{html_body}</body></html>"
    )

def results_to_boxes(res):
    out = []
    r = res[0]
    if r.boxes is None:
        return out
    xyxy = r.boxes.xyxy.cpu().numpy()
    conf = r.boxes.conf.cpu().numpy()
    for (x1,y1,x2,y2), c in zip(xyxy, conf):
        out.append([int(x1), int(y1), int(x2), int(y2), float(c)])
    return out

def iou(a, b):
    ax1,ay1,ax2,ay2 = a; bx1,by1,bx2,by2 = b
    ix1,iy1 = max(ax1,bx1), max(ay1,by1)
    ix2,iy2 = min(ax2,bx2), min(ay2,by2)
    iw,ih = max(0, ix2-ix1), max(0, iy2-iy1)
    inter = iw*ih
    ua = (ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter
    return inter/ua if ua > 0 else 0

def nms_merge(boxes, thr=0.30):
    boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
    keep = []
    for b in boxes:
        merged = False
        for k in keep:
            if iou(b[:4], k[:4]) > thr:
                k[0] = min(k[0], b[0]); k[1] = min(k[1], b[1])
                k[2] = max(k[2], b[2]); k[3] = max(k[3], b[3])
                k[4] = max(k[4], b[4])
                merged = True
                break
        if not merged:
            keep.append(b.copy())
    return keep

def cluster_rows(boxes, y_overlap_thr=0.30):
    """
    Satırları, kutuların dikey aralıklarının örtüşmesine göre band'lere ayırır.
    y_overlap_thr: aynı satır sayılmak için dikey IoU eşiği.
    """
    if not boxes:
        return []

    # y1'e göre sırala
    order = sorted(range(len(boxes)), key=lambda i: boxes[i][1])
    bands = []  # her band: dict(y_min, y_max, indices)

    for i in order:
        x1,y1,x2,y2,_ = boxes[i]
        placed = False
        for band in bands:
            # dikey IoU
            inter = max(0, min(y2, band["y_max"]) - max(y1, band["y_min"]))
            h_union = (y2 - y1) + (band["y_max"] - band["y_min"]) - inter
            iou_v = inter / h_union if h_union > 0 else 0.0
            if iou_v >= y_overlap_thr:
                band["y_min"] = min(band["y_min"], y1)
                band["y_max"] = max(band["y_max"], y2)
                band["indices"].append(i)
                placed = True
                break
        if not placed:
            bands.append({"y_min": y1, "y_max": y2, "indices": [i]})

    # band'leri yukarıdan aşağı sırala ve satır içini soldan sağa sırala
    rows_idx = []
    bands.sort(key=lambda b: b["y_min"])
    for band in bands:
        idxs = band["indices"]
        idxs.sort(key=lambda j: (boxes[j][0]+boxes[j][2])/2.0)
        rows_idx.append(idxs)

    return rows_idx

def build_grid(boxes, y_tol_factor=0.30):
    rows_idx = cluster_rows(boxes, y_tol_factor)
    if not rows_idx:
        return []

    row_cells = []
    for idxs in rows_idx:
        row = [boxes[i] for i in idxs]
        row.sort(key=lambda b: (b[0]+b[2])/2)
        row_cells.append(row)

    lengths = [len(r) for r in row_cells]
    lengths = [l for l in lengths if 2 <= l <= max(lengths)]
    from statistics import mode
    num_cols = mode(lengths)

    ref_row = row_cells[0]
    ref_centers = [(b[0]+b[2])/2 for b in ref_row]

    grid = []
    for r in row_cells:
        centers = [(b[0]+b[2])/2 for b in r]
        row = [None] * num_cols

        for b, xc in zip(r, centers):
            c_idx = int(np.argmin([abs(xc - rc) for rc in ref_centers]))
            if c_idx >= num_cols: c_idx = num_cols - 1
            if c_idx < 0: c_idx = 0

            if row[c_idx] is None:
                row[c_idx] = {"bbox": b[:4]}
            else:
                placed = False
                for k in range(c_idx+1, num_cols):
                    if row[k] is None:
                        row[k] = {"bbox": b[:4]}; placed = True; break
                if not placed:
                    for k in range(c_idx-1, -1, -1):
                        if row[k] is None:
                            row[k] = {"bbox": b[:4]}; placed = True; break
                if not placed:
                    pass

        grid.append(row)

    return grid

def ocr_text(img, bbox):
    x1,y1,x2,y2 = bbox
    pad = 4
    x1 = max(0, x1 - pad); y1 = max(0, y1 - pad)
    x2 = min(img.shape[1], x2 + pad); y2 = min(img.shape[0], y2 + pad)
    crop = img[y1:y2, x1:x2]

    if crop.size == 0:
        return ""

    results = reader.readtext(crop, detail=0)
    if results:
        text = " ".join(part.strip() for part in results if part.strip())
    else:
        # A detector can miss isolated characters such as 0 and 1. YOLO has
        # already located the cell, so recognize its interior directly.
        bx1, by1, bx2, by2 = bbox
        inset = max(2, min(8, int(min(bx2 - bx1, by2 - by1) * 0.08)))
        interior = img[max(0, by1 + inset):min(img.shape[0], by2 - inset),
                       max(0, bx1 + inset):min(img.shape[1], bx2 - inset)]
        if interior.size == 0:
            return ""
        gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY)
        # Avoid asking the recognizer to invent text in a uniform blank cell.
        if float(gray.std()) < 5:
            return ""
        recognized = reader.recognize(gray, detail=1)
        text = " ".join(str(value).strip() for _, value, confidence in recognized
                        if float(confidence) >= 0.5 and str(value).strip())

    # küçük düzeltmeler
    text = text.replace("  ", " ").strip()
    return text

def save_overlay(img, boxes, texts, out_path):
    vis = img.copy()
    for i, b in enumerate(boxes):
        x1,y1,x2,y2,_ = b
        cv2.rectangle(vis, (x1,y1), (x2,y2), (0,128,255), 2)
    cv2.imwrite(out_path, vis)

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(page(""))

@app.post("/predict", response_class=HTMLResponse)
async def predict(file: UploadFile = File(...)):
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return HTMLResponse(page("<p style='color:#b00'>The image could not be decoded.</p>"), status_code=400)

    res = model(img, conf=0.45)
    boxes = results_to_boxes(res)

    H, W = img.shape[:2]
    min_area = max(80, int(0.00008 * W * H))
    boxes = [b for b in boxes if (b[2]-b[0]) * (b[3]-b[1]) >= min_area]

    boxes = nms_merge(boxes, thr=0.30)
    grid = build_grid(boxes)

    rows = []
    for row in grid:
        new_row = []
        for cell in row:
            if cell is None:
                new_row.append("")
            else:
                new_row.append(ocr_text(img, cell["bbox"]))
        rows.append(new_row)


    uid = uuid.uuid4().hex[:6]
    out_img = f"static/tmp/out_{uid}.jpg"
    out_csv = f"static/tmp/table_{uid}.csv"

    save_overlay(img, boxes, [], str(BASE_DIR / out_img))

    with open(BASE_DIR / out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(r)

    body = (
        f"<h3>Result</h3><img src='/{out_img}' alt='Detected table cells'>"
        f"<p><a href='/{out_csv}' download>Download CSV</a></p>"
        "<p style='color:#555;font-size:13px'>Review the CSV for recognition and column alignment errors.</p>"
    )
    return HTMLResponse(page(body))
