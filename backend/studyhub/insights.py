"""What a student's answers say: a topic-by-topic confidence score (a small IRT model), backtracking, revision lists, a report.

IRT here is the three-parameter logistic model with FIXED discrimination (1.0) and guessing (0.25, four options).
Ability (theta) per topic is the posterior mean over a grid, with a Normal(0, 1.2) prior, so a topic with few answers stays near
"average" and shows a wide uncertainty instead of a made-up certainty. Item difficulty is learned only from this student's OTHER
answers to the same question (leave-one-out, shrunk toward 0), so a question is never judged by the very answer being scored.
Nothing here is invented: every number comes from answers the student gave.
"""
from __future__ import annotations

import math
import random
import sqlite3
from collections import defaultdict

GUESS = 0.25
DISC = 1.0
PRIOR_SD = 1.2
GRID = [i / 10 for i in range(-40, 41)]
PRIOR_B = {"easy": -0.8, "medium": 0.0, "hard": 0.8}    # starting difficulty of a question, from how it was written
MIN_EVIDENCE = 3            # answers needed before a topic gets a label other than "not enough answers"
BACKTRACK_MAX_DEPTH = 2     # a prerequisite of a prerequisite, no further
BACKTRACK_PER_STEP = 2      # questions asked from each prerequisite
BACKTRACK_MAX_TOTAL = 8     # per quiz


def p_correct(theta: float, b: float) -> float:
    return GUESS + (1 - GUESS) / (1 + math.exp(-DISC * (theta - b)))


def estimate(responses: list[tuple[float, bool]]) -> dict:
    """responses: (item difficulty b, answered correctly). Returns theta, its uncertainty, and the confidence score."""
    logp = []
    for th in GRID:
        lp = -0.5 * (th / PRIOR_SD) ** 2
        for b, ok in responses:
            p = p_correct(th, b)
            lp += math.log(p if ok else 1 - p)
        logp.append(lp)
    m = max(logp)
    w = [math.exp(x - m) for x in logp]
    z = sum(w)
    post = [x / z for x in w]
    mean = sum(t * p for t, p in zip(GRID, post))
    sd = math.sqrt(sum(p * (t - mean) ** 2 for t, p in zip(GRID, post)))
    return {
        "theta": round(mean, 3), "se": round(sd, 3),
        # the chance the student's true ability is above the "proficient" line (theta > 0 = right on an average question about 6 times in 10)
        "confidence": round(sum(p for t, p in zip(GRID, post) if t > 0), 4),
        "expected_accuracy": round(sum(p * p_correct(t, 0.0) for t, p in zip(GRID, post)), 4),
    }


def label(answered: int, confidence: float) -> str:
    if answered == 0:
        return "untried"
    if answered < MIN_EVIDENCE:
        return "few"
    return "confident" if confidence >= 0.8 else "building" if confidence >= 0.55 else "shaky"


def _rows(db: sqlite3.Connection, user_id: int, subject_id: int) -> list[dict]:
    q = ("SELECT aa.item_id, aa.is_correct, aa.response_time, aa.answered_at, aa.attempt_id, mi.topic_id, mi.difficulty FROM attempt_answers aa "
         "JOIN quiz_attempts qa ON qa.id=aa.attempt_id JOIN mcq_items mi ON mi.id=aa.item_id "
         "WHERE qa.user_id=? AND qa.subject_id=? AND aa.is_correct IS NOT NULL ORDER BY aa.answered_at, aa.id")
    return [dict(r) for r in db.execute(q, (user_id, subject_id))]


def _difficulty_table(rows: list[dict]) -> dict[int, tuple[int, int, float]]:
    t: dict[int, list] = defaultdict(lambda: [0, 0, 0.0])
    for r in rows:
        t[r["item_id"]][0] += 1
        t[r["item_id"]][1] += int(r["is_correct"])
        t[r["item_id"]][2] = PRIOR_B.get(r.get("difficulty"), 0.0)
    return {k: (v[0], v[1], v[2]) for k, v in t.items()}


def _b(table: dict, item_id: int, ok: bool) -> float:
    """Difficulty of an item: how it was written (prior), pulled toward what the student's OTHER answers to it show (leave-one-out)."""
    n, c, prior = table.get(item_id, (0, 0, 0.0))
    n, c = n - 1, c - int(ok)
    if n <= 0:
        return prior
    q = (c + 1) / (n + 2)
    q = min(max((q - GUESS) / (1 - GUESS), 0.1), 0.9)
    return (2 * prior + n * -math.log(q / (1 - q))) / (2 + n)


def _pack(rows: list[dict], table: dict) -> list[tuple[float, bool]]:
    return [(_b(table, r["item_id"], bool(r["is_correct"])), bool(r["is_correct"])) for r in rows]


