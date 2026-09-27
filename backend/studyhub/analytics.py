"""Cross-subject analytics for the Analytics page, the data tables and the exported reports.

Every query is scoped to one user in its SQL (the same rule as repo.py) and every number comes from rows the student
produced: answers, quizzes, questions asked, flashcard reviews, focus events. Nothing is estimated except where a function
says so (ability and confidence come from the Bayesian IRT model in insights.py).
"""
from __future__ import annotations

import sqlite3
import time
from collections import defaultdict

from . import foresight, insights, patterns, roadmap
from .repo import Repo

DAY = 86400


def _iso(ts) -> str | None:
    return None if ts is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _day(ts) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def _subjects(db: sqlite3.Connection, user_id: int, subject_id: int | None) -> list[dict]:
    subs = Repo(db).list_subjects(user_id)
    return [s for s in subs if subject_id is None or s["id"] == subject_id]


# ---------------------------------------------------------------------------------------------------- tables

def attempts_table(db: sqlite3.Connection, user_id: int, subject_id: int | None = None, limit: int = 2000) -> list[dict]:
    """One row per finished quiz, newest first."""
    sql = ("SELECT qa.*, s.name AS subject FROM quiz_attempts qa JOIN subjects s ON s.id=qa.subject_id AND s.user_id=qa.user_id "
           "WHERE qa.user_id=? AND qa.is_active=0 AND qa.correct_answers+qa.incorrect_answers>0" + (" AND qa.subject_id=?" if subject_id else "")
           + " ORDER BY qa.finished_at DESC, qa.id DESC LIMIT ?")
    args = (user_id, subject_id, limit) if subject_id else (user_id, limit)
    out = []
    for r in db.execute(sql, args).fetchall():
        c, w = int(r["correct_answers"]), int(r["incorrect_answers"])
        dur = (r["finished_at"] - r["started_at"]) if r["finished_at"] and r["started_at"] else None
        out.append({"id": r["id"], "subject_id": r["subject_id"], "subject": r["subject"], "mode": r["mode"] or "practice", "kind": r["kind"] or "standard",
                    "started_at": _iso(r["started_at"]), "finished_at": _iso(r["finished_at"]), "duration_min": round(dur / 60, 1) if dur else None,
                    "answered": c + w, "correct": c, "accuracy": round(100 * c / (c + w), 1) if c + w else None,
                    "avg_seconds": round(r["avg_response_time"], 1) if r["avg_response_time"] else None, "behavior_score": round(r["behavior_score"]),
                    "tab_switches": r["total_tab_switches"], "fullscreen_exits": r["total_fullscreen_exits"], "copy_attempts": r["total_copy_attempts"]})
    return out


def topics_table(db: sqlite3.Connection, user_id: int, subject_id: int | None = None) -> list[dict]:
    """One row per topic with material: IRT confidence and ability, accuracy, status against the target, drift, last practised."""
    out = []
    for s in _subjects(db, user_id, subject_id):
        info = roadmap.skill_gaps(db, user_id, s["id"], s.get("level"))
        conf = insights.topic_confidence(db, user_id, s["id"])["topics"]
        drift = patterns.drift(db, user_id, s["id"])
        for g in info["gaps"]:
            e = conf.get(g["topic_id"]) or {}
            d = drift.get(g["topic_id"]) or {}
            out.append({"subject_id": s["id"], "subject": s["name"], "topic_id": g["topic_id"], "topic": g["name"], "path": g["path"],
                        "answered": g["answered"], "correct": g["correct"], "accuracy": round(100 * g["correct"] / g["answered"], 1) if g["answered"] else None,
                        "confidence": round(100 * g["confidence"], 1) if g["confidence"] is not None else None, "theta": e.get("theta"), "se": e.get("se"),
                        "label": e.get("label", "untried"), "status": g["status"], "target": round(100 * g["target"]), "trend": g["trend"],
                        "drift": d.get("state", "none"), "days_since": d.get("days_since"), "avg_seconds": g["avg_seconds"], "exam_count": g.get("exam_count", 0)})
    return out


