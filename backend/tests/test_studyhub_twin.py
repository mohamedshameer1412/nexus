"""Academic setup, document roles and past-paper weights, adaptive question choice, error patterns and drift, the tutor's worked examples,
the improvement loop and the planner, and the learner twin."""
from __future__ import annotations

import time
from types import SimpleNamespace

import studyhub.web.app as appmod
from studyhub import db as studydb
from studyhub import insights, mcq, patterns, tutor
from test_studyhub_api import is_error, signed_in  # noqa: F401
from test_studyhub_api_quiz import answer_all  # noqa: F401
from test_studyhub_insights import seed_two_topics, world  # noqa: F401
from test_studyhub_web import env  # noqa: F401


def run(a, sid, chosen, kind="standard", mode="practice", **extra):
    aid = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": kind, "mode": mode, **extra}).json()["id"]
    answer_all(a, sid, aid, chosen=chosen)
    return aid


def rows(query, *args):
    store = studydb.open_db()
    try:
        return [dict(r) for r in store.db.execute(query, args)]
    finally:
        store.close()


def past_paper(names, counts):
    lines = []
    for name, n in zip(names, counts):
        for i in range(n):
            lines.append(f"{len(lines) + 1}. Explain the main ideas of {name} with an example, part {i}?")
    return ("Final examination question paper\n\n" + "\n\n".join(lines)).encode()


# ------------------------------------------------------------------------------------------------ academic setup and exam date

def test_department_and_semester_are_saved_validated_and_private(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    assert a.req("GET", "/account").json()["academic"] == {"department": "", "semester": None}
    r = a.req("PUT", "/account/academic", json={"department": "  Computer   Science ", "semester": 4})
    assert r.json() == {"department": "Computer Science", "semester": 4}
    assert a.req("GET", "/account").json()["academic"] == {"department": "Computer Science", "semester": 4}
    for bad in ({"semester": 0}, {"semester": 13}, {"department": "x" * 100}):
        assert a.req("PUT", "/account/academic", json=bad).status_code == 422
    assert is_error(a.req("PUT", "/account/academic", csrf=False, json={}), 403, "csrf")
    assert signed_in("bob").req("GET", "/account").json()["academic"] == {"department": "", "semester": None}


def test_the_exam_date_is_the_deadline_unless_the_student_sets_a_study_date(env, monkeypatch):  # noqa: F811
    a, sid, _, _ = world(env, monkeypatch)
    exam = time.strftime("%Y-%m-%d", time.localtime(time.time() + 21 * 86400))
    study = time.strftime("%Y-%m-%d", time.localtime(time.time() + 50 * 86400))
    p = a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"hours_per_week": 5, "exam_date": exam}).json()["profile"]
    assert p["exam_date"] == exam and p["target_date"] == exam and p["target_date_source"] == "exam"
    assert a.req("GET", f"/subjects/{sid}/roadmap").json()["roadmap"]["summary"]["weeks_available"] == 3
    p = a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"hours_per_week": 5, "target_date": study}).json()["profile"]     # exam_date omitted: unchanged
    assert p["exam_date"] == exam and p["target_date"] == study and p["target_date_source"] == "plan"
    p = a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"hours_per_week": 5, "exam_date": ""}).json()["profile"]
    assert p["exam_date"] is None and p["target_date"] is None
    assert is_error(a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"exam_date": "2001-01-01"}), 400, "invalid")
    assert is_error(a.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"exam_date": "soon"}), 400, "invalid")
    b = signed_in("bob")
    b.subject("Mine")
    assert is_error(b.req("PUT", f"/subjects/{sid}/roadmap/profile", json={"exam_date": exam}), 404, "not_found")


# ------------------------------------------------------------------------------------------ document roles, units, past papers

