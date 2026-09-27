"""Turn an uploaded file into text blocks with locators (page number, heading level).

Nothing here talks to a model or the network. The result is what the chunker cuts up and what every later citation
points back to, so the rule is: keep the words exactly as the document has them, and say so when something was lost
(a scanned PDF, pages with no text, a non-UTF-8 text file).

Files are recognised by their CONTENT, not their extension.
"""
from __future__ import annotations

import io
import logging
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePath

from . import ocr, settings

logging.getLogger("pypdf").setLevel(logging.ERROR)          # pypdf logs every oddity in a real-world PDF

MIN_TEXT_CHARS = 20                                          # fewer than this in a whole PDF: treat as scanned
MAX_UNZIPPED_BYTES = 100 * 1024 * 1024                       # zip-bomb guard for DOCX
MAX_ZIP_RATIO = 200


class ExtractError(ValueError):
    """The file cannot be used; the message is written for the student."""


@dataclass
class Block:
    text: str
    page: int | None = None
    level: int = 0                                           # 0 = paragraph, 1..6 = heading


@dataclass
class Extracted:
    kind: str                                                # txt | pdf | docx | image
    title: str
    blocks: list[Block] = field(default_factory=list)
    pages: int | None = None
    warnings: list[str] = field(default_factory=list)
    ocr_pages: int = 0                                       # pages whose text was read from the picture (OCR)

    @property
    def chars(self) -> int:
        return sum(len(b.text) for b in self.blocks)

    @property
    def status(self) -> str:
        return "parsed" if self.chars >= MIN_TEXT_CHARS else "empty"


# ------------------------------------------------------------------------------------------------ helpers

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​‌‍⁠﻿]")


def clean(text: str, *, compat: bool = False) -> str:
    """Normalise without changing wording. `compat` (PDF) also folds ligatures such as 'ﬁ' into 'fi'."""
    text = unicodedata.normalize("NFKC" if compat else "NFC", text)
    text = _CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    return text.replace(" ", " ")


def _title_from_name(filename: str) -> str:
    stem = PurePath((filename or "").replace("\\", "/")).stem
    return " ".join(stem.replace("_", " ").split())[:200] or "Untitled"


_MD_HEADING = re.compile(r"^(#{1,6})\s+(\S.*?)\s*#*\s*$")
_NUMBERED = re.compile(r"^(\d+(?:\.\d+){0,3})[.)]?\s+([A-Z][^\n]{2,78})$")


def _looks_like_heading(line: str) -> int:
    """Heading level 1..6 for a stand-alone line, or 0. Deliberately conservative."""
    line = line.strip()
    if not line or len(line) > 80 or line.endswith((".", ",", ";", ":")):
        return 0
    m = _MD_HEADING.match(line)
    if m:
        return len(m.group(1))
    m = _NUMBERED.match(line)
    if m:
        return m.group(1).count(".") + 1
    letters = [c for c in line if c.isalpha()]
    if len(letters) >= 3 and line == line.upper() and len(line.split()) <= 10:
        return 1
    return 0


def _heading_text(line: str) -> str:
    m = _MD_HEADING.match(line.strip())
    return (m.group(2) if m else line).strip()


def _paragraphs(text: str) -> list[str]:
    parts = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]
    return [p for p in parts if p]


# ---------------------------------------------------------------------------------------------------- TXT

def extract_txt(filename: str, data: bytes) -> Extracted:
    if b"\x00" in data:
        raise ExtractError("This file contains binary data, so it cannot be read as plain text.")
    warnings: list[str] = []
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
        warnings.append("The file is not UTF-8; it was read as Windows-1252, so a few characters may look wrong.")
    text = clean(text)
    blocks: list[Block] = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.split("\n") if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1 and (level := _looks_like_heading(lines[0])):
            blocks.append(Block(_heading_text(lines[0]), None, level))
            continue
        # A heading directly above its text with no blank line between ("## Title\ntext ...")
        if len(lines) > 1 and (level := _looks_like_heading(lines[0])) and _MD_HEADING.match(lines[0].strip()):
            blocks.append(Block(_heading_text(lines[0]), None, level))
            lines = lines[1:]
        body = " ".join(" ".join(ln.split()) for ln in lines)
        if body:
            blocks.append(Block(body))
    return Extracted("txt", _title_from_name(filename), blocks, None, warnings)


