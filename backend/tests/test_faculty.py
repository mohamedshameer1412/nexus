"""The deck's project flow beyond the original engine: SymPy key checks, BKT mastery, the faculty review step, "contest a score",
verified re-tests on unseen questions with a confidence rating, roles, and the NSSTA insights."""
from __future__ import annotations

import json
import time

import pytest

from studyhub import bkt, numcheck
from studyhub.db import open_db
from studyhub.mcq import Draft, verify
from test_studyhub_api import signed_in  # noqa: F401
from test_studyhub_api_quiz import answer_all, start
from test_studyhub_web import env  # noqa: F401

P_CPI = {"id": 1, "text": "In the pilot survey the three districts reported 12, 15 and 18 vacant posts of statistical investigators, "
                          "and the state office used the average of these figures to plan recruitment for the next quarter.",
         "doc_title": "survey", "page_start": 1, "page_end": 1, "heading_path": "Survey › Staffing"}


def numeric(correct: str, calculation: str, distractors=("12", "18", "45")):
    return Draft.model_validate({
        "question": "What is the average number of vacant posts reported by the three districts?", "correct_answer": correct,
        "distractors": list(distractors), "explanation": "The average of 12, 15 and 18 is 15.", "passage": 1,
        "quote": "the three districts reported 12, 15 and 18 vacant posts of statistical investigators", "calculation": calculation})


# ------------------------------------------------------------------------------------------------ SymPy

def test_sympy_accepts_a_correct_computed_key_and_records_the_check():
    c = verify(numeric("15", "(12 + 15 + 18) / 3"), 1, [P_CPI], [])
    assert c.ok, c.problems
    assert c.item["key_check"] == "SymPy: (12 + 15 + 18) / 3 = 15"


def test_sympy_catches_a_wrong_key():
    c = verify(numeric("16", "(12 + 15 + 18) / 3", ("12", "18", "45")), 1, [P_CPI], [])
    assert not c.ok and any("SymPy recomputed" in p for p in c.problems)


def test_sympy_catches_a_distractor_that_is_also_correct():
    c = verify(numeric("15", "(12 + 15 + 18) / 3", ("15.0", "18", "45")), 1, [P_CPI], [])
    assert not c.ok and any("also equals" in p for p in c.problems)


def test_model_written_calculations_are_never_evaluated_as_code():
    for evil in ("__import__('os').system('x')", "9^9^9^9", "open('f')", "2**99999"):
        with pytest.raises(numcheck.CalcError):
            numcheck.evaluate(evil)


# ------------------------------------------------------------------------------------------------ BKT

def test_bkt_mastery_rises_with_right_answers_and_falls_with_wrong_ones():
    assert bkt.mastery([True, True, True]) >= bkt.MASTERED > bkt.mastery([True, True])
    assert bkt.mastery([True, False, False]) < bkt.mastery([True])
    assert bkt.update(0.5, True) > 0.5 > bkt.update(0.5, False)


# ------------------------------------------------------------------------------------------------ helpers

def seed_bank(sid: int, n: int = 4, review: str = "approved") -> list[int]:
    """n questions in one topic of subject `sid`; the correct option is always index 1."""
    store = open_db()
    db = store.db
    tid = db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,?,'manual')", (sid, "Sampling", "Stats > Sampling", 0)).lastrowid
    ids = [db.execute("INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at,review) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (sid, tid, "Stats > Sampling", f"Sampling question number {j}?", json.dumps(["a", "b", "c", "d"]),
                                                         1, "why", "quote", f"sampling{j}", time.time(), review)).lastrowid for j in range(n)]
    store.close()
    return ids


def make_faculty(name: str = "prof"):
    f = signed_in(name)
    store = open_db()
    store.db.execute("UPDATE users SET role='faculty' WHERE username=?", (name,))
    store.close()
    return f


# ------------------------------------------------------------------------------------------------ roles + review

def test_officers_cannot_use_faculty_endpoints_and_me_reports_the_role(env):  # noqa: F811
    a = signed_in("alice")
    assert a.req("GET", "/me").json()["user"]["role"] == "officer"
    for method, path in (("GET", "/faculty/review"), ("POST", "/faculty/review/1/approve"), ("GET", "/faculty/contests"), ("GET", "/faculty/insights")):
        assert a.req(method, path, json={}).status_code == 403
    f = make_faculty()
    assert f.req("GET", "/me").json()["user"]["role"] == "faculty"
    assert f.req("GET", "/faculty/review").status_code == 200