def questions_table(db: sqlite3.Connection, user_id: int, subject_id: int | None = None, limit: int = 2000) -> list[dict]:
    sql = ("SELECT d.id, d.subject_id, s.name AS subject, d.question, d.status, d.tier, d.model, d.feedback, d.saved, d.created_at, d.finished_at, "
           "(SELECT COUNT(*) FROM doubt_claims c WHERE c.doubt_id=d.id) AS statements "
           "FROM doubts d JOIN subjects s ON s.id=d.subject_id AND s.user_id=d.user_id WHERE d.user_id=?" + (" AND d.subject_id=?" if subject_id else "")
           + " ORDER BY d.created_at DESC LIMIT ?")
    args = (user_id, subject_id, limit) if subject_id else (user_id, limit)
    return [{"id": r["id"], "subject_id": r["subject_id"], "subject": r["subject"], "question": r["question"], "status": r["status"], "tier": r["tier"] or "",
             "model": r["model"] or "", "feedback": r["feedback"] or "", "saved": bool(r["saved"]), "statements": r["statements"],
             "seconds": round(r["finished_at"] - r["created_at"], 1) if r["finished_at"] else None, "created_at": _iso(r["created_at"])}
            for r in db.execute(sql, args).fetchall()]


def materials_table(db: sqlite3.Connection, user_id: int, subject_id: int | None = None) -> list[dict]:
    sql = ("SELECT d.id, d.subject_id, s.name AS subject, d.title, d.kind, d.role, d.pages, d.bytes, d.status, d.ocr_pages, d.created_at, "
           "(SELECT COUNT(*) FROM chunks c WHERE c.document_id=d.id) AS passages, "
           "(SELECT COUNT(*) FROM chunks c JOIN chunk_embeddings ce ON ce.chunk_id=c.id WHERE c.document_id=d.id) AS indexed "
           "FROM documents d JOIN subjects s ON s.id=d.subject_id WHERE s.user_id=?" + (" AND d.subject_id=?" if subject_id else "") + " ORDER BY d.created_at DESC")
    args = (user_id, subject_id) if subject_id else (user_id,)
    return [{"id": r["id"], "subject_id": r["subject_id"], "subject": r["subject"], "title": r["title"], "kind": r["kind"], "role": r["role"], "pages": r["pages"],
             "size_kb": round(r["bytes"] / 1024, 1), "status": r["status"], "ocr_pages": r["ocr_pages"], "passages": r["passages"], "indexed": r["indexed"],
             "created_at": _iso(r["created_at"])} for r in db.execute(sql, args).fetchall()]


TABLES = {"attempts": attempts_table, "topics": topics_table, "questions": questions_table, "materials": materials_table}

COLUMNS = {
    "attempts": [("id", "Quiz"), ("subject", "Subject"), ("mode", "Mode"), ("kind", "Kind"), ("finished_at", "Finished"), ("duration_min", "Minutes"),
                 ("answered", "Answered"), ("correct", "Correct"), ("accuracy", "Accuracy %"), ("avg_seconds", "Avg s/question"), ("behavior_score", "Integrity"),
                 ("tab_switches", "Tab switches"), ("fullscreen_exits", "Fullscreen exits")],
    "topics": [("subject", "Subject"), ("topic", "Topic"), ("answered", "Answered"), ("correct", "Correct"), ("accuracy", "Accuracy %"),
               ("confidence", "Confidence %"), ("theta", "Ability θ"), ("se", "± SE"), ("status", "Status"), ("target", "Target %"), ("trend", "Trend"),
               ("drift", "Drift"), ("days_since", "Days since practice")],
    "questions": [("id", "#"), ("subject", "Subject"), ("question", "Question"), ("status", "Outcome"), ("tier", "Tier"), ("model", "Model"),
                  ("statements", "Cited statements"), ("seconds", "Seconds"), ("feedback", "Feedback"), ("created_at", "Asked")],
    "materials": [("subject", "Subject"), ("title", "Title"), ("kind", "Type"), ("role", "Role"), ("pages", "Pages"), ("size_kb", "KB"), ("passages", "Passages"),
                  ("indexed", "Embedded"), ("ocr_pages", "OCR pages"), ("status", "Status"), ("created_at", "Added")],
}


# ---------------------------------------------------------------------------------------------------- overview

