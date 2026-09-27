"""Quiz attempt scoring — pure SQL and arithmetic, no LLM.

Every public function takes a sqlite3.Connection and user_id so ownership is
always enforced.  Nothing here talks to a model.

Mastery rule (mirroring ai_learnmate WeakTopicPredictor heuristic):
  answered >= 2 and correct/answered >= MASTERY_THRESHOLD -> 'mastered'
  answered >= 2 and correct/answered <  WEAK_THRESHOLD   -> 'weak'
  else -> 'learning'

Behavior score (adapted from ai_learnmate ProctoringEvent severity):
  Starts at 100; each proctoring event deducts its severity.  Floor = 0.
"""
from __future__ import annotations

import json
import sqlite3
import time

# ── Mastery thresholds (code decides, not the model) ─────────────────────────
MASTERY_THRESHOLD = 0.70   # >= 70% correct on this topic -> mastered
WEAK_THRESHOLD    = 0.40   # <  40% correct on this topic -> weak
MIN_ANSWERED      = 2      # need at least this many answers before classifying

# ── Proctoring event severity (mirrors ai_learnmate ProctoringEvent.save) ────
SEVERITY: dict[str, int] = {
    "tab_switch":       60,
    "full_screen_exit": 30,
    "copy_attempt":     20,
    "paste_attempt":    20,
    "browser_resize":   10,
    "auto_submit":       0,   # informational only
}


# ── Confidence from response behaviour (from ai_learnmate Response.save) ─────

def compute_confidence(response_time: float, hesitation_count: int) -> float:
    """0–1 confidence estimate purely from timing + hesitation."""
    if response_time < 5 and hesitation_count == 0:
        return 0.9
    if response_time < 10 and hesitation_count <= 1:
        return 0.7
    if response_time < 20 and hesitation_count <= 2:
        return 0.5
    return 0.3


# ── Attempt helpers ───────────────────────────────────────────────────────────

def _own_attempt(db: sqlite3.Connection, user_id: int, attempt_id: int) -> dict | None:
    """Return the attempt row or None if it doesn't belong to this user."""
    row = db.execute(
        "SELECT * FROM quiz_attempts WHERE id=? AND user_id=?",
        (attempt_id, user_id)).fetchone()
    return dict(row) if row else None


def record_answer(
    db: sqlite3.Connection,
    user_id: int,
    attempt_id: int,
    item_id: int,
    chosen_index: int | None,
    response_time: float,
    hesitation_count: int,
    answer_row_id: int | None = None,
) -> dict | None:
    """Answer ONE queued question of this user's active attempt.

    The answer UPDATES the row queued for (attempt, item): that row must belong to this attempt, be for this item, be
    unanswered, and (if given) have id `answer_row_id`; the item must belong to the attempt's subject. Anything else returns
    None and changes nothing, so an item id copied from another attempt, subject or user cannot score, and a question can be
    answered only once. chosen_index=None records a skip (the row is closed, no score); a choice outside 0-3 is refused.
    Returns the updated attempt, or None.
    """
    attempt = _own_attempt(db, user_id, attempt_id)
    if attempt is None or not attempt["is_active"]:
        return None
    if chosen_index is not None and not 0 <= chosen_index <= 3:
        return None
    queued = db.execute(
        "SELECT aa.id AS row_id, mi.answer_index, mi.topic_id FROM attempt_answers aa "
        "JOIN mcq_items mi ON mi.id = aa.item_id "
        "WHERE aa.attempt_id=? AND aa.item_id=? AND aa.answered_at IS NULL AND mi.subject_id=? "
        "AND (? IS NULL OR aa.id=?) ORDER BY aa.id LIMIT 1",
        (attempt_id, item_id, attempt["subject_id"], answer_row_id, answer_row_id)).fetchone()
    if queued is None:
        return None

    is_correct: int | None = None
    if chosen_index is not None:
        is_correct = 1 if chosen_index == queued["answer_index"] else 0
    cur = db.execute(
        "UPDATE attempt_answers SET chosen_index=?, is_correct=?, response_time=?, hesitation_count=?, "
        "confidence_level=?, answered_at=? WHERE id=? AND answered_at IS NULL",
        (chosen_index, is_correct, response_time, hesitation_count,
         compute_confidence(response_time, hesitation_count), time.time(), queued["row_id"]))
    if cur.rowcount != 1:
        return None

    correct_delta, incorrect_delta = (1 if is_correct == 1 else 0), (1 if is_correct == 0 else 0)
    db.execute(
        "UPDATE quiz_attempts SET correct_answers=correct_answers+?, incorrect_answers=incorrect_answers+?, "
        "score=score+?, max_score=max_score+1 WHERE id=?",
        (correct_delta, incorrect_delta, correct_delta, attempt_id))
    _refresh_avg_time(db, attempt_id)
    if queued["topic_id"]:
        _refresh_topic_progress(db, user_id, attempt["subject_id"], queued["topic_id"])
    return _own_attempt(db, user_id, attempt_id)


def _refresh_avg_time(db: sqlite3.Connection, attempt_id: int) -> None:
    row = db.execute(
        "SELECT AVG(response_time) FROM attempt_answers WHERE attempt_id=? AND response_time IS NOT NULL",
        (attempt_id,)).fetchone()
    avg = row[0] or 0.0
    db.execute("UPDATE quiz_attempts SET avg_response_time=? WHERE id=?", (avg, attempt_id))


