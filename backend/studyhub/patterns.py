"""What the evidence says about HOW a student goes wrong and how mastery moves over time.

Everything is counted from answers and materials the student already has; each finding carries the numbers behind it. Rules are plain and
stated on the page. Nothing here is a prediction.

  exam_weights   how often each topic is asked in the student's own past-paper documents (role "pyq")
  unit_of        "Unit 2 › Trees › AVL" -> unit "Unit 2", subtopic "Trees › AVL"
  error_patterns repeated misses, the same wrong choice twice, rushing, position bias, slipping on hard questions
  drift          a topic's confidence in the earlier answers vs the recent ones, and time since it was last practised
  rollup         topic -> unit -> subject mastery
"""
from __future__ import annotations

import json
import re
import sqlite3
import statistics
import time
from collections import Counter, defaultdict

from . import career, insights

SEP = " › "
MIN_DRIFT_ANSWERS = 6
DRIFT_DELTA = 0.15
STALE_DAYS = 14
LETTERS = "ABCD"


def unit_of(path: str) -> tuple[str, str]:
    parts = [p for p in (path or "").split(SEP) if p]
    return (parts[0] if parts else "General", SEP.join(parts[1:]))


# ------------------------------------------------------------------------------------------------------------- exam weights

_QUESTION_SPLIT = re.compile(r"\n\s*\n|\n(?=\s*(?:Q\.?\s*)?\d+[.)]\s)|(?<=[?])\s+")


def exam_weights(db: sqlite3.Connection, subject_id: int) -> dict[int, dict]:
    """{topic_id: {"count": questions that mention it, "weight": share of all matches}} from past-paper documents; empty without any."""
    texts = [r[0] for r in db.execute("SELECT c.text FROM chunks c JOIN documents d ON d.id=c.document_id WHERE c.subject_id=? AND d.role='pyq' AND c.quarantined=0", (subject_id,))]
    if not texts:
        return {}
    topics = [(r["id"], career.tokens(r["name"])) for r in db.execute(
        "SELECT t.id, t.name FROM topics t WHERE t.subject_id=? AND EXISTS(SELECT 1 FROM chunks c WHERE c.topic_id=t.id)", (subject_id,))]
    topics = [(t, tk) for t, tk in topics if tk]
    hits: Counter = Counter()
    for text in texts:
        for seg in _QUESTION_SPLIT.split(text):
            if len(seg.strip()) < 15:
                continue
            words = career.tokens(seg)
            for tid, need in topics:
                if len(need & words) / len(need) >= 0.6:
                    hits[tid] += 1
    total = sum(hits.values())
    return {tid: {"count": n, "weight": round(n / total, 3)} for tid, n in hits.items()} if total else {}


# ---------------------------------------------------------------------------------------------------------- error patterns

def _answers(db: sqlite3.Connection, user_id: int, subject_id: int) -> list[dict]:
    q = ("SELECT aa.item_id, aa.chosen_index, aa.is_correct, aa.response_time, aa.answered_at, mi.topic_id, mi.question, mi.options, mi.answer_index, mi.difficulty, "
         "COALESCE(t.name, '') AS topic FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id JOIN mcq_items mi ON mi.id=aa.item_id "
         "LEFT JOIN topics t ON t.id=mi.topic_id WHERE qa.user_id=? AND qa.subject_id=? AND aa.is_correct IS NOT NULL ORDER BY aa.answered_at, aa.id")
    return [dict(r) for r in db.execute(q, (user_id, subject_id))]


