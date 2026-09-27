"""Quiz state machine — 4 states: QUESTIONING → EVALUATING → BACKWARD_PASS → COMPLETE.

Ported from tracer/flow.py (agentic-slice-kit) and adapted for the StudyHub
web environment:
  - No blocking input() calls. The web handler calls one step at a time and
    persists state in the quiz_attempts table between HTTP requests.
  - All LLM callables are injected so tests can replace them with stubs.
  - All DB writes go through the Repo / scoring module so ownership is enforced.

State is stored in quiz_attempts columns:
  topic_stack_json       — JSON list of topic_id ints (top of stack = current)
  depth                  — how many BACKWARD_PASS steps taken this session
  topics_verified_json   — topic_ids that received PASS
  callback_state         — none | waiting | step_back | retry | timeout
  current_difficulty     — 1-3, increases on RETRY for same topic
  is_active              — 1 while in progress, 0 when COMPLETE
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Callable, Any

from . import prereq as prereq_mod
from . import scoring

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60   # seconds before auto-STEP_BACK on callback page


# ── State step results ────────────────────────────────────────────────────────

class StepResult:
    """Returned by each advance_* function so the web layer knows what to render."""
    __slots__ = ("state", "topic_id", "topic_name", "question", "verdict",
                 "prereq_id", "prereq_name", "depth", "complete_summary")

    def __init__(self, state: str, **kw):
        self.state = state          # questioning | evaluating | backward_pass | complete | error
        self.topic_id: int | None   = kw.get("topic_id")
        self.topic_name: str        = kw.get("topic_name", "")
        self.question: str          = kw.get("question", "")
        self.verdict: str           = kw.get("verdict", "")        # PASS | BLOCK
        self.prereq_id: int | None  = kw.get("prereq_id")
        self.prereq_name: str       = kw.get("prereq_name", "")
        self.depth: int             = kw.get("depth", 0)
        self.complete_summary: dict = kw.get("complete_summary", {})

    def as_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_attempt(db: sqlite3.Connection, user_id: int, attempt_id: int) -> dict | None:
    row = db.execute(
        "SELECT * FROM quiz_attempts WHERE id=? AND user_id=?",
        (attempt_id, user_id)).fetchone()
    return dict(row) if row else None


def _save_stack(db: sqlite3.Connection, attempt_id: int,
                stack: list[int], depth: int,
                verified: list[int], difficulty: int,
                callback_state: str = "none") -> None:
    db.execute(
        "UPDATE quiz_attempts SET topic_stack_json=?, depth=?, topics_verified_json=?, "
        "current_difficulty=?, callback_state=? WHERE id=?",
        (json.dumps(stack), depth, json.dumps(verified), difficulty, callback_state, attempt_id))


def _load_state(attempt: dict) -> tuple[list[int], int, list[int], int]:
    stack    = json.loads(attempt["topic_stack_json"] or "[]")
    depth    = attempt["depth"]
    verified = json.loads(attempt["topics_verified_json"] or "[]")
    diff     = attempt["current_difficulty"]
    return stack, depth, verified, diff


def _topic_info(db: sqlite3.Connection, topic_id: int) -> dict | None:
    row = db.execute("SELECT id, name, path, subject_id FROM topics WHERE id=?", (topic_id,)).fetchone()
    return dict(row) if row else None


# ── Session creation ──────────────────────────────────────────────────────────

def start_session(
    db: sqlite3.Connection,
    user_id: int,
    subject_id: int,
    root_topic_id: int,
    item_ids: list[int],
    *,
    attempt_number: int = 1,
) -> dict | None:
    """Create a new quiz_attempts row and return it.

    item_ids = list of mcq_items the student will answer (already filtered by
               topic, shuffled externally so this function is pure).
    Returns None if the topic doesn't belong to this user's subject.
    """
    topic = _topic_info(db, root_topic_id)
    if topic is None or topic["subject_id"] != subject_id:
        return None
    # Verify subject ownership
    owns = db.execute("SELECT 1 FROM subjects WHERE id=? AND user_id=?",
                      (subject_id, user_id)).fetchone()
    if owns is None:
        return None

    attempt_id = db.execute(
        "INSERT INTO quiz_attempts(user_id, subject_id, topic_ids_json, started_at, "
        "topic_stack_json, topics_verified_json, attempt_number, callback_state, current_difficulty) "
        "VALUES (?,?,?,?,?,?,?,'none',1)",
        (user_id, subject_id,
         json.dumps([root_topic_id]),
         time.time(),
         json.dumps([root_topic_id]),
         json.dumps([]),
         1)).lastrowid

    # Queue MCQ items as attempt_answers rows (not yet answered)
    for item_id in item_ids:
        db.execute(
            "INSERT INTO attempt_answers(attempt_id, item_id) VALUES (?,?)",
            (attempt_id, item_id))

    return _get_attempt(db, user_id, int(attempt_id))


# ── Step: get current question ────────────────────────────────────────────────

def current_question(
    db: sqlite3.Connection,
    user_id: int,
    attempt_id: int,
    generate_fn: Callable,
) -> StepResult:
    """QUESTIONING state: generate a diagnostic question for the top topic.

    generate_fn(topic_id, topic_name, difficulty, prior_objections) -> str
    """
    attempt = _get_attempt(db, user_id, attempt_id)
    if attempt is None:
        return StepResult("error")
    if not attempt["is_active"]:
        return StepResult("complete", complete_summary=_build_summary(db, attempt))

    stack, depth, verified, diff = _load_state(attempt)
    if not stack:
        return _complete(db, user_id, attempt_id, attempt)

    topic_id = stack[-1]
    topic    = _topic_info(db, topic_id)
    if topic is None:
        return StepResult("error")

    # Skip already-verified topics (resume behaviour from tracer/flow.py)
    if topic_id in verified:
        stack.pop()
        _save_stack(db, attempt_id, stack, depth, verified, diff)
        return current_question(db, user_id, attempt_id, generate_fn)

    # Collect prior objections for this topic
    prior_verdicts = _prior_verdicts(db, attempt_id, topic_id)
    prior_objections = [o for v in prior_verdicts for o in v.get("objections", [])]

    question = generate_fn(
        topic_id=topic_id,
        topic_name=topic["name"],
        difficulty=diff,
        prior_objections=prior_objections,
    )

    # Persist the generated question so the evaluator can reference it
    db.execute(
        "UPDATE quiz_attempts SET callback_state='none' WHERE id=?", (attempt_id,))

    return StepResult(
        "questioning",
        topic_id=topic_id,
        topic_name=topic["name"],
        question=question,
        depth=depth,
    )


# ── Step: submit answer ───────────────────────────────────────────────────────

def submit_answer(
    db: sqlite3.Connection,
    user_id: int,
    attempt_id: int,
    question: str,
    student_answer: str,
    evaluate_fn: Callable,
) -> StepResult:
    """EVALUATING state: evaluate the answer, update state, return next step.

    evaluate_fn(topic_id, topic_name, question, student_answer,
                prior_verdicts, prereq_id, graph) -> dict
    """
    attempt = _get_attempt(db, user_id, attempt_id)
    if attempt is None or not attempt["is_active"]:
        return StepResult("error")

    stack, depth, verified, diff = _load_state(attempt)
    if not stack:
        return _complete(db, user_id, attempt_id, attempt)

    topic_id = stack[-1]
    topic    = _topic_info(db, topic_id)
    if topic is None:
        return StepResult("error")

    # Load prerequisite graph for this subject
    graph = prereq_mod.load_graph(db, attempt["subject_id"])

    prior_verdicts   = _prior_verdicts(db, attempt_id, topic_id)
    prereq_id        = prereq_mod.prereq_of(graph, topic_id)

    verdict = evaluate_fn(
        topic_id=topic_id,
        topic_name=topic["name"],
        question=question,
        student_answer=student_answer,
        prior_verdicts=prior_verdicts,
        prereq_id=prereq_id,
        graph=graph,
    )

    # Store verdict in spine-style JSON column on the attempt row
    _append_verdict(db, attempt_id, verdict)

    if verdict["status"] == "PASS":
        verified = verified + [topic_id]
        stack.pop()
        _save_stack(db, attempt_id, stack, depth, verified, diff)
        if not stack:
            return _complete(db, user_id, attempt_id, _get_attempt(db, user_id, attempt_id))
        return StepResult("questioning", topic_id=stack[-1] if stack else None, depth=depth)

    # BLOCK — decide whether backward pass is possible
    v_prereq_id = verdict.get("prerequisite_id")
    can_back = prereq_mod.can_step_back(graph, topic_id, depth, verified)

    if not can_back:
        # No deeper prerequisite — just retry with harder question
        new_diff = min(diff + 1, 3)
        _save_stack(db, attempt_id, stack, depth, verified, new_diff)
        return StepResult(
            "questioning",
            topic_id=topic_id,
            topic_name=topic["name"],
            verdict="BLOCK",
            depth=depth,
        )

    # Show backward-pass callback page
    p_name = prereq_mod.prereq_label(graph, v_prereq_id)
    _save_stack(db, attempt_id, stack, depth, verified, diff, callback_state="waiting")

    return StepResult(
        "backward_pass",
        topic_id=topic_id,
        topic_name=topic["name"],
        verdict="BLOCK",
        prereq_id=v_prereq_id,
        prereq_name=p_name,
        depth=depth,
    )


# ── Step: backward-pass callback ──────────────────────────────────────────────

def resolve_callback(
    db: sqlite3.Connection,
    user_id: int,
    attempt_id: int,
    decision: str,          # "step_back" | "retry" | "timeout"
) -> StepResult:
    """BACKWARD_PASS state: record the student's STEP_BACK / RETRY decision."""
    attempt = _get_attempt(db, user_id, attempt_id)
    if attempt is None or not attempt["is_active"]:
        return StepResult("error")
    if attempt["callback_state"] != "waiting":
        return StepResult("error")

    stack, depth, verified, diff = _load_state(attempt)
    if not stack:
        return _complete(db, user_id, attempt_id, attempt)

    topic_id = stack[-1]
    graph    = prereq_mod.load_graph(db, attempt["subject_id"])

    if decision in ("step_back", "timeout"):
        if decision == "timeout":
            db.execute("UPDATE quiz_attempts SET had_timeout=1 WHERE id=?", (attempt_id,))
        prereq_id = prereq_mod.prereq_of(graph, topic_id)
        if prereq_id and prereq_id in graph:
            stack.append(prereq_id)
            depth += 1
        _save_stack(db, attempt_id, stack, depth, verified, diff, callback_state="none")
        next_topic = _topic_info(db, stack[-1]) if stack else None
        return StepResult(
            "questioning",
            topic_id=stack[-1] if stack else None,
            topic_name=next_topic["name"] if next_topic else "",
            depth=depth,
        )
    else:
        # RETRY — stay on same topic, increase difficulty
        new_diff = min(diff + 1, 3)
        _save_stack(db, attempt_id, stack, depth, verified, new_diff, callback_state="none")
        topic = _topic_info(db, topic_id)
        return StepResult(
            "questioning",
            topic_id=topic_id,
            topic_name=topic["name"] if topic else "",
            depth=depth,
        )


