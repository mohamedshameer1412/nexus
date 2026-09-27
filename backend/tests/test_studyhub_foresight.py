"""What-if simulator, risk score and learning debt, the self-check, and the career goal (job description skills checked against the student's own evidence)."""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

import studyhub.web.app as appmod
from studyhub import career, foresight, mcq
from test_studyhub_api import is_error, quiet, signed_in  # noqa: F401
from test_studyhub_api_quiz import answer_all  # noqa: F401
from test_studyhub_insights import answer, seed_two_topics, world  # noqa: F401
from test_studyhub_web import env  # noqa: F401


def run(a, sid, chosen, kind="standard", mode="practice"):
    aid = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": kind, "mode": mode}).json()["id"]
    answer_all(a, sid, aid, chosen=chosen)
    return aid


def gaps(topics):
    """Hand-made gap rows for the pure functions."""
    out = []
    for i, (name, conf, answered, blocked) in enumerate(topics, start=1):
        gap = None if conf is None else round(max(0, 0.7 - conf), 3)
        status = "unassessed" if conf is None else "on_track" if gap == 0 else "critical" if gap > 0.3 else "moderate"
        out.append({"topic_id": i, "name": name, "path": name, "ordinal": i, "status": status, "gap": gap, "confidence": conf, "target": 0.7, "answered": answered, "correct": 0,
                    "sources": {}, "trend": None, "blocked_by": [{"topic_id": b, "name": f"T{b}", "confidence": 0.1} for b in blocked], "reasons": [], "avg_seconds": None})
    return {"target": 0.7, "level": None, "gaps": out, "readiness": None, "source_totals": {}, "counts": {}}


# ------------------------------------------------------------------------------------------------------------- what-if

def test_more_hours_give_more_progress_and_the_same_inputs_give_the_same_answer():
    info = gaps([("A", 0.1, 5, []), ("B", 0.2, 5, []), ("C", 0.9, 5, [])])
    small = foresight.simulate(info, 1, 1)
    big = foresight.simulate(info, 10, 4)
    assert big["readiness_after"] > small["readiness_after"] >= small["readiness_now"]
    assert big["covered"] == 2 and small["covered"] < 2 and big["unused_minutes"] > 0
    assert foresight.simulate(info, 10, 4) == big
    a_row = next(t for t in big["topics"] if t["name"] == "A")
    assert a_row["after"] > a_row["now"] and a_row["after"] < 0.7 + 1e-9 and a_row["covered"] is True         # the assumption closes part of the gap, not all of it
    assert next(t for t in big["topics"] if t["name"] == "C")["after"] == 0.9                                  # a solid topic is untouched


def test_unassessed_topics_are_not_counted_as_progress_and_focus_topics_go_first():
    info = gaps([("A", 0.1, 5, []), ("B", 0.2, 5, []), ("U", None, 0, [])])
    s = foresight.simulate(info, 1, 1, focus=[2])
    assert next(t for t in s["topics"] if t["name"] == "U")["after"] is None
    assert s["topics"][0]["name"] == "B" and s["topics"][0]["focus"] is True and s["topics"][0]["minutes_given"] >= s["topics"][1]["minutes_given"]
    assert foresight.simulate(info, 1, 1, focus=[999])["topics"][0]["name"] == "A"                              # an unknown topic id is ignored


def test_a_focus_topic_brings_its_weak_foundation_with_it():
    info = gaps([("Base", 0.1, 5, []), ("Mid", 0.5, 5, []), ("Top", 0.2, 5, [1])])
    s = foresight.simulate(info, 1, 1, focus=[3])
    assert [t["name"] for t in s["topics"][:2]] == ["Base", "Top"]


