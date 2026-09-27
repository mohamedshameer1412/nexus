"""Nexus JSON API: quiz attempts and progress. Ownership, CSRF, no answer leaks while a quiz runs, and the follow-up/step-back flow."""
from __future__ import annotations

import json
import time

import pytest

import studyhub.web.app as appmod
from studyhub import quiz_agents
from studyhub.db import open_db
from test_studyhub_api import Api, is_error, quiet, signed_in  # noqa: F401
from test_studyhub_web import env  # noqa: F401


def seed(sid: int, n: int = 3) -> int:
    """A topic with n practice questions (answer is always option index 1)."""
    store = open_db()
    db = store.db
    db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,1,'manual')", (sid, "Algebra", "Math > Algebra"))
    tid = db.execute("SELECT id FROM topics WHERE subject_id=?", (sid,)).fetchone()["id"]
    for i in range(n):
        db.execute("INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (sid, tid, "Math > Algebra", f"Question {i}?", json.dumps(["a", "b", "c", "d"]), 1, "because", "quote", f"k{i}", time.time()))
    store.close()
    return tid


def world(env, monkeypatch, provider=None):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: provider)
    a = signed_in("alice")
    sid = a.subject("Math")
    seed(sid)
    return a, sid


def start(a, sid):
    r = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def answer_all(a, sid, aid, chosen=1):
    while True:
        st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()
        if st["state"] != "mcq":
            return st
        it = st["item"]
        r = a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer",
                  json={"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": chosen, "response_time": 3.0})
        assert r.status_code == 200, r.text


MUTATIONS = [
    ("POST", "/subjects/{sid}/quiz/attempts", {"json": {}}),
    ("POST", "/subjects/{sid}/quiz/attempts/1/answer", {"json": {"answer_row_id": 1, "item_id": 1, "chosen": 1}}),
    ("POST", "/subjects/{sid}/quiz/attempts/1/events", {"json": {"event_type": "tab_switch"}}),
    ("POST", "/subjects/{sid}/quiz/attempts/1/terminate", {"json": {"reason": "tab_switch"}}),
    ("POST", "/subjects/{sid}/prerequisites", {"json": {"topic_id": 1, "prereq_id": 2}}),
    ("DELETE", "/subjects/{sid}/prerequisites/1/2", {}),
]


@pytest.mark.parametrize("method,path,kw", MUTATIONS)
def test_every_quiz_mutation_without_the_csrf_token_is_403(env, monkeypatch, method, path, kw):  # noqa: F811
    a, sid = world(env, monkeypatch)
    assert is_error(a.req(method, path.format(sid=sid), csrf=False, **kw), 403, "csrf")


def test_bob_cannot_see_or_touch_alices_quiz_or_progress(env, monkeypatch):  # noqa: F811
    a, sid = world(env, monkeypatch)
    aid = start(a, sid)
    b = signed_in("bob")
    for method, path, kw in [("GET", f"/subjects/{sid}/quiz", {}), ("GET", f"/subjects/{sid}/progress", {}),
                             ("POST", f"/subjects/{sid}/quiz/attempts", {"json": {}}),
                             ("GET", f"/subjects/{sid}/quiz/attempts/{aid}", {}), ("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result", {}),
                             ("POST", f"/subjects/{sid}/quiz/attempts/{aid}/events", {"json": {"event_type": "tab_switch"}})]:
        assert is_error(b.req(method, path, **kw), 404, "not_found"), (method, path)
    own = b.subject("Mine")
    assert is_error(b.req("GET", f"/subjects/{own}/quiz/attempts/{aid}"), 404, "not_found")   # right subject, someone else's attempt


