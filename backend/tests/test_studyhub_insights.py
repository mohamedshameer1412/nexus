"""Topic confidence (IRT), backtracking, revision, diagnostic and the report, through the JSON API."""
from __future__ import annotations

import json
import time

import studyhub.web.app as appmod
from studyhub import insights
from studyhub.db import open_db
from test_studyhub_api import is_error, quiet, signed_in  # noqa: F401
from test_studyhub_api_quiz import answer_all, start  # noqa: F401
from test_studyhub_web import env  # noqa: F401


def seed_two_topics(a, sid: int):
    """Upload a document (so topics have passages), then give its first two topics practice questions whose right answer is option index 1."""
    assert a.upload(sid).status_code == 201
    topics = [t for t in a.req("GET", f"/subjects/{sid}/topics").json()["topics"] if t["passages"] > 0][:2]
    store = open_db()
    db = store.db
    for t in topics:
        for i in range(3):
            db.execute("INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (sid, t["id"], t["path"], f"{t['name']} question {i}?", json.dumps(["a", "b", "c", "d"]), 1, "because", "quote", f"{t['id']}-{i}", time.time()))
    store.close()
    return [t["id"] for t in topics], [t["name"] for t in topics]


def world(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    a = signed_in("alice")
    sid = a.subject("Math")
    ids, names = seed_two_topics(a, sid)
    return a, sid, ids, names


def answer(a, sid, aid, item, chosen):
    return a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer",
                 json={"answer_row_id": item["answer_row_id"], "item_id": item["item_id"], "chosen": chosen, "response_time": 4.0})


def test_the_estimator_moves_the_right_way_and_is_honest_about_little_evidence():
    none, right, wrong = insights.estimate([]), insights.estimate([(0, True)] * 5), insights.estimate([(0, False)] * 5)
    assert wrong["confidence"] < none["confidence"] < right["confidence"]
    assert right["theta"] > 0 > wrong["theta"]
    assert insights.estimate([(0, True)] * 30)["se"] < right["se"] < none["se"]      # more answers, less uncertainty
    assert insights.label(0, 0.5) == "untried" and insights.label(2, 0.99) == "few" and insights.label(5, 0.9) == "confident" and insights.label(5, 0.2) == "shaky"


def test_a_missed_question_steps_back_to_the_topic_it_builds_on_once(env, monkeypatch):  # noqa: F811
    a, sid, (basics, advanced), (n_basics, n_advanced) = world(env, monkeypatch)
    import random
    monkeypatch.setattr(random, "shuffle", lambda x: x.reverse())              # the later topic comes first, so there is something to step back from
    aid = start(a, sid)
    stepped, saw_backtrack_item = 0, False
    for _ in range(20):
        st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()
        if st["state"] != "mcq":
            break
        it = st["item"]
        if it["backtrack"]:
            saw_backtrack_item = True
            assert it["backtrack"] == {"from": n_advanced, "topic": n_basics} and it["topic"] == n_basics
        r = answer(a, sid, aid, it, 0).json()                                   # always wrong
        stepped += 1 if r["backtrack"] else 0
    assert saw_backtrack_item and stepped == 1                                  # one step back per missed topic, only Advanced has a topic before it


def test_confirmed_prerequisites_win_over_the_automatic_one(env, monkeypatch):  # noqa: F811
    a, sid, (basics, advanced), (n_basics, n_advanced) = world(env, monkeypatch)
    store = open_db()
    assert insights.prerequisite_topics(store.db, sid, advanced) == [basics]           # automatic: the topic before it
    assert insights.prerequisite_topics(store.db, sid, basics) == []
    store.close()
    assert a.req("POST", f"/subjects/{sid}/prerequisites", json={"topic_id": basics, "prereq_id": advanced}).status_code == 201
    store = open_db()
    assert insights.prerequisite_topics(store.db, sid, basics) == [advanced]           # chosen by the student
    store.close()


def test_progress_shows_a_confidence_score_per_topic_with_the_evidence_behind_it(env, monkeypatch):  # noqa: F811
    a, sid, (basics, advanced), (n_basics, n_advanced) = world(env, monkeypatch)
    assert a.req("GET", f"/subjects/{sid}/progress").json()["overall"] is None
    aid = start(a, sid)
    answer_all(a, sid, aid, chosen=1)                                           # everything right
    p = a.req("GET", f"/subjects/{sid}/progress").json()
    assert p["overall"]["answered"] == 6 and p["overall"]["confidence"] > 0.7 and len(p["ability_trend"]) == 1
    seen = [t for t in p["topics"] if t["answered"]]
    assert seen and all(0 < t["confidence"] < 1 and t["label"] in ("building", "confident") and t["theta"] > 0 for t in seen)


def test_revision_collects_the_latest_mistakes_and_a_diagnostic_covers_every_topic(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "revision"}), 400, "nothing_to_revise")
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "exam"}), 400, "invalid")
    aid = start(a, sid)
    answer_all(a, sid, aid, chosen=0)                                           # all wrong
    rev = a.req("GET", f"/subjects/{sid}/revision").json()
    assert len(rev["wrong"]) >= 6 and rev["wrong"][0]["answer_index"] == 1 and rev["wrong"][0]["chosen_index"] == 0
    r = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "revision"})
    assert r.status_code == 201 and r.json()["kind"] == "revision"
    raid = r.json()["id"]
    answer_all(a, sid, raid, chosen=1)                                          # now answered right: they drop off the list
    assert a.req("GET", f"/subjects/{sid}/revision").json()["wrong"] == []
    d = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "diagnostic"}).json()
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{d['id']}").json()["total_questions"] == 4      # two per topic