def _refresh_topic_progress(
    db: sqlite3.Connection,
    user_id: int,
    subject_id: int,
    topic_id: int,
) -> None:
    """Recompute mastery for one topic from all this user's attempt_answers."""
    row = db.execute(
        "SELECT COUNT(*) AS answered, SUM(is_correct) AS correct "
        "FROM attempt_answers aa "
        "JOIN quiz_attempts qa ON qa.id = aa.attempt_id "
        "JOIN mcq_items mi ON mi.id = aa.item_id "
        "WHERE qa.user_id=? AND qa.subject_id=? AND mi.topic_id=? AND aa.is_correct IS NOT NULL",
        (user_id, subject_id, topic_id)).fetchone()

    answered = row["answered"] or 0
    correct  = int(row["correct"] or 0)

    if answered < MIN_ANSWERED:
        state   = "unknown"
        mastery = 0.0
    else:
        ratio   = correct / answered
        mastery = round(ratio, 4)
        if ratio >= MASTERY_THRESHOLD:
            state = "mastered"
        elif ratio < WEAK_THRESHOLD:
            state = "weak"
        else:
            state = "learning"

    db.execute(
        "INSERT INTO topic_progress(user_id, subject_id, topic_id, answered, correct, mastery, state, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(user_id, subject_id, topic_id) DO UPDATE SET "
        "answered=excluded.answered, correct=excluded.correct, mastery=excluded.mastery, "
        "state=excluded.state, updated_at=excluded.updated_at",
        (user_id, subject_id, topic_id, answered, correct, mastery, state, time.time()))


# ── Proctoring ────────────────────────────────────────────────────────────────

def record_proctoring_event(
    db: sqlite3.Connection,
    user_id: int,
    attempt_id: int,
    event_type: str,
    details: dict | None = None,
) -> bool:
    """Record one browser-side proctoring event and deduct from behavior_score.

    Returns False if attempt_id doesn't belong to the user.
    """
    attempt = _own_attempt(db, user_id, attempt_id)
    if attempt is None or event_type not in SEVERITY:      # unknown types are refused, not passed to the database
        return False

    severity = SEVERITY[event_type]
    db.execute(
        "INSERT INTO quiz_proctoring_events(attempt_id, event_type, severity, details_json, captured_at) "
        "VALUES (?,?,?,?,?)",
        (attempt_id, event_type, severity, json.dumps(details if isinstance(details, dict) else {})[:500], time.time()))

    # Update attempt counters
    col_map = {
        "tab_switch":       "total_tab_switches",
        "full_screen_exit": "total_fullscreen_exits",
        "copy_attempt":     "total_copy_attempts",
        "paste_attempt":    "total_copy_attempts",  # same counter
    }
    col = col_map.get(event_type)
    if col:
        db.execute(f"UPDATE quiz_attempts SET {col}={col}+1 WHERE id=?", (attempt_id,))

    # Deduct severity from behavior_score (floor 0)
    if severity:
        db.execute(
            "UPDATE quiz_attempts SET behavior_score=MAX(0, behavior_score-?) WHERE id=?",
            (severity, attempt_id))

    return True


def trust_score(db: sqlite3.Connection, user_id: int, attempt_id: int) -> int | None:
    """Returns 0-100 trust score, or None if not the user's attempt."""
    row = db.execute(
        "SELECT behavior_score FROM quiz_attempts WHERE id=? AND user_id=?",
        (attempt_id, user_id)).fetchone()
    if row is None:
        return None
    return max(0, min(100, round(row["behavior_score"])))


# ── Finishing an attempt ──────────────────────────────────────────────────────

def finish_attempt(db: sqlite3.Connection, user_id: int, attempt_id: int) -> dict | None:
    """Mark attempt finished. Returns final summary or None if not the user's."""
    attempt = _own_attempt(db, user_id, attempt_id)
    if attempt is None:
        return None
    db.execute(
        "UPDATE quiz_attempts SET is_active=0, finished_at=? WHERE id=? AND user_id=?",
        (time.time(), attempt_id, user_id))
    return _own_attempt(db, user_id, attempt_id)


# ── Weak-topic detection (SQL heuristic, no ML dependency) ───────────────────

def weak_topics(
    db: sqlite3.Connection,
    user_id: int,
    subject_id: int,
    limit: int = 5,
) -> list[dict]:
    """Top-N topics by weakness_score = 1 - (correct/answered).
    Returns [] if no answers yet.  No sklearn required.
    """
    rows = db.execute(
        "SELECT tp.topic_id, t.name AS topic_name, t.path AS topic_path, "
        "tp.answered, tp.correct, tp.mastery, tp.state "
        "FROM topic_progress tp "
        "JOIN topics t ON t.id = tp.topic_id "
        "WHERE tp.user_id=? AND tp.subject_id=? AND tp.answered>=? "
        "ORDER BY tp.mastery ASC LIMIT ?",
        (user_id, subject_id, MIN_ANSWERED, limit)).fetchall()
    return [dict(r) for r in rows]


def progress_summary(
    db: sqlite3.Connection,
    user_id: int,
    subject_id: int,
) -> list[dict]:
    """All topic_progress rows for this user+subject, with topic name."""
    rows = db.execute(
        "SELECT tp.topic_id, t.name, t.path, tp.answered, tp.correct, tp.mastery, tp.state "
        "FROM topic_progress tp JOIN topics t ON t.id=tp.topic_id "
        "WHERE tp.user_id=? AND tp.subject_id=? ORDER BY t.ordinal",
        (user_id, subject_id)).fetchall()
    return [dict(r) for r in rows]

