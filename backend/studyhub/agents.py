"""The Nexus agent pipeline: Observe -> Diagnose -> Predict -> Decide -> Intervene -> Verify -> Remember -> Replan.

Six agents run, in order, after a quiz (and whenever the student asks on the Agent Console). Each one reads the database,
decides something, and writes one step into `agent_runs.steps_json`, so "why did Nexus tell me that?" always has an answer.
They are deterministic: formulas over the student's own answers (the Bayesian IRT in insights.py, the prerequisite graph,
the roadmap, the risk and debt formulas). No agent calls a language model, so the pipeline is instant, free and repeatable.

  1. Evaluator  - scores the last quiz and traces every miss BACKWARDS through the prerequisite graph to the deepest weak
                  ancestor: the root cause. "Weak" is Bayesian Knowledge Tracing mastery (bkt.py) below the target.
  2. Analytics  - updates the learner twin: ability (theta) and its uncertainty, change since the previous quiz, concept drift,
                  and the confidence-ability gap between how sure the student feels and what the answers show.
  3. Predictor  - future risk per topic (distance below target, slipping trend, weak foundations, deadline).
  4. Planner    - learning debt with its "interest" (time owed on topics that block others) and the next best actions.
  5. Tutor      - picks the intervention for the top root cause and the passages from the student's own material to use.
  6. Mentor     - re-scores career readiness for every saved job description against verified skills.
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections import defaultdict, deque

from . import bkt, career, foresight, insights, patterns, roadmap, tutor
from .repo import Repo

AGENTS = [
    {"key": "evaluator", "name": "Evaluator", "role": "Scores the quiz and traces misses back to their root cause"},
    {"key": "analytics", "name": "Analytics", "role": "Updates the learner twin: ability, drift, confidence gap"},
    {"key": "predictor", "name": "Predictor", "role": "Estimates which topics are at risk next"},
    {"key": "planner", "name": "Planner", "role": "Prices learning debt and ranks the next best actions"},
    {"key": "tutor", "name": "Tutor", "role": "Chooses the intervention and the passages to learn from"},
    {"key": "mentor", "name": "Mentor", "role": "Re-scores career readiness against verified skills"},
]


MAX_TRACE_DEPTH = 4            # a foundation of a foundation ... four steps back at most


# ------------------------------------------------------------------------------------------------- the graph

def prereq_graph(db: sqlite3.Connection, subject_id: int) -> tuple[dict[int, str], dict[int, list[int]]]:
    """(names, parents): parents[t] are the topics t builds on. Confirmed edges; a topic without any gets the implicit one
    insights.prerequisite_topics uses (the nearest earlier topic that has questions), so the graph matches the quiz backtracking."""
    names = {r["id"]: r["name"] for r in db.execute("SELECT id, name FROM topics WHERE subject_id=? ORDER BY ordinal", (subject_id,))}
    parents: dict[int, list[int]] = {t: [] for t in names}
    for t in names:
        parents[t] = [p for p in insights.prerequisite_topics(db, subject_id, t) if p in names and p != t]
    return names, parents


def find_root_cause(parents: dict[int, list[int]], failed: int, mastery: dict[int, float | None], threshold: float) -> dict:
    """Walk backwards from a failed topic; the root cause is the weak ancestor furthest away (breadth-first, cycle-safe).
    mastery[t] is the BKT probability the skill is known, 0..1 (None = never assessed, treated as weak: an untested foundation
    is a suspect)."""
    dist = {failed: 0}
    prev: dict[int, int] = {}
    q = deque([failed])
    weak: list[int] = []
    while q:
        cur = q.popleft()
        if dist[cur] >= MAX_TRACE_DEPTH:
            continue
        for p in parents.get(cur, []):
            if p in dist:
                continue
            dist[p] = dist[cur] + 1
            prev[p] = cur
            m = mastery.get(p)
            if m is None or m < threshold:
                weak.append(p)
                q.append(p)                      # keep walking only through weak foundations
    root = max(weak, key=lambda t: (dist[t], -(mastery.get(t) or 0))) if weak else failed
    chain = [root]
    while chain[-1] != failed:
        chain.append(prev[chain[-1]])
    return {"failed": failed, "root": root, "chain": chain, "weak_ancestors": weak, "depth": dist[root]}


# ------------------------------------------------------------------------------------------------- the agents

def _step(key: str, t0: float, summary: str, status: str = "done", **details) -> dict:
    a = next(x for x in AGENTS if x["key"] == key)
    return {"agent": key, "name": a["name"], "role": a["role"], "status": status, "summary": summary, "ms": round((time.perf_counter() - t0) * 1000, 1), "details": details}


def _last_attempt(db: sqlite3.Connection, user_id: int, subject_id: int, attempt_id: int | None) -> dict | None:
    if attempt_id:
        r = db.execute("SELECT * FROM quiz_attempts WHERE id=? AND user_id=? AND subject_id=?", (attempt_id, user_id, subject_id)).fetchone()
    else:
        r = db.execute("SELECT * FROM quiz_attempts WHERE user_id=? AND subject_id=? AND is_active=0 AND correct_answers+incorrect_answers>0 "
                       "ORDER BY finished_at DESC, id DESC LIMIT 1", (user_id, subject_id)).fetchone()
    return dict(r) if r else None


def evaluator(db, user_id, subject_id, attempt, conf, target, names, parents) -> dict:
    t0 = time.perf_counter()
    if attempt is None:
        return _step("evaluator", t0, "No finished quiz yet, so there is nothing to score.", "idle", misses=[], root_causes=[])
    rows = db.execute("SELECT aa.is_correct, mi.topic_id FROM attempt_answers aa JOIN mcq_items mi ON mi.id=aa.item_id "
                      "WHERE aa.attempt_id=? AND aa.is_correct IS NOT NULL", (attempt["id"],)).fetchall()
    answered = len(rows)
    correct = sum(int(r["is_correct"]) for r in rows)
    missed: dict[int, int] = defaultdict(int)
    for r in rows:
        if not r["is_correct"] and r["topic_id"]:
            missed[r["topic_id"]] += 1
    known = bkt.topic_mastery(db, user_id, subject_id)               # BKT: P(mastered) per skill, answer by answer
    mastery = {t: known[t]["p"] if t in known else None for t in names}
    roots: dict[int, dict] = {}
    traces = []
    for tid, n in sorted(missed.items(), key=lambda kv: -kv[1]):
        rc = find_root_cause(parents, tid, mastery, target)
        traces.append({"topic_id": tid, "topic": names.get(tid, "?"), "missed": n, "root_id": rc["root"], "root": names.get(rc["root"], "?"),
                       "chain": [names.get(c, "?") for c in rc["chain"]], "depth": rc["depth"]})
        r = roots.setdefault(rc["root"], {"topic_id": rc["root"], "topic": names.get(rc["root"], "?"), "explains": [], "missed": 0,
                                          "confidence": (conf.get(rc["root"]) or {}).get("confidence"), "bkt": mastery.get(rc["root"])})
        r["explains"].append(names.get(tid, "?"))
        r["missed"] += n
    ranked = sorted(roots.values(), key=lambda r: (-r["missed"], -len(r["explains"])))
    pct = round(100 * correct / answered) if answered else 0
    if not missed:
        summary = f"Quiz #{attempt['id']}: {correct} of {answered} correct ({pct}%). No misses to trace."
    else:
        top = ranked[0]
        deeper = [t for t in traces if t["depth"] > 0]
        summary = (f"Quiz #{attempt['id']}: {correct} of {answered} correct ({pct}%). "
                   + (f"{len(deeper)} of {len(traces)} missed topics trace back to a weaker foundation; the main root cause is {top['topic']}."
                      if deeper else f"The misses sit in the topics themselves; {top['topic']} needs the most work."))
    return _step("evaluator", t0, summary, attempt_id=attempt["id"], answered=answered, correct=correct, accuracy=pct,
                 misses=traces, root_causes=ranked[:5])


def analytics(db, user_id, subject_id, conf_all, info, attempt) -> dict:
    t0 = time.perf_counter()
    overall = conf_all["overall"]
    trend = insights.ability_trend(db, user_id, subject_id)
    delta = round(trend[-1]["theta"] - trend[-2]["theta"], 3) if len(trend) >= 2 else None
    drift = patterns.drift(db, user_id, subject_id)
    names = {g["topic_id"]: g["name"] for g in info["gaps"]}
    drifting = [{"topic_id": t, "topic": names.get(t, "?"), "state": d["state"], "note": patterns.drift_note(d)} for t, d in drift.items() if d["state"] in ("drifting", "fading") and t in names]
    growing = [names[t] for t, d in drift.items() if d["state"] == "growing" and t in names]
    sc = foresight.self_check(info, foresight.get_ratings(db, user_id, subject_id))
    gaps = [t for t in sc["topics"] if t["delta"] is not None and abs(t["delta"]) >= foresight.MISMATCH]
    if overall is None:
        return _step("analytics", t0, "No answers yet: the twin starts at average ability with wide uncertainty.", "idle", overall=None, trend=[], drift=[], confidence_gap=[])
    parts = [f"Ability θ = {overall['theta']:+.2f} ± {overall['se']:.2f} (confidence {round(overall['confidence'] * 100)}%)"]
    if delta is not None:
        parts.append(("up " if delta >= 0 else "down ") + f"{abs(delta):.2f} since the previous quiz")
    if drifting:
        parts.append(f"{len(drifting)} topic{'s' if len(drifting) != 1 else ''} drifting or fading")
    if gaps:
        parts.append(f"{len(gaps)} topic{'s' if len(gaps) != 1 else ''} where feeling and results disagree")
    return _step("analytics", t0, "; ".join(parts) + ".", overall=overall, theta_delta=delta,
                 trend=[{"attempt_id": x["attempt_id"], "theta": x["theta"], "confidence": x["confidence"], "accuracy": x["accuracy"]} for x in trend[-12:]],
                 drift=drifting[:8], growing=growing[:8],
                 confidence_gap=[{"topic_id": t["topic_id"], "topic": t["name"], "felt": t["perceived"], "measured": t["confidence"], "delta": t["delta"], "verdict": t["verdict"]} for t in gaps[:8]])


def predictor(info, plan) -> dict:
    t0 = time.perf_counter()
    r = foresight.risk(info, plan["summary"])
    s = r["summary"]
    top = [t for t in r["topics"] if t["score"] is not None][:6]
    if s["score"] is None:
        return _step("predictor", t0, "Not enough answers to judge risk yet. Take a quiz to seed the twin.", "idle", summary=s, topics=[])
    summary = f"Overall risk {s['score']}/100 ({s['level']}). {s['high']} high-risk and {s['medium']} medium-risk topic(s)" + (", and the plan does not fit before the target date." if s["late"] else ".")
    return _step("predictor", t0, summary, summary_stats=s, topics=top, method=r["method"])


def planner(db, user_id, subject_id, info, plan, conf) -> dict:
    t0 = time.perf_counter()
    d = foresight.debt(info)
    actions = tutor.next_actions(db, user_id, subject_id, info, conf, patterns.exam_weights(db, subject_id), patterns.drift(db, user_id, subject_id), plan["summary"])
    s = plan["summary"]
    if not actions and not d["topics"]:
        return _step("planner", t0, "No debt to repay: every assessed topic is at or above target.", debt_hours=0, debt=[], actions=[], plan=s)
    first = actions[0]["title"] if actions else None
    summary = (f"Learning debt {d['total_hours']} h across {len(d['topics'])} topic(s)."
               + (f" Next: {first}." if first else "")
               + (f" At {s['hours_per_week']} h/week the plan needs about {s['weeks']} week(s)." if s.get("weeks") else ""))
    return _step("planner", t0, summary, debt_hours=d["total_hours"], debt=d["topics"][:8], edges=d["edges"], actions=actions[:5], plan=s)


def tutor_agent(db, subject_id, root_causes, actions, conf) -> dict:
    t0 = time.perf_counter()
    focus = root_causes[0]["topic_id"] if root_causes else (actions[0]["topic_id"] if actions else None)
    if focus is None:
        return _step("tutor", t0, "Nothing to teach right now. Keep practising to confirm mastery.", "idle", focus=None)
    name = db.execute("SELECT name FROM topics WHERE id=?", (focus,)).fetchone()
    name = name[0] if name else "?"
    e = conf.get(focus)
    level = tutor.advise_level(e["theta"] if e else None, e["answered"] if e else 0)
    act = next((a for a in actions if a["topic_id"] == focus), None)
    texts = tutor.passages(db, subject_id, focus, 3)
    kind = act["kind"] if act else "worked_example"
    label = tutor.KIND_INFO.get(kind, (kind.replace("_", " ").title(), 0))[0]
    summary = f"Intervention for {name}: {label.lower()} at {level['difficulty']} difficulty, from {len(texts)} passage(s) of your own material."
    return _step("tutor", t0, summary, focus={"topic_id": focus, "topic": name}, kind=kind, label=label, difficulty=level["difficulty"], why=level["why"],
                 href=act["href"] if act else f"/subjects/{subject_id}/twin?topic={focus}", passages=[t[:280] for t in texts])


def mentor(db, user_id) -> dict:
    t0 = time.perf_counter()
    goals = [g for g in career.listing(db, user_id) if g["status"] == "done"]
    if not goals:
        return _step("mentor", t0, "No career goal yet. Paste a job description on the Career page to connect study to a role.", "idle", goals=[])
    pool = career.evidence_pool(db, user_id)
    out = []
    for g in goals[:5]:
        skills = json.loads(g["skills_json"] or "[]")
        assessed = career.assess(db, user_id, skills, pool)
        sc = career.score(assessed)
        career.snapshot(db, g["id"], sc["readiness"], sc["verified"], sc["total"])
        out.append({"id": g["id"], "title": g["title"], "readiness": sc["readiness"], "verified": sc["verified"], "total": sc["total"]})
    best = max(out, key=lambda g: g["readiness"] or 0)
    summary = f"{len(out)} career goal(s) re-scored. Closest: {best['title']} at {round((best['readiness'] or 0) * 100)}% ready ({best['verified']}/{best['total']} skills verified)."
    return _step("mentor", t0, summary, goals=out)


# ------------------------------------------------------------------------------------------------- the pipeline

def run(db: sqlite3.Connection, user_id: int, subject_id: int, *, trigger: str = "manual", attempt_id: int | None = None, save: bool = True) -> dict:
    """Run all six agents for one subject and (by default) store the run. Returns the run as the API shows it."""
    t0 = time.perf_counter()
    subject = Repo(db).get_subject(user_id, subject_id)
    if subject is None:
        raise KeyError(subject_id)
    profile = roadmap.get_profile(db, user_id, subject_id)
    info = roadmap.skill_gaps(db, user_id, subject_id, subject.get("level"))
    plan = roadmap.build(info, subject_id, profile["hours_per_week"], profile["target_date"])
    conf_all = insights.topic_confidence(db, user_id, subject_id)
    conf = conf_all["topics"]
    names, parents = prereq_graph(db, subject_id)
    attempt = _last_attempt(db, user_id, subject_id, attempt_id)
    steps = []
    ev = evaluator(db, user_id, subject_id, attempt, conf, info["target"], names, parents)
    steps.append(ev)
    steps.append(analytics(db, user_id, subject_id, conf_all, info, attempt))
    steps.append(predictor(info, plan))
    pl = planner(db, user_id, subject_id, info, plan, conf)
    steps.append(pl)
    steps.append(tutor_agent(db, subject_id, ev["details"].get("root_causes", []), pl["details"].get("actions", []), conf))
    steps.append(mentor(db, user_id))
    ms = round((time.perf_counter() - t0) * 1000)
    active = [s for s in steps if s["status"] == "done"]
    summary = " ".join(s["summary"] for s in active[:2]) if active else "Upload material and take a quiz: the agents start working as soon as there are answers."
    now = time.time()
    rid = None
    if save:
        rid = db.execute("INSERT INTO agent_runs(user_id, subject_id, attempt_id, trigger, steps_json, summary, ms, created_at) VALUES (?,?,?,?,?,?,?,?)",
                         (user_id, subject_id, attempt["id"] if attempt else None, trigger, json.dumps(steps), summary, ms, now)).lastrowid
        db.execute("DELETE FROM agent_runs WHERE user_id=? AND subject_id=? AND id NOT IN (SELECT id FROM agent_runs WHERE user_id=? AND subject_id=? ORDER BY id DESC LIMIT 30)",
                   (user_id, subject_id, user_id, subject_id))
    return {"id": rid, "trigger": trigger, "attempt_id": attempt["id"] if attempt else None, "steps": steps, "summary": summary, "ms": ms,
            "created_at": now, "graph": graph_json(names, parents, conf, info["target"])}


def graph_json(names: dict[int, str], parents: dict[int, list[int]], conf: dict[int, dict], target: float) -> dict:
    nodes = []
    for t, n in names.items():
        c = (conf.get(t) or {}).get("confidence")
        nodes.append({"id": t, "name": n, "confidence": c, "state": "unknown" if c is None else "solid" if c >= target else "weak"})
    return {"nodes": nodes, "edges": [{"from": p, "to": t} for t, ps in parents.items() for p in ps]}


def latest(db: sqlite3.Connection, user_id: int, subject_id: int) -> dict | None:
    r = db.execute("SELECT * FROM agent_runs WHERE user_id=? AND subject_id=? ORDER BY id DESC LIMIT 1", (user_id, subject_id)).fetchone()
    if not r:
        return None
    names, parents = prereq_graph(db, subject_id)
    subject = Repo(db).get_subject(user_id, subject_id)
    conf = insights.topic_confidence(db, user_id, subject_id)["topics"]
    return {"id": r["id"], "trigger": r["trigger"], "attempt_id": r["attempt_id"], "steps": json.loads(r["steps_json"]), "summary": r["summary"], "ms": r["ms"],
            "created_at": r["created_at"], "graph": graph_json(names, parents, conf, roadmap.target_for(subject.get("level") if subject else None))}


def history(db: sqlite3.Connection, user_id: int, subject_id: int, limit: int = 15) -> list[dict]:
    return [{"id": r["id"], "trigger": r["trigger"], "attempt_id": r["attempt_id"], "summary": r["summary"], "ms": r["ms"], "created_at": r["created_at"]}
            for r in db.execute("SELECT id, trigger, attempt_id, summary, ms, created_at FROM agent_runs WHERE user_id=? AND subject_id=? ORDER BY id DESC LIMIT ?",
                                (user_id, subject_id, limit))]


def after_quiz(db: sqlite3.Connection, user_id: int, subject_id: int, attempt_id: int) -> dict | None:
    """Run the pipeline once per finished quiz (idempotent: a second call for the same attempt returns the stored run)."""
    if db.execute("SELECT 1 FROM agent_runs WHERE user_id=? AND subject_id=? AND attempt_id=? AND trigger='quiz'", (user_id, subject_id, attempt_id)).fetchone():
        return latest(db, user_id, subject_id)
    try:
        return run(db, user_id, subject_id, trigger="quiz", attempt_id=attempt_id)
    except Exception:
        return None
