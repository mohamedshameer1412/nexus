"""Bayesian Knowledge Tracing: the probability that an officer has mastered a skill (topic), updated answer by answer.

Each topic is a hidden state, learned or not. Four parameters (Corbett & Anderson, 1995):
    P_INIT   chance the skill is already known before any answer
    P_LEARN  chance of learning it between two answers
    P_SLIP   chance of a wrong answer although it is known
    P_GUESS  chance of a right answer although it is not (a four-option question: about 1 in 4)
After each answer the posterior is computed with Bayes' rule and then the learning step is applied. Three right answers in a
row from scratch give about 0.96, which crosses MASTERED.

The root-cause trace (agents.Evaluator) walks the prerequisite graph with these probabilities, and a verified re-test
(`gap_report`) uses them to say whether a gap is closed. STUDYHUB_BKT="init,learn,slip,guess" tunes the four numbers.
"""
from __future__ import annotations

import os
import sqlite3
from collections import defaultdict


def params() -> tuple[float, float, float, float]:
    raw = os.environ.get("STUDYHUB_BKT", "0.2,0.15,0.1,0.25")
    p_init, p_learn, p_slip, p_guess = (float(x) for x in raw.split(","))
    return p_init, p_learn, p_slip, p_guess


MASTERED = float(os.environ.get("STUDYHUB_BKT_MASTERED", "0.95"))


def update(p: float, correct: bool, prm: tuple[float, float, float, float] | None = None) -> float:
    """P(known) after one more answer."""
    _, learn, slip, guess = prm or params()
    if correct:
        post = p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)
    else:
        post = p * slip / (p * slip + (1 - p) * (1 - guess))
    return post + (1 - post) * learn


def mastery(answers: list[bool], prm: tuple[float, float, float, float] | None = None) -> float:
    prm = prm or params()
    p = prm[0]
    for a in answers:
        p = update(p, a, prm)
    return p


def sequences(db: sqlite3.Connection, user_id: int, subject_id: int, *, exclude_attempt: int | None = None) -> dict[int, list[bool]]:
    """Every marked answer of this officer in this subject, per topic, oldest first."""
    rows = db.execute(
        "SELECT mi.topic_id AS t, aa.is_correct AS c FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id "
        "JOIN mcq_items mi ON mi.id=aa.item_id WHERE qa.user_id=? AND qa.subject_id=? AND aa.is_correct IS NOT NULL "
        "AND mi.topic_id IS NOT NULL AND qa.id <> ? ORDER BY aa.answered_at, aa.id",
        (user_id, subject_id, exclude_attempt or -1)).fetchall()
    out: dict[int, list[bool]] = defaultdict(list)
    for r in rows:
        out[int(r["t"])].append(bool(r["c"]))
    return dict(out)


def topic_mastery(db: sqlite3.Connection, user_id: int, subject_id: int, *, exclude_attempt: int | None = None) -> dict[int, dict]:
    """{topic_id: {"p": P(known), "answered": n, "mastered": bool}} for every topic with at least one marked answer."""
    prm = params()
    return {t: {"p": round(mastery(seq, prm), 4), "answered": len(seq), "mastered": mastery(seq, prm) >= MASTERED}
            for t, seq in sequences(db, user_id, subject_id, exclude_attempt=exclude_attempt).items()}


def gap_report(db: sqlite3.Connection, user_id: int, subject_id: int, attempt_id: int) -> dict:
    """After a quiz (a verified re-test above all): per topic, mastery before and after it, whether the gap is closed, and
    when it is not, the next root gap to work on (traced back through the prerequisite graph with BKT mastery)."""
    from . import agents                                    # agents imports this module
    before = topic_mastery(db, user_id, subject_id, exclude_attempt=attempt_id)
    after = topic_mastery(db, user_id, subject_id)
    rows = db.execute(
        "SELECT mi.topic_id AS t, aa.is_correct AS c, aa.self_confidence AS sc FROM attempt_answers aa JOIN mcq_items mi ON mi.id=aa.item_id "
        "JOIN quiz_attempts qa ON qa.id=aa.attempt_id WHERE aa.attempt_id=? AND qa.user_id=? AND aa.is_correct IS NOT NULL",
        (attempt_id, user_id)).fetchall()
    names, parents = agents.prereq_graph(db, subject_id)
    p_after = {t: v["p"] for t, v in after.items()}
    topics = []
    for t in sorted({int(r["t"]) for r in rows if r["t"] is not None}, key=lambda t: names.get(t, "")):
        a = after.get(t, {"p": params()[0], "mastered": False})
        entry = {"topic_id": t, "topic": names.get(t, "?"), "before": before.get(t, {}).get("p"), "after": a["p"], "closed": a["mastered"]}
        if not a["mastered"]:
            rc = agents.find_root_cause(parents, t, p_after, MASTERED)
            entry["next_gap"] = {"topic_id": rc["root"], "topic": names.get(rc["root"], "?"), "chain": [names.get(c, "?") for c in rc["chain"]]}
        topics.append(entry)
    sure_wrong = sum(1 for r in rows if r["sc"] == 3 and not r["c"])
    return {"attempt_id": attempt_id, "mastered_at": MASTERED, "topics": topics,
            "closed": bool(topics) and all(t["closed"] for t in topics),
            "confidently_wrong": sure_wrong, "rated": sum(1 for r in rows if r["sc"] is not None)}


if __name__ == "__main__":                                 # self-check: three right answers from scratch cross MASTERED
    assert mastery([True, True, True]) >= MASTERED > mastery([True, True])
    assert mastery([False, False]) < params()[0] + 0.1 and update(0.5, True) > 0.5 > update(0.5, False)
    print("bkt ok", round(mastery([True, True, True]), 3))