def topic_confidence(db: sqlite3.Connection, user_id: int, subject_id: int) -> dict:
    """Per-topic and overall confidence for one subject."""
    rows = _rows(db, user_id, subject_id)
    table = _difficulty_table(rows)
    by_topic: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r["topic_id"]:
            by_topic[r["topic_id"]].append(r)
    out = {}
    for tid, rs in by_topic.items():
        est = estimate(_pack(rs, table))
        n, c = len(rs), sum(int(r["is_correct"]) for r in rs)
        times = [r["response_time"] for r in rs if r["response_time"]]
        recent = rs[-5:]
        est.update({"answered": n, "correct": c, "label": label(n, est["confidence"]),
                    "avg_seconds": round(sum(times) / len(times), 1) if times else None,
                    "recent_accuracy": round(sum(int(r["is_correct"]) for r in recent) / len(recent), 3)})
        out[tid] = est
    overall = estimate(_pack(rows, table)) if rows else None
    if overall:
        overall.update({"answered": len(rows), "correct": sum(int(r["is_correct"]) for r in rows)})
    return {"topics": out, "overall": overall}


def ability_trend(db: sqlite3.Connection, user_id: int, subject_id: int, limit: int = 20) -> list[dict]:
    """Overall ability after each finished quiz, oldest first (cumulative over every answer up to that quiz)."""
    rows = _rows(db, user_id, subject_id)
    table = _difficulty_table(rows)
    order: list[int] = []
    for r in rows:
        if r["attempt_id"] not in order:
            order.append(r["attempt_id"])
    trend = []
    for aid in order[-limit:]:
        upto = [r for r in rows if r["attempt_id"] <= aid and (r["attempt_id"] in order[: order.index(aid) + 1])]
        mine = [r for r in rows if r["attempt_id"] == aid]
        est = estimate(_pack(upto, table))
        trend.append({"attempt_id": aid, "at": mine[-1]["answered_at"], "theta": est["theta"], "confidence": est["confidence"],
                      "accuracy": round(sum(int(r["is_correct"]) for r in mine) / len(mine), 3), "answered": len(mine)})
    return trend


def prerequisite_topics(db: sqlite3.Connection, subject_id: int, topic_id: int) -> list[int]:
    """The student's confirmed prerequisites of a topic; without any, the nearest earlier topic (document order) that has practice questions."""
    rows = db.execute("SELECT prereq_id FROM topic_prereqs WHERE topic_id=? AND confirmed=1", (topic_id,)).fetchall()
    if rows:
        return [r[0] for r in rows]
    cur = db.execute("SELECT ordinal FROM topics WHERE id=? AND subject_id=?", (topic_id, subject_id)).fetchone()
    if cur is None:
        return []
    prev = db.execute(
        "SELECT t.id FROM topics t WHERE t.subject_id=? AND t.ordinal<? AND EXISTS(SELECT 1 FROM mcq_items m WHERE m.topic_id=t.id) "
        "ORDER BY t.ordinal DESC LIMIT 1", (subject_id, cur[0])).fetchone()
    return [prev[0]] if prev else []


def backtrack(db: sqlite3.Connection, user_id: int, subject_id: int, attempt_id: int, missed_row_id: int) -> dict | None:
    """After a wrong answer, queue a few questions from the topic it builds on, to be asked NEXT. Returns what was queued, or None."""
    row = db.execute(
        "SELECT aa.item_id, aa.depth, aa.is_correct, mi.topic_id FROM attempt_answers aa JOIN mcq_items mi ON mi.id=aa.item_id "
        "WHERE aa.id=? AND aa.attempt_id=?", (missed_row_id, attempt_id)).fetchone()
    if row is None or row["is_correct"] != 0 or not row["topic_id"] or row["depth"] >= BACKTRACK_MAX_DEPTH:
        return None
    total = db.execute("SELECT COUNT(*) FROM attempt_answers WHERE attempt_id=? AND backtrack_from IS NOT NULL", (attempt_id,)).fetchone()[0]
    if total >= BACKTRACK_MAX_TOTAL:
        return None
    topic = row["topic_id"]
    if db.execute("SELECT 1 FROM attempt_answers WHERE attempt_id=? AND backtrack_from=? LIMIT 1", (attempt_id, topic)).fetchone():
        return None                                              # one step back per missed topic per quiz
    existing = {r["item_id"]: r for r in db.execute("SELECT id, item_id, answered_at, backtrack_from FROM attempt_answers WHERE attempt_id=?", (attempt_id,))}
    queued, names = 0, []
    for pre in prerequisite_topics(db, subject_id, topic):
        pool = [r[0] for r in db.execute(
            "SELECT m.id FROM mcq_items m JOIN subjects s ON s.id=m.subject_id WHERE m.topic_id=? AND m.subject_id=? AND s.user_id=?",
            (pre, subject_id, user_id))]
        # questions of that topic that are already waiting later in this quiz are pulled forward; new ones are added if the quiz has too few
        pull = [i for i in pool if i in existing and existing[i]["answered_at"] is None and existing[i]["backtrack_from"] is None]
        fresh = [i for i in pool if i not in existing]
        random.shuffle(pull)
        random.shuffle(fresh)
        took = 0
        for item in (pull + fresh)[:BACKTRACK_PER_STEP]:
            if total + queued >= BACKTRACK_MAX_TOTAL:
                break
            if item in existing:
                db.execute("UPDATE attempt_answers SET backtrack_from=?, depth=? WHERE id=?", (topic, row["depth"] + 1, existing[item]["id"]))
            else:
                db.execute("INSERT INTO attempt_answers(attempt_id, item_id, backtrack_from, depth) VALUES (?,?,?,?)", (attempt_id, item, topic, row["depth"] + 1))
            queued += 1
            took += 1
        if took:
            names.append(db.execute("SELECT name FROM topics WHERE id=?", (pre,)).fetchone()[0])
    if not queued:
        return None
    return {"from": db.execute("SELECT name FROM topics WHERE id=?", (topic,)).fetchone()[0], "to": names, "questions": queued}


