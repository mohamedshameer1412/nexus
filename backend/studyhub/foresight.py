"""Looking ahead from the evidence: a what-if simulator, a risk score with a learning-debt graph, and the "how sure do you feel" self-check.

Everything is a plain formula over numbers the student already produced (confidence per topic, trend, weak foundations, hours and target date).
Nothing here is a trained model and nothing is a prediction of a grade: the pages say so. Same inputs, same answer.
"""
from __future__ import annotations

import math
import sqlite3
import time

from . import insights, roadmap

# What-if assumption, stated on the page: finishing the planned steps for a topic closes this share of its gap to the target.
CLOSE_RATE = 0.70
MAX_WEEKS = 26
RATING_TO_PERCEIVED = {1: 0.10, 2: 0.30, 3: 0.50, 4: 0.70, 5: 0.90}
RATING_LABELS = {1: "Lost", 2: "Unsure", 3: "Okay", 4: "Good", 5: "Very sure"}
MISMATCH = 0.25             # how far apart feeling and measurement must be to be called out


def _minutes(g: dict) -> int:
    return sum(s["minutes"] for s in roadmap._steps(g, 0))


def _readiness(gaps: list[dict], conf: dict[int, float | None], target: float) -> float | None:
    assessed = [g for g in gaps if conf.get(g["topic_id"]) is not None]
    return round(sum(min(1.0, conf[g["topic_id"]] / target) for g in assessed) / len(gaps), 3) if gaps and assessed else None


# ------------------------------------------------------------------------------------------------------- what-if

def simulate(gaps_info: dict, hours_per_week: float, weeks: int, focus: list[int] | None = None) -> dict:
    """Spend `hours_per_week` for `weeks` weeks, following the roadmap's order (chosen topics first), and say where each topic would end up."""
    gaps, target = gaps_info["gaps"], gaps_info["target"]
    by_id = {g["topic_id"]: g for g in gaps}
    order = roadmap._order(gaps)
    chosen = [t for t in dict.fromkeys(focus or []) if t in by_id]
    if chosen:                                                            # chosen topics (and their weak foundations) jump the queue
        head = roadmap._order([by_id[t] for t in chosen] + [by_id[b["topic_id"]] for t in chosen for b in by_id[t]["blocked_by"] if b["topic_id"] in by_id])
        seen = {g["topic_id"] for g in head}
        order = head + [g for g in order if g["topic_id"] not in seen]
    budget = int(round(hours_per_week * 60 * weeks))
    left = budget
    now = {g["topic_id"]: g["confidence"] for g in gaps}
    after = dict(now)
    rows, reaching = [], 0
    for g in order:
        need = _minutes(g) if (g["gap"] or 0) > 0 or g["status"] == "unassessed" else 0
        give = min(left, need)
        left -= give
        frac = (give / need) if need else 1.0
        conf = g["confidence"]
        if conf is not None and (g["gap"] or 0) > 0:
            after[g["topic_id"]] = round(min(1.0, conf + CLOSE_RATE * frac * (target - conf)), 3)
        covered = give >= need
        reaching += bool(covered and conf is not None and (g["gap"] or 0) > 0)
        rows.append({"topic_id": g["topic_id"], "name": g["name"], "status": g["status"], "now": conf, "after": after[g["topic_id"]], "minutes_needed": need,
                     "minutes_given": give, "covered": covered, "focus": g["topic_id"] in chosen})
    lagging = [g for g in gaps if (g["gap"] or 0) > 0]
    need_all = sum(_minutes(g) for g in lagging) + sum(_minutes(g) for g in gaps if g["status"] == "unassessed")
    return {"hours_per_week": hours_per_week, "weeks": weeks, "budget_minutes": budget, "unused_minutes": left, "readiness_now": _readiness(gaps, now, target),
            "readiness_after": _readiness(gaps, after, target), "lagging": len(lagging), "covered": reaching, "target": target,
            "weeks_to_finish": math.ceil(need_all / 60 / hours_per_week) if hours_per_week and need_all else 0, "topics": rows}