# ---------------------------------------------------------------------------------------------------- PDF

def _flatten_outline(reader, outline, level: int = 1, out: list | None = None) -> list[tuple[int, str, int]]:
    out = [] if out is None else out
    for item in outline:
        if isinstance(item, list):
            _flatten_outline(reader, item, level + 1, out)
            continue
        try:
            page = reader.get_destination_page_number(item) + 1
            title = " ".join(str(item.title).split())
        except Exception:                                    # a broken bookmark must not break the upload
            continue
        if title and page > 0:
            out.append((level, title[:120], page))
    return out


_GENERIC_BOOKMARK = re.compile(r"^(slide|page|pg|p|sheet|folio)\s*[-.:]?\s*\d+$", re.I)
SLIDE_TOPIC_MIN_CHARS = 1200                                 # a slide-deck topic gathers slides until it holds about this much text


def generic_outline(headings: dict[int, list[tuple[int, str]]]) -> bool:
    """True when the bookmarks are only numbers ("Slide 1", "Page 2"): what PowerPoint and some exporters write, and no help as topic names."""
    titles = [t for hs in headings.values() for _, t in hs]
    return bool(titles) and sum(1 for t in titles if _GENERIC_BOOKMARK.match(t.strip())) / len(titles) >= 0.6


def slide_title(raw: str) -> str | None:
    """The first line of a slide or page, when it reads like a title (short, has letters, not a number or a date)."""
    for line in raw.splitlines():
        line = " ".join(line.split())
        if not line:
            continue
        if 3 <= len(line) <= 90 and sum(c.isalpha() for c in line) >= 3 and not _GENERIC_BOOKMARK.match(line) and not re.fullmatch(r"[\d\W]+", line):
            return line
        return None
    return None


def pdf_paragraphs(text: str) -> list[str]:
    """Paragraphs from one page of pypdf text.

    A paragraph break is two or more newlines in a row and nothing else. Some real PDFs emit every word as
    "word\\n \\nword" (newline, space, newline); treating that as a blank line makes every word its own paragraph.
    """
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)              # words hyphenated across a line break
    parts = [" ".join(p.split()) for p in re.split(r"\n{2,}", text)]
    return [p for p in parts if p]


