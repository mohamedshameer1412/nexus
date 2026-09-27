"""Skill-gap analysis and the study roadmap for one subject.

Skill gap = how far each topic is below the target confidence, judged from EVERY kind of evidence the student has produced:
the diagnostic test, regular quizzes, revision quizzes, assessments (with the rules on), and flashcard practice. Nothing is guessed:
a topic with no answers is "not assessed", not "weak". The gap says why (numbers per source) and whether an earlier topic it builds on
is the real cause.

Roadmap = the topics in learning order (a topic's foundations first, the biggest gaps early), cut into weeks that fit the hours the
student says they have, each week with concrete steps that link into the app. It is computed from the numbers, so it is the same
every time for the same data. An optional "coach" paragraph is written by a model from those numbers only (topic names and scores,
never passages).
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from collections import defaultdict

from . import cards, insights, patterns
from .repo import Repo

TARGETS = {"new": 0.60, "intermediate": 0.70, "professional": 0.80}
DEFAULT_TARGET = 0.70
MIN_EVIDENCE = insights.MIN_EVIDENCE
PRIORITY = {"critical": 0, "moderate": 1, "unassessed": 2, "minor": 3, "on_track": 4}
MINUTES = {"critical": 150, "moderate": 90, "unassessed": 45, "minor": 45, "on_track": 20}
MAX_WEEKS = 12
SOURCES = ("diagnostic", "quiz", "revision", "assessment", "flashcards")
SOURCE_LABELS = {"diagnostic": "Diagnostic", "quiz": "Regular quizzes", "revision": "Revision quizzes", "assessment": "Assessments", "flashcards": "Flashcards"}


def target_for(level: str | None) -> float:
    return TARGETS.get(level or "", DEFAULT_TARGET)


def _sources(db: sqlite3.Connection, user_id: int, subject_id: int) -> dict[int, dict]:
    """Per topic and kind of evidence: answers given and right. An assessment counts as an assessment whatever its kind."""
    out: dict[int, dict] = defaultdict(lambda: {k: {"answered": 0, "correct": 0} for k in SOURCES})
    rows = db.execute(
        "SELECT mi.topic_id AS t, qa.kind AS kind, qa.mode AS mode, COUNT(*) AS n, COALESCE(SUM(aa.is_correct),0) AS c "
        "FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id JOIN mcq_items mi ON mi.id=aa.item_id "
        "WHERE qa.user_id=? AND qa.subject_id=? AND aa.is_correct IS NOT NULL AND mi.topic_id IS NOT NULL GROUP BY mi.topic_id, qa.kind, qa.mode",
        (user_id, subject_id)).fetchall()
    for r in rows:
        key = "assessment" if r["mode"] == "assessment" else "diagnostic" if r["kind"] == "diagnostic" else "revision" if r["kind"] == "revision" else "quiz"
        out[r["t"]][key]["answered"] += r["n"]
        out[r["t"]][key]["correct"] += int(r["c"])
    for r in db.execute(
            "SELECT mi.topic_id AS t, COUNT(*) AS n, COALESCE(SUM(c.lapses),0) AS lapses FROM card_reviews c JOIN mcq_items mi ON mi.id=c.item_id "
            "JOIN subjects s ON s.id=mi.subject_id WHERE c.user_id=? AND mi.subject_id=? AND s.user_id=? AND mi.topic_id IS NOT NULL GROUP BY mi.topic_id",
            (user_id, subject_id, user_id)):
        out[r["t"]]["flashcards"] = {"answered": r["n"], "correct": max(0, r["n"] - int(r["lapses"]))}
    return out


def _trend(db: sqlite3.Connection, user_id: int, subject_id: int, topic_id: int) -> str | None:
    rows = [r["is_correct"] for r in db.execute(
        "SELECT aa.is_correct FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id JOIN mcq_items mi ON mi.id=aa.item_id "
        "WHERE qa.user_id=? AND qa.subject_id=? AND mi.topic_id=? AND aa.is_correct IS NOT NULL ORDER BY aa.answered_at, aa.id", (user_id, subject_id, topic_id))]
    if len(rows) < 6:
        return None
    half = len(rows) // 2
    a, b = sum(rows[:half]) / half, sum(rows[half:]) / (len(rows) - half)
    return "improving" if b - a >= 0.2 else "slipping" if a - b >= 0.2 else "steady"


def skill_gaps(db: sqlite3.Connection, user_id: int, subject_id: int, level: str | None = None) -> dict:
    repo = Repo(db)
    target = target_for(level)
    conf = insights.topic_confidence(db, user_id, subject_id)["topics"]
    src = _sources(db, user_id, subject_id)
    topics = [t for t in repo.list_topics(user_id, subject_id) if t["chunks"]]
    weights = patterns.exam_weights(db, subject_id)
    names = {t["id"]: t["name"] for t in topics}
    gaps: list[dict] = []
    for t in topics:
        e = conf.get(t["id"])
        s = src.get(t["id"], {k: {"answered": 0, "correct": 0} for k in SOURCES})
        answered = e["answered"] if e else 0
        confidence = e["confidence"] if e else None
        if answered == 0:
            status, gap = "unassessed", None
        elif confidence >= target and answered >= MIN_EVIDENCE:
            status, gap = "on_track", 0.0
        else:
            gap = round(max(0.0, target - confidence), 3)
            status = "critical" if gap > 0.30 else "moderate" if gap > 0.10 else "minor"
            if answered < MIN_EVIDENCE and status == "on_track":
                status = "minor"
        blockers = []
        for pre in insights.prerequisite_topics(db, subject_id, t["id"]):
            pe = conf.get(pre)
            if pre in names and (pe is None or pe["confidence"] < target) and status not in ("on_track",):
                blockers.append({"topic_id": pre, "name": names[pre], "confidence": pe["confidence"] if pe else None})
        reasons = []
        for k in SOURCES:
            a = s[k]
            if a["answered"]:
                reasons.append(f"{SOURCE_LABELS[k]}: {a['correct']} of {a['answered']} " + ("recalled" if k == "flashcards" else "correct"))
        if answered and answered < MIN_EVIDENCE:
            reasons.append(f"Only {answered} answer{'s' if answered != 1 else ''} so far, so this is a rough guess")
        if blockers:
            reasons.append("Builds on " + ", ".join(b["name"] for b in blockers) + (", which is not solid yet" if len(blockers) == 1 else ", which are not solid yet"))
        gaps.append({"topic_id": t["id"], "name": t["name"], "path": t["path"], "ordinal": t["ordinal"], "status": status, "gap": gap, "confidence": confidence,
                     "target": target, "answered": answered, "correct": e["correct"] if e else 0, "sources": s,
                     "exam_count": weights.get(t["id"], {}).get("count", 0), "exam_weight": weights.get(t["id"], {}).get("weight", 0.0), "trend": _trend(db, user_id, subject_id, t["id"]),
                     "blocked_by": blockers, "reasons": reasons, "avg_seconds": e["avg_seconds"] if e else None})
    assessed = [g for g in gaps if g["confidence"] is not None]
    readiness = round(sum(min(1.0, g["confidence"] / target) for g in assessed) / len(gaps), 3) if gaps and assessed else None
    totals = {k: {"answered": sum(g["sources"][k]["answered"] for g in gaps), "correct": sum(g["sources"][k]["correct"] for g in gaps)} for k in SOURCES}
    return {"target": target, "level": level, "gaps": gaps, "readiness": readiness, "source_totals": totals,
            "counts": {s: sum(1 for g in gaps if g["status"] == s) for s in PRIORITY}}


# ------------------------------------------------------------------------------------------------------- the roadmap

def _steps(g: dict, sid: int) -> list[dict]:
    base = f"/subjects/{sid}"
    tid = g["topic_id"]
    read = {"type": "read", "title": f"Read: {g['name']}", "href": f"{base}/materials", "topic_id": tid}
    quiz = {"type": "quiz", "title": f"Quiz yourself on {g['name']}", "href": f"{base}/quiz", "topic_id": tid}
    cards_ = {"type": "flashcards", "title": f"Flashcards for {g['name']}", "href": f"{base}/practice/flashcards", "topic_id": tid}
    note = {"type": "notes", "title": f"Write a short note that explains {g['name']} in your own words", "href": f"{base}/notes", "topic_id": tid}
    revise = {"type": "revision", "title": "Revision quiz on what you missed", "href": f"{base}/quiz", "topic_id": tid}
    plan = {"critical": [(read, 40), (note, 25), (cards_, 30), (quiz, 30), (revise, 25)],
            "moderate": [(read, 20), (cards_, 25), (quiz, 25), (revise, 20)],
            "unassessed": [(read, 20), (quiz, 25)],
            "minor": [(cards_, 15), (quiz, 30)],
            "on_track": [(cards_, 10), (quiz, 10)]}[g["status"]]
    return [{**step, "minutes": m} for step, m in plan]


def _order(gaps: list[dict]) -> list[dict]:
    """Biggest needs first, but a topic's weak foundations always come before it."""
    by_id = {g["topic_id"]: g for g in gaps}
    order: list[dict] = []
    seen: set[int] = set()

    def visit(g: dict, depth: int = 0) -> None:
        if g["topic_id"] in seen or depth > 20:
            return
        seen.add(g["topic_id"])
        for b in g["blocked_by"]:
            if b["topic_id"] in by_id:
                visit(by_id[b["topic_id"]], depth + 1)
        order.append(g)

    for g in sorted(gaps, key=lambda x: (PRIORITY[x["status"]], -x.get("exam_weight", 0.0), x["ordinal"])):
        visit(g)
    return order


