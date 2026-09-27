"""Upload -> checks -> extract -> chunk -> store. The one function the web layer calls for a new file."""
from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from . import settings
from .chunker import _SENTENCE, ChunkSpec, chunk_blocks
from .extract import Block, ExtractError, extract, sniff
from .repo import Repo
from . import screen, semantic


class IngestError(ValueError):
    """The upload was refused; the message is written for the student. Nothing was stored."""


@dataclass
class IngestResult:
    document_id: int
    title: str
    status: str                                              # parsed | empty | failed
    chunks: int = 0
    topics: int = 0
    duplicate: bool = False
    warnings: list[str] = field(default_factory=list)


def _upload_path(user_id: int, sha256: str) -> Path:
    return Path(settings.upload_dir()) / str(int(user_id)) / sha256           # digits and hex only: no traversal


def _piece(c: ChunkSpec, sentences: list[str], flagged: bool) -> ChunkSpec:
    text = " ".join(sentences).strip()
    return ChunkSpec(text, c.page_start, c.page_end, c.heading_path, c.topic_path, c.topic_origin,
                     screen.find(text) if flagged else [])


def quarantine(chunks: list[ChunkSpec]) -> list[ChunkSpec]:
    """Mark passages that read as orders to an AI. When only some sentences do, the passage is split at sentence
    boundaries so ONLY those sentences are quarantined and the legitimate text around them stays usable. Every piece is a
    verbatim part of the original text. If the suspicious phrase cannot be pinned to sentences, the whole passage is marked."""
    out: list[ChunkSpec] = []
    for c in chunks:
        if not screen.find(c.text):
            out.append(c)
            continue
        sentences = _SENTENCE.split(c.text)
        marks = [bool(screen.find(s)) for s in sentences]
        if not any(marks):
            c.flags = screen.find(c.text)
            out.append(c)
            continue
        run: list[str] = []
        run_flag = False
        for s, m in zip(sentences, marks):
            if run and m != run_flag:
                out.append(_piece(c, run, run_flag))
                run = []
            run.append(s)
            run_flag = m
        out.append(_piece(c, run, run_flag))
    return out


ROLES = ("notes", "syllabus", "pyq")


def ingest(db: sqlite3.Connection, user_id: int, subject_id: int, filename: str, data: bytes, *, source_url: str | None = None, role: str = "notes") -> IngestResult:
    repo = Repo(db)
    if role not in ROLES:
        raise IngestError("Choose whether this is notes, a syllabus or past papers.")
    if repo.get_subject(user_id, subject_id) is None:
        raise IngestError("That subject does not exist.")
    if not data:
        raise IngestError("The file is empty.")
    if len(data) > settings.max_upload_bytes():
        raise IngestError(f"The file is larger than the {settings.max_upload_bytes() / 1048576:.3g} MB limit.")

    sha = hashlib.sha256(data).hexdigest()
    existing = repo.find_document_by_hash(user_id, subject_id, sha)
    if existing:
        return IngestResult(existing["id"], existing["title"], existing["status"], duplicate=True,
                            warnings=["This exact file is already in this subject, so nothing was added."])

    try:
        kind = sniff(filename, data)
    except ExtractError as e:
        raise IngestError(str(e)) from None
    try:
        ex = extract(filename, data)
        blocks = [Block(b.text, b.page, 0) for b in ex.blocks] if role == "pyq" else ex.blocks       # a past paper's short numbered lines are questions, not headings
        chunks = chunk_blocks(blocks, ex.title) if ex.status == "parsed" else []
        status, warnings, title, pages, ocr_pages = ex.status, list(ex.warnings), ex.title, ex.pages, ex.ocr_pages
    except ExtractError as e:                                # recognised type, unusable content: keep a visible record
        chunks, status, warnings, title, pages, ocr_pages = [], "failed", [str(e)], (filename or "upload")[:200], None, 0

    chunks = quarantine(chunks)
    flagged = sum(1 for c in chunks if c.flags)
    if flagged:
        warnings.append(f"{flagged} passage{'s' if flagged != 1 else ''} in this file read like instructions to an AI "
                        "assistant. They stay readable and searchable, but are never used to write answers.")
    new_chars = sum(len(c.text) for c in chunks)
    if repo.subject_chars(user_id, subject_id) + new_chars > settings.max_subject_chars():
        raise IngestError("This subject has reached its material limit. Delete a document or start another subject.")

    path = _upload_path(user_id, sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(".part")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    doc_id = repo.store_document(user_id, subject_id, {
        "kind": "url" if source_url else kind, "title": title, "source": (source_url or " ".join((filename or "upload").split()))[:500 if source_url else 200], "sha256": sha,
        "bytes": len(data), "pages": pages, "status": status, "warnings": warnings, "role": role, "ocr_pages": ocr_pages}, chunks)
    if doc_id is None:                                       # lost the subject between the check and the insert
        raise IngestError("That subject does not exist.")
    if chunks:
        semantic.schedule_for(db, doc_id)                    # embeddings for semantic search, off the request thread
    return IngestResult(doc_id, title, status, len(chunks), len({c.topic_path for c in chunks}), False, warnings)


def delete_subject(db: sqlite3.Connection, user_id: int, subject_id: int) -> bool:
    """Delete a subject with everything in it, then the stored originals nothing else uses."""
    repo = Repo(db)
    hashes = repo.document_hashes(user_id, subject_id)
    if not repo.delete_subject(user_id, subject_id):
        return False
    for sha in hashes:
        if not repo.hash_in_use(user_id, sha):
            try:
                _upload_path(user_id, sha).unlink(missing_ok=True)
            except OSError:
                pass
    return True


def delete_document(db: sqlite3.Connection, user_id: int, subject_id: int, document_id: int) -> bool:
    """Delete a document and, if no other document of this user has the same bytes, the stored original."""
    gone = Repo(db).delete_document(user_id, subject_id, document_id)
    if gone is None:
        return False
    if not gone["still_used"]:
        try:
            _upload_path(user_id, gone["sha256"]).unlink(missing_ok=True)
        except OSError:
            pass
    return True