def error_patterns(db: sqlite3.Connection, user_id: int, subject_id: int) -> dict:
    rows = _answers(db, user_id, subject_id)
    found: list[dict] = []
    by_item: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_item[r["item_id"]].append(r)
    recurring = 0
    for item, rs in by_item.items():
        misses = [r for r in rs if not r["is_correct"]]
        if len(misses) >= 2:
            recurring += 1
            found.append({"kind": "repeat_miss", "topic_id": rs[0]["topic_id"], "topic": rs[0]["topic"], "count": len(misses), "title": "Missed more than once",
                          "detail": f"“{rs[0]['question'][:140]}” was answered wrongly {len(misses)} times."})
        wrong_choice = Counter(r["chosen_index"] for r in misses if r["chosen_index"] is not None)
        for idx, n in wrong_choice.items():
            if n >= 2:
                options = json.loads(rs[0]["options"])
                found.append({"kind": "same_wrong_choice", "topic_id": rs[0]["topic_id"], "topic": rs[0]["topic"], "count": n, "title": "The same wrong answer twice",
                              "detail": f"You chose “{str(options[idx])[:100]}” {n} times for “{rs[0]['question'][:100]}”. That may be a misunderstanding worth clearing up."})
    times_ok = [r["response_time"] for r in rows if r["is_correct"] and r["response_time"]]
    fast = max(3.0, 0.4 * statistics.median(times_ok)) if len(times_ok) >= 5 else None
    per_topic: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r["topic_id"]:
            per_topic[r["topic_id"]].append(r)
    for tid, rs in per_topic.items():
        wrong = [r for r in rs if not r["is_correct"]]
        if fast and len(wrong) >= 3:
            quick = [r for r in wrong if r["response_time"] and r["response_time"] < fast]
            if len(quick) / len(wrong) >= 0.5:
                found.append({"kind": "rushing", "topic_id": tid, "topic": rs[0]["topic"], "count": len(quick), "title": "Wrong answers came very fast",
                              "detail": f"{len(quick)} of {len(wrong)} wrong answers took under {round(fast)} seconds. Read every option before you answer."})
        easy = [r for r in rs if r["difficulty"] in ("easy", "medium", None)]
        hard = [r for r in rs if r["difficulty"] == "hard"]
        if len(easy) >= 3 and len(hard) >= 3:
            e, h = sum(r["is_correct"] for r in easy) / len(easy), sum(r["is_correct"] for r in hard) / len(hard)
            if e >= 0.75 and h <= 0.34:
                found.append({"kind": "slips_on_hard", "topic_id": tid, "topic": rs[0]["topic"], "count": len(hard), "title": "Solid on basics, slips on hard questions",
                              "detail": f"{round(e * 100)}% right on easy and medium questions but {round(h * 100)}% on hard ones ({len(hard)} answered)."})
    chosen = [r["chosen_index"] for r in rows if r["chosen_index"] is not None]
    if len(chosen) >= 12:
        idx, n = Counter(chosen).most_common(1)[0]
        if n / len(chosen) >= 0.55:
            found.append({"kind": "position_bias", "topic_id": None, "topic": "", "count": n, "title": "Leaning on one option position",
                          "detail": f"Option {LETTERS[idx]} was your choice in {round(100 * n / len(chosen))}% of {len(chosen)} answers. The right answer is placed at random, so this may be guessing."})
    order = {"repeat_miss": 0, "same_wrong_choice": 1, "rushing": 2, "slips_on_hard": 3, "position_bias": 4}
    found.sort(key=lambda p: (order[p["kind"]], -p["count"]))
    return {"patterns": found[:20], "recurring": recurring, "answers": len(rows),
            "method": "Counted from your own answers: a question missed twice or more, the same wrong option chosen twice, most wrong answers given very fast, "
                      "big gaps between easy and hard questions, and one option position chosen in over half of 12 or more answers."}


# ------------------------------------------------------------------------------------------------------------------- drift

def drift(db: sqlite3.Connection, user_id: int, subject_id: int, now: float | None = None) -> dict[int, dict]:
    """Per topic: confidence in the earlier 60% of answers vs the later 40%, and days since the last answer."""
    now = time.time() if now is None else now
    rows = insights._rows(db, user_id, subject_id)
    table = insights._difficulty_table(rows)
    by_topic: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r["topic_id"]:
            by_topic[r["topic_id"]].append(r)
    out = {}
    for tid, rs in by_topic.items():
        last = max((r["answered_at"] or 0) for r in rs)
        days = round((now - last) / 86400, 1) if last else None
        entry = {"days_since": days, "state": "steady", "earlier": None, "recent": None, "delta": None, "answers": len(rs)}
        if len(rs) >= MIN_DRIFT_ANSWERS:
            cut = max(3, int(len(rs) * 0.6))
            early, late = rs[:cut], rs[cut:]
            if len(late) >= 2:
                a = insights.estimate(insights._pack(early, table))["confidence"]
                b = insights.estimate(insights._pack(late, table))["confidence"]
                entry.update(earlier=a, recent=b, delta=round(b - a, 3))
                entry["state"] = "drifting" if b - a <= -DRIFT_DELTA else "growing" if b - a >= DRIFT_DELTA else "steady"
        if entry["state"] == "steady" and days is not None and days >= STALE_DAYS and len(rs) >= insights.MIN_EVIDENCE:
            entry["state"] = "fading"
        out[tid] = entry
    return out


def drift_note(d: dict) -> str | None:
    if d["state"] == "drifting":
        return f"Confidence fell from {round(d['earlier'] * 100)}% to {round(d['recent'] * 100)}% between your earlier and recent answers."
    if d["state"] == "growing":
        return f"Confidence rose from {round(d['earlier'] * 100)}% to {round(d['recent'] * 100)}% between your earlier and recent answers."
    if d["state"] == "fading":
        return f"Not practised for {round(d['days_since'])} days. Knowledge fades without review."
    return None


# ------------------------------------------------------------------------------------------------------------------ rollup

def rollup(gaps: list[dict]) -> list[dict]:
    """Topic -> unit mastery: the mean confidence of the assessed topics in each unit (unassessed topics are counted, not scored)."""
    units: dict[str, list[dict]] = defaultdict(list)
    for g in gaps:
        units[unit_of(g["path"])[0]].append(g)
    out = []
    for name, gs in units.items():
        scored = [g for g in gs if g["confidence"] is not None]
        conf = round(sum(g["confidence"] for g in scored) / len(scored), 3) if scored else None
        target = gs[0]["target"]
        out.append({"unit": name, "topics": len(gs), "assessed": len(scored), "confidence": conf, "answered": sum(g["answered"] for g in gs),
                    "status": "unassessed" if conf is None else "on_track" if conf >= target else "below", "order": min(g["ordinal"] for g in gs)})
    return sorted(out, key=lambda u: u["order"])
