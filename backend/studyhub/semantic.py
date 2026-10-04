"""Local semantic search: Sentence-BERT embeddings stored next to the passages, searched with FAISS.

Keyword search (full-text, `retrieval.py`) finds passages that share the question's words. It misses a passage that says
the same thing in other words ("LIFO" vs "last in, first out"). This module adds the missing half, and it is also how a
generated question finds its source paragraph:

  * every passage gets a 384-number embedding from Sentence-BERT (`sentence-transformers/all-MiniLM-L6-v2`, CPU, no API
    key; fastembed's bge-small is the fallback when sentence-transformers is not installed),
  * embeddings are plain rows in `chunk_embeddings` (a normal table, so ON DELETE CASCADE keeps it tidy),
  * a query is matched with a FAISS inner-product index (cosine, the vectors are normalised) built from ONE subject of ONE
    user and cached until that subject's passages change; without FAISS the same comparison runs in Python.

Indexing runs in its own background thread after an upload (the model worker stays free for answers) and on start-up
for anything not yet indexed. Semantic search is an addition, never a requirement: if the model cannot be loaded
(offline first run, no disk), `available()` turns False and keyword search keeps working exactly as before.

STUDYHUB_SEMANTIC=on|off|auto (auto: on, except inside the test suite unless a test installs an embedder).
"""
from __future__ import annotations

import logging
import math
import os
import sqlite3
import struct
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, Protocol

log = logging.getLogger("studyhub.semantic")

MODEL = os.environ.get("STUDYHUB_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
BATCH = 64
CANDIDATES = 30
# Cosine similarity at or above which a passage counts as "about the question" even when it shares few words with it.
# MiniLM scores unrelated English text below 0.25 and paraphrases 0.4-0.6; bge-small scores higher across the board.
RELEVANT_SIMILARITY = float(os.environ.get("STUDYHUB_SEMANTIC_RELEVANT", "0.78" if "bge" in MODEL.lower() else "0.5"))


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceBertEmbedder:
    """Sentence-BERT (sentence-transformers), loaded once per process on first use."""

    def __init__(self, model: str = MODEL):
        from sentence_transformers import SentenceTransformer   # imported lazily: start-up stays fast and tests never load it
        self.name = model
        self._m = SentenceTransformer(model, device="cpu")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._m.encode(texts, batch_size=BATCH, normalize_embeddings=True)]


class FastEmbedder:
    """fastembed's TextEmbedding (ONNX, no torch): the fallback when sentence-transformers is missing."""

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding
        self.name = model
        self._m = TextEmbedding(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._m.embed(texts, batch_size=BATCH)]


def _default_embedder() -> "Embedder":
    if "bge" in MODEL.lower():
        return FastEmbedder(MODEL)
    try:
        return SentenceBertEmbedder(MODEL)
    except ImportError:
        return FastEmbedder()


_lock = threading.Lock()
_embedder: Embedder | None = None
_failed: str | None = None
_factory: Callable[[], Embedder] = _default_embedder
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nexus-embed")


def mode() -> str:
    return os.environ.get("STUDYHUB_SEMANTIC", "auto").lower()


def set_embedder(e: Embedder | None) -> None:
    """Tests (and scripts) install a deterministic embedder. None resets to the default."""
    global _embedder, _failed
    with _lock:
        _embedder, _failed = e, None


def embedder() -> Embedder | None:
    """The embedder, or None when semantic search is off or the model could not be loaded (the reason is logged once)."""
    global _embedder, _failed
    m = mode()
    if m == "off":
        return None
    if _embedder is not None:
        return _embedder
    if m == "auto" and os.environ.get("PYTEST_CURRENT_TEST"):
        return None
    if _failed:
        return None
    with _lock:
        if _embedder is None and not _failed:
            try:
                _embedder = _factory()
                log.info("semantic search on (%s)", getattr(_embedder, "name", "embedder"))
            except Exception as e:                       # offline first run, missing package, no disk
                _failed = f"{type(e).__name__}: {e}"
                log.warning("semantic search off: the embedding model could not be loaded (%s)", _failed)
    return _embedder