def what_if(gaps_info: dict, base_hours: float, base_weeks: int, hours: float, weeks: int, focus: list[int] | None) -> dict:
    base = simulate(gaps_info, base_hours, base_weeks)
    scenario = simulate(gaps_info, hours, weeks, focus)
    moves = sorted(({"name": t["name"], "points": round(((t["after"] or 0) - (b["after"] or 0)) * 100)} for t, b in zip(scenario["topics"], base["topics"])
                    if t["topic_id"] == b["topic_id"] and t["after"] is not None and b["after"] is not None), key=lambda x: -abs(x["points"]))
    moves = [m for m in moves if m["points"]][:3]
    why = []
    d_h = round(scenario["hours_per_week"] * scenario["weeks"] - base["hours_per_week"] * base["weeks"], 1)
    if d_h:
        why.append(f"{'Adds' if d_h > 0 else 'Removes'} {abs(d_h)} study hours compared with your current plan.")
    if focus:
        why.append("The topics you picked, and the weaker topics they build on, are studied first.")
    if moves:
        why.append("Biggest changes: " + ", ".join(f"{m['name']} {'+' if m['points'] > 0 else ''}{m['points']} points" for m in moves) + ".")
    if scenario["unused_minutes"] > 0 and scenario["lagging"]:
        why.append(f"About {round(scenario['unused_minutes'] / 60, 1)} hours would be left over, so you could aim for more or finish sooner.")
    if scenario["covered"] < scenario["lagging"]:
        why.append(f"{scenario['lagging'] - scenario['covered']} of {scenario['lagging']} topics below target would not get their full plan.")
    elif scenario["lagging"]:
        why.append("Every topic below target would get its full plan.")
    return {"baseline": base, "scenario": scenario, "why": why,
            "assumption": f"Estimate, not a promise: finishing the planned steps for a topic is assumed to close {round(CLOSE_RATE * 100)}% of its gap to your target. Topics with no answers yet are not counted."}


# ------------------------------------------------------------------------------------------------------- risk and debt

def _level(score: int) -> str:
    return "high" if score >= 60 else "medium" if score >= 30 else "low"


def risk(gaps_info: dict, plan_summary: dict) -> dict:
    gaps = gaps_info["gaps"]
    late = plan_summary.get("on_track") is False
    rows = []
    for g in gaps:
        if g["confidence"] is None:
            rows.append({"topic_id": g["topic_id"], "name": g["name"], "score": None, "level": "unknown", "reasons": ["No answers yet, so the risk cannot be judged."], "confidence": None})
            continue
        gap = g["gap"] or 0
        score, why = round(min(1.0, gap / 0.5) * 55), []
        if gap:
            why.append(f"{round(gap * 100)} points below your {round(g['target'] * 100)}% target")
        if g["trend"] == "slipping":
            score += 15
            why.append("recent answers are worse than earlier ones")
        elif g["trend"] == "improving" and score:
            score = max(0, score - 10)
            why.append("recent answers are improving")
        if g["blocked_by"] and gap:
            score += 15
            why.append("builds on " + ", ".join(b["name"] for b in g["blocked_by"]) + " which is not solid")
        if g["answered"] < insights.MIN_EVIDENCE:
            score += 5
            why.append(f"only {g['answered']} answer{'s' if g['answered'] != 1 else ''}, so this is uncertain")
        if late and gap:
            score += 10
            why.append("the plan does not fit before your target date")
        score = min(100, score)
        rows.append({"topic_id": g["topic_id"], "name": g["name"], "score": score, "level": _level(score), "reasons": why or ["On track."], "confidence": g["confidence"]})
    scored = [r["score"] for r in rows if r["score"] is not None]
    overall = None
    if scored:
        overall = min(100, round(sum(scored) / len(scored)) + (10 if late else 0))
    summary = {"score": overall, "level": _level(overall) if overall is not None else "unknown", "assessed": len(scored), "unassessed": len(rows) - len(scored),
               "high": sum(1 for r in rows if r["level"] == "high"), "medium": sum(1 for r in rows if r["level"] == "medium"),
               "late": late, "hours_needed": plan_summary.get("hours_needed"), "hours_per_week": plan_summary.get("hours_per_week")}
    return {"summary": summary, "topics": sorted(rows, key=lambda r: (-(r["score"] if r["score"] is not None else -1), r["name"])),
            "method": "A weighted formula, not a trained model: distance below target (up to 55), slipping trend (+15), a weak foundation (+15), too few answers (+5) "
                      "and a target date the plan cannot meet (+10). 60 or more is high, 30 or more is medium."}


