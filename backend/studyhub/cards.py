"""Spaced repetition for practice questions (the SM-2 idea): a card you know comes back later and later; one you miss comes back soon."""
from __future__ import annotations

import sqlite3
import time

DAY = 86400.0
GRADES = {"again": 1, "hard": 3, "good": 4, "easy": 5}
NEW_PER_SESSION = 10
SESSION_MAX = 20


def schedule(ease: float, interval_days: float, reps: int, lapses: int, grade: str, now: float) -> dict:
    """The next state of a card after the student rated their recall. `again` returns in 10 minutes."""
    q = GRADES[grade]
    if q < 3:
        return {"ease": max(1.3, ease - 0.2), "interval_days": 10 / 1440, "reps": 0, "lapses": lapses + 1, "due": now + 600}
    reps += 1
    if reps == 1:
        interval = 1.0 if grade != "easy" else 3.0
    elif reps == 2:
        interval = 3.0 if grade != "hard" else 2.0
    else:
        interval = max(1.0, interval_days * ease * (0.85 if grade == "hard" else 1.3 if grade == "easy" else 1.0))
    ease = max(1.3, ease + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    return {"ease": ease, "interval_days": interval, "reps": reps, "lapses": lapses, "due": now + interval * DAY}


def due_cards(db: sqlite3.Connection, user_id: int, subject_id: int, now: float | None = None) -> dict:
    """Cards to study now: overdue ones first, then a few new ones. Only this user's questions in this subject."""
    now = time.time() if now is None else now
    rows = db.execute(
        "SELECT m.id, m.question, m.options, m.topic_path, c.due, c.reps FROM mcq_items m JOIN subjects s ON s.id=m.subject_id "
        "LEFT JOIN card_reviews c ON c.item_id=m.id AND c.user_id=? WHERE m.subject_id=? AND s.user_id=? ORDER BY m.id", (user_id, subject_id, user_id)).fetchall()
    import json
    due = sorted([r for r in rows if r["due"] is not None and r["due"] <= now], key=lambda r: r["due"])
    new = [r for r in rows if r["due"] is None][:NEW_PER_SESSION]
    later = [r["due"] for r in rows if r["due"] is not None and r["due"] > now]
    cards = [{"item_id": r["id"], "question": r["question"], "options": json.loads(r["options"]), "topic": r["topic_path"] or "", "is_new": r["due"] is None}
             for r in (due + new)[:SESSION_MAX]]
    return {"cards": cards, "total": len(rows), "due": len(due), "new": len([r for r in rows if r["due"] is None]), "next_due": min(later) if later else None}


def review(db: sqlite3.Connection, user_id: int, subject_id: int, item_id: int, grade: str, now: float | None = None) -> dict | None:
    """Record a rating for one of this user's questions. None if the question is not theirs or the grade is unknown."""
    if grade not in GRADES:
        return None
    now = time.time() if now is None else now
    owns = db.execute("SELECT 1 FROM mcq_items m JOIN subjects s ON s.id=m.subject_id WHERE m.id=? AND m.subject_id=? AND s.user_id=?", (item_id, subject_id, user_id)).fetchone()
    if owns is None:
        return None
    cur = db.execute("SELECT ease, interval_days, reps, lapses FROM card_reviews WHERE user_id=? AND item_id=?", (user_id, item_id)).fetchone()
    nxt = schedule(cur["ease"] if cur else 2.5, cur["interval_days"] if cur else 0.0, cur["reps"] if cur else 0, cur["lapses"] if cur else 0, grade, now)
    db.execute(
        "INSERT INTO card_reviews(user_id, item_id, ease, interval_days, reps, lapses, due, last_at) VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(user_id, item_id) DO UPDATE SET ease=excluded.ease, interval_days=excluded.interval_days, reps=excluded.reps, "
        "lapses=excluded.lapses, due=excluded.due, last_at=excluded.last_at",
        (user_id, item_id, nxt["ease"], nxt["interval_days"], nxt["reps"], nxt["lapses"], nxt["due"], now))
    return nxt