def overview(db: sqlite3.Connection, user_id: int, days: int = 30, subject_id: int | None = None) -> dict:
    days = max(7, min(int(days), 365))
    now = time.time()
    today = int(now) // DAY
    first = today - (days - 1)
    since = first * DAY
    sub_filter = " AND qa.subject_id=?" if subject_id else ""
    sargs = (subject_id,) if subject_id else ()

    # daily timeline: answers, correct, questions asked, flashcards reviewed
    ans = {r["d"]: (r["n"], r["c"] or 0, r["t"]) for r in db.execute(
        "SELECT date(aa.answered_at,'unixepoch') d, COUNT(*) n, SUM(aa.is_correct) c, AVG(aa.response_time) t FROM attempt_answers aa "
        "JOIN quiz_attempts qa ON qa.id=aa.attempt_id WHERE qa.user_id=? AND aa.is_correct IS NOT NULL AND aa.answered_at>=?" + sub_filter + " GROUP BY d",
        (user_id, since, *sargs))}
    asked = dict(db.execute("SELECT date(created_at,'unixepoch') d, COUNT(*) FROM doubts WHERE user_id=? AND created_at>=?"
                            + (" AND subject_id=?" if subject_id else "") + " GROUP BY d", (user_id, since, *sargs)).fetchall())
    cards = dict(db.execute("SELECT date(cr.last_at,'unixepoch') d, COUNT(*) FROM card_reviews cr JOIN mcq_items mi ON mi.id=cr.item_id WHERE cr.user_id=? AND cr.last_at>=?"
                            + (" AND mi.subject_id=?" if subject_id else "") + " GROUP BY d", (user_id, since, *sargs)).fetchall())
    timeline = []
    for n in range(first, today + 1):
        d = _day(n * DAY)
        a = ans.get(d, (0, 0, None))
        timeline.append({"date": d, "answered": a[0], "correct": a[1], "accuracy": round(100 * a[1] / a[0], 1) if a[0] else None,
                         "avg_seconds": round(a[2], 1) if a[2] else None, "asked": asked.get(d, 0), "flashcards": cards.get(d, 0)})

    # weekday x hour habit matrix (UTC) over the window
    habit = [[0] * 24 for _ in range(7)]
    for r in db.execute("SELECT aa.answered_at t FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id "
                        "WHERE qa.user_id=? AND aa.answered_at>=?" + sub_filter, (user_id, since, *sargs)):
        g = time.gmtime(r["t"])
        habit[g.tm_wday][g.tm_hour] += 1

    # difficulty and response-time breakdowns (all time)
    diff = {k: {"answered": 0, "correct": 0} for k in ("easy", "medium", "hard")}
    buckets = {"< 10 s": 0, "10-20 s": 0, "20-40 s": 0, "40-60 s": 0, "> 60 s": 0}
    time_ok = {k: [0, 0] for k in buckets}
    for r in db.execute("SELECT mi.difficulty, aa.is_correct, aa.response_time FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id "
                        "JOIN mcq_items mi ON mi.id=aa.item_id WHERE qa.user_id=? AND aa.is_correct IS NOT NULL" + sub_filter, (user_id, *sargs)):
        k = r["difficulty"] if r["difficulty"] in diff else "medium"
        diff[k]["answered"] += 1
        diff[k]["correct"] += int(r["is_correct"])
        t = r["response_time"]
        if t is not None:
            b = "< 10 s" if t < 10 else "10-20 s" if t < 20 else "20-40 s" if t < 40 else "40-60 s" if t < 60 else "> 60 s"
            buckets[b] += 1
            time_ok[b][0] += 1
            time_ok[b][1] += int(r["is_correct"])

    # per-subject summary with IRT ability, readiness, risk, debt
    subjects = []
    thetas = []
    for s in _subjects(db, user_id, subject_id):
        sid = s["id"]
        conf = insights.topic_confidence(db, user_id, sid)
        info = roadmap.skill_gaps(db, user_id, sid, s.get("level"))
        profile = roadmap.get_profile(db, user_id, sid)
        plan = roadmap.build(info, sid, profile["hours_per_week"], profile["target_date"])
        risk = foresight.risk(info, plan["summary"])["summary"]
        debt = foresight.debt(info)
        o = conf["overall"]
        if o:
            thetas.append(o["theta"])
        row = db.execute("SELECT COALESCE(SUM(correct_answers),0) c, COALESCE(SUM(incorrect_answers),0) w, COUNT(*) n FROM quiz_attempts "
                         "WHERE user_id=? AND subject_id=? AND is_active=0 AND correct_answers+incorrect_answers>0", (user_id, sid)).fetchone()
        subjects.append({"id": sid, "name": s["name"], "level": s.get("level"), "exam_date": s.get("exam_date"),
                         "materials": db.execute("SELECT COUNT(*) FROM documents WHERE subject_id=?", (sid,)).fetchone()[0],
                         "topics": len(info["gaps"]), "quizzes": row["n"], "answered": row["c"] + row["w"], "correct": row["c"],
                         "accuracy": round(100 * row["c"] / (row["c"] + row["w"]), 1) if row["c"] + row["w"] else None,
                         "theta": o["theta"] if o else None, "se": o["se"] if o else None, "confidence": round(100 * o["confidence"], 1) if o else None,
                         "readiness": round(100 * info["readiness"], 1) if info["readiness"] is not None else None, "risk": risk["score"], "risk_level": risk["level"],
                         "debt_hours": debt["total_hours"], "counts": info["counts"]})

    total_answered = sum(x["answered"] for x in timeline)
    total_correct = sum(x["correct"] for x in timeline)
    all_answered = sum(s["answered"] for s in subjects)
    all_correct = sum(s["correct"] for s in subjects)
    focus = {r["event_type"]: r["n"] for r in db.execute(
        "SELECT e.event_type, COUNT(*) n FROM quiz_proctoring_events e JOIN quiz_attempts qa ON qa.id=e.attempt_id WHERE qa.user_id=?" + sub_filter + " GROUP BY e.event_type",
        (user_id, *sargs))}
    integrity = db.execute("SELECT AVG(behavior_score) FROM quiz_attempts qa WHERE qa.user_id=? AND qa.mode='assessment' AND qa.is_active=0" + sub_filter, (user_id, *sargs)).fetchone()[0]
    outcomes = {r[0]: r[1] for r in db.execute("SELECT status, COUNT(*) FROM doubts WHERE user_id=?" + (" AND subject_id=?" if subject_id else "") + " GROUP BY status", (user_id, *sargs))}
    tiers = {(r[0] or "none"): r[1] for r in db.execute("SELECT tier, COUNT(*) FROM doubts WHERE user_id=? AND status!='pending'" + (" AND subject_id=?" if subject_id else "") + " GROUP BY tier", (user_id, *sargs))}
    cloud = [{"date": r["day"], "model": r["model"], "tokens": r["t"]} for r in db.execute(
        "SELECT day, model, SUM(tokens) t FROM cloud_usage WHERE user_id=? AND at>=? GROUP BY day, model ORDER BY day", (user_id, since))]
    active_days = sum(1 for x in timeline if x["answered"] or x["asked"] or x["flashcards"])
    status_counts = defaultdict(int)
    for s in subjects:
        for k, v in s["counts"].items():
            status_counts[k] += v
    return {
        "generated_at": _iso(now), "days": days, "subject_id": subject_id,
        "kpis": {"subjects": len(subjects), "materials": sum(s["materials"] for s in subjects), "topics": sum(s["topics"] for s in subjects),
                 "quizzes": sum(s["quizzes"] for s in subjects), "answered": all_answered, "accuracy": round(100 * all_correct / all_answered, 1) if all_answered else None,
                 "window_answered": total_answered, "window_accuracy": round(100 * total_correct / total_answered, 1) if total_answered else None,
                 "questions_asked": sum(outcomes.values()), "active_days": active_days,
                 "mean_theta": round(sum(thetas) / len(thetas), 3) if thetas else None,
                 "readiness": round(sum(s["readiness"] for s in subjects if s["readiness"] is not None) / max(1, sum(1 for s in subjects if s["readiness"] is not None)), 1)
                 if any(s["readiness"] is not None for s in subjects) else None,
                 "integrity": round(integrity) if integrity is not None else None,
                 "debt_hours": round(sum(s["debt_hours"] for s in subjects), 1)},
        "timeline": timeline, "habit": habit, "subjects": subjects,
        "difficulty": [{"level": k, **v, "accuracy": round(100 * v["correct"] / v["answered"], 1) if v["answered"] else None} for k, v in diff.items()],
        "response_time": [{"bucket": k, "count": buckets[k], "accuracy": round(100 * time_ok[k][1] / time_ok[k][0], 1) if time_ok[k][0] else None} for k in buckets],
        "topic_status": dict(status_counts), "focus_events": focus, "question_outcomes": outcomes, "answer_tiers": tiers, "cloud_usage": cloud,
    }
