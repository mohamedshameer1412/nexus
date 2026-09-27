"""Skill-gap analysis and the study roadmap: evidence from every kind of test, learning order, weekly plan, coach paragraph, ownership."""
from __future__ import annotations

import time
from types import SimpleNamespace

import studyhub.web.app as appmod
from studyhub import mcq, roadmap
from test_studyhub_api import is_error, quiet, signed_in  # noqa: F401
from test_studyhub_api_quiz import answer_all  # noqa: F401
from test_studyhub_insights import answer, seed_two_topics, world  # noqa: F401
from test_studyhub_web import env  # noqa: F401


def run(a, sid, chosen, kind="standard", mode="practice"):
    aid = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": kind, "mode": mode}).json()["id"]
    answer_all(a, sid, aid, chosen=chosen)
    return aid


def by_name(rm):
    return {g["name"]: g for g in rm["gaps"]}


def test_a_topic_with_no_answers_is_not_assessed_rather_than_weak(env, monkeypatch):  # noqa: F811
    a, sid, _, (n1, n2) = world(env, monkeypatch)
    rm = a.req("GET", f"/subjects/{sid}/roadmap").json()
    g = by_name(rm)
    assert g[n1]["status"] == "unassessed" and g[n1]["gap"] is None and g[n1]["confidence"] is None
    assert rm["counts"]["unassessed"] >= 2 and rm["readiness"] is None and rm["level"] is None and rm["target"] == 0.70


def test_the_gap_is_judged_against_the_level_and_names_each_kind_of_evidence(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    run(a, sid, 0, kind="diagnostic")                                          # every diagnostic answer wrong
    run(a, sid, 1)                                                              # a regular quiz, all right
    run(a, sid, 0, kind="revision")                                             # wrong again
    run(a, sid, 0, mode="assessment")                                           # an assessment, wrong
    a.req("PUT", f"/subjects/{sid}/level", json={"level": "professional"})
    rm = a.req("GET", f"/subjects/{sid}/roadmap").json()
    assert rm["target"] == 0.80 and rm["level"] == "professional"
    g = by_name(rm)[n1]
    src = g["sources"]
    assert src["diagnostic"]["answered"] >= 1 and src["quiz"]["correct"] == src["quiz"]["answered"] >= 1
    assert src["revision"]["answered"] >= 1 and src["assessment"]["answered"] >= 1 and src["flashcards"]["answered"] == 0
    assert g["status"] in ("critical", "moderate") and g["gap"] > 0 and any("Assessments" in r for r in g["reasons"])
    assert rm["source_totals"]["assessment"]["answered"] >= 2 and rm["readiness"] is not None and 0 <= rm["readiness"] < 1
    items = a.req("GET", f"/subjects/{sid}/mcq").json()["questions"]
    a.req("POST", f"/subjects/{sid}/flashcards/{items[0]['id']}/review", json={"grade": "again"})       # a forgotten card counts as evidence too
    fc = by_name(a.req("GET", f"/subjects/{sid}/roadmap").json())
    assert sum(x["sources"]["flashcards"]["answered"] for x in fc.values()) == 1


def test_solid_topics_are_on_track_and_the_target_moves_with_the_level(env, monkeypatch):  # noqa: F811
    a, sid, _, (n1, n2) = world(env, monkeypatch)
    for _ in range(3):
        run(a, sid, 1)
    g = by_name(a.req("GET", f"/subjects/{sid}/roadmap").json())
    assert g[n1]["status"] == "on_track" and g[n1]["gap"] == 0.0
    a.req("PUT", f"/subjects/{sid}/level", json={"level": "new"})
    assert a.req("GET", f"/subjects/{sid}/roadmap").json()["target"] == 0.60


def test_a_weak_foundation_is_named_as_the_blocker_and_comes_first_in_the_plan(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    import random
    monkeypatch.setattr(random, "shuffle", lambda x: x.sort(key=lambda i: -(i["topic_id"] or 0) if isinstance(i, dict) else 0))    # the later topic is asked first
    for _ in range(2):
        run(a, sid, 0)
    rm = a.req("GET", f"/subjects/{sid}/roadmap").json()
    g = by_name(rm)
    assert [b["name"] for b in g[n2]["blocked_by"]] == [n1] and any("Builds on" in r for r in g[n2]["reasons"])
    first_topics = [s["topic_id"] for s in rm["roadmap"]["weeks"][0]["steps"]]
    assert first_topics.index(t1) < first_topics.index(t2)                                      # foundations before what builds on them


def test_the_weeks_fit_the_hours_and_the_target_date_says_whether_it_is_reachable(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    run(a, sid, 0)
    tight = a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"goal": "Pass the exam", "hours_per_week": 1})
    assert tight.status_code == 200
    rm = tight.json()
    weeks = rm["roadmap"]["weeks"]
    assert rm["profile"]["goal"] == "Pass the exam" and len(weeks) >= 2 and all(w["minutes"] <= 60 or len(w["steps"]) == 1 for w in weeks)
    assert weeks[0]["goal"] and weeks[0]["milestone"] and weeks[0]["steps"][0]["href"].startswith(f"/subjects/{sid}/")
    soon = time.strftime("%Y-%m-%d", time.localtime(time.time() + 7 * 86400))
    rm = a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"hours_per_week": 1, "target_date": soon}).json()
    assert rm["roadmap"]["summary"]["on_track"] is False and rm["roadmap"]["summary"]["hours_needed"] > 1
    roomy = a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"hours_per_week": 40, "target_date": time.strftime("%Y-%m-%d", time.localtime(time.time() + 60 * 86400))}).json()
    assert roomy["roadmap"]["summary"]["on_track"] is True and len(roomy["roadmap"]["weeks"]) == 1
    assert a.req("GET", f"/subjects/{sid}/roadmap").json() == a.req("GET", f"/subjects/{sid}/roadmap").json()      # the same data gives the same plan