def test_quiz_needs_questions_and_a_running_quiz_never_reveals_answers(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    carol = signed_in("carol")
    empty = carol.subject("Empty")
    assert is_error(carol.req("POST", f"/subjects/{empty}/quiz/attempts", json={}), 400, "no_questions")
    a2, sid2 = world(env, monkeypatch)
    aid = start(a2, sid2)
    st = a2.req("GET", f"/subjects/{sid2}/quiz/attempts/{aid}").json()
    assert st["state"] == "mcq" and st["position"] == 1 and st["total_questions"] == 3
    assert "answer_index" not in json.dumps(st) and "because" not in json.dumps(st)
    assert is_error(a2.req("GET", f"/subjects/{sid2}/quiz/attempts/{aid}/result"), 409, "in_progress")


def test_without_a_model_the_quiz_ends_after_the_questions_with_a_scored_result(env, monkeypatch):  # noqa: F811
    a, sid = world(env, monkeypatch)
    aid = start(a, sid)
    assert answer_all(a, sid, aid, chosen=1)["state"] == "complete"           # no invented follow-up question
    res = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").json()
    assert res["attempt"]["correct"] == 3 and res["attempt"]["incorrect"] == 0 and not res["attempt"]["active"]
    assert all(x["correct"] and x["answer_index"] == 1 and x["explanation"] == "because" for x in res["answers"])
    assert "trust" not in json.dumps(res).lower()
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", json={"answer_row_id": 1, "item_id": 1, "chosen": 1}), 409, "finished")
    prog = a.req("GET", f"/subjects/{sid}/progress").json()
    assert prog["topics"] == [] or all(t["answered"] >= 0 for t in prog["topics"])


def test_a_wrong_choice_is_counted_and_a_choice_outside_the_options_is_refused(env, monkeypatch):  # noqa: F811
    a, sid = world(env, monkeypatch)
    aid = start(a, sid)
    it = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()["item"]
    body = {"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "response_time": 1}
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", json={**body, "chosen": 9}), 400, "not_recorded")
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", json={**body, "item_id": 99999, "chosen": 1}), 400, "not_recorded")
    assert a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", json={**body, "chosen": 3}).status_code == 200
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", json={**body, "chosen": 1}), 400, "not_recorded")   # only once


def test_focus_events_are_recorded_only_for_known_types(env, monkeypatch):  # noqa: F811
    a, sid = world(env, monkeypatch)
    aid = start(a, sid)
    assert a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/events", json={"event_type": "tab_switch"}).json() == {"ok": True}
    assert a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/events", json={"event_type": "drop table"}).json() == {"ok": False}
    answer_all(a, sid, aid)
    res = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").json()
    assert res["focus_events"]["tab_switch"] == 1 and res["focus_events"]["copy_attempt"] == 0


def test_a_quiz_is_multiple_choice_only_even_when_a_model_is_available(env, monkeypatch):  # noqa: F811
    called = []
    monkeypatch.setattr(quiz_agents, "spot_agent", lambda *a, **k: called.append("spot") or "Explain it.")
    a, sid = world(env, monkeypatch, provider=lambda *x, **k: None)
    aid = start(a, sid)
    st = answer_all(a, sid, aid)
    assert st["state"] == "complete" and called == []                       # no written follow-up question is ever generated
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").status_code == 200
    for gone in ("diagnostic", "callback"):
        assert a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/{gone}", json={"answer": "x", "question": "q", "decision": "retry"}).status_code in (404, 405)


def test_progress_lists_topics_with_material_and_prerequisites_are_validated(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    a = signed_in()
    sid = a.subject("Data Structures")
    assert a.upload(sid).status_code == 201
    topics = a.req("GET", f"/subjects/{sid}/progress").json()["topics"]
    assert len(topics) >= 2 and all(t["state"] == "unknown" and t["answered"] == 0 for t in topics)
    t1, t2 = topics[0]["topic_id"], topics[1]["topic_id"]
    assert is_error(a.req("POST", f"/subjects/{sid}/prerequisites", json={"topic_id": t1, "prereq_id": t1}), 400, "invalid")
    assert is_error(a.req("POST", f"/subjects/{sid}/prerequisites", json={"topic_id": t1, "prereq_id": 99999}), 400, "invalid")
    assert a.req("POST", f"/subjects/{sid}/prerequisites", json={"topic_id": t2, "prereq_id": t1}).status_code == 201
    assert is_error(a.req("POST", f"/subjects/{sid}/prerequisites", json={"topic_id": t1, "prereq_id": t2}), 400, "invalid")   # 2-cycle
    pre = a.req("GET", f"/subjects/{sid}/progress").json()["prerequisites"]
    assert pre == [{"topic_id": t2, "topic": topics[1]["name"], "prereq_id": t1, "prereq": topics[0]["name"]}]
    other = signed_in("bob")
    bs = other.subject("Mine")
    assert is_error(other.req("DELETE", f"/subjects/{bs}/prerequisites/{t2}/{t1}"), 404, "not_found")
    assert a.req("DELETE", f"/subjects/{sid}/prerequisites/{t2}/{t1}").status_code == 204
    assert a.req("GET", f"/subjects/{sid}/progress").json()["prerequisites"] == []


# ------------------------------------------------------------------------------------------------ dashboard

def test_dashboard_needs_sign_in_and_only_counts_the_users_own_data(env, monkeypatch):  # noqa: F811
    assert is_error(Api().req("GET", "/dashboard"), 401, "unauthenticated")
    a, sid = world(env, monkeypatch)
    aid = start(a, sid)
    answer_all(a, sid, aid, chosen=1)
    assert a.upload(sid).status_code == 201
    assert a.req("POST", f"/subjects/{sid}/questions", json={"question": "what is photosynthesis in plants"}).status_code == 202
    d = a.req("GET", "/dashboard").json()
    assert d["totals"]["subjects"] == 1 and d["totals"]["practice_questions"] == 3 and d["totals"]["quizzes"] == 1
    assert d["totals"]["answered"] == 3 and d["totals"]["correct"] == 3
    assert d["subjects"][0]["name"] == "Math" and d["subjects"][0]["correct"] == 3
    assert len(d["activity"]) == 14 and d["activity"][-1]["answered"] == 3 and d["activity"][-1]["asked"] == 1
    assert len(d["quiz_trend"]) == 1 and d["quiz_trend"][0]["correct"] == 3 and d["quiz_trend"][0]["answered"] == 3
    assert sum(d["question_outcomes"].values()) == 1
    b = signed_in("bob")
    e = b.req("GET", "/dashboard").json()
    assert e["totals"] == {"subjects": 0, "materials": 0, "questions": 0, "practice_questions": 0, "quizzes": 0, "answered": 0, "correct": 0}
    assert e["subjects"] == [] and e["quiz_trend"] == [] and all(x["asked"] == 0 and x["answered"] == 0 for x in e["activity"])


def test_the_mode_is_stored_with_the_quiz_so_resuming_keeps_the_assessment_rules(env, monkeypatch):  # noqa: F811
    a, sid = world(env, monkeypatch)
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"mode": "exam"}), 400, "invalid")
    r = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"mode": "assessment"})
    assert r.status_code == 201 and r.json()["mode"] == "assessment"
    aid = r.json()["id"]
    home = a.req("GET", f"/subjects/{sid}/quiz").json()
    assert home["active_attempt"] == aid and home["active_mode"] == "assessment" and home["attempts"][0]["mode"] == "assessment"
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()["attempt"]["mode"] == "assessment"
    practice = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={}).json()          # the default stays practice
    assert practice["mode"] == "practice"
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{practice['id']}").json()["attempt"]["mode"] == "practice"


def test_an_assessment_ends_at_once_when_the_rules_are_broken_and_a_practice_quiz_cannot_be_ended_that_way(env, monkeypatch):  # noqa: F811
    a, sid = world(env, monkeypatch)
    practice = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={}).json()["id"]
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts/{practice}/terminate", json={"reason": "tab_switch"}), 400, "not_assessment")
    aid = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"mode": "assessment"}).json()["id"]     # starting it closed the practice one
    it = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()["item"]
    a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", json={"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": 1})
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/terminate", json={"reason": "cheating"}), 400, "invalid")
    b = signed_in("bob")
    assert is_error(b.req("POST", f"/subjects/{b.subject('Mine')}/quiz/attempts/{aid}/terminate", json={"reason": "tab_switch"}), 404, "not_found")
    r = a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/terminate", json={"reason": "no_face"})
    assert r.status_code == 200 and r.json()["reason"] == "No face was visible to the camera"
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/terminate", json={"reason": "tab_switch"}), 409, "finished")
    res = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").json()
    assert res["ended_reason"] == "No face was visible to the camera" and not res["attempt"]["active"]
    assert res["skipped"] == 2 and res["attempt"]["correct"] == 1            # the unanswered questions are not scored
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{practice}/result").json()["ended_reason"] is None
