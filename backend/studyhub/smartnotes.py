"""Smart notes: a study sheet per topic, built only from that topic's own passages.

Extractive on purpose: every key point and definition is a sentence copied word for word from the student's material, with
the page it came from, so a smart note can be trusted like a citation. Sentences are ranked by a small TextRank-style score
(how many of the topic's important words a sentence carries), with a bonus for definitions ("X is a ...", "called", "refers
to") and for the opening sentence of a section. The note ends with the topic's practice questions (without answers) as a
self-check. No model is called, so notes are instant, free and cannot invent anything.
"""
from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter

from .chunker import _SENTENCE
from .repo import Repo
from .retrieval import STOPWORDS, stem

_WORD = re.compile(r"[A-Za-z][A-Za-z\-]{2,}")
_DEFINITION = re.compile(r"\b(is a|is an|is the|are|refers to|is called|are called|means|is defined as|consists of)\b", re.I)
MAX_POINTS = 7
MAX_DEFS = 4


def _words(text: str) -> list[str]:
    return [stem(w.lower()) for w in _WORD.findall(text) if w.lower() not in STOPWORDS]


def topic_passages(db: sqlite3.Connection, subject_id: int, topic_id: int) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT c.id, c.text, c.page_start, c.page_end, c.heading_path, d.title AS doc FROM chunks c JOIN documents d ON d.id=c.document_id "
        "WHERE c.subject_id=? AND c.topic_id=? AND c.quarantined=0 ORDER BY c.document_id, c.ordinal", (subject_id, topic_id))]


def build(db: sqlite3.Connection, subject_id: int, topic: dict) -> dict | None:
    """{'title', 'body', 'points', 'definitions', 'terms'} for one topic, or None when it has no usable text."""
    passages = topic_passages(db, subject_id, topic["id"])
    sentences: list[tuple[int, str, dict, bool]] = []            # (order, sentence, passage, first in passage)
    for p in passages:
        for j, s in enumerate(_SENTENCE.split(" ".join(p["text"].split()))):
            s = s.strip()
            if 40 <= len(s) <= 420:
                sentences.append((len(sentences), s, p, j == 0))
    if not sentences:
        return None
    tf = Counter(w for _, s, _, _ in sentences for w in set(_words(s)))
    name_words = set(_words(topic["name"]))
    total = len(sentences)

    def score(s: str, first: bool) -> float:
        ws = set(_words(s))
        if not ws:
            return 0.0
        base = sum(math.log(1 + tf[w]) for w in ws) / math.sqrt(len(ws))
        return base + (1.2 if _DEFINITION.search(s) else 0) + (0.8 if first else 0) + (0.6 if ws & name_words else 0) + (0.3 if re.search(r"O\(|\d", s) else 0)

    ranked = sorted(sentences, key=lambda x: -score(x[1], x[3]))
    k = min(MAX_POINTS, max(2, round(total * 0.45)))
    points = sorted(ranked[:k], key=lambda x: x[0])
    defs = [x for x in sentences if _DEFINITION.search(x[1])][:MAX_DEFS]
    terms = [w for w, _ in Counter(w.lower() for _, s, _, _ in sentences for w in _WORD.findall(s) if w.lower() not in STOPWORDS and len(w) > 3).most_common(40)
             if w not in {x.lower() for x in topic["name"].split()}][:10]
    where = lambda p: p["doc"] + (f", p. {p['page_start']}" if p["page_start"] is not None else "")      # noqa: E731
    lines = [f"## {topic['name']}", "", "**Key points**", ""]
    lines += [f"- {s}  _({where(p)})_" for _, s, p, _ in points]
    def_lines = [f"> {s}" for _, s, _, _ in defs if s not in {p[1] for p in points}]
    if def_lines:
        lines += ["", "**Definitions**", ""] + def_lines
    if terms:
        lines += ["", "**Key terms:** " + ", ".join(terms)]
    qs = [r["question"] for r in db.execute("SELECT question FROM mcq_items WHERE subject_id=? AND topic_id=? ORDER BY id LIMIT 5", (subject_id, topic["id"]))]
    if qs:
        lines += ["", "**Check yourself**", ""] + [f"{i}. {q}" for i, q in enumerate(qs, start=1)]
    docs = sorted({p["doc"] for p in passages})
    lines += ["", f"_Built from {len(passages)} passage{'s' if len(passages) != 1 else ''} of {', '.join(docs)}. Every point above is copied word for word from your material._"]
    return {"title": f"Smart notes: {topic['name']}", "body": "\n".join(lines) + "\n", "points": len(points), "definitions": len(def_lines), "terms": terms}


def generate(db: sqlite3.Connection, user_id: int, subject_id: int, topic_ids: list[int] | None = None) -> list[int]:
    """Create or refresh the smart note of each topic (all topics with passages when topic_ids is None). Returns the note ids."""
    repo = Repo(db)
    topics = [t for t in repo.list_topics(user_id, subject_id) if t["chunks"] and (topic_ids is None or t["id"] in topic_ids)]
    out = []
    for t in topics:
        note = build(db, subject_id, t)
        if note is None:
            continue
        row = db.execute("SELECT id FROM notes WHERE user_id=? AND subject_id=? AND topic_id=? AND source='smart'", (user_id, subject_id, t["id"])).fetchone()
        if row:
            repo.update_note(user_id, subject_id, row[0], note["title"], note["body"])
            out.append(int(row[0]))
        else:
            nid = repo.add_note(user_id, subject_id, note["title"], note["body"], source="smart", topic_id=t["id"])
            if nid:
                out.append(nid)
    return out