def available() -> bool:
    return embedder() is not None


def status() -> dict:
    e = embedder()
    return {"enabled": e is not None, "model": getattr(e, "name", None) if e else None, "reason": None if e else (_failed or ("switched off" if mode() == "off" else "not loaded"))}


# --------------------------------------------------------------------------------------------------- vectors

def pack(v: Iterable[float]) -> bytes:
    v = list(v)
    n = math.sqrt(sum(x * x for x in v)) or 1.0              # stored normalised: cosine == dot product
    return struct.pack(f"{len(v)}f", *(x / n for x in v))


def unpack(b: bytes) -> list[float]:
    return list(struct.unpack(f"{len(b) // 4}f", b))


def ensure_schema(db: sqlite3.Connection) -> None:
    if getattr(db, "pg", False):                          # created by migration 16
        return
    db.execute("""CREATE TABLE IF NOT EXISTS chunk_embeddings (
        chunk_id  INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
        model     TEXT NOT NULL,
        dim       INTEGER NOT NULL,
        vec       BLOB NOT NULL
    )""")


def pending_chunk_ids(db: sqlite3.Connection, limit: int = 5000, document_id: int | None = None) -> list[int]:
    ensure_schema(db)
    e = embedder()
    model = getattr(e, "name", MODEL)
    sql = ("SELECT c.id FROM chunks c LEFT JOIN chunk_embeddings ce ON ce.chunk_id=c.id AND ce.model=? "
           "WHERE ce.chunk_id IS NULL" + (" AND c.document_id=?" if document_id else "") + " ORDER BY c.id LIMIT ?")
    args = (model, document_id, limit) if document_id else (model, limit)
    return [int(r[0]) for r in db.execute(sql, args).fetchall()]


def index_chunks(db: sqlite3.Connection, chunk_ids: list[int]) -> int:
    """Embed and store these passages. Returns how many were stored."""
    e = embedder()
    if e is None or not chunk_ids:
        return 0
    ensure_schema(db)
    done = 0
    for i in range(0, len(chunk_ids), BATCH):
        part = chunk_ids[i:i + BATCH]
        marks = ",".join("?" * len(part))
        rows = db.execute(f"SELECT id, heading_path, text FROM chunks WHERE id IN ({marks})", part).fetchall()
        if not rows:
            continue
        texts = [((r["heading_path"] + "\n") if r["heading_path"] else "") + r["text"] for r in rows]
        vecs = e.embed(texts)
        db.executemany("INSERT INTO chunk_embeddings(chunk_id, model, dim, vec) VALUES (?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE "
                       "SET model=excluded.model, dim=excluded.dim, vec=excluded.vec",
                       [(r["id"], e.name, len(v), pack(v)) for r, v in zip(rows, vecs)])
        done += len(rows)
    return done


def index_pending(open_db: Callable[[], object], document_id: int | None = None) -> int:
    """Index what is missing. `open_db` returns a Store (its own connection: this runs on the indexing thread)."""
    if embedder() is None:
        return 0
    store = open_db()
    try:
        db = store.db
        total = 0
        while True:
            ids = pending_chunk_ids(db, 512, document_id)
            if not ids:
                return total
            n = index_chunks(db, ids)
            total += n
            if n == 0:
                return total
    except Exception:
        log.exception("semantic indexing failed")
        return 0
    finally:
        try:
            store.db.close()
        except Exception:
            pass


def schedule_for(db: sqlite3.Connection, document_id: int | None = None):
    """Index a document's passages in the background, on a new connection to the same database file as `db`.
    For an in-memory database (tests, scripts) it indexes right away on `db` itself."""
    if embedder() is None:
        return None
    if getattr(db, "pg", False):
        path = db.path if not db.schema.startswith("m_") else ""
    else:
        row = db.execute("PRAGMA database_list").fetchone()
        path = row[2] if row else ""
    if not path:
        index_chunks(db, pending_chunk_ids(db, 100000, document_id))
        return None
    from .db import open_db
    return schedule(lambda: open_db(path), document_id)


