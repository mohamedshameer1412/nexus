"""Subject-scoped keyword retrieval (SQLite FTS5, BM25) with a relevance test.

`search()` is the only entry point the Q&A and quiz code use. It cannot be pointed at another subject or user: the
scope is two required arguments that go straight into the SQL. When local embeddings are available (`semantic.py`) the
search is HYBRID: keyword and vector candidates are merged with reciprocal-rank fusion, so a passage that says the same
thing in other words is found too. No caller changed.

BM25 alone ranks but never says "not relevant": one shared common word is enough to return a passage. So every hit also
carries which query terms it matched (counted by the same FTS index, so stemming agrees) and `relevant` says whether it
matched enough of them to be worth showing or answering from.
"""
from __future__ import annotations

import math
import re
import sqlite3
from dataclasses import dataclass

from . import semantic
from .repo import Repo

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
STOPWORDS = frozenset("""a an the and or but if then else of to in on at by for with from as is are was were be been being
do does did have has had it its this that these those i you he she we they me my your our their what which who whom
whose when where why how can could should would will shall may might must not no yes than so such into about over
under between also there here explain describe tell please mean means meant define definition give show list""".split())
MAX_TERMS = 12
CANDIDATES = 30
RRF_K = 60                      # reciprocal-rank fusion constant (the usual 60: rank matters, raw scores do not)


_SUFFIXES = (("ations", 4), ("ation", 4), ("ingly", 4), ("ings", 3), ("ing", 3), ("edly", 3), ("ied", 3), ("ies", 3),
             ("ed", 3), ("es", 3), ("s", 3), ("ly", 4))


def stem(word: str) -> str:
    """A light stemmer for comparing words in Python (pops / popping / pop, queue / queues). Ranking uses FTS5's own."""
    w = word.lower()
    base = w
    for suffix, keep in _SUFFIXES:
        if w.endswith(suffix) and len(w) - len(suffix) >= keep and not (suffix == "s" and w.endswith("ss")):
            base = w[: -len(suffix)]
            if suffix in ("ing", "ings", "ed", "edly") and len(base) >= 3 and base[-1] == base[-2] and base[-1] not in "aeioulsz":
                base = base[:-1]                                   # popping -> popp -> pop
            break
    return base[:-1] if len(base) > 3 and base.endswith("e") else base


def terms(query: str) -> list[str]:
    """Content words of a question, lower-cased, without repeats, at most MAX_TERMS."""
    seen: list[str] = []
    for word in _WORD.findall((query or "").lower()):
        if len(word) > 1 and word not in STOPWORDS and word not in seen:
            seen.append(word)
    return seen[:MAX_TERMS]


def build_match(query: str, only: list[str] | None = None) -> str:
    """A safe FTS5 expression: content words only, each quoted, joined with OR.

    Quoting means operators the user types (AND, NEAR, *, ", -, column: filters) are treated as plain words.
    """
    return " OR ".join(f'"{w}"' for w in (only if only is not None else terms(query)))


def needed(n_terms: int) -> int:
    """How many of the question's terms a passage must contain to count as relevant (at least half, and two if it can)."""
    return max(min(2, n_terms), math.ceil(n_terms / 2)) if n_terms else 0


@dataclass
class Hit:
    id: int
    document_id: int
    doc_title: str
    topic_id: int | None
    heading_path: str
    page_start: int | None
    page_end: int | None
    text: str
    score: float                    # BM25, lower is better
    matched: list[str]              # query terms found in this passage
    n_terms: int
    quarantined: bool = False       # reads like orders to an AI: never given to a model
    similarity: float | None = None # cosine similarity to the question (None: semantic search off or not a vector hit)

    @property
    def coverage(self) -> float:
        return len(self.matched) / self.n_terms if self.n_terms else 0.0

    @property
    def relevant(self) -> bool:
        if len(self.matched) >= needed(self.n_terms) > 0:
            return True
        return self.similarity is not None and self.similarity >= semantic.RELEVANT_SIMILARITY and len(self.matched) >= 1

    def __getitem__(self, key: str):                        # hit["text"] reads like the row it came from
        return getattr(self, key)

    def as_dict(self) -> dict:
        return {"id": self.id, "document_id": self.document_id, "doc_title": self.doc_title, "topic_id": self.topic_id,
                "heading_path": self.heading_path, "page_start": self.page_start, "page_end": self.page_end,
                "text": self.text, "score": self.score, "matched": list(self.matched), "coverage": round(self.coverage, 2),
                "quarantined": self.quarantined, "similarity": self.similarity}


