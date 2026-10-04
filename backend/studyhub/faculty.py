"""Faculty: the human step between AI-drafted questions and officers, and the answer to a contested score.

  * Review queue  - every question the pipeline verified (quote found, independent reader agreed, SymPy recomputed a numeric
                    key) waits as 'pending'. A faculty member approves it, edits then approves it, or rejects it with a note.
                    Officers only ever see approved questions (Repo.list_mcq, cards, backtracking).
  * Contests      - an officer disputes one answer marked wrong ("the key is wrong", "two options are right"). Faculty uphold
                    it (the answer is re-marked correct, the attempt and topic progress are recomputed, and the question is
                    withdrawn from the bank) or reject it with a reason. Either way the officer sees the decision.
  * Insights      - for NSSTA: which interventions close which gaps, across all officers, without naming anyone.

Every change records who made it and when; the request itself is also in the audit log (core.audit).
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections import defaultdict

from . import citations, mcq, scoring

REVIEW_STATES = ("pending", "approved", "rejected")


# ------------------------------------------------------------------------------------------------ review queue

def _item_json(r) -> dict:
    d = dict(r)
    d["options"] = json.loads(d["options"])
    return {k: d.get(k) for k in ("id", "subject_id", "subject", "topic_path", "question", "options", "answer_index", "explanation",
                                  "quote", "doc_title", "page_start", "page_end", "solver", "key_check", "difficulty", "model",
                                  "review", "review_note", "reviewed_by", "reviewed_at", "created_at")}


def review_queue(db: sqlite3.Connection, status: str = "pending", limit: int = 50) -> dict:
    counts = {s: 0 for s in REVIEW_STATES}
    for r in db.execute("SELECT review, COUNT(*) AS n FROM mcq_items GROUP BY review"):
        counts[r["review"]] = int(r["n"])
    rows = db.execute(
        "SELECT m.*, s.name AS subject FROM mcq_items m JOIN subjects s ON s.id=m.subject_id WHERE m.review=? "
        "ORDER BY m.created_at" + (" DESC" if status != "pending" else "") + ", m.id LIMIT ?", (status, limit)).fetchall()
    return {"counts": counts, "items": [_item_json(r) for r in rows]}


def decide(db: sqlite3.Connection, faculty_id: int, item_id: int, decision: str, note: str = "") -> dict | None:
    """Approve or reject one pending (or previously decided) question. None if there is no such question."""
    if decision not in ("approved", "rejected"):
        raise ValueError(decision)
    cur = db.execute("UPDATE mcq_items SET review=?, review_note=?, reviewed_by=?, reviewed_at=? WHERE id=?",
                     (decision, note.strip()[:500], faculty_id, time.time(), item_id))
    if cur.rowcount != 1:
        return None
    return _item_json(db.execute("SELECT m.*, s.name AS subject FROM mcq_items m JOIN subjects s ON s.id=m.subject_id WHERE m.id=?", (item_id,)).fetchone())


def edit(db: sqlite3.Connection, faculty_id: int, item_id: int, *, question: str, options: list[str], answer_index: int,
         explanation: str, note: str = "") -> dict | str | None:
    """Correct a drafted question and approve it. Returns the item, an error message (str), or None if it does not exist."""
    row = db.execute("SELECT subject_id FROM mcq_items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        return None
    q = citations.normalize(question)
    opts = [citations.normalize(o) for o in options]
    if not 12 <= len(q) <= 300:
        return "The question must be 12 to 300 characters."
    if len(opts) != 4 or any(not o or len(o) > 200 for o in opts) or len({o.lower() for o in opts}) != 4:
        return "There must be exactly four different, non-empty options of at most 200 characters."
    if not 0 <= answer_index <= 3:
        return "Choose which option is correct."
    try:
        db.execute("UPDATE mcq_items SET question=?, options=?, answer_index=?, explanation=?, key=?, review='approved', review_note=?, "
                   "reviewed_by=?, reviewed_at=? WHERE id=?",
                   (q, json.dumps(opts), answer_index, citations.normalize(explanation)[:1000], mcq.key_of(q),
                    (note.strip() or "Edited by faculty")[:500], faculty_id, time.time(), item_id))
    except sqlite3.IntegrityError:
        return "The same question is already in this subject's bank."
    return decide(db, faculty_id, item_id, "approved", note.strip() or "Edited by faculty")


# ------------------------------------------------------------------------------------------------ contests

def open_contest(db: sqlite3.Connection, user_id: int, subject_id: int, attempt_id: int, answer_id: int, reason: str) -> dict | str | None:
    """An officer contests one answer that was marked wrong in a finished quiz of theirs. None = not theirs / not found."""
    reason = " ".join((reason or "").split())
    row = db.execute(
        "SELECT aa.id, aa.item_id, aa.is_correct, qa.is_active FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id "
        "WHERE aa.id=? AND aa.attempt_id=? AND qa.user_id=? AND qa.subject_id=?", (answer_id, attempt_id, user_id, subject_id)).fetchone()
    if row is None:
        return None
    if row["is_active"]:
        return "Finish the quiz first; a score can be contested once it is marked."
    if row["is_correct"] != 0:
        return "Only an answer marked wrong can be contested."
    if not 10 <= len(reason) <= 1000:
        return "Say in a sentence or two why the marking is wrong (10 to 1000 characters)."
    try:
        cid = db.execute("INSERT INTO score_contests(user_id, subject_id, attempt_id, answer_id, item_id, reason, created_at) VALUES (?,?,?,?,?,?,?)",
                         (user_id, subject_id, attempt_id, answer_id, row["item_id"], reason, time.time())).lastrowid
    except sqlite3.IntegrityError:
        return "This answer has already been contested."
    return get_contest(db, int(cid))


_CONTEST_SQL = ("SELECT c.*, mi.question, mi.options, mi.answer_index, mi.explanation, mi.quote, mi.doc_title, mi.topic_path, "
                "aa.chosen_index, s.name AS subject FROM score_contests c JOIN mcq_items mi ON mi.id=c.item_id "
                "JOIN attempt_answers aa ON aa.id=c.answer_id JOIN subjects s ON s.id=c.subject_id ")


def _contest_json(r) -> dict:
    d = dict(r)
    d["options"] = json.loads(d["options"])
    return d


def get_contest(db: sqlite3.Connection, contest_id: int) -> dict | None:
    r = db.execute(_CONTEST_SQL + "WHERE c.id=?", (contest_id,)).fetchone()
    return _contest_json(r) if r else None


def list_contests(db: sqlite3.Connection, *, user_id: int | None = None, status: str | None = None, attempt_id: int | None = None,
                  limit: int = 100) -> list[dict]:
    """A faculty member's queue (user_id=None) or one officer's own contests."""
    sql, args = _CONTEST_SQL + "WHERE 1=1", []
    for col, val in (("c.user_id", user_id), ("c.status", status), ("c.attempt_id", attempt_id)):
        if val is not None:
            sql += f" AND {col}=?"
            args.append(val)
    return [_contest_json(r) for r in db.execute(sql + " ORDER BY c.created_at, c.id LIMIT ?", (*args, limit)).fetchall()]


def resolve(db: sqlite3.Connection, faculty_id: int, contest_id: int, decision: str, resolution: str) -> dict | str | None:
    """Uphold (re-mark the answer correct, recompute the attempt and topic progress, withdraw the question) or reject."""
    if decision not in ("upheld", "rejected"):
        return "The decision must be upheld or rejected."
    resolution = " ".join((resolution or "").split())
    if not 5 <= len(resolution) <= 1000:
        return "Write the reason for the decision (5 to 1000 characters); the officer will read it."
    c = get_contest(db, contest_id)
    if c is None:
        return None
    if c["status"] != "open":
        return "This contest has already been decided."
    now = time.time()
    db.execute("BEGIN")
    try:
        cur = db.execute("UPDATE score_contests SET status=?, resolution=?, resolved_by=?, resolved_at=? WHERE id=? AND status='open'",
                         (decision, resolution, faculty_id, now, contest_id))
        if cur.rowcount != 1:
            db.execute("ROLLBACK")
            return "This contest has already been decided."
        if decision == "upheld":
            if db.execute("UPDATE attempt_answers SET is_correct=1 WHERE id=? AND is_correct=0", (c["answer_id"],)).rowcount == 1:
                db.execute("UPDATE quiz_attempts SET correct_answers=correct_answers+1, incorrect_answers=incorrect_answers-1, score=score+1 "
                           "WHERE id=?", (c["attempt_id"],))
            db.execute("UPDATE mcq_items SET review='rejected', review_note=?, reviewed_by=?, reviewed_at=? WHERE id=?",
                       (f"Withdrawn: contest #{contest_id} upheld. {resolution}"[:500], faculty_id, now, c["item_id"]))
            topic = db.execute("SELECT topic_id FROM mcq_items WHERE id=?", (c["item_id"],)).fetchone()
            if topic and topic["topic_id"]:
                scoring._refresh_topic_progress(db, c["user_id"], c["subject_id"], topic["topic_id"])
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return get_contest(db, contest_id)


# ------------------------------------------------------------------------------------------------ NSSTA insights

def insights(db: sqlite3.Connection) -> dict:
    """Which interventions close which gaps, across every officer (no names): verified outcomes per kind and per topic, plus the
    state of the question bank and of contests."""
    kinds: dict[str, dict] = defaultdict(lambda: {"tried": 0, "verified": 0, "improved": 0, "gain": 0.0})
    topics: dict[str, dict] = defaultdict(lambda: {"tried": 0, "verified": 0, "improved": 0, "best": defaultdict(int)})
    for r in db.execute("SELECT i.kind, i.outcome, i.conf_before, i.conf_after, t.name AS topic FROM interventions i "
                        "JOIN topics t ON t.id=i.topic_id WHERE i.status='done'"):
        k, t = kinds[r["kind"]], topics[r["topic"]]
        k["tried"] += 1
        t["tried"] += 1
        if r["outcome"]:
            k["verified"] += 1
            t["verified"] += 1
            k["gain"] += (r["conf_after"] or 0) - (r["conf_before"] or 0)
        if r["outcome"] == "improved":
            k["improved"] += 1
            t["improved"] += 1
            t["best"][r["kind"]] += 1
    by_kind = [{"kind": kind, **{x: v[x] for x in ("tried", "verified", "improved")},
                "closes_rate": round(v["improved"] / v["verified"], 2) if v["verified"] else None,
                "avg_gain": round(v["gain"] / v["verified"], 3) if v["verified"] else None}
               for kind, v in sorted(kinds.items(), key=lambda kv: -kv[1]["improved"])]
    by_topic = [{"topic": name, "tried": v["tried"], "verified": v["verified"], "improved": v["improved"],
                 "works_best": max(v["best"], key=v["best"].get) if v["best"] else None}
                for name, v in sorted(topics.items(), key=lambda kv: (-kv[1]["improved"], kv[0]))][:25]
    bank = {s: 0 for s in REVIEW_STATES}
    for r in db.execute("SELECT review, COUNT(*) AS n FROM mcq_items GROUP BY review"):
        bank[r["review"]] = int(r["n"])
    contests = {s: 0 for s in ("open", "upheld", "rejected")}
    for r in db.execute("SELECT status, COUNT(*) AS n FROM score_contests GROUP BY status"):
        contests[r["status"]] = int(r["n"])
    officers = db.execute("SELECT COUNT(*) FROM users WHERE role='officer'").fetchone()[0]
    sympy = db.execute("SELECT COUNT(*) FROM mcq_items WHERE key_check<>''").fetchone()[0]
    return {"officers": int(officers), "interventions": by_kind, "topics": by_topic, "question_bank": bank,
            "sympy_checked": int(sympy), "contests": contests}