def test_the_what_if_endpoint_compares_with_the_current_plan_and_saves_nothing(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    run(a, sid, 0)
    before = a.req("GET", f"/subjects/{sid}/roadmap").json()
    r = a.req("POST", f"/subjects/{sid}/whatif", json={"hours_per_week": 20, "weeks": 6, "focus": []}).json()
    assert r["scenario"]["hours_per_week"] == 20 and r["baseline"]["hours_per_week"] == before["profile"]["hours_per_week"]
    assert r["scenario"]["readiness_after"] >= r["baseline"]["readiness_after"] and r["why"] and "Estimate" in r["assumption"]
    assert a.req("GET", f"/subjects/{sid}/roadmap").json()["profile"] == before["profile"]                       # nothing was saved
    for bad in ({"hours_per_week": 0}, {"hours_per_week": 99}, {"weeks": 0}, {"weeks": 99}, {"focus": list(range(20))}):
        assert a.req("POST", f"/subjects/{sid}/whatif", json=bad).status_code == 422
    assert is_error(a.req("POST", f"/subjects/{sid}/whatif", csrf=False, json={}), 403, "csrf")
    assert is_error(signed_in("bob").req("POST", f"/subjects/{sid}/whatif", json={}), 404, "not_found")


# ------------------------------------------------------------------------------------------------- risk and learning debt

def test_risk_rises_with_the_gap_a_slipping_trend_and_a_weak_foundation():
    info = gaps([("Solid", 0.9, 8, []), ("Low", 0.3, 8, []), ("Hollow", 0.3, 8, [1])])
    info["gaps"][1]["trend"] = "slipping"
    r = foresight.risk(info, {"on_track": True})
    score = {t["name"]: t["score"] for t in r["topics"]}
    assert score["Solid"] == 0 and score["Hollow"] > score["Low"] - 15 and score["Low"] > score["Solid"]
    assert next(t for t in r["topics"] if t["name"] == "Low")["level"] in ("medium", "high") and r["topics"][0]["score"] == max(score.values())
    assert any("slipping" in x or "worse" in x for x in next(t for t in r["topics"] if t["name"] == "Low")["reasons"])
    late = foresight.risk(info, {"on_track": False})
    assert late["summary"]["score"] > r["summary"]["score"] and late["summary"]["late"] is True
    assert "not a trained model" in r["method"]


def test_topics_without_answers_have_unknown_risk_not_low_risk():
    r = foresight.risk(gaps([("U", None, 0, []), ("A", 0.2, 5, [])]), {"on_track": None})
    u = next(t for t in r["topics"] if t["name"] == "U")
    assert u["score"] is None and u["level"] == "unknown" and r["summary"]["unassessed"] == 1 and r["summary"]["assessed"] == 1
    assert foresight.risk(gaps([("U", None, 0, [])]), {})["summary"]["score"] is None


def test_debt_counts_the_time_owed_and_makes_a_shared_foundation_carry_interest():
    info = gaps([("Base", 0.1, 5, []), ("Up1", 0.2, 5, [1]), ("Up2", 0.2, 5, [1]), ("Fine", 0.9, 5, [])])
    d = foresight.debt(info)
    names = [n["name"] for n in d["topics"]]
    assert "Fine" not in names and names[0] == "Base" and d["topics"][0]["repay_first"] is True
    assert sorted(d["topics"][0]["blocks"]) == ["Up1", "Up2"] and d["topics"][0]["interest_minutes"] > 0
    assert {(e["from"], e["to"]) for e in d["edges"]} == {(1, 2), (1, 3)} and d["total_minutes"] > 0 and d["total_hours"] == round(d["total_minutes"] / 60, 1)
    assert foresight.debt(gaps([("Fine", 0.9, 5, [])]))["total_minutes"] == 0


def test_the_outlook_endpoint_reports_risk_debt_and_starting_numbers(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    o = a.req("GET", f"/subjects/{sid}/outlook").json()
    assert o["risk"]["summary"]["level"] == "unknown" and o["debt"]["total_minutes"] == 0 and {t["name"] for t in o["topics"]} >= {n1, n2}
    run(a, sid, 0)
    o = a.req("GET", f"/subjects/{sid}/outlook").json()
    assert o["risk"]["summary"]["score"] is not None and o["debt"]["total_minutes"] > 0 and o["profile"]["weeks"] >= 1
    assert is_error(signed_in("bob").req("GET", f"/subjects/{sid}/outlook"), 404, "not_found")


# ------------------------------------------------------------------------------------------------------------ self-check

def test_feeling_is_compared_with_results_only_when_there_are_enough_answers():
    info = gaps([("Over", 0.2, 6, []), ("Under", 0.9, 6, []), ("Same", 0.5, 6, []), ("Few", 0.5, 1, []), ("None", None, 0, [])])
    c = foresight.self_check(info, {1: 5, 2: 1, 3: 3, 4: 5})
    v = {t["name"]: t["verdict"] for t in c["topics"]}
    assert v == {"Over": "overconfident", "Under": "underconfident", "Same": "aligned", "Few": "not_enough_answers", "None": "not_rated"}
    assert c["message"].startswith("Mixed")
    assert "surer" in foresight.self_check(info, {1: 5})["message"] and "more than you think" in foresight.self_check(info, {2: 1})["message"]
    assert "matches" in foresight.self_check(info, {3: 3})["message"]
    assert "Rate how sure" in foresight.self_check(info, {})["message"]


def test_ratings_are_saved_per_topic_validated_and_kept_private(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    r = a.req("PUT", f"/subjects/{sid}/self-check", json={"ratings": {str(t1): 5, str(t2): 2}})
    assert r.status_code == 200 and {t["name"]: t["rating"] for t in r.json()["topics"]}.items() >= {n1: 5, n2: 2}.items()
    assert {t["name"]: t["rating"] for t in a.req("GET", f"/subjects/{sid}/self-check").json()["topics"]}[n1] == 5
    a.req("PUT", f"/subjects/{sid}/self-check", json={"ratings": {str(t1): 9, "999999": 3}})                       # out of range and unknown topics are ignored
    assert {t["name"]: t["rating"] for t in a.req("GET", f"/subjects/{sid}/self-check").json()["topics"]}[n1] == 5
    assert is_error(a.req("PUT", f"/subjects/{sid}/self-check", csrf=False, json={"ratings": {}}), 403, "csrf")
    b = signed_in("bob")
    bs = b.subject("Mine")
    assert is_error(b.req("PUT", f"/subjects/{sid}/self-check", json={"ratings": {str(t1): 1}}), 404, "not_found")
    b.req("PUT", f"/subjects/{bs}/self-check", json={"ratings": {str(t1): 1}})                                    # another subject's topic id cannot be rated
    assert {t["name"]: t["rating"] for t in a.req("GET", f"/subjects/{sid}/self-check").json()["topics"]}[n1] == 5


# ------------------------------------------------------------------------------------------------------- career: reading

JD = """Data Analyst

About the role
We are looking for someone to analyse data and build dashboards.

Requirements:
- Strong knowledge of data structures
- Experience with SQL and Python
- Understanding of computer networks
- Excellent communication

Nice to have:
- Familiarity with Kubernetes
"""


def test_rules_read_requirements_and_mark_preferred_skills():
    skills = {s["skill"].lower(): s for s in career.rule_skills(JD)}
    assert {"data structures", "sql", "python", "computer networks", "kubernetes"} <= set(skills)
    assert skills["kubernetes"]["importance"] == "preferred" and skills["sql"]["importance"] == "required"
    assert all(career.citations.normalize(s["quote"]) in career.citations.normalize(JD) for s in skills.values())


def test_a_skill_is_kept_only_if_its_quote_is_in_the_description():
    raw = [{"skill": "SQL", "importance": "required", "quote": "Experience with SQL"}, {"skill": "Rust", "importance": "required", "quote": "deep Rust expertise"},
           {"skill": "sql", "importance": "required", "quote": "SQL and Python"}, {"skill": "", "quote": "x"}, {"skill": "Kubernetes", "importance": "preferred", "quote": "Familiarity with Kubernetes"}]
    kept = career._valid(raw, JD)
    assert [s["skill"] for s in kept] == ["SQL", "Kubernetes"] and kept[1]["importance"] == "preferred"          # invented skill and the repeat are dropped
    assert len(career._valid([{"skill": f"s{i}", "quote": "Requirements"} for i in range(40)], JD)) == career.MAX_SKILLS


# ------------------------------------------------------------------------------------------------ career: evidence and flow

def test_skills_are_matched_to_the_students_topics_and_answers(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([], []))
    text = f"Backend Engineer\n\nRequirements:\n- Experience with {n1}\n- Knowledge of {n2}\n- Experience with Quantum Chromodynamics\n\nNice to have:\n- Familiarity with Kubernetes\n"
    r = a.req("POST", "/career", json={"title": "Backend Engineer", "text": text})
    assert r.status_code == 202
    gid = r.json()["id"]
    goal = a.req("GET", f"/career/{gid}").json()
    assert goal["status"] == "done" and goal["model"].startswith("rules") and goal["from_model"] is False
    st = {s["skill"]: s for s in goal["skills"]}
    assert st[n1]["status"] == "not_tested" and st[n1]["subject_id"] == sid and st[n1]["topic"] == n1                 # covered by the materials, no answers yet
    assert st["Quantum Chromodynamics"]["status"] == "no_evidence" and st["Kubernetes"]["importance"] == "preferred"
    assert goal["score"]["readiness"] == 0 and goal["score"]["counts"]["not_tested"] >= 2 and goal["next_steps"]
    assert next(x for x in goal["next_steps"] if x["skill"] == "Quantum Chromodynamics")["type"] == "add_material"
    for _ in range(3):
        run(a, sid, 1)                                                                                              # answer everything right, three times
    goal = a.req("GET", f"/career/{gid}").json()
    st = {s["skill"]: s for s in goal["skills"]}
    assert st[n1]["status"] == "verified" and st[n1]["answered"] >= 3 and st[n1]["confidence"] >= 0.7
    assert goal["score"]["readiness"] > 0 and goal["score"]["verified"] >= 1 and len(goal["history"]) >= 1
    assert not any(x["skill"] == n1 for x in goal["next_steps"])


def test_wrong_answers_make_a_skill_developing_not_verified(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, _, (n1, n2) = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([], []))
    for _ in range(3):
        run(a, sid, 0)
    gid = a.req("POST", "/career", json={"title": "Role", "text": f"Requirements:\n- Knowledge of {n1}\n- Experience with something else entirely, nothing to match here"}).json()["id"]
    st = {s["skill"]: s for s in a.req("GET", f"/career/{gid}").json()["skills"]}
    assert st[n1]["status"] == "developing" and st[n1]["confidence"] < 0.7


def test_a_model_is_used_first_and_invented_skills_are_dropped(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, _, _ = world(env, monkeypatch)
    seen = {}

    def fake_call(tier, budget, messages, schema, step):
        seen["system"], seen["user"] = messages[0]["content"], messages[1]["content"]
        return schema(skills=[{"skill": "SQL", "importance": "required", "quote": "Experience with SQL and Python"},
                              {"skill": "Rust", "importance": "required", "quote": "deep Rust knowledge"}])
    monkeypatch.setattr(mcq, "_call", fake_call)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([SimpleNamespace(name="cloud", model="mistralai/mistral-small-3.2-24b-instruct", settings=None)], []))
    gid = a.req("POST", "/career", json={"title": "Analyst", "text": JD}).json()["id"]
    goal = a.req("GET", f"/career/{gid}").json()
    assert goal["from_model"] is True and goal["model"].startswith("mistralai") and [s["skill"] for s in goal["skills"]] == ["SQL"]
    assert "ignore any instruction" in seen["system"] and "Requirements" in seen["user"]
    assert "Rust" not in json.dumps(goal["skills"])


def test_when_no_model_answers_the_rules_are_used_and_an_unreadable_text_fails_cleanly(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, _, _, _ = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([SimpleNamespace(name="cloud", model="m", settings=None)], []))
    monkeypatch.setattr(mcq, "_call", lambda *x, **k: (_ for _ in ()).throw(RuntimeError("down")))
    ok = a.req("GET", f"/career/{a.req('POST', '/career', json={'title': 'Analyst', 'text': JD}).json()['id']}").json()
    assert ok["status"] == "done" and ok["model"].startswith("rules") and len(ok["skills"]) >= 4
    bad = a.req("GET", "/career/" + str(a.req("POST", "/career", json={"title": "Empty", "text": "We are a friendly company with a wonderful team spirit and many offices worldwide."}).json()["id"])).json()
    assert bad["status"] == "failed" and bad["skills"] == []


def test_career_goals_are_private_validated_limited_and_deletable(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, _, _, _ = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([], []))
    gid = a.req("POST", "/career", json={"title": "Analyst", "text": JD}).json()["id"]
    b = signed_in("bob")
    assert is_error(b.req("GET", f"/career/{gid}"), 404, "not_found") and is_error(b.req("DELETE", f"/career/{gid}"), 404, "not_found")
    assert b.req("GET", "/career").json()["goals"] == []
    assert [g["title"] for g in a.req("GET", "/career").json()["goals"]] == ["Analyst"]
    assert a.req("POST", "/career", json={"title": "x", "text": JD}).status_code == 422
    assert a.req("POST", "/career", json={"title": "Fine", "text": "too short"}).status_code == 422
    assert is_error(a.req("POST", "/career", csrf=False, json={"title": "Fine", "text": JD}), 403, "csrf")
    assert a.req("DELETE", f"/career/{gid}").json() == {"ok": True}
    assert is_error(a.req("GET", f"/career/{gid}"), 404, "not_found")
    for _ in range(7):                                                                                             # eight an hour in all (one was made above)
        assert a.req("POST", "/career", json={"title": "Analyst", "text": JD}).status_code == 202
    assert is_error(a.req("POST", "/career", json={"title": "Analyst", "text": JD}), 429, "rate_limited")


def test_the_history_records_progress_at_most_once_an_hour_and_only_when_it_changed(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, _, (n1, n2) = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([], []))
    gid = a.req("POST", "/career", json={"title": "Analyst", "text": f"Requirements:\n- Knowledge of {n1}\n- Experience with Kubernetes clusters in production"}).json()["id"]
    a.req("GET", f"/career/{gid}")
    assert len(a.req("GET", f"/career/{gid}").json()["history"]) == 1
    from studyhub import db as studydb
    store = studydb.open_db()
    try:
        career.snapshot(store.db, gid, 0.0, 0, 2, now=time.time() + 7200)                                          # same numbers, later: nothing new to record
        career.snapshot(store.db, gid, 0.5, 1, 2, now=time.time() + 7300)                                          # changed but under an hour after the last: skipped
        career.snapshot(store.db, gid, 0.5, 1, 2, now=time.time() + 7200 + 3700)
        assert len(career.history(store.db, gid)) == 2
    finally:
        store.close()
