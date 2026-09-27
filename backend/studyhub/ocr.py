"""Reading text out of pictures: scanned PDF pages and photos of notes (EasyOCR, on the CPU).

Why EasyOCR and not Surya: EasyOCR is Apache-2.0, runs acceptably on a CPU, covers 80+ languages (English and Indian
scripts included) and needs no GPU; Surya is more accurate on dense layouts but is GPL-licensed and expects a GPU for
reasonable speed. Tesseract (pytesseract) is used as a fallback when it is installed and EasyOCR is not.

Rules the rest of the app relies on:
  * OCR is only used when a page has NO selectable text. Real text is never replaced by a guess.
  * OCR text is marked: the document says how many pages were read by OCR, and a warning asks the student to check quotes
    against the page image, because OCR can misread characters.
  * Work is bounded: at most STUDYHUB_OCR_MAX_PAGES pages per file (default 40), each rendered at ~200 dpi.
  * Nothing here talks to the network except EasyOCR's own one-time model download on first use.

STUDYHUB_OCR = auto | easyocr | tesseract | off   (auto: EasyOCR if installed, else Tesseract if installed, else off)
STUDYHUB_OCR_LANGS = comma list of EasyOCR language codes (default "en"), e.g. "en,hi" or "en,ta".
"""
from __future__ import annotations

import io
import logging
import os
import threading
from dataclasses import dataclass

log = logging.getLogger("studyhub.ocr")

IMAGE_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpeg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"BM": "bmp",
    b"II*\x00": "tiff",
    b"MM\x00*": "tiff",
}
MIME = {"png": "image/png", "jpeg": "image/jpeg", "gif": "image/gif", "bmp": "image/bmp", "tiff": "image/tiff", "webp": "image/webp"}
RENDER_SCALE = 2.8            # PDF points (1/72 in) -> ~200 dpi
MAX_SIDE = 3000               # a photo is shrunk to this many pixels on its longer side before reading

_lock = threading.Lock()
_reader = None
_engine: str | None = None
_failed: str | None = None


def image_kind(data: bytes) -> str | None:
    """'png' | 'jpeg' | ... when the bytes are a picture we can read, else None."""
    for magic, kind in IMAGE_MAGIC.items():
        if data.startswith(magic):
            return kind
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def max_pages() -> int:
    return int(os.environ.get("STUDYHUB_OCR_MAX_PAGES", "40"))


def langs() -> list[str]:
    return [x.strip() for x in os.environ.get("STUDYHUB_OCR_LANGS", "en").split(",") if x.strip()] or ["en"]