IDEAS = ["Explain {t} to a friend in five sentences, then save it as a note.", "Write three practice questions of your own about {t}, then check them against your material.",
         "Make a one-page cheat sheet for {t}: definitions, one example, one common mistake.", "Find one place in your material where {t} and another topic connect, and note how."]


def build(gaps_info: dict, sid: int, hours_per_week: float = 5.0, target_date: str | None = None, today: float | None = None) -> dict:
    """Weeks of steps that fit the student's hours. Pure function of its inputs."""
    gaps = gaps_info["gaps"]
    capacity = max(30, int(round(hours_per_week * 60)))
    order = _order(gaps)
    weeks: list[dict] = []
    cur: list[dict] = []
    used = 0
    for g in order:
        for step in _steps(g, sid):
            if used and used + step["minutes"] > capacity:
                weeks.append({"steps": cur, "minutes": used})
                cur, used = [], 0
            cur.append({**step, "status": g["status"]})
            used += step["minutes"]
    if cur:
        weeks.append({"steps": cur, "minutes": used})
    total_weeks = len(weeks)
    out = []
    for n, w in enumerate(weeks[:MAX_WEEKS], start=1):
        topics = list(dict.fromkeys(s["topic_id"] for s in w["steps"]))
        names = {g["topic_id"]: g["name"] for g in gaps}
        focus = [names[t] for t in topics][:3]
        lagging = [s for s in w["steps"] if s["status"] in ("critical", "moderate")]
        out.append({
            "week": n, "minutes": w["minutes"], "steps": w["steps"], "focus": focus,
            "goal": (f"Bring {', '.join(focus[:2])} up to {round(gaps_info['target'] * 100)}% confidence." if lagging else f"Check and keep {', '.join(focus[:2])} solid."),
            "milestone": "Finish a revision quiz and see the confidence bars move on the Progress tab." if lagging else "A short quiz with no misses.",
            "idea": IDEAS[(n - 1) % len(IDEAS)].format(t=focus[0]) if focus else None})
    total_min = sum(w["minutes"] for w in weeks)
    summary = {"total_minutes": total_min, "weeks": total_weeks, "shown_weeks": len(out), "hours_per_week": hours_per_week,
               "lagging": sum(1 for g in gaps if g["status"] in ("critical", "moderate")), "unassessed": gaps_info["counts"]["unassessed"],
               "target_date": target_date, "weeks_available": None, "on_track": None, "hours_needed": None}
    if target_date:
        try:
            end = time.mktime(time.strptime(target_date, "%Y-%m-%d"))
            now = time.time() if today is None else today
            avail = max(0, math.ceil((end - now) / (7 * 86400)))
            summary.update(weeks_available=avail, on_track=total_weeks <= avail if avail else False,
                           hours_needed=round(total_min / 60 / avail, 1) if avail else None)
        except ValueError:
            pass
    return {"weeks": out, "summary": summary}


