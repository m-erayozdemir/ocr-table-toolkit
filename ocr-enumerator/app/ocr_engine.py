# app/ocr_engine.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple
import numpy as np
import cv2
import easyocr
import re

# EasyOCR (CPU)
try:
    _reader = easyocr.Reader(['en','tr'], gpu=False, verbose=False)
except Exception:
    _reader = easyocr.Reader(['en','tr'], gpu=False, verbose=False)

# -------- helpers --------
def _ensure_bgr(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img

def _preprocess_variants(img_bgr: np.ndarray) -> List[np.ndarray]:
    out: List[np.ndarray] = []
    img = _ensure_bgr(img_bgr)
    h, w = img.shape[:2]

    # ölçek
    if max(h, w) < 1800:
        s = 1800.0 / max(h, w)
        img1 = cv2.resize(img, (int(w*s), int(h*s)), interpolation=cv2.INTER_CUBIC)
    else:
        img1 = img.copy()
    out.append(img1)

    # kontrast/keskinlik + hafif morfoloji
    gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)
    sharp = cv2.addWeighted(clahe, 1.6, cv2.GaussianBlur(clahe, (0,0), 1.0), -0.6, 0)
    kernel = np.ones((2,2), np.uint8)
    sharp2 = cv2.morphologyEx(sharp, cv2.MORPH_CLOSE, kernel, iterations=1)
    out.append(cv2.cvtColor(sharp2, cv2.COLOR_GRAY2BGR))

    # ikili + tersleme kontrolü
    _, th = cv2.threshold(sharp2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # metin/çizgiler koyu ise beyaza çevir ki morfoloji ile çıkarabilelim
    if np.mean(th) > 127:  # arka plan açık ise çizgiler siyah demektir
        th = cv2.bitwise_not(th)
    out.append(cv2.cvtColor(th, cv2.COLOR_GRAY2BGR))
    return out

def _median(vals):
    if not vals: return 0.0
    s = sorted(vals); n = len(s); m = n//2
    return s[m] if n%2 else (s[m-1]+s[m])/2.0

def _group_rows(cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not cells: return []
    heights = [(c["bbox"][3]-c["bbox"][1]) for c in cells]
    y_tol = max(10, int(_median(heights) * 0.6))
    rows: List[Dict[str, Any]] = []
    for c in cells:
        x1,y1,x2,y2 = c["bbox"]
        cy = (y1+y2)//2
        placed = False
        for r in rows:
            if abs(r["cy"]-cy) <= y_tol:
                r["cells"].append(c); r["cy"]=(r["cy"]+cy)//2; placed=True; break
        if not placed:
            rows.append({"cy": cy, "cells":[c]})
    for r in rows:
        r["cells"].sort(key=lambda z:(z["bbox"][0], z["bbox"][1]))
    rows.sort(key=lambda r:r["cy"])
    return rows

def _merge_inline(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not words: return []
    merged = [words[0].copy()]
    for c in words[1:]:
        a = merged[-1]
        x1,y1,x2,y2 = a["bbox"]; X1,Y1,X2,Y2 = c["bbox"]
        same_row = abs(((y1+y2)//2) - ((Y1+Y2)//2)) <= max(6, int((y2-y1)*0.5))
        gap = X1 - x2
        if same_row and 0 <= gap <= 6:  # daha dar: farklı sütunlar birleşmesin
            a["text"] = (a["text"] + " " + c["text"]).strip()
            a["confidence"] = float(min(a["confidence"], c["confidence"]))
            a["bbox"] = [x1, min(y1,Y1), max(x2,X2), max(y2,Y2)]
        else:
            merged.append(c.copy())
    return merged

# ---- başlıklardan kolon merkezleri
_HEADER_HINTS = [
    re.compile(r"\bindex\b", re.I),
    re.compile(r"\bvariable\b|\bvar\b", re.I),
    re.compile(r"\bvalue\b|\bval\b", re.I),
]
def _centers_from_headers(cells: List[Dict[str, Any]]) -> List[float]:
    xs = []
    for c in cells:
        txt = (c.get("text") or "").strip()
        for pat in _HEADER_HINTS:
            if pat.search(txt):
                x1,y1,x2,y2 = c["bbox"]
                xs.append((x1+x2)/2.0)
                break
    if not xs: return []
    xs.sort()
    centers: List[float] = []
    cur = xs[0]; cnt = 1
    for x in xs[1:]:
        if abs(x-cur) <= 20:
            cur = (cur*cnt + x)/(cnt+1); cnt += 1
        else:
            centers.append(cur); cur = x; cnt = 1
    centers.append(cur)
    return centers

# ---- dikey çizgilerden kolon merkezleri (düzenlendi)
def _centers_from_vertical_lines(img_bgr: np.ndarray) -> List[float]:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    # çizgiler beyaz olsun
    if np.mean(bw) > 127:  # arka plan açık
        bw = 255 - bw
    h, w = bw.shape
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h//20)))
    vlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk, iterations=1)

    colsum = vlines.sum(axis=0).astype(np.float32)
    if colsum.max() <= 0:
        return []
    colsum /= colsum.max()

    # güçlü dikey çizgi bölgeleri
    mask = (colsum > 0.4).astype(np.uint8)
    xs = []
    i = 0
    while i < w:
        if mask[i]:
            j = i
            while j < w and mask[j]:
                j += 1
            xs.append((i + j - 1) / 2.0)  # blok merkezi
            i = j
        else:
            i += 1
    if len(xs) >= 4:
        centers = [ (xs[i] + xs[i+1]) / 2.0 for i in range(len(xs)-1) ]
        # dış kenarların ortalarını çıkar (çok fazlaysa)
        while len(centers) > 6:
            centers = centers[1:-1]
        return centers
    return []

def _cluster_columns_x(xs: List[float]) -> List[float]:
    if not xs: return []
    xs = sorted(xs)
    comp = [xs[0]]
    for x in xs[1:]:
        if abs(x - comp[-1]) > 8:
            comp.append(x)
    if len(comp) <= 2:
        return comp
    diffs = [comp[i+1]-comp[i] for i in range(len(comp)-1)]
    med = _median(diffs) or 1.0
    cuts = [i for i,d in enumerate(diffs) if d > 1.3*med]
    centers: List[float] = []
    start = 0
    for cut in cuts + [len(comp)-1]:
        block = comp[start:cut+1]
        centers.append(float(sum(block)/len(block)))
        start = cut+1
    if len(centers) < 2 and len(comp) >= 2:
        i = int(np.argmax(diffs))
        left = comp[:i+1]; right = comp[i+1:]
        if left and right and (right[0]-left[-1]) > 30:
            centers = [float(sum(left)/len(left)), float(sum(right)/len(right))]
    return centers

# ---- K-Means fallback (k=3) ----
def _centers_kmeans(xs: List[float], k: int) -> List[float]:
    if len(xs) < k: 
        return []
    data = np.float32(np.array(xs).reshape(-1,1))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.5)
    _ret, _labels, centers = cv2.kmeans(data, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    cs = sorted([float(c[0]) for c in centers])
    return cs

def _kmeans_best_k(xs: List[float], kmin: int = 2, kmax: int = 5) -> List[float]:
    best = []
    best_gap = -1.0
    kmax = min(kmax, max(kmin, len(xs)))  # veri kadar küme
    for k in range(kmin, kmax + 1):
        cs = _centers_kmeans(xs, k)
        if len(cs) < k:
            continue
        gaps = np.diff(cs)
        gap = float(gaps.min()) if len(gaps) else 0.0
        # min aralık ne kadar büyükse kümeler o kadar ayrık
        if gap > best_gap:
            best_gap = gap
            best = cs
    return best

# -------- public: tüm tabloyu çıkart --------
def extract_table(img_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Dönen yapı:
    { "columns": N, "rows": [[{"text":str,"conf":float}, ...] ...] }
    """
    if img_bgr is None or not isinstance(img_bgr, np.ndarray):
        raise RuntimeError("Invalid image input")

    for variant in _preprocess_variants(img_bgr):
        # OCR
        res = _reader.readtext(variant, detail=1, paragraph=False)
        cells: List[Dict[str, Any]] = []
        for it in res:
            if not isinstance(it, (list, tuple)) or len(it) < 3:
                continue
            pts, text, conf = it[0], (it[1] or "").strip(), float(it[2] or 0.0)
            if not text:
                continue
            try:
                pts = np.array(pts).reshape(-1,2)
                xs, ys = pts[:,0], pts[:,1]
                x1,y1,x2,y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            except Exception:
                continue
            cells.append({"text": text, "confidence": conf, "bbox": [x1,y1,x2,y2]})

        if not cells:
            continue

        rows = _group_rows(cells)
        if not rows:
            continue

        flat_cells = [c for r in rows for c in r["cells"]]

        # 1) başlıklardan
        centers = _centers_from_headers(flat_cells)

        # 2) dikey çizgilerden
        if len(centers) < 3:
            centers = _centers_from_vertical_lines(variant)

        # 3) metin merkezlerinden kümleme
        all_xc = [ (c["bbox"][0]+c["bbox"][2])/2.0 for c in flat_cells ]
        if len(centers) < 3:
            centers = _cluster_columns_x(all_xc)

        # 4) K-Means (k=3) fallback
        if len(centers) < 3 and len(all_xc) >= 6:
            km = _centers_kmeans(all_xc, k=3)
            if km:
                centers = km

        if not centers:
            continue

        centers = sorted(centers)
        
        flat_cells = [c for r in rows for c in r["cells"]]

        # 1) başlıklardan
        centers = _centers_from_headers(flat_cells)

        # 2) dikey çizgilerden
        if len(centers) < 2:
            centers = _centers_from_vertical_lines(variant)

        # 3) metin merkezlerinden kümleme
        all_xc = [ (c["bbox"][0]+c["bbox"][2])/2.0 for c in flat_cells ]
        if len(centers) < 2:
            centers = _cluster_columns_x(all_xc)

        # 4) K-Means: k=2..5 arasında en iyi ayrımı seç (gerçekten dinamik)
        if len(centers) < 2 and len(all_xc) >= 4:
            km = _kmeans_best_k(all_xc, kmin=2, kmax=5)
            if km:
                centers = km

        if not centers:
            continue

        centers = sorted(centers)
        # DİKKAT: Artık 3'e ZORLAMA YOK
        K = max(2, len(centers))


        K = max(2, len(centers))

        # satırları matrise dök
        table_rows: List[List[Dict[str, Any]]] = []
        for r in rows:
            merged = _merge_inline(r["cells"])
            row = [ {"text":"", "conf":0.0} for _ in range(K) ]
            for c in merged:
                xc = (c["bbox"][0]+c["bbox"][2])/2.0
                j = int(np.argmin([abs(xc - m) for m in centers]))
                if not row[j]["text"]:
                    row[j] = {"text": c["text"], "conf": float(c["confidence"])}
            if any(cell["text"] for cell in row):
                table_rows.append(row)

        if table_rows:
            return {"columns": K, "rows": table_rows}

    raise RuntimeError("No text detected")