def debt(gaps_info: dict) -> dict:
    """Learning debt: the study time still owed on each topic below target, plus the "interest" of topics that cannot be learned well until a weak foundation is repaid."""
    gaps = {g["topic_id"]: g for g in gaps_info["gaps"]}
    owed = {t: _minutes(g) for t, g in gaps.items() if (g["gap"] or 0) > 0}
    edges, dependents = [], {}
    for t, g in gaps.items():
        if t not in owed:
            continue
        for b in g["blocked_by"]:
            if b["topic_id"] in gaps:
                edges.append({"from": b["topic_id"], "to": t})
                dependents.setdefault(b["topic_id"], []).append(t)
    nodes = {}
    for t in set(owed) | {e["from"] for e in edges}:
        g = gaps[t]
        own = owed.get(t, 0)
        interest = sum(owed.get(d, 0) for d in dependents.get(t, []))
        nodes[t] = {"topic_id": t, "name": g["name"], "own_minutes": own, "blocks": [gaps[d]["name"] for d in dependents.get(t, [])], "interest_minutes": interest,
                    "confidence": g["confidence"], "status": g["status"], "repay_first": bool(dependents.get(t))}
    ranked = sorted(nodes.values(), key=lambda n: (-(n["own_minutes"] + n["interest_minutes"]), n["name"]))
    total = sum(owed.values())
    return {"total_minutes": total, "total_hours": round(total / 60, 1), "topics": ranked, "edges": edges,
            "method": "Debt is the study time the roadmap plans for each topic below target. A topic that other weak topics build on carries their time as interest: repay it first."}


# ------------------------------------------------------------------------------------------------------ self-check

def get_ratings(db: sqlite3.Connection, user_id: int, subject_id: int) -> dict[int, int]:
    return {r["topic_id"]: r["rating"] for r in db.execute("SELECT topic_id, rating FROM self_ratings WHERE user_id=? AND subject_id=?", (user_id, subject_id))}


def save_ratings(db: sqlite3.Connection, user_id: int, subject_id: int, ratings: dict[int, int]) -> int:
    """Store ratings for topics of this subject only; returns how many were saved."""
    valid = {r["id"] for r in db.execute("SELECT id FROM topics WHERE subject_id=?", (subject_id,))}
    n, now = 0, time.time()
    for topic_id, rating in ratings.items():
        if topic_id in valid and rating in RATING_TO_PERCEIVED:
            db.execute("INSERT INTO self_ratings(user_id, subject_id, topic_id, rating, updated_at) VALUES (?,?,?,?,?) "
                       "ON CONFLICT(user_id, topic_id) DO UPDATE SET rating=excluded.rating, updated_at=excluded.updated_at", (user_id, subject_id, topic_id, rating, now))
            n += 1
    return n


def self_check(gaps_info: dict, ratings: dict[int, int]) -> dict:
    rows = []
    for g in gaps_info["gaps"]:
        r = ratings.get(g["topic_id"])
        perceived = RATING_TO_PERCEIVED.get(r) if r else None
        measured, enough = g["confidence"], g["confidence"] is not None and g["answered"] >= insights.MIN_EVIDENCE
        delta = round(perceived - measured, 3) if perceived is not None and measured is not None else None
        if r is None:
            verdict = "not_rated"
        elif not enough:
            verdict = "not_enough_answers"
        else:
            verdict = "overconfident" if delta >= MISMATCH else "underconfident" if delta <= -MISMATCH else "aligned"
        rows.append({"topic_id": g["topic_id"], "name": g["name"], "rating": r, "perceived": perceived, "confidence": measured, "answered": g["answered"], "delta": delta, "verdict": verdict})
    counts = {k: sum(1 for x in rows if x["verdict"] == k) for k in ("overconfident", "underconfident", "aligned", "not_enough_answers", "not_rated")}
    judged = counts["overconfident"] + counts["underconfident"] + counts["aligned"]
    if not judged:
        message = "Rate how sure you feel about each topic, and answer at least 3 questions on it, to see how your feeling compares with your results."
    elif counts["overconfident"] and counts["underconfident"]:
        message = f"Mixed: you feel surer than your answers show on {counts['overconfident']} topic(s) and less sure than they show on {counts['underconfident']}."
    elif counts["overconfident"]:
        message = f"You feel surer than your answers show on {counts['overconfident']} topic(s). Quiz yourself on those before you rely on them."
    elif counts["underconfident"]:
        message = f"You know more than you think on {counts['underconfident']} topic(s). Your answers are better than your feeling."
    else:
        message = "Your feeling matches your results on the topics checked so far."
    return {"topics": rows, "counts": counts, "message": message, "labels": {str(k): v for k, v in RATING_LABELS.items()}}