def test_pending_questions_reach_officers_only_after_faculty_approve_them(env):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Statistics")
    ids = seed_bank(sid, 4, review="pending")
    assert a.req("GET", f"/subjects/{sid}/mcq").json()["questions"] == []
    assert a.req("POST", f"/subjects/{sid}/quiz/attempts", json={}).status_code == 400          # nothing approved yet
    f = make_faculty()
    queue = f.req("GET", "/faculty/review").json()
    assert queue["counts"]["pending"] == 4 and {i["id"] for i in queue["items"]} == set(ids)
    assert f.req("POST", f"/faculty/review/{ids[0]}/approve", json={}).json()["review"] == "approved"
    assert f.req("POST", f"/faculty/review/{ids[1]}/reject", json={"note": ""}).status_code == 400   # a rejection needs a reason
    assert f.req("POST", f"/faculty/review/{ids[1]}/reject", json={"note": "Two options are defensible"}).json()["review"] == "rejected"
    edited = f.req("PUT", f"/faculty/review/{ids[2]}", json={"question": "Which sampling design gives every unit an equal chance?",
                                                             "options": ["Simple random", "Quota", "Snowball", "Convenience"], "answer_index": 0,
                                                             "explanation": "Equal probability of selection."})
    assert edited.status_code == 200 and edited.json()["review"] == "approved" and edited.json()["options"][0] == "Simple random"
    assert f.req("PUT", f"/faculty/review/{ids[3]}", json={"question": "Too short?", "options": ["a", "b", "c", "d"], "answer_index": 0}).status_code == 400
    shown = {q["id"] for q in a.req("GET", f"/subjects/{sid}/mcq").json()["questions"]}
    assert shown == {ids[0], ids[2]}


def test_new_questions_wait_for_review_when_review_is_on(env, monkeypatch):  # noqa: F811
    from studyhub.repo import Repo
    monkeypatch.setenv("STUDYHUB_FACULTY_REVIEW", "on")
    a = signed_in("alice")
    sid = a.subject("Statistics")
    store = open_db()
    repo = Repo(store.db)
    uid = store.db.execute("SELECT id FROM users WHERE username='alice'").fetchone()[0]
    job = repo.create_mcq_job(uid, sid, None, "all", 1)
    item = verify(numeric("15", "(12 + 15 + 18) / 3"), 1, [P_CPI], []).item | {"topic_id": None, "topic_path": ""}
    assert repo.finish_mcq_job(uid, job, status="done", reason="", rejected=0, tier="local", model="m", items=[item]) == 1
    row = store.db.execute("SELECT review, key_check FROM mcq_items").fetchone()
    store.close()
    assert row["review"] == "pending" and row["key_check"].startswith("SymPy:")
    assert repo is not None and a.req("GET", f"/subjects/{sid}/mcq").json()["questions"] == []


# ------------------------------------------------------------------------------------------------ contest a score

def test_an_officer_contests_a_score_and_faculty_uphold_it(env):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Statistics")
    seed_bank(sid, 3)
    aid = start(a, sid)
    assert answer_all(a, sid, aid, chosen=0)["state"] == "complete"                 # every answer marked wrong
    res = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").json()
    assert res["attempt"]["correct"] == 0 and res["gap"]["topics"][0]["closed"] is False
    first = res["answers"][0]
    path = f"/subjects/{sid}/quiz/attempts/{aid}/answers/{first['answer_id']}/contest"
    assert a.req("POST", path, json={"reason": "short"}).status_code == 400
    c = a.req("POST", path, json={"reason": "Option A is what the handbook says on page 4."})
    assert c.status_code == 201 and c.json()["status"] == "open"
    assert a.req("POST", path, json={"reason": "Option A is what the handbook says on page 4."}).status_code == 409
    b = signed_in("bob")                                                              # someone else cannot contest alice's answer
    bsid = b.subject("Mine")
    assert b.req("POST", f"/subjects/{bsid}/quiz/attempts/{aid}/answers/{first['answer_id']}/contest", json={"reason": "not mine at all"}).status_code == 404

    f = make_faculty()
    queue = f.req("GET", "/faculty/contests").json()["contests"]
    assert len(queue) == 1 and queue[0]["reason"].startswith("Option A")
    done = f.req("POST", f"/faculty/contests/{queue[0]['id']}/resolve", json={"decision": "upheld", "resolution": "The key was wrong; corrected."})
    assert done.status_code == 200 and done.json()["status"] == "upheld"
    assert f.req("POST", f"/faculty/contests/{queue[0]['id']}/resolve", json={"decision": "rejected", "resolution": "again"}).status_code == 409
    res = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").json()
    assert res["attempt"]["correct"] == 1 and res["answers"][0]["contest"]["status"] == "upheld"
    assert len(a.req("GET", f"/subjects/{sid}/mcq").json()["questions"]) == 2          # the disputed question is withdrawn
    assert a.req("GET", "/contests").json()["contests"][0]["resolution"] == "The key was wrong; corrected."