def wrong_items(db: sqlite3.Connection, user_id: int, subject_id: int) -> list[dict]:
    """Questions whose LATEST answer was wrong, newest mistake first, with what the student chose and the right answer."""
    q = ("SELECT aa.item_id, aa.chosen_index, aa.answered_at, mi.question, mi.options, mi.answer_index, mi.explanation, mi.topic_id, mi.topic_path, "
         "(SELECT is_correct FROM attempt_answers b JOIN quiz_attempts bq ON bq.id=b.attempt_id WHERE b.item_id=aa.item_id AND bq.user_id=? "
         " AND b.is_correct IS NOT NULL ORDER BY b.answered_at DESC, b.id DESC LIMIT 1) AS latest "
         "FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id JOIN mcq_items mi ON mi.id=aa.item_id "
         "WHERE qa.user_id=? AND qa.subject_id=? AND aa.is_correct=0 ORDER BY aa.answered_at DESC, aa.id DESC")
    import json
    seen, out = set(), []
    for r in db.execute(q, (user_id, user_id, subject_id)):
        if r["latest"] != 0 or r["item_id"] in seen:
            continue
        seen.add(r["item_id"])
        out.append({"item_id": r["item_id"], "question": r["question"], "options": json.loads(r["options"]), "chosen_index": r["chosen_index"],
                    "answer_index": r["answer_index"], "explanation": r["explanation"] or "", "topic_id": r["topic_id"], "topic": r["topic_path"] or ""})
    return out


def recommendations(topics: list[dict], overall: dict | None, wrong: int) -> list[str]:
    """Plain rules over the numbers above; each line says which numbers it rests on."""
    tips: list[str] = []
    if not overall:
        return ["Take a diagnostic quiz to get a first confidence score for every topic."]
    shaky = sorted([t for t in topics if t["label"] == "shaky"], key=lambda t: t["confidence"])
    if shaky:
        tips.append("Revise first: " + ", ".join(f'{t["name"]} ({round(t["confidence"] * 100)}% confidence, {t["correct"]}/{t["answered"]} correct)' for t in shaky[:3]) + ".")
    untried = [t for t in topics if t["label"] == "untried"]
    if untried:
        tips.append(f"{len(untried)} topic(s) have no answers yet, for example {untried[0]['name']}. A diagnostic quiz covers them quickly.")
    few = [t for t in topics if t["label"] == "few"]
    if few:
        tips.append(f"{len(few)} topic(s) have fewer than {MIN_EVIDENCE} answers, so their score is still a rough guess.")
    if wrong:
        tips.append(f"{wrong} question(s) are still answered wrongly. A revision quiz repeats exactly those.")
    slow = [t for t in topics if t.get("avg_seconds") and t["avg_seconds"] > 45 and t["answered"] >= MIN_EVIDENCE]
    if slow:
        tips.append(f"You are slow on {slow[0]['name']} (about {round(slow[0]['avg_seconds'])} s per question): more practice there should help.")
    if not tips:
        tips.append("Everything with enough answers looks solid. Keep practising to keep it that way.")
    return tips


LEVEL_NAMES = {"new": "New learner", "intermediate": "Intermediate", "professional": "Professional"}