def test_the_profile_is_validated_and_belongs_to_its_owner(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    for bad in ({"hours_per_week": 0}, {"hours_per_week": 99}, {"goal": "x" * 400}):
        assert a.req("PUT", f"/subjects/{sid}/roadmap/profile", json=bad).status_code == 422
    assert is_error(a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"target_date": "2001-01-01"}), 400, "invalid")
    assert is_error(a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"target_date": "soon"}), 400, "invalid")
    assert is_error(a.req("PUT", f"/subjects/{sid}/roadmap/profile", csrf=False, json={"hours_per_week": 3}), 403, "csrf")
    b = signed_in("bob")
    bs = b.subject("Mine")
    assert is_error(b.req("GET", f"/subjects/{sid}/roadmap"), 404, "not_found")
    assert is_error(b.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"hours_per_week": 3}), 404, "not_found")
    assert is_error(b.req("POST", f"/subjects/{sid}/roadmap/coach"), 404, "not_found")
    b.req("PUT", f"/subjects/{bs}/roadmap/profile", json={"goal": "mine", "hours_per_week": 2})
    assert a.req("GET", f"/subjects/{sid}/roadmap").json()["profile"]["goal"] == ""                # another account's profile never leaks


def test_the_coach_uses_a_model_when_one_answers_and_the_rules_when_none_does(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, _, (n1, n2) = world(env, monkeypatch)
    run(a, sid, 0)
    before = a.req("GET", f"/subjects/{sid}/roadmap").json()["coach"]
    assert before["status"] == "idle" and before["from_model"] is False and before["text"]                 # the rule text is shown from the start
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([], []))
    assert a.req("POST", f"/subjects/{sid}/roadmap/coach").status_code == 202
    c = a.req("GET", f"/subjects/{sid}/roadmap").json()["coach"]
    assert c["status"] == "done" and c["from_model"] is False and c["model"].startswith("rules") and not c["stale"]
    seen = {}

    def fake_call(tier, budget, messages, schema, step):
        seen["prompt"] = messages[1]["content"]
        return schema(text=f"You are doing fine on {n2}. This week, focus on {n1} and take a short quiz. Keep a daily ten minute habit going.")
    monkeypatch.setattr(mcq, "_call", fake_call)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([SimpleNamespace(name="cloud", model="qwen/qwen3.7-flash", settings=None)], []))
    a.req("POST", f"/subjects/{sid}/roadmap/coach")
    c = a.req("GET", f"/subjects/{sid}/roadmap").json()["coach"]
    assert c["model"] == "qwen/qwen3.7-flash" and c["from_model"] is True and n1 in c["text"]
    assert "passage" not in seen["prompt"].lower() and n1 in seen["prompt"]                            # names and numbers only: no material is sent
    run(a, sid, 1)                                                                                      # new answers make the paragraph stale
    assert a.req("GET", f"/subjects/{sid}/roadmap").json()["coach"]["stale"] is True
    monkeypatch.setattr(mcq, "_call", lambda *x, **k: schema_text("see http://evil.example now " * 4))
    a.req("POST", f"/subjects/{sid}/roadmap/coach")
    assert a.req("GET", f"/subjects/{sid}/roadmap").json()["coach"]["model"].startswith("rules")       # a paragraph with a link is refused


def schema_text(t):
    return SimpleNamespace(text=t)


def test_the_coach_text_filter_and_the_plain_rules():
    info = {"gaps": [], "counts": {"unassessed": 0}, "readiness": None}
    assert roadmap.clean_coach("short", info) is None and roadmap.clean_coach("x" * 2000, info) is None
    assert roadmap.clean_coach("<b>bold</b> " * 10, info) is None
    assert roadmap.clean_coach("**Keep going.** " * 6, info) == ("Keep going. " * 6).strip()
    assert roadmap.target_for(None) == 0.70 and roadmap.target_for("professional") == 0.80


def test_coach_requests_are_rate_limited(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, _, _ = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: ([], []))
    for _ in range(6):
        assert a.req("POST", f"/subjects/{sid}/roadmap/coach").status_code == 202
    assert is_error(a.req("POST", f"/subjects/{sid}/roadmap/coach"), 429, "rate_limited")