def schedule(open_db: Callable[[], object], document_id: int | None = None):
    """Index in the background. Returns the future (tests wait on it), or None when semantic search is off."""
    if embedder() is None:
        return None
    return _executor.submit(index_pending, open_db, document_id)


# ---------------------------------------------------------------------------------------------------- search

def search(db: sqlite3.Connection, user_id: int, subject_id: int, query: str, k: int = CANDIDATES, *, answers: bool = False) -> list[tuple[int, float]]:
    """[(chunk_id, cosine similarity)] best first, only passages of this user's subject. [] when semantic search is off."""
    e = embedder()
    if e is None or not (query or "").strip():
        return []
    ensure_schema(db)
    qv = pack(e.embed([query])[0])
    base = ("FROM chunk_embeddings ce JOIN chunks c ON c.id = ce.chunk_id JOIN subjects s ON s.id = c.subject_id "
            "WHERE c.subject_id = ? AND s.user_id = ? AND c.quarantined <= ? AND ce.model = ?")
    args = (subject_id, user_id, 0 if answers else 1, e.name)
    ids, index = _index(db, base, args)
    if not ids:
        return []
    q = unpack(qv)
    if index is not None:
        import numpy as np
        sims, pos = index.search(np.asarray([q], dtype="float32"), min(int(k), len(ids)))
        return [(ids[p], round(float(d), 4)) for d, p in zip(sims[0], pos[0]) if p >= 0]
    scored = []
    for cid, blob in db.execute(f"SELECT c.id, ce.vec {base}", args).fetchall():
        v = unpack(blob)
        if len(v) == len(q):
            scored.append((int(cid), round(sum(a * b for a, b in zip(q, v)), 4)))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


# One FAISS index per (database, subject, user, quarantine filter, model), rebuilt when the subject's embeddings change.
_faiss: dict[tuple, tuple] = {}
_faiss_lock = threading.Lock()


def _index(db, base: str, args: tuple):
    """(chunk ids in index order, faiss.IndexFlatIP or None when FAISS is not installed)."""
    sig = tuple(db.execute(f"SELECT COUNT(*), MAX(ce.chunk_id), SUM(ce.dim) {base}", args).fetchone())
    if not sig[0]:
        return [], None
    key = (getattr(db, "path", None) or id(db), *args)
    with _faiss_lock:
        hit = _faiss.get(key)
        if hit and hit[0] == sig:
            return hit[1], hit[2]
    try:
        import faiss
        import numpy as np
    except ImportError:
        return [1], None                                       # any non-empty list: the caller scores in Python
    rows = db.execute(f"SELECT c.id, ce.vec {base} ORDER BY c.id", args).fetchall()
    vecs = [unpack(r[1]) for r in rows]
    dim = len(vecs[0])
    rows_ok = [(int(r[0]), v) for r, v in zip(rows, vecs) if len(v) == dim]
    index = faiss.IndexFlatIP(dim)
    index.add(np.asarray([v for _, v in rows_ok], dtype="float32"))
    ids = [cid for cid, _ in rows_ok]
    with _faiss_lock:
        if len(_faiss) > 256:
            _faiss.clear()
        _faiss[key] = (sig, ids, index)
    return ids, index


def coverage(db: sqlite3.Connection, user_id: int | None = None) -> dict:
    """How much of the material is indexed (for the account page and the health check)."""
    ensure_schema(db)
    if user_id is None:
        total = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        done = db.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0]
    else:
        total = db.execute("SELECT COUNT(*) FROM chunks c JOIN subjects s ON s.id=c.subject_id WHERE s.user_id=?", (user_id,)).fetchone()[0]
        done = db.execute("SELECT COUNT(*) FROM chunk_embeddings ce JOIN chunks c ON c.id=ce.chunk_id JOIN subjects s ON s.id=c.subject_id WHERE s.user_id=?", (user_id,)).fetchone()[0]
    return {"passages": int(total), "indexed": int(done)}