def suggested_level(theta: float, answered: int) -> str | None:
    if answered < 5:
        return None
    return "new" if theta < -0.35 else "intermediate" if theta < 0.45 else "professional"


def diagnosis(db: sqlite3.Connection, user_id: int, subject_id: int, attempt_id: int, claimed: str | None) -> dict | None:
    """What a diagnostic quiz says: accuracy by difficulty, the level it suggests, and which topics look strong or weak."""
    rows = [r for r in _rows(db, user_id, subject_id) if r["attempt_id"] == attempt_id]
    if not rows:
        return None
    by = {d: [0, 0] for d in ("easy", "medium", "hard")}
    for r in rows:
        d = r["difficulty"] if r["difficulty"] in by else "medium"
        by[d][1] += 1
        by[d][0] += int(r["is_correct"])
    est = estimate([(PRIOR_B.get(r["difficulty"], 0.0), bool(r["is_correct"])) for r in rows])
    level = suggested_level(est["theta"], len(rows))
    conf = topic_confidence(db, user_id, subject_id)["topics"]
    names = {r["id"]: r["name"] for r in db.execute("SELECT id, name FROM topics WHERE subject_id=?", (subject_id,))}
    mine = []
    for tid in {r["topic_id"] for r in rows if r["topic_id"]}:
        e = conf.get(tid)
        if e and tid in names:
            mine.append({"topic_id": tid, "name": names[tid], "confidence": e["confidence"], "label": e["label"], "answered": e["answered"], "correct": e["correct"]})
    mine.sort(key=lambda t: t["confidence"])
    order = ["new", "intermediate", "professional"]
    note = None
    if level and claimed in order:
        gap = order.index(level) - order.index(claimed)
        note = ("Your result matches what you said." if gap == 0 else
                f"You said {LEVEL_NAMES[claimed]}; this test suggests {LEVEL_NAMES[level]} ({'a step lower' if gap < 0 else 'a step higher'}). "
                "It is only ten questions, so treat it as a starting point.")
    return {"claimed": claimed, "suggested": level, "note": note, "theta": est["theta"], "confidence": est["confidence"],
            "by_difficulty": {k: {"correct": v[0], "answered": v[1]} for k, v in by.items()},
            "weakest": mine[:3], "strongest": [t for t in reversed(mine) if t["confidence"] >= 0.55][:3],
            "answered": len(rows), "correct": sum(int(r["is_correct"]) for r in rows)}


# ------------------------------------------------------------------------------------------------ adaptive selection

def information(theta: float, b: float) -> float:
    """Fisher information of a 3PL item at ability theta: how much answering it would teach us about the student."""
    p = p_correct(theta, b)
    return (DISC ** 2) * ((1 - p) / p) * ((p - GUESS) / (1 - GUESS)) ** 2


def select_adaptive(db: sqlite3.Connection, user_id: int, subject_id: int, items: list[dict], n: int, target: float = 0.7,
                    weights: dict[int, dict] | None = None, rng: random.Random | None = None) -> list[dict]:
    """Choose n questions that are most informative at the student's current ability on each topic, favouring topics below target and topics that
    past papers ask about. A question answered before counts less, and no topic takes more than half the quiz. Same ability, same picks (ties aside)."""
    rng = rng or random.Random()
    weights = weights or {}
    conf = topic_confidence(db, user_id, subject_id)["topics"]
    table = _difficulty_table(_rows(db, user_id, subject_id))
    scored = []
    for it in items:
        e = conf.get(it["topic_id"])
        theta = e["theta"] if e else 0.0
        seen, correct, _ = table.get(it["id"], (0, 0, 0.0))
        b = PRIOR_B.get(it.get("difficulty"), 0.0)
        if seen:
            q = min(max(((correct + 1) / (seen + 2) - GUESS) / (1 - GUESS), 0.1), 0.9)
            b = (2 * b + seen * -math.log(q / (1 - q))) / (2 + seen)
        gap = max(0.0, target - e["confidence"]) if e else 0.25
        w = (1 + gap * 2) * (1 + 2 * weights.get(it["topic_id"], {}).get("weight", 0)) * (0.6 if seen else 1.0)
        scored.append((information(theta, b) * w * (1 + rng.random() * 0.05), it))
    scored.sort(key=lambda x: -x[0])
    cap, taken, chosen = max(2, -(-n // 2)), defaultdict(int), []
    for _, it in scored:
        if len(chosen) >= n:
            break
        if taken[it["topic_id"]] < cap:
            taken[it["topic_id"]] += 1
            chosen.append(it)
    for _, it in scored:                                                    # a small subject: fill the rest whatever the cap
        if len(chosen) >= n:
            break
        if it not in chosen:
            chosen.append(it)
    return chosen