def plan_hash(gaps_info: dict, profile: dict) -> str:
    """Changes when anything the plan depends on changes (used to tell a stale coach paragraph)."""
    core = [(g["topic_id"], g["status"], round(g["confidence"] or 0, 2), g["answered"]) for g in gaps_info["gaps"]]
    return hashlib.sha256(json.dumps([core, gaps_info["target"], profile.get("hours_per_week"), profile.get("target_date"), profile.get("goal")], default=str).encode()).hexdigest()[:20]


# ---------------------------------------------------------------------------------------------------------- profile

def get_profile(db: sqlite3.Connection, user_id: int, subject_id: int) -> dict:
    r = db.execute("SELECT goal, hours_per_week, target_date, coach_status, coach_text, coach_model, coach_hash, coach_at FROM study_plans WHERE subject_id=? AND user_id=?",
                   (subject_id, user_id)).fetchone()
    p = dict(r) if r else {"goal": "", "hours_per_week": 5.0, "target_date": None, "coach_status": "idle", "coach_text": "", "coach_model": None, "coach_hash": None, "coach_at": None}
    exam = db.execute("SELECT exam_date FROM subjects WHERE id=? AND user_id=?", (subject_id, user_id)).fetchone()
    p["exam_date"] = exam["exam_date"] if exam else None
    p["target_date_source"] = "plan" if p["target_date"] else "exam" if p["exam_date"] else None
    p["target_date"] = p["target_date"] or p["exam_date"]                       # a study date wins; without one the exam date is the deadline
    return p