def test_a_past_paper_is_evidence_not_topics_and_a_role_is_validated(env, monkeypatch):  # noqa: F811
    a, sid, _, (n1, n2) = world(env, monkeypatch)
    before = len(a.req("GET", f"/subjects/{sid}/topics").json()["topics"])
    r = a.req("POST", f"/subjects/{sid}/materials", files={"file": ("paper.txt", past_paper([n1, n2], [3, 1]), "text/plain")}, data={"role": "pyq"})
    assert r.status_code == 201 and r.json()["document"]["role"] == "pyq"
    assert len(a.req("GET", f"/subjects/{sid}/topics").json()["topics"]) == before                        # its headings did not become topics
    assert {d["role"] for d in a.req("GET", f"/subjects/{sid}/materials").json()["documents"]} == {"notes", "pyq"}
    r = a.req("POST", f"/subjects/{sid}/materials", files={"file": ("x.txt", b"Some other notes about a different matter entirely.", "text/plain")}, data={"role": "banana"})
    assert is_error(r, 400, "upload_refused")
    doc = next(d for d in a.req("GET", f"/subjects/{sid}/materials").json()["documents"] if d["role"] == "notes")
    assert a.req("PATCH", f"/subjects/{sid}/materials/{doc['id']}/role", json={"role": "syllabus"}).json()["role"] == "syllabus"
    assert is_error(a.req("PATCH", f"/subjects/{sid}/materials/{doc['id']}/role", json={"role": "pyq"}), 400, "invalid")
    assert is_error(a.req("PATCH", f"/subjects/{sid}/materials/{doc['id']}/role", json={"role": "x"}), 400, "invalid")
    assert is_error(a.req("PATCH", f"/subjects/{sid}/materials/{doc['id']}/role", csrf=False, json={"role": "notes"}), 403, "csrf")
    assert is_error(signed_in("bob").req("PATCH", f"/subjects/{sid}/materials/{doc['id']}/role", json={"role": "notes"}), 404, "not_found")