def _have(module: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(module) is not None


def engine() -> str | None:
    """Which OCR engine will be used, or None. Cheap: does not load any model."""
    want = os.environ.get("STUDYHUB_OCR", "auto").lower()
    if want == "off" or _failed:
        return None
    if want == "auto" and os.environ.get("PYTEST_CURRENT_TEST"):
        return None                                      # the test suite opts in explicitly (STUDYHUB_OCR=...)
    if want in ("auto", "easyocr") and _have("easyocr"):
        return "easyocr"
    if want in ("auto", "tesseract") and _have("pytesseract"):
        import shutil
        if shutil.which("tesseract"):
            return "tesseract"
    return None


def available() -> bool:
    return engine() is not None


def label() -> str:
    return {"easyocr": "EasyOCR", "tesseract": "Tesseract"}.get(engine() or "", "OCR")


def _load():
    global _reader, _engine, _failed
    eng = engine()
    if eng is None:
        return None
    if _reader is not None and _engine == eng:
        return _reader
    with _lock:
        if _reader is None or _engine != eng:
            try:
                if eng == "easyocr":
                    import easyocr
                    _reader = easyocr.Reader(langs(), gpu=os.environ.get("STUDYHUB_OCR_GPU", "0") == "1", verbose=False)
                else:
                    import pytesseract
                    _reader = pytesseract
                _engine = eng
            except Exception as e:                       # model download blocked, broken install
                _failed = f"{type(e).__name__}: {e}"
                log.warning("OCR off: %s could not be loaded (%s)", eng, _failed)
                return None
    return _reader


@dataclass
class OcrText:
    paragraphs: list[str]
    confidence: float | None          # mean word confidence 0..1 (EasyOCR), None when the engine does not say


def _prepare(img):
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(img)                   # phone photos carry their rotation in EXIF
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        s = MAX_SIDE / max(w, h)
        img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
    return img


def _headingish(line: str) -> bool:
    """A short stand-alone title line (all capitals, or a few capitalised words without a full stop)."""
    line = line.strip()
    words = line.split()
    if not line or len(line) > 60 or line.endswith((".", ",", ";", ":")) or len(words) > 8:
        return False
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 3 and (line == line.upper() or (len(words) <= 5 and all(w[:1].isupper() or not w[:1].isalpha() for w in words)))


def read_image(img) -> OcrText:
    """OCR one PIL image into paragraphs, in reading order."""
    reader = _load()
    if reader is None:
        return OcrText([], None)
    img = _prepare(img)
    if _engine == "easyocr":
        import numpy as np
        arr = np.array(img)
        lines = reader.readtext(arr, detail=1, paragraph=False)
        # group lines into paragraphs by vertical gaps; keep reading order top-to-bottom, left-to-right
        items = sorted(((min(p[1] for p in box), min(p[0] for p in box), max(p[1] for p in box), text, conf) for box, text, conf in lines),
                       key=lambda x: (round(x[0] / 12), x[1]))
        paras, cur, last_bottom, heights, confs = [], [], None, [], []
        for top, _left, bottom, text, conf in items:
            text = " ".join(str(text).split())
            if not text:
                continue
            confs.append(float(conf))
            h = max(1.0, bottom - top)
            heights.append(h)
            gap_limit = 0.8 * (sum(heights) / len(heights))
            heading = _headingish(text)
            if cur and (heading or _headingish(cur[-1]) or (last_bottom is not None and top - last_bottom > gap_limit)):
                paras.append(" ".join(cur))
                cur = []
            cur.append(text)
            last_bottom = bottom if last_bottom is None else max(last_bottom, bottom)
        if cur:
            paras.append(" ".join(cur))
        return OcrText(paras, round(sum(confs) / len(confs), 3) if confs else None)
    text = reader.image_to_string(img, lang="+".join({"en": "eng", "hi": "hin", "ta": "tam", "te": "tel", "kn": "kan", "ml": "mal", "bn": "ben", "mr": "mar"}.get(x, x) for x in langs()))
    paras = [" ".join(p.split()) for p in text.split("\n\n")]
    return OcrText([p for p in paras if p], None)


def read_image_bytes(data: bytes) -> OcrText:
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        return read_image(im)


def render_pdf_pages(data: bytes, page_numbers: list[int]):
    """Yield (page_number, PIL image) for the given 1-based pages, rendered with pdfium (no poppler needed)."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(data)
    try:
        for n in page_numbers:
            if 1 <= n <= len(pdf):
                page = pdf[n - 1]
                try:
                    yield n, page.render(scale=RENDER_SCALE, grayscale=True).to_pil()
                finally:
                    page.close()
    finally:
        pdf.close()


def ocr_pdf_pages(data: bytes, page_numbers: list[int]) -> tuple[dict[int, list[str]], float | None]:
    """{page: paragraphs} for pages with no selectable text, and the mean confidence. Bounded by max_pages()."""
    if not available() or not page_numbers or not _have("pypdfium2"):
        return {}, None
    out: dict[int, list[str]] = {}
    confs: list[float] = []
    for n, img in render_pdf_pages(data, page_numbers[: max_pages()]):
        r = read_image(img)
        if r.paragraphs:
            out[n] = r.paragraphs
        if r.confidence is not None:
            confs.append(r.confidence)
    return out, (round(sum(confs) / len(confs), 3) if confs else None)


def status() -> dict:
    return {"engine": engine(), "label": label() if engine() else None, "languages": langs(), "max_pages": max_pages(),
            "reason": None if engine() else (_failed or "no OCR engine is installed (pip install easyocr)")}