def test_a_right_answer_or_a_running_quiz_cannot_be_contested(env):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Statistics")
    seed_bank(sid, 3)
    aid = start(a, sid)
    answer_all(a, sid, aid, chosen=1)
    ans = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").json()["answers"][0]
    r = a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answers/{ans['answer_id']}/contest", json={"reason": "I just want more marks"})
    assert r.status_code == 400 and "marked wrong" in r.json()["error"]["message"]


# ------------------------------------------------------------------------------------------------ re-test + confidence

def test_verified_retest_uses_only_unseen_questions_and_reports_the_gap(env):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Statistics")
    ids = seed_bank(sid, 6)
    first = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"count": 3}).json()["id"]
    st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{first}").json()
    seen = set()
    while st["state"] == "mcq":
        it = st["item"]
        seen.add(it["item_id"])
        a.req("POST", f"/subjects/{sid}/quiz/attempts/{first}/answer",
              json={"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": 0, "confidence": 3})
        st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{first}").json()
    gap = a.req("GET", f"/subjects/{sid}/quiz/attempts/{first}/result").json()["gap"]
    assert gap["confidently_wrong"] == 3 and gap["closed"] is False and "next_gap" in gap["topics"][0]

    r = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"unseen_only": True})
    assert r.status_code == 201 and r.json()["verified_retest"] is True
    retest = r.json()["id"]
    st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{retest}").json()
    asked = set()
    while st["state"] == "mcq":
        it = st["item"]
        asked.add(it["item_id"])
        a.req("POST", f"/subjects/{sid}/quiz/attempts/{retest}/answer",
              json={"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": 1, "confidence": 2})
        st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{retest}").json()
    assert asked and not (asked & seen) and asked <= set(ids)
    topic = a.req("GET", f"/subjects/{sid}/quiz/attempts/{retest}/result").json()["gap"]["topics"][0]
    assert topic["after"] > topic["before"] and topic["closed"] is True
    assert a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"unseen_only": True}).json()["error"]["code"] == "no_unseen_questions"


# ------------------------------------------------------------------------------------------------ insights

def test_nssta_insights_summarise_interventions_bank_and_contests(env):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Statistics")
    seed_bank(sid, 2, review="pending")
    store = open_db()
    db = store.db
    uid = db.execute("SELECT id FROM users WHERE username='alice'").fetchone()[0]
    tid = db.execute("SELECT id FROM topics").fetchone()[0]
    now = time.time()
    for outcome, after in (("improved", 0.8), ("no_change", 0.42)):
        db.execute("INSERT INTO interventions(user_id,subject_id,topic_id,kind,status,conf_before,outcome,conf_after,verified_at,created_at,updated_at) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (uid, sid, tid, "worked_example", "done", 0.4, outcome, after, now, now, now))
    store.close()
    out = make_faculty().req("GET", "/faculty/insights").json()
    k = out["interventions"][0]
    assert (k["kind"], k["verified"], k["improved"], k["closes_rate"]) == ("worked_example", 2, 1, 0.5)
    assert out["topics"][0] == {"topic": "Sampling", "tried": 2, "verified": 2, "improved": 1, "works_best": "worked_example"}
    assert out["question_bank"]["pending"] == 2 and out["officers"] == 1


# ------------------------------------------------------------------------------------------------ database

def test_keyword_search_runs_on_the_configured_database(env):  # noqa: F811
    """On PostgreSQL this exercises the tsvector path; on SQLite, FTS5."""
    a = signed_in("alice")
    sid = a.subject("DS")
    assert a.upload(sid).status_code == 201
    hits = a.req("GET", "/search", params={"q": "stack"}).json()
    assert hits and json.dumps(hits).lower().count("stack") >= 1


# ------------------------------------------------------------------------------------------------ Celery

def test_jobs_go_through_celery_when_a_broker_answers_and_a_thread_otherwise(monkeypatch):
    from nexus_api.celery import app, run_job
    from studyhub import jobs
    ran = []
    monkeypatch.setattr(jobs, "process_coach", lambda *a: ran.append(("celery", a)))
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "0")
    monkeypatch.setattr(jobs, "celery_ready", lambda: True)
    monkeypatch.setattr(app.conf, "task_always_eager", True)
    jobs.submit_task(jobs.process_coach, 7, 9)
    assert ran == [("celery", (7, 9))]
    with pytest.raises(ValueError):
        run_job.apply(args=("system",)).get()                                    # only known job names
    monkeypatch.setattr(jobs, "celery_ready", lambda: False)
    done = []
    monkeypatch.setattr(jobs, "process_coach", lambda *a: done.append(a))
    jobs.submit_task(jobs.process_coach, 1, 2)
    jobs._worker.submit(lambda: None).result(timeout=5)                         # the thread queue has drained
    assert done == [(1, 2)]
    monkeypatch.undo()
    monkeypatch.setenv("STUDYHUB_CELERY", "off")
    assert jobs.celery_ready() is False