# ── COMPLETE ──────────────────────────────────────────────────────────────────

def _complete(db: sqlite3.Connection, user_id: int, attempt_id: int, attempt: dict) -> StepResult:
    db.execute(
        "UPDATE quiz_attempts SET is_active=0, finished_at=? WHERE id=?",
        (time.time(), attempt_id))
    summary = _build_summary(db, _get_attempt(db, user_id, attempt_id))
    return StepResult("complete", complete_summary=summary)


def _build_summary(db: sqlite3.Connection, attempt: dict) -> dict:
    if attempt is None:
        return {}
    _, depth, verified, _ = _load_state(attempt)
    return {
        "attempt_id":      attempt["id"],
        "subject_id":      attempt["subject_id"],
        "score":           attempt["score"],
        "max_score":       attempt["max_score"],
        "correct":         attempt["correct_answers"],
        "incorrect":       attempt["incorrect_answers"],
        "behavior_score":  round(attempt["behavior_score"]),
        "depth_reached":   depth,
        "topics_verified": verified,
        "had_timeout":     bool(attempt["had_timeout"]),
        "finished_at":     attempt["finished_at"],
    }


# ── Verdict persistence (stored on the attempt row as JSON log) ───────────────

def _prior_verdicts(db: sqlite3.Connection, attempt_id: int, topic_id: int) -> list[dict]:
    """Read verdicts recorded for this attempt + topic from the attempt's log column."""
    row = db.execute(
        "SELECT verdict_log_json FROM quiz_attempts WHERE id=?", (attempt_id,)).fetchone()
    if row is None:
        return []
    log = json.loads(row[0] or "[]") if row[0] else []
    return [v for v in log if v.get("topic_id") == topic_id]


def _append_verdict(db: sqlite3.Connection, attempt_id: int, verdict: dict) -> None:
    """Append one verdict to the JSON log column on the attempt row."""
    row = db.execute(
        "SELECT verdict_log_json FROM quiz_attempts WHERE id=?", (attempt_id,)).fetchone()
    if row is None:
        return
    log = json.loads(row[0] or "[]") if row[0] else []
    log.append(verdict)
    db.execute(
        "UPDATE quiz_attempts SET verdict_log_json=? WHERE id=?",
        (json.dumps(log), attempt_id))

