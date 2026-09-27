"""Prerequisite graph loader and walker — pure SQLite, no LLM.

Rules enforced entirely in code (models propose topics, code decides edges):
  - Only confirmed=1 edges are ever followed.
  - MAX_DEPTH prevents infinite backward loops.
  - The graph is per-subject: topics in different subjects are independent.
"""
from __future__ import annotations

import sqlite3

MAX_DEPTH = 3  # Never step back more than 3 levels in one session


# ── Graph loading ─────────────────────────────────────────────────────────────

def load_graph(db: sqlite3.Connection, subject_id: int) -> dict[int, dict]:
    """Return {topic_id: {'id':…, 'name':…, 'path':…, 'prereq_id': int|None}}
    for all topics in this subject. Only confirmed prerequisite edges included.
    """
    topics = db.execute(
        "SELECT id, name, path FROM topics WHERE subject_id=? ORDER BY ordinal",
        (subject_id,)).fetchall()
    graph: dict[int, dict] = {}
    for t in topics:
        graph[t["id"]] = {"id": t["id"], "name": t["name"], "path": t["path"], "prereq_id": None}

    edges = db.execute(
        "SELECT tp.topic_id, tp.prereq_id FROM topic_prereqs tp "
        "JOIN topics t ON t.id=tp.topic_id "
        "WHERE t.subject_id=? AND tp.confirmed=1",
        (subject_id,)).fetchall()
    for e in edges:
        if e["topic_id"] in graph:
            graph[e["topic_id"]]["prereq_id"] = e["prereq_id"]

    return graph


def prereq_of(graph: dict[int, dict], topic_id: int) -> int | None:
    """Return the confirmed prerequisite topic_id, or None."""
    node = graph.get(topic_id)
    return node["prereq_id"] if node else None


def prereq_label(graph: dict[int, dict], prereq_id: int | None) -> str:
    if prereq_id is None or prereq_id not in graph:
        return "—"
    return graph[prereq_id]["name"]


def can_step_back(
    graph: dict[int, dict],
    topic_id: int,
    depth: int,
    verified_ids: list[int],
) -> bool:
    """True if there is an unverified confirmed prerequisite and depth allows it."""
    p = prereq_of(graph, topic_id)
    return (
        p is not None
        and p in graph
        and depth < MAX_DEPTH
        and p not in verified_ids
    )


# ── Prerequisite management (user-facing) ─────────────────────────────────────

def set_prereq(
    db: sqlite3.Connection,
    user_id: int,
    subject_id: int,
    topic_id: int,
    prereq_id: int,
    *,
    confirmed: bool = True,
) -> bool:
    """Set (or confirm) a prerequisite edge. Returns False if either topic is
    not in this user's subject.
    """
    # Ownership check
    count = db.execute(
        "SELECT COUNT(*) FROM topics t JOIN subjects s ON s.id=t.subject_id "
        "WHERE t.id IN (?,?) AND s.id=? AND s.user_id=?",
        (topic_id, prereq_id, subject_id, user_id)).fetchone()[0]
    if count != 2:
        return False
    # Guard against cycles: prereq must not already (directly) depend on topic_id
    existing = db.execute(
        "SELECT prereq_id FROM topic_prereqs WHERE topic_id=? AND confirmed=1",
        (prereq_id,)).fetchone()
    if existing and existing["prereq_id"] == topic_id:
        return False  # would create a 2-cycle
    db.execute(
        "INSERT INTO topic_prereqs(topic_id, prereq_id, confirmed, origin) VALUES (?,?,?,?) "
        "ON CONFLICT(topic_id, prereq_id) DO UPDATE SET confirmed=excluded.confirmed",
        (topic_id, prereq_id, 1 if confirmed else 0, "manual"))
    return True


def remove_prereq(
    db: sqlite3.Connection,
    user_id: int,
    subject_id: int,
    topic_id: int,
    prereq_id: int,
) -> bool:
    count = db.execute(
        "SELECT COUNT(*) FROM topics t JOIN subjects s ON s.id=t.subject_id "
        "WHERE t.id=? AND s.id=? AND s.user_id=?",
        (topic_id, subject_id, user_id)).fetchone()[0]
    if count != 1:
        return False
    return db.execute(
        "DELETE FROM topic_prereqs WHERE topic_id=? AND prereq_id=?",
        (topic_id, prereq_id)).rowcount == 1


def list_prereqs(
    db: sqlite3.Connection,
    user_id: int,
    subject_id: int,
) -> list[dict]:
    """All confirmed prerequisite edges for this subject."""
    rows = db.execute(
        "SELECT tp.topic_id, t1.name AS topic_name, tp.prereq_id, t2.name AS prereq_name, tp.confirmed "
        "FROM topic_prereqs tp "
        "JOIN topics t1 ON t1.id=tp.topic_id "
        "JOIN topics t2 ON t2.id=tp.prereq_id "
        "JOIN subjects s ON s.id=t1.subject_id "
        "WHERE t1.subject_id=? AND s.user_id=? ORDER BY t1.ordinal",
        (subject_id, user_id)).fetchall()
    return [dict(r) for r in rows]