def save_profile(db: sqlite3.Connection, user_id: int, subject_id: int, goal: str, hours: float, target_date: str | None) -> None:
    db.execute(
        "INSERT INTO study_plans(subject_id, user_id, goal, hours_per_week, target_date, updated_at) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(subject_id) DO UPDATE SET goal=excluded.goal, hours_per_week=excluded.hours_per_week, target_date=excluded.target_date, updated_at=excluded.updated_at "
        "WHERE study_plans.user_id=excluded.user_id", (subject_id, user_id, goal, hours, target_date, time.time()))


# ------------------------------------------------------------------------------------------------------------ coach

def rule_coach(gaps_info: dict, plan: dict) -> str:
    """The plain-words summary used when no model is available. Says only what the numbers say."""
    c = gaps_info["counts"]
    lag = [g for g in gaps_info["gaps"] if g["status"] in ("critical", "moderate")]
    lag.sort(key=lambda g: -(g["gap"] or 0))
    parts = []
    if gaps_info["readiness"] is not None:
        parts.append(f"You are at about {round(gaps_info['readiness'] * 100)}% of the way to your target confidence overall.")
    if lag:
        parts.append("Start with " + ", ".join(g["name"] for g in lag[:3]) + ": these are furthest below target.")
    if c["unassessed"]:
        parts.append(f"{c['unassessed']} topic(s) have no answers yet, so take a quick quiz on them before deciding where to spend time.")
    w1 = plan["weeks"][0] if plan["weeks"] else None
    if w1:
        parts.append(f"This week: about {round(w1['minutes'] / 60, 1)} hours on " + ", ".join(w1["focus"][:2]) + ".")
    if not parts:
        parts.append("Everything with enough answers is at or above your target. Keep it that way with a short quiz each week.")
    return " ".join(parts)


COACH_SYSTEM = """You are a friendly, honest study coach. You are given a student's numbers for one subject: topics with a confidence percent, a target, and a weekly plan.
Write a short plain-text plan (at most 120 words, no lists longer than three items, no headings, no markdown):
1) where they stand in one sentence, 2) the two most important things to do this week, 3) one habit tip.
Use ONLY the topic names and numbers you are given. Do not invent topics, facts, dates or scores. Do not promise results.
Reply with JSON only: {"text": "..."}"""


def coach_prompt(subject: str, gaps_info: dict, plan: dict, profile: dict) -> str:
    rows = [{"topic": g["name"], "status": g["status"], "confidence_percent": None if g["confidence"] is None else round(g["confidence"] * 100), "answers": g["answered"],
             "builds_on_weak": [b["name"] for b in g["blocked_by"]], "trend": g["trend"]} for g in _order(gaps_info["gaps"])[:12]]
    w1 = plan["weeks"][0] if plan["weeks"] else None
    return json.dumps({"subject": subject, "student_level": gaps_info["level"], "target_confidence_percent": round(gaps_info["target"] * 100),
                       "hours_per_week": profile.get("hours_per_week"), "goal": profile.get("goal") or None,
                       "topics_in_priority_order": rows, "this_week": {"focus": w1["focus"] if w1 else [], "minutes": w1["minutes"] if w1 else 0}}, indent=1)


def clean_coach(text: str, gaps_info: dict) -> str | None:
    """A model's paragraph is accepted only if it is a reasonable length, has no links or markup, and mentions no topic that is not there."""
    t = " ".join((text or "").replace("*", "").replace("#", "").split())
    if not 40 <= len(t) <= 1400 or "http" in t.lower() or "<" in t:
        return None
    return t