def test_the_report_has_the_numbers_a_csv_and_belongs_to_its_owner(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    aid = start(a, sid)
    answer_all(a, sid, aid, chosen=1)
    rep = a.req("GET", f"/subjects/{sid}/report").json()
    assert rep["subject"] == "Math" and rep["overall"]["answered"] == 6 and rep["topics"] and rep["attempts"] and rep["recommendations"] and "IRT" in rep["method"]
    n_first = rep["topics"][0]["name"]
    csv = a.req("GET", f"/subjects/{sid}/report.csv")
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv") and n_first in csv.text
    b = signed_in("bob")
    assert is_error(b.req("GET", f"/subjects/{sid}/report"), 404, "not_found")
    assert is_error(b.req("GET", f"/subjects/{sid}/revision"), 404, "not_found")
    assert is_error(b.req("GET", f"/subjects/{sid}/report.csv"), 404, "not_found")


# ------------------------------------------------------------------------------------------ level and diagnostic

def test_the_level_is_stored_per_subject_and_only_by_its_owner(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    assert a.req("GET", f"/subjects/{sid}").json()["level"] is None
    assert is_error(a.req("PUT", f"/subjects/{sid}/level", json={"level": "wizard"}), 400, "invalid")
    assert is_error(a.req("PUT", f"/subjects/{sid}/level", csrf=False, json={"level": "new"}), 403, "csrf")
    assert a.req("PUT", f"/subjects/{sid}/level", json={"level": "intermediate"}).json() == {"level": "intermediate"}
    assert a.req("GET", f"/subjects/{sid}").json()["level"] == "intermediate"
    b = signed_in("bob")
    assert is_error(b.req("PUT", f"/subjects/{sid}/level", json={"level": "new"}), 404, "not_found")


def test_a_diagnostic_job_asks_for_a_spread_of_difficulties():
    from studyhub import mcq
    import itertools
    token = mcq._MIX.set(itertools.cycle(mcq.LEVELS))
    try:
        prompts = [mcq.write_prompt([{"doc_title": "d", "heading_path": "", "page_start": None, "text": "x" * 200}], 1, []) for _ in range(4)]
    finally:
        mcq._MIX.reset(token)
    assert [("easy" in p, "medium" in p, "hard" in p) for p in prompts] == [(True, False, False), (False, True, False), (False, False, True), (True, False, False)]
    assert mcq._norm_difficulty("HARD") == "hard" and mcq._norm_difficulty("tricky") == "medium" and mcq._norm_difficulty(None) == "medium"


def test_a_diagnostic_from_a_job_concludes_a_level_and_names_strong_and_weak_topics(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    job = a.req("POST", f"/subjects/{sid}/mcq/jobs", json={"purpose": "wizard"})
    assert is_error(job, 400, "invalid")
    store = open_db()
    jid = store.db.execute("INSERT INTO mcq_jobs(user_id, subject_id, scope, requested, status, created_at, purpose) "
                           "SELECT user_id, id, 'diagnostic', 10, 'done', 0, 'diagnostic' FROM subjects WHERE id=?", (sid,)).lastrowid
    for i, diff in enumerate(["easy", "easy", "easy", "medium", "medium", "medium", "hard", "hard", "hard", "hard"]):
        tid = t1 if i < 5 else t2
        store.db.execute("INSERT INTO mcq_items(subject_id,topic_id,job_id,topic_path,question,options,answer_index,explanation,quote,key,created_at,difficulty) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (sid, tid, jid, "p", f"Diagnostic {i}?", json.dumps(["a", "b", "c", "d"]), 1, "because", "quote", f"diag{i}", time.time(), diff))
    store.close()
    a.req("PUT", f"/subjects/{sid}/level", json={"level": "professional"})
    r = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "diagnostic", "job_id": jid})
    assert r.status_code == 201
    aid = r.json()["id"]
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()["total_questions"] == 10
    assert is_error(a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "diagnostic", "job_id": 9999}), 404, "not_found")
    while True:                                                    # topic 1 questions right, topic 2 questions wrong
        st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()
        if st["state"] != "mcq":
            break
        it = st["item"]
        right = it["topic"] == n1
        answer(a, sid, aid, it, 1 if right else 0)
    res = a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result").json()
    d = res["diagnosis"]
    assert d["claimed"] == "professional" and d["suggested"] in ("new", "intermediate") and "You said Professional" in d["note"]
    assert sum(v["answered"] for v in d["by_difficulty"].values()) >= 10 and d["by_difficulty"]["hard"]["answered"] >= 4
    assert d["weakest"][0]["name"] == n2 and (not d["strongest"] or d["strongest"][0]["name"] == n1)
    other = start(a, sid)                                          # a normal quiz has no diagnosis
    answer_all(a, sid, other)
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{other}/result").json()["diagnosis"] is None