def extract_pdf(filename: str, data: bytes) -> Extracted:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractError("This PDF is password-protected. Remove the password and upload it again.")
        n = len(reader.pages)
    except ExtractError:
        raise
    except (PyPdfError, ValueError, KeyError, OSError, RecursionError, NotImplementedError):
        raise ExtractError("This file could not be read as a PDF (it may be damaged).") from None
    if n > settings.max_pages():
        raise ExtractError(f"This PDF has {n} pages; the limit is {settings.max_pages()}. Split it and upload the parts.")

    headings: dict[int, list[tuple[int, str]]] = {}
    try:
        for level, title, page in _flatten_outline(reader, reader.outline):
            headings.setdefault(page, []).append((min(level, 6), title))
    except Exception:
        headings = {}

    slides = generic_outline(headings)                       # "Slide 1, Slide 2...": name topics from the slides' own titles instead
    if slides:
        headings = {}
    texts: list[str] = []
    for i in range(n):
        try:
            raw = reader.pages[i].extract_text() or ""
        except Exception:
            raw = ""
        texts.append(clean(raw, compat=True))
    # Pages with no selectable text are pictures (a scan, a photo). Read them with OCR when an engine is installed.
    blank = [i + 1 for i, t in enumerate(texts) if not pdf_paragraphs(t)]
    ocr_text: dict[int, list[str]] = {}
    ocr_conf = None
    if blank and ocr.available():
        try:
            ocr_text, ocr_conf = ocr.ocr_pdf_pages(data, blank)
        except Exception:                                    # a broken renderer must not break the upload
            ocr_text = {}

    blocks: list[Block] = []
    blank_pages = 0
    since_heading, titled = 0, False
    for i in range(n):
        page_no = i + 1
        for level, title in headings.get(page_no, []):
            blocks.append(Block(clean(title, compat=True), page_no, level))
        text = texts[i]
        paras = pdf_paragraphs(text)
        if not paras and page_no in ocr_text:               # a scanned page: short title lines become headings when the PDF has no outline
            for p in (clean(p, compat=True) for p in ocr_text[page_no]):
                level = 0 if headings else _looks_like_heading(p)
                if level:
                    blocks.append(Block(_heading_text(p), page_no, level))
                    since_heading = 0
                else:
                    paras.append(p)
            if not paras:
                continue
        if slides:
            title = slide_title(text)
            if title and (not titled or since_heading >= SLIDE_TOPIC_MIN_CHARS) and (not blocks or blocks[-1].text != title):
                blocks.append(Block(title, page_no, 1))
                since_heading, titled = 0, True
            since_heading += sum(len(p) for p in paras)
        if not paras:
            blank_pages += 1
        blocks.extend(Block(p, page_no) for p in paras)

    warnings: list[str] = []
    result = Extracted("pdf", _pdf_title(reader, filename), blocks, n, warnings, ocr_pages=len(ocr_text))
    if ocr_text:
        conf = f" (average OCR confidence {round(ocr_conf * 100)}%)" if ocr_conf is not None else ""
        warnings.append(f"{len(ocr_text)} of {n} pages were scanned images; their text was read with {ocr.label()}{conf}. "
                        "OCR can misread characters, so check important quotes against the page.")
        if len(blank) > ocr.max_pages():
            warnings.append(f"Only the first {ocr.max_pages()} scanned pages were read with OCR; split the file to read the rest.")
    if result.chars < MIN_TEXT_CHARS:
        if ocr_text:
            warnings.append("Almost no text could be read from this file, even with OCR.")
        elif ocr.available():
            warnings.append(f"No selectable text was found. This looks like a scanned PDF, and OCR ({ocr.label()}) could not read any text from its pages, "
                            "so nothing from this file can be searched or quizzed.")
        else:
            warnings.append("No selectable text was found. This looks like a scanned PDF, and OCR is not supported on this server "
                            "(install EasyOCR to enable it), so nothing from this file can be searched or quizzed.")
    elif blank_pages:
        warnings.append(f"{blank_pages} of {n} pages contained no selectable text (images or scans) and were skipped.")
    if slides and titled:
        warnings.append("This PDF looks like slides (its bookmarks are just \"Slide 1, Slide 2...\"), so topics are named after the slide titles, several slides per topic.")
    elif not headings and result.chars >= MIN_TEXT_CHARS and not any(b.level for b in blocks):
        warnings.append("This PDF has no outline (bookmarks), so it is treated as a single topic.")
    return result


def _pdf_title(reader, filename: str) -> str:
    try:
        meta = (reader.metadata.title or "").strip() if reader.metadata else ""
    except Exception:
        meta = ""
    meta = " ".join(clean(meta, compat=True).split())
    return meta[:200] if 3 <= len(meta) and any(c.isalpha() for c in meta) else _title_from_name(filename)


# --------------------------------------------------------------------------------------------------- DOCX

_HEADING_STYLE = re.compile(r"^heading\s*([1-9])$", re.I)


