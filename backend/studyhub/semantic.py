"""Local semantic search: fastembed embeddings stored next to the passages, compared with sqlite-vec.

Keyword search (FTS5/BM25, `retrieval.py`) finds passages that share the question's words. It misses a passage that says
the same thing in other words ("LIFO" vs "last in, first out"). This module adds the missing half:

  * every passage gets a 384-number embedding from `BAAI/bge-small-en-v1.5` (fastembed, runs on the CPU, no API key),
  * embeddings are plain BLOBs in `chunk_embeddings` (a normal table, so ON DELETE CASCADE keeps it tidy and a
    connection without the extension can still delete a document),
  * a query is compared with `vec_distance_cosine()` from sqlite-vec, scoped to ONE subject of ONE user in the SQL,
  * when sqlite-vec cannot be loaded the same comparison runs in Python, so results never depend on the extension.

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

MODEL = os.environ.get("STUDYHUB_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
BATCH = 64
CANDIDATES = 30
# Cosine similarity at or above which a passage counts as "about the question" even when it shares few words with it.
# bge-small scores unrelated English text around 0.4-0.6 and paraphrases above 0.75.
RELEVANT_SIMILARITY = float(os.environ.get("STUDYHUB_SEMANTIC_RELEVANT", "0.78"))


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedder:
    """fastembed's TextEmbedding, loaded once per process on first use."""

    def __init__(self, model: str = MODEL):
        from fastembed import TextEmbedding              # imported lazily: start-up stays fast and tests never load it
        self.name = model
        self._m = TextEmbedding(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._m.embed(texts, batch_size=BATCH)]


_lock = threading.Lock()
_embedder: Embedder | None = None
_failed: str | None = None
_factory: Callable[[], Embedder] = FastEmbedder
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


def load_vec(db: sqlite3.Connection) -> bool:
    """Load sqlite-vec into this connection if possible (a no-op when it is already loaded)."""
    try:
        db.execute("SELECT vec_version()").fetchone()
        return True
    except sqlite3.OperationalError:
        pass
    try:
        import sqlite_vec
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        return True
    except Exception:
        return False


def ensure_schema(db: sqlite3.Connection) -> None:
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
        db.executemany("INSERT OR REPLACE INTO chunk_embeddings(chunk_id, model, dim, vec) VALUES (?,?,?,?)",
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
    if load_vec(db):
        try:
            rows = db.execute(f"SELECT c.id, vec_distance_cosine(ce.vec, ?) AS d {base} ORDER BY d LIMIT ?", (qv, *args, int(k))).fetchall()
            return [(int(r[0]), round(1.0 - float(r[1]), 4)) for r in rows]
        except sqlite3.OperationalError:
            pass
    q = unpack(qv)
    scored = []
    for cid, blob in db.execute(f"SELECT c.id, ce.vec {base}", args).fetchall():
        v = unpack(blob)
        if len(v) == len(q):
            scored.append((int(cid), round(sum(a * b for a, b in zip(q, v)), 4)))
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


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