def search(db: sqlite3.Connection, user_id: int, subject_id: int, query: str, k: int = 5, *,
           relevant_only: bool = False, answers: bool = False) -> list[Hit]:
    """Best passages for `query` inside this user's subject: most query terms matched first, then BM25.

    With relevant_only=True, passages that match too few of the terms are dropped. With answers=True, quarantined
    passages (text that reads as orders to an AI) are excluded: use it for anything a model will read. [] if nothing qualifies."""
    repo, ts = Repo(db), terms(query)
    if not ts:
        return []
    rows = repo.search_chunks(user_id, subject_id, build_match(query), CANDIDATES, answers)
    vec = semantic.search(db, user_id, subject_id, query, CANDIDATES, answers=answers)
    sims = dict(vec)
    have = {r["id"] for r in rows}
    extra = [cid for cid, _ in vec if cid not in have]
    if extra:
        marks = ",".join("?" * len(extra))
        rows += [dict(r) | {"score": 0.0} for r in db.execute(
            "SELECT c.id, c.document_id, d.title AS doc_title, c.topic_id, c.heading_path, c.page_start, c.page_end, c.text, c.quarantined "
            "FROM chunks c JOIN documents d ON d.id = c.document_id JOIN subjects s ON s.id = c.subject_id "
            f"WHERE c.subject_id = ? AND s.user_id = ? AND c.quarantined <= ? AND c.id IN ({marks})",
            (subject_id, user_id, 0 if answers else 1, *extra)).fetchall()]
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    found: dict[int, list[str]] = {i: [] for i in ids}
    for t in ts:
        for cid in repo.matching_chunk_ids(user_id, subject_id, build_match(query, [t]), ids):
            found[cid].append(t)
    hits = [Hit(r["id"], r["document_id"], r["doc_title"], r["topic_id"], r["heading_path"], r["page_start"],
                r["page_end"], r["text"], r["score"], found[r["id"]], len(ts), bool(r["quarantined"]), sims.get(r["id"])) for r in rows]
    hits.sort(key=lambda h: (-len(h.matched), h.score))
    if vec:                                                     # hybrid: fuse the keyword order with the vector order
        kw_rank = {h.id: i for i, h in enumerate(hits) if h.matched}
        vec_rank = {cid: i for i, (cid, _) in enumerate(vec)}
        fused = lambda h: (1 / (RRF_K + kw_rank[h.id]) if h.id in kw_rank else 0) + (1 / (RRF_K + vec_rank[h.id]) if h.id in vec_rank else 0)  # noqa: E731
        hits.sort(key=lambda h: (-int(h.relevant), -fused(h)))
    if relevant_only:
        hits = select_relevant(hits)
    return hits[:max(1, min(int(k), 20))]


def select_relevant(hits: list[Hit], most: int = 3) -> list[Hit]:
    """The passages worth answering from.

    Any passage that matches enough of the question's words on its own. If there is none, a question that compares or
    joins two ideas ("how does a queue differ from a stack?") has its words spread over separate passages: then up to
    `most` passages are accepted if TOGETHER they cover enough of the words. Otherwise nothing qualifies."""
    strong = [h for h in hits if h.relevant]
    if strong or not hits:
        return strong
    chosen: list[Hit] = []
    covered: set[str] = set()
    for h in hits:                                              # already best first
        if set(h.matched) - covered:
            chosen.append(h)
            covered |= set(h.matched)
        if len(chosen) == most:
            break
    return chosen if len(covered) >= needed(hits[0].n_terms) > 0 else []


def focus_terms(db: sqlite3.Connection, user_id: int, subject_id: int, question: str, hits: list[Hit]) -> list[str]:
    """The question's key words: for each retrieved passage, the question word it contains that is rarest in the whole
    subject (ties: the one that occurs least in these passages, then the longer word). A statement must mention at least
    one of them. "What does pop do on a stack?" -> ["pop"]; "How does a queue differ from a stack?" -> ["stack", "queue"]
    (each side of a comparison lives in its own passage)."""
    repo = Repo(db)
    words = [stem(w) for h in hits for w in _WORD.findall(h.text.lower())]
    freq: dict[str, int] = {}
    out: list[str] = []
    for h in hits:
        for t in h.matched:
            if t not in freq:
                freq[t] = repo.term_frequency(user_id, subject_id, build_match(question, [t]), True)
        if h.matched:
            best = min(h.matched, key=lambda t: (freq[t], words.count(stem(t)), -len(t)))
            if best not in out:
                out.append(best)
    return out