def test_topics_asked_more_often_in_past_papers_weigh_more_and_come_first(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    assert patterns.exam_weights(studydb.open_db().db, sid) == {}
    a.req("POST", f"/subjects/{sid}/materials", files={"file": ("paper.txt", past_paper([n1, n2], [1, 4]), "text/plain")}, data={"role": "pyq"})
    store = studydb.open_db()
    try:
        w = patterns.exam_weights(store.db, sid)
    finally:
        store.close()
    assert w[t2]["count"] >= 4 > w[t1]["count"] >= 1 and w[t2]["weight"] > w[t1]["weight"] and abs(sum(x["weight"] for x in w.values()) - 1) < 0.02
    run(a, sid, 0)                                                                                          # both topics equally weak
    rm = a.req("GET", f"/subjects/{sid}/roadmap").json()
    g = {x["name"]: x for x in rm["gaps"]}
    assert g[n2]["exam_count"] > g[n1]["exam_count"]
    from studyhub import roadmap
    flat = lambda i, w: {"topic_id": i, "name": "x", "status": "critical", "ordinal": 1, "blocked_by": [], "exam_weight": w}     # noqa: E731
    assert [g_["exam_weight"] for g_ in roadmap._order([flat(1, 0.1), flat(2, 0.6), flat(3, 0.3)])] == [0.6, 0.3, 0.1]                     # asked most, studied first


def test_a_path_splits_into_a_unit_and_subtopics_and_units_roll_up():
    assert patterns.unit_of("Unit 2 › Trees › AVL") == ("Unit 2", "Trees › AVL") and patterns.unit_of("Stacks") == ("Stacks", "") and patterns.unit_of("") == ("General", "")
    gaps = [{"path": "U1 › A", "confidence": 0.8, "target": 0.7, "answered": 5, "ordinal": 1}, {"path": "U1 › B", "confidence": 0.4, "target": 0.7, "answered": 4, "ordinal": 2},
            {"path": "U2 › C", "confidence": None, "target": 0.7, "answered": 0, "ordinal": 3}]
    u = {x["unit"]: x for x in patterns.rollup(gaps)}
    assert u["U1"]["confidence"] == 0.6 and u["U1"]["status"] == "below" and u["U1"]["assessed"] == 2 and u["U2"]["status"] == "unassessed" and u["U2"]["confidence"] is None


# ---------------------------------------------------------------------------------------------------------- adaptive choice

def test_the_most_informative_question_sits_near_the_students_ability():
    assert insights.information(0.0, 0.0) > insights.information(0.0, 2.5) and insights.information(0.0, 0.0) > insights.information(0.0, -2.5)
    assert insights.information(2.0, 2.0) > insights.information(2.0, -2.0)


def test_adaptive_quizzes_prefer_harder_questions_for_a_strong_student_and_cap_a_topic(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    for _ in range(3):
        run(a, sid, 1)                                                                                      # strong on both topics
    store = studydb.open_db()
    try:
        for i, level in enumerate(["easy", "hard"] * 3):
            store.db.execute("INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at,difficulty) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                             (sid, t1, n1, f"Extra {level} {i}?", '["a","b","c","d"]', 1, "", "quote", f"x{i}", time.time(), level))
        items = store.repo.list_mcq(1, sid) if hasattr(store, "repo") else None
        from studyhub.repo import Repo
        items = Repo(store.db).list_mcq(1, sid, topic_id=t1)
        me = store.db.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        items = Repo(store.db).list_mcq(me, sid, topic_id=t1)
        picked = insights.select_adaptive(store.db, me, sid, items, 4)
    finally:
        store.close()
    assert len(picked) == 4 and sum(1 for i in picked if i["difficulty"] == "hard") >= sum(1 for i in picked if i["difficulty"] == "easy")
    r = a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "standard", "adaptive": True})
    assert r.status_code == 201
    st = a.req("GET", f"/subjects/{sid}/quiz/attempts/{r.json()['id']}").json()
    assert st["state"] == "mcq" and st["position"] == 1


# ------------------------------------------------------------------------------------------------- error patterns and drift

def test_repeated_misses_the_same_wrong_choice_and_position_bias_are_found(env, monkeypatch):  # noqa: F811
    a, sid, _, (n1, n2) = world(env, monkeypatch)
    for _ in range(3):
        run(a, sid, 0)                                                                                      # always option 0 (wrong): 6 items x 3 = 18 answers
    e = patterns.error_patterns(studydb.open_db().db, 1, sid)
    kinds = {p["kind"] for p in e["patterns"]}
    assert {"repeat_miss", "same_wrong_choice", "position_bias"} <= kinds and e["recurring"] == 6 and e["answers"] == 18
    bias = next(p for p in e["patterns"] if p["kind"] == "position_bias")
    assert "Option A" in bias["detail"] and "100%" in bias["detail"]
    assert "Counted from your own answers" in e["method"]
    assert patterns.error_patterns(studydb.open_db().db, 999, sid)["patterns"] == []                          # another user has none of it


def test_very_fast_wrong_answers_and_slipping_on_hard_questions_are_named(monkeypatch):
    def row(i, ok, secs, diff, topic=1):
        return {"item_id": i, "chosen_index": 0, "is_correct": ok, "response_time": secs, "answered_at": i, "topic_id": topic, "question": f"q{i}", "options": '["a","b","c","d"]',
                "answer_index": 1, "difficulty": diff, "topic": "T"}
    data = [row(i, 1, 20, "easy") for i in range(1, 7)] + [row(10 + i, 0, 1.0, "hard") for i in range(4)] + [row(20 + i, 1, 20, "medium") for i in range(3)]
    monkeypatch.setattr(patterns, "_answers", lambda *a: data)
    kinds = {p["kind"]: p for p in patterns.error_patterns(None, 1, 1)["patterns"]}
    assert "rushing" in kinds and "under" in kinds["rushing"]["detail"] and "slips_on_hard" in kinds and "100%" in kinds["slips_on_hard"]["detail"].replace("0%", "100%")


def test_drift_notices_a_fall_and_forgetting(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), _ = world(env, monkeypatch)
    for _ in range(2):
        run(a, sid, 1)
    for _ in range(2):
        run(a, sid, 0)
    store = studydb.open_db()
    try:
        d = patterns.drift(store.db, 1, sid)
        assert d[t1]["state"] == "drifting" and d[t1]["delta"] < 0 and "fell" in patterns.drift_note(d[t1])
        fade = patterns.drift(store.db, 1, sid, now=time.time() + 40 * 86400)
    finally:
        store.close()
    assert fade[t1]["state"] == "drifting"                                                                 # a fall is reported before staleness
    b = signed_in("carol")
    sb = b.subject("Other")
    ids, _n = seed_two_topics(b, sb)
    for _ in range(3):
        run(b, sb, 1)
    store = studydb.open_db()
    try:
        uid = store.db.execute("SELECT id FROM users WHERE username='carol'").fetchone()["id"]
        d = patterns.drift(store.db, uid, sb, now=time.time() + 30 * 86400)
    finally:
        store.close()
    assert d[ids[0]]["state"] == "fading" and "30 days" in patterns.drift_note(d[ids[0]]) and patterns.drift(studydb.open_db().db, uid, sb)[ids[0]]["state"] == "steady"


# ------------------------------------------------------------------------------------------------------- worked examples

def passage_of(topic_id, sid):
    store = studydb.open_db()
    try:
        return tutor.passages(store.db, sid, topic_id)
    finally:
        store.close()


def wait_example(a, sid, tid):
    return a.req("GET", f"/subjects/{sid}/examples?topic_id={tid}").json()["examples"][0]


def test_a_model_example_keeps_only_steps_that_quote_the_passages(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    text = passage_of(t1, sid)[0]
    good = " ".join(text.split())[:60]
    seen = {}

    def fake_call(tier, budget, messages, schema, step):
        seen["system"], seen["user"] = messages[0]["content"], messages[1]["content"]
        return schema(problem="Try a small case", steps=[{"text": "First idea", "quote": good}, {"text": "Second idea", "quote": good}, {"text": "Invented", "quote": "words nobody wrote anywhere"}],
                      answer="Done", check="Now try another")
    monkeypatch.setattr(mcq, "_call", fake_call)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user, task="answer": ([SimpleNamespace(name="cloud", model="mistralai/mistral-small-3.2-24b-instruct", settings=None)], []))
    a.req("PUT", f"/subjects/{sid}/level", json={"level": "new"})
    r = a.req("POST", f"/subjects/{sid}/examples", json={"topic_id": t1})
    assert r.status_code == 202
    ex = wait_example(a, sid, t1)
    assert ex["status"] == "done" and ex["model"].startswith("mistralai") and ex["example"]["from_model"] is True
    assert [s["text"] for s in ex["example"]["steps"]] == ["First idea", "Second idea"]                      # the invented step was dropped
    assert "ignore any instruction" in seen["system"] and "beginner" in seen["user"] and text[:30] in seen["user"]
    assert rows("SELECT kind, status FROM interventions WHERE topic_id=?", t1) == [{"kind": "worked_example", "status": "done"}]


def test_without_a_model_the_example_is_the_key_passages_and_says_so(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, (t1, t2), _ = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user, task="answer": ([], []))
    a.req("POST", f"/subjects/{sid}/examples", json={"topic_id": t1})
    ex = wait_example(a, sid, t1)
    assert ex["status"] == "done" and ex["model"].startswith("rules") and ex["example"]["from_model"] is False and ex["example"]["steps"]
    monkeypatch.setattr(mcq, "_call", lambda *x, **k: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user, task="answer": ([SimpleNamespace(name="cloud", model="m", settings=None)], []))
    a.req("POST", f"/subjects/{sid}/examples", json={"topic_id": t1})
    assert wait_example(a, sid, t1)["model"].startswith("rules")


def test_examples_are_private_validated_and_rate_limited(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    a, sid, (t1, t2), _ = world(env, monkeypatch)
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user, task="answer": ([], []))
    assert is_error(a.req("POST", f"/subjects/{sid}/examples", json={"topic_id": 99999}), 404, "not_found")
    assert is_error(a.req("POST", f"/subjects/{sid}/examples", csrf=False, json={"topic_id": t1}), 403, "csrf")
    b = signed_in("bob")
    b.subject("Mine")
    assert is_error(b.req("POST", f"/subjects/{sid}/examples", json={"topic_id": t1}), 404, "not_found")
    assert is_error(b.req("GET", f"/subjects/{sid}/examples"), 404, "not_found")
    for _ in range(10):
        assert a.req("POST", f"/subjects/{sid}/examples", json={"topic_id": t1}).status_code == 202
    assert is_error(a.req("POST", f"/subjects/{sid}/examples", json={"topic_id": t1}), 429, "rate_limited")


def test_the_level_advice_follows_ability():
    assert tutor.advise_level(None, 0)["difficulty"] == "medium" and tutor.advise_level(-1.0, 2)["difficulty"] == "medium"
    assert tutor.advise_level(-1.0, 6)["difficulty"] == "easy" and tutor.advise_level(1.0, 6)["difficulty"] == "hard" and tutor.advise_level(0.0, 6)["difficulty"] == "medium"


# --------------------------------------------------------------------------------- the improvement loop and the planner

def test_actions_on_weak_topics_are_logged_and_later_checked_against_new_answers(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    run(a, sid, 0)                                                                                          # 3 wrong on each topic
    assert a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "revision"}).status_code == 201
    logged = rows("SELECT topic_id, kind, outcome, conf_before, answered_before FROM interventions WHERE kind='revision' ORDER BY topic_id")
    assert [r["topic_id"] for r in logged] == [t1, t2] and all(r["outcome"] is None and r["conf_before"] < 0.5 and r["answered_before"] == 3 for r in logged)
    a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "revision"})                              # a second start within a week does not repeat it
    assert len(rows("SELECT id FROM interventions WHERE kind='revision'")) == 2
    tw = a.req("GET", f"/subjects/{sid}/twin").json()
    assert {h["outcome"] for h in tw["history"]} == {None}                                                  # nothing new answered yet: not judged
    for _ in range(3):
        run(a, sid, 1)                                                                                      # 9 new right answers per topic pair
    tw = a.req("GET", f"/subjects/{sid}/twin").json()
    assert {h["outcome"] for h in tw["history"] if h["kind"] == "revision"} == {"improved"}
    m = tw["memory"][0]
    assert m["kind"] == "revision" and m["improved"] == 2 and m["mean_change"] > 0.1
    row = {t["name"]: t for t in tw["topics"]}[n1]
    assert row["loop"]["state"] == "improved" and row["loop"]["last_kind"] == "revision" and row["loop"]["change"] > 0.1