def extract_docx(filename: str, data: bytes) -> Extracted:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            total = sum(i.file_size for i in infos)
            if total > MAX_UNZIPPED_BYTES or (len(data) and total / len(data) > MAX_ZIP_RATIO and total > 5_000_000):
                raise ExtractError("This document expands to an unreasonable size and was refused.")
            if "word/document.xml" not in z.namelist():
                raise ExtractError("This file is not a Word (.docx) document.")
        from docx import Document
        doc = Document(io.BytesIO(data))
    except ExtractError:
        raise
    except Exception:
        raise ExtractError("This file could not be read as a Word (.docx) document.") from None

    blocks: list[Block] = []
    title = ""
    try:
        title = " ".join(clean(doc.core_properties.title or "").split())
    except Exception:
        pass
    for item in doc.iter_inner_content():
        if hasattr(item, "rows"):                            # a table: one paragraph per row
            for row in item.rows:
                cells, seen = [], set()
                for cell in row.cells:
                    if id(cell._tc) in seen:                 # merged cells repeat
                        continue
                    seen.add(id(cell._tc))
                    t = " ".join(clean(cell.text).split())
                    if t:
                        cells.append(t)
                if cells:
                    blocks.append(Block(" | ".join(cells)))
            continue
        text = " ".join(clean(item.text).split())
        if not text:
            continue
        style = (item.style.name if item.style is not None else "") or ""
        m = _HEADING_STYLE.match(style)
        if m:
            blocks.append(Block(text[:200], None, int(m.group(1))))
        elif style.lower() == "title" and not title:
            title = text[:200]
        else:
            blocks.append(Block(text))
    result = Extracted("docx", title[:200] if len(title) >= 3 else _title_from_name(filename), blocks, None, [])
    if result.chars < MIN_TEXT_CHARS:
        result.warnings.append("No text was found in this document.")
    return result


# -------------------------------------------------------------------------------------------------- IMAGE

def extract_image(filename: str, data: bytes) -> Extracted:
    """A photo or scan of notes: read with OCR, one topic, page 1. Lines that look like headings become headings."""
    try:
        r = ocr.read_image_bytes(data)
    except Exception:
        raise ExtractError("This picture could not be opened (it may be damaged).") from None
    blocks: list[Block] = []
    for p in r.paragraphs:
        p = clean(p, compat=True)
        level = _looks_like_heading(p)
        blocks.append(Block(_heading_text(p), 1, level) if level else Block(p, 1))
    conf = f" (average confidence {round(r.confidence * 100)}%)" if r.confidence is not None else ""
    result = Extracted("image", _title_from_name(filename), blocks, 1,
                       [f"The text of this picture was read with {ocr.label()}{conf}. OCR can misread characters, so check important quotes against the image."],
                       ocr_pages=1 if blocks else 0)
    if result.chars < MIN_TEXT_CHARS:
        result.warnings.append("Almost no text could be read from this picture. A sharper, well-lit photo taken straight on works best.")
    return result


# ------------------------------------------------------------------------------------------------- entry

def sniff(filename: str, data: bytes) -> str:
    """'pdf' | 'docx' | 'txt' | 'image', decided by content. Anything else is refused."""
    head = data[:2048]
    if b"%PDF-" in head:
        return "pdf"
    if ocr.image_kind(data):
        if ocr.available():
            return "image"
        raise ExtractError("Only PDF, Word (.docx) and plain-text files are supported. Photos of notes need OCR, which is not installed on this server.")
    if data[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" in z.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            pass
        raise ExtractError("Only PDF, Word (.docx) and plain-text files are supported.")
    if b"\x00" in data[:8192] or data[:4] in (b"\x89PNG", b"GIF8", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1") \
            or data[:2] == b"MZ" or data[:4] == b"\x7fELF" or data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ExtractError("Only PDF, Word (.docx) and plain-text files are supported.")
    return "txt"


def extract(filename: str, data: bytes) -> Extracted:
    kind = sniff(filename, data)
    return {"pdf": extract_pdf, "docx": extract_docx, "txt": extract_txt, "image": extract_image}[kind](filename, data)
