"""The learner's digital twin for one subject: one picture built only from what the student has done, and the planner's next steps from it."""
from __future__ import annotations

import sqlite3

from . import foresight, insights, patterns, roadmap, tutor


def build(db: sqlite3.Connection, user_id: int, subject: dict, profile: dict, user: dict, plan: dict, info: dict) -> dict:
    sid = subject["id"]
    conf = insights.topic_confidence(db, user_id, sid)
    tutor.verify(db, user_id, sid, conf["topics"])
    weights = patterns.exam_weights(db, sid)
    drift = patterns.drift(db, user_id, sid)
    ratings = foresight.get_ratings(db, user_id, sid)
    feel = {t["topic_id"]: t for t in foresight.self_check(info, ratings)["topics"]}
    mem = tutor.memory(db, user_id)
    hist = tutor.history(db, user_id, sid, 200)
    by_topic: dict[int, list] = {}
    for h in hist:
        by_topic.setdefault(h["topic_id"], []).append(h)
    topics = []
    for g in info["gaps"]:
        e = conf["topics"].get(g["topic_id"])
        unit, sub = patterns.unit_of(g["path"])
        d = drift.get(g["topic_id"])
        level = tutor.advise_level(e["theta"] if e else None, e["answered"] if e else 0)
        topics.append({"topic_id": g["topic_id"], "name": g["name"], "unit": unit, "subtopic": sub, "status": g["status"], "confidence": g["confidence"], "theta": e["theta"] if e else None,
                       "se": e["se"] if e else None, "answered": g["answered"], "trend": g["trend"], "gap": g["gap"], "blocked_by": [b["name"] for b in g["blocked_by"]],
                       "exam_count": weights.get(g["topic_id"], {}).get("count", 0), "exam_weight": weights.get(g["topic_id"], {}).get("weight", 0.0),
                       "drift": d["state"] if d else "none", "drift_note": patterns.drift_note(d) if d else None, "days_since": d["days_since"] if d else None,
                       "feeling": feel[g["topic_id"]]["verdict"], "rating": feel[g["topic_id"]]["rating"], "difficulty": level["difficulty"], "difficulty_why": level["why"],
                       "loop": tutor.loop_state(by_topic.get(g["topic_id"], []))})
    strengths = [t["name"] for t in topics if t["status"] == "on_track"][:5]
    weaknesses = [t["name"] for t in sorted((t for t in topics if (t["gap"] or 0) > 0), key=lambda t: -t["gap"])][:5]
    errs = patterns.error_patterns(db, user_id, sid)
    return {
        "subject": subject["name"], "target": info["target"], "readiness": info["readiness"], "overall": conf["overall"],
        "profile": {"level": subject.get("level"), "goal": profile["goal"], "hours_per_week": profile["hours_per_week"], "target_date": profile["target_date"], "exam_date": subject.get("exam_date"),
                    "department": user.get("department") or "", "semester": user.get("semester")},
        "strengths": strengths, "weaknesses": weaknesses, "units": patterns.rollup(info["gaps"]), "topics": topics,
        "patterns": errs, "next": tutor.next_actions(db, user_id, sid, info, conf["topics"], weights, drift, plan["summary"], mem),
        "memory": mem, "history": [{**h, "created_at": roadmap_iso(h["created_at"]), "verified_at": roadmap_iso(h["verified_at"])} for h in hist[:12]],
        "has_past_papers": bool(weights), "sources": info["source_totals"], "source_labels": roadmap.SOURCE_LABELS,
    }


def roadmap_iso(ts):
    import time
    return None if ts is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