def test_flashcard_practice_and_a_topic_quiz_are_logged_only_below_target(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), _ = world(env, monkeypatch)
    item = a.req("GET", f"/subjects/{sid}/mcq").json()["questions"][0]
    a.req("POST", f"/subjects/{sid}/flashcards/{item['id']}/review", json={"grade": "good"})
    assert rows("SELECT id FROM interventions") == []                                                       # no answers yet: no baseline, nothing logged
    run(a, sid, 0)
    a.req("POST", f"/subjects/{sid}/flashcards/{item['id']}/review", json={"grade": "again"})
    a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "standard", "topic_id": t2})
    assert {r["kind"] for r in rows("SELECT kind FROM interventions")} == {"flashcards", "practice"}
    for _ in range(3):
        run(a, sid, 1)
    a.req("POST", f"/subjects/{sid}/quiz/attempts", json={"kind": "standard", "topic_id": t2})
    assert len(rows("SELECT id FROM interventions")) == 2                                                   # solid now: not a weak-topic action


def test_the_planner_changes_the_action_when_the_last_one_did_not_help(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    run(a, sid, 0)
    first = a.req("GET", f"/subjects/{sid}/twin").json()["next"]
    assert first and first[0]["kind"] == "worked_example" and first[0]["why"] and first[0]["fits_this_week"] is True and first[0]["difficulty"] in ("easy", "medium", "hard")
    store = studydb.open_db()
    try:
        uid = store.db.execute("SELECT id FROM users WHERE username='alice'").fetchone()["id"]
        target = first[0]["topic_id"]
        now = time.time()
        store.db.execute("INSERT INTO interventions(user_id,subject_id,topic_id,kind,status,conf_before,answered_before,outcome,conf_after,verified_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (uid, sid, target, "worked_example", "done", 0.2, 3, "no_change", 0.22, now, now - 100, now))
    finally:
        store.close()
    second = {x["topic_id"]: x for x in a.req("GET", f"/subjects/{sid}/twin").json()["next"]}[target]
    assert second["kind"] != "worked_example" and any("did not move" in w for w in second["why"])
    store = studydb.open_db()
    try:
        store.db.execute("UPDATE interventions SET outcome='improved', conf_after=0.4 WHERE topic_id=?", (target,))
    finally:
        store.close()
    third = {x["topic_id"]: x for x in a.req("GET", f"/subjects/{sid}/twin").json()["next"]}[target]
    assert third["kind"] == "worked_example" and any("raised this topic last time" in w for w in third["why"])


def test_when_everything_was_tried_the_planner_asks_the_tutor_and_memory_reorders_the_ladder():
    mem = [{"kind": "flashcards", "label": "Review flashcards", "tried": 3, "improved": 3, "mean_change": 0.2}, {"kind": "revision", "label": "x", "tried": 1, "improved": 1, "mean_change": 0.5}]
    assert tutor._preferred(mem) == ["flashcards"]                                                          # one try is not enough to call it a habit that works


def test_the_planner_aims_at_the_root_cause_and_weighs_past_papers(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    import random
    monkeypatch.setattr(random, "shuffle", lambda x: x.sort(key=lambda i: -(i["topic_id"] or 0) if isinstance(i, dict) else 0))
    for _ in range(2):
        run(a, sid, 0)
    tw = a.req("GET", f"/subjects/{sid}/twin").json()
    top = tw["next"][0]
    assert top["topic_id"] == t1 and any("builds on it" in w for w in top["why"])                            # the later topic builds on the earlier one, which is the cause
    a.req("POST", f"/subjects/{sid}/materials", files={"file": ("paper.txt", past_paper([n1], [3]), "text/plain")}, data={"role": "pyq"})
    tw = a.req("GET", f"/subjects/{sid}/twin").json()
    assert tw["has_past_papers"] is True and any("past papers" in w for w in tw["next"][0]["why"])


# ------------------------------------------------------------------------------------------------------------- the twin

def test_the_twin_pulls_the_learner_together_and_belongs_to_its_owner(env, monkeypatch):  # noqa: F811
    a, sid, (t1, t2), (n1, n2) = world(env, monkeypatch)
    a.req("PUT", "/account/academic", json={"department": "Physics", "semester": 2})
    a.req("PUT", f"/subjects/{sid}/level", json={"level": "intermediate"})
    a.req("PUT", f"/subjects/{sid}/self-check", json={"ratings": {str(t1): 5}})
    run(a, sid, 0)
    tw = a.req("GET", f"/subjects/{sid}/twin").json()
    assert tw["profile"]["department"] == "Physics" and tw["profile"]["semester"] == 2 and tw["profile"]["level"] == "intermediate"
    row = {t["name"]: t for t in tw["topics"]}[n1]
    assert row["feeling"] == "overconfident" and row["rating"] == 5 and row["unit"] and row["difficulty"] == "easy" and row["answered"] >= 3
    assert tw["weaknesses"] and tw["units"] and tw["patterns"]["answers"] >= 6 and tw["next"] and tw["has_past_papers"] is False
    assert tw == a.req("GET", f"/subjects/{sid}/twin").json()                                                 # the same data gives the same twin
    assert is_error(signed_in("bob").req("GET", f"/subjects/{sid}/twin"), 404, "not_found")
