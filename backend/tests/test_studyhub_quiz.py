"""Phase C tests: quiz attempts, scoring, proctoring, backward-pass, progress, prereqs.

All tests use stub agent callables so no Ollama model is required.
The autouse `isolated` fixture (from test_studyhub_qa) gives a clean DB per test.
"""
from __future__ import annotations

import json
import time

import pytest
from django_client import TestClient

import studyhub.jobs as appmod
from studyhub import quiz_flow
from studyhub import auth
from studyhub.db import open_db
from studyhub.repo import Repo
from studyhub import scoring, quiz_flow, quiz_agents
from studyhub.prereq import load_graph, can_step_back

# autouse fixture — same pattern as all other test modules in this project
from test_studyhub_qa import isolated  # noqa: F401

PW = "hunter22"  # ≥ 8 chars as required by auth.check_password

# ── test-local helpers ─────────────────────────────────────────────────────────

def _fresh() -> tuple:
    """Open DB, create user+subject+topic+chunk+MCQ item, return (store, uid, sid, tid, item_id)."""
    store = open_db()
    db    = store.db
    uid   = auth.register(db, "quiz_user", PW)
    repo  = Repo(db)
    sid   = repo.create_subject(uid, "Math", "Basic math")
    # Insert topic (origin required — must be 'manual' or other valid value per schema)
    db.execute("INSERT INTO topics(subject_id, name, path, ordinal, origin) VALUES (?,?,?,1,'manual')",
               (sid, "Algebra", "Math > Algebra"))
    tid = db.execute("SELECT id FROM topics WHERE subject_id=? AND name='Algebra'", (sid,)).fetchone()["id"]
    # Insert a fake document + chunk so the topic has chunks > 0 for route filtering
    import time as _t
    db.execute(
        "INSERT INTO documents(subject_id, kind, title, source, sha256, bytes, pages, status, warnings, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sid, "txt", "Test Doc", "test.txt", "aabbcc112233", 10, 1, "parsed", "[]", _t.time()))
    doc_id = db.execute("SELECT id FROM documents WHERE subject_id=?", (sid,)).fetchone()["id"]
    db.execute(
        "INSERT INTO chunks(subject_id, document_id, topic_id, ordinal, page_start, page_end, heading_path, text, sha256) "
        "VALUES (?,?,?,0,1,1,'Algebra','test content','00aabb')",
        (sid, doc_id, tid))
    # Insert an MCQ item (all NOT NULL columns required)
    import time as _t2
    db.execute(
        "INSERT INTO mcq_items(subject_id, topic_id, topic_path, question, options, answer_index, explanation, "
        "quote, key, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sid, tid, "Math > Algebra", "What is 2+2?",
         json.dumps(["3", "4", "5", "6"]), 1, "Basic addition",
         "2+2=4", "k1", _t2.time()))
    item_id = db.execute("SELECT id FROM mcq_items WHERE subject_id=?", (sid,)).fetchone()["id"]
    return store, uid, sid, tid, item_id


# ── Migration + schema ────────────────────────────────────────────────────────

def test_migration_creates_tables(isolated):  # noqa: F811
    store = open_db()
    try:
        db = store.db
        tables = {r[0] for r in db.execute(("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()") if getattr(db, "pg", False) else "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "quiz_attempts"          in tables
        assert "attempt_answers"        in tables
        assert "quiz_proctoring_events" in tables
        assert "topic_progress"         in tables
        assert "topic_prereqs"          in tables
    finally:
        store.close()


def test_schema_version_is_the_latest_migration(isolated):  # noqa: F811
    store = open_db()
    try:
        v = store.db.execute("SELECT MAX(v) FROM schema_version").fetchone()[0]
        from studyhub.db import MIGRATIONS
        assert v == max(n for n, _ in MIGRATIONS) == 18
    finally:
        store.close()


# ── Quiz flow: start session ──────────────────────────────────────────────────

def test_start_session_creates_attempt(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        assert attempt is not None
        assert attempt["is_active"] == 1
        assert attempt["user_id"] == uid
        row = db.execute("SELECT * FROM attempt_answers WHERE attempt_id=?", (attempt["id"],)).fetchone()
        assert row["chosen_index"] is None
    finally:
        store.close()


def test_start_session_wrong_user_returns_none(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        other_uid = auth.register(db, "other", PW)
        attempt = quiz_flow.start_session(db, other_uid, sid, root_topic_id=tid, item_ids=[item_id])
        assert attempt is None
    finally:
        store.close()


# ── Scoring ───────────────────────────────────────────────────────────────────

def test_correct_answer_updates_counters(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        updated = scoring.record_answer(db, uid, attempt["id"], item_id,
                                        chosen_index=1, response_time=5.0, hesitation_count=0)
        assert updated["correct_answers"]   == 1
        assert updated["incorrect_answers"] == 0
        assert updated["score"]             == 1
    finally:
        store.close()


def test_wrong_answer_updates_counters(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        updated = scoring.record_answer(db, uid, attempt["id"], item_id,
                                        chosen_index=0, response_time=12.0, hesitation_count=2)
        assert updated["correct_answers"]   == 0
        assert updated["incorrect_answers"] == 1
    finally:
        store.close()


def test_answer_wrong_user_returns_none(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        other = auth.register(db, "xxx", PW)
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        result = scoring.record_answer(db, other, attempt["id"], item_id, 1, 5.0, 0)
        assert result is None
    finally:
        store.close()


def test_topic_progress_mastered(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        import time as _ti
        db.execute(
            "INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, tid, "Math > Algebra", "What is 3+3?", json.dumps(["5","6","7","8"]), 1, "", "3+3=6", "k2", _ti.time()))
        item2 = db.execute("SELECT id FROM mcq_items WHERE subject_id=? ORDER BY id DESC LIMIT 1", (sid,)).fetchone()["id"]
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id, item2])
        aid = attempt["id"]
        scoring.record_answer(db, uid, aid, item_id, 1, 5.0, 0)   # correct
        scoring.record_answer(db, uid, aid, item2,   1, 5.0, 0)   # correct
        prog = db.execute("SELECT * FROM topic_progress WHERE user_id=? AND topic_id=?", (uid, tid)).fetchone()
        assert prog is not None
        assert prog["answered"] == 2
        assert prog["correct"]  == 2
        assert prog["state"]    == "mastered"
    finally:
        store.close()


def test_topic_progress_weak(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        import time as _ti2
        db.execute(
            "INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, tid, "Math > Algebra", "What is 10+10?", json.dumps(["10","20","30","40"]), 1, "", "10+10=20", "k3", _ti2.time()))
        item2 = db.execute("SELECT id FROM mcq_items WHERE subject_id=? ORDER BY id DESC LIMIT 1", (sid,)).fetchone()["id"]
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id, item2])
        aid = attempt["id"]
        scoring.record_answer(db, uid, aid, item_id, 0, 5.0, 0)  # wrong
        scoring.record_answer(db, uid, aid, item2,   0, 5.0, 0)  # wrong
        prog = db.execute("SELECT * FROM topic_progress WHERE user_id=? AND topic_id=?", (uid, tid)).fetchone()
        assert prog["state"] == "weak"
    finally:
        store.close()


# ── Confidence scoring ────────────────────────────────────────────────────────

def test_confidence_fast_no_hes():
    assert scoring.compute_confidence(3.0, 0) == pytest.approx(0.9)


def test_confidence_slow_many_hes():
    assert scoring.compute_confidence(25.0, 5) == pytest.approx(0.3)


# ── Proctoring ────────────────────────────────────────────────────────────────

def test_proctoring_deducts_behavior(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        aid = attempt["id"]
        scoring.record_proctoring_event(db, uid, aid, "tab_switch")
        row = db.execute("SELECT behavior_score FROM quiz_attempts WHERE id=?", (aid,)).fetchone()
        assert row["behavior_score"] == pytest.approx(40.0)   # 100 - 60
    finally:
        store.close()


def test_trust_score(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        aid = attempt["id"]
        scoring.record_proctoring_event(db, uid, aid, "full_screen_exit")  # -30
        scoring.record_proctoring_event(db, uid, aid, "copy_attempt")      # -20
        ts = scoring.trust_score(db, uid, aid)
        assert ts == 50
    finally:
        store.close()


def test_trust_score_floor_at_zero(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        aid = attempt["id"]
        for _ in range(5):
            scoring.record_proctoring_event(db, uid, aid, "tab_switch")  # each = -60
        ts = scoring.trust_score(db, uid, aid)
        assert ts == 0
    finally:
        store.close()


def test_proctor_wrong_user_returns_false(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        other = auth.register(db, "yyy", PW)
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        ok = scoring.record_proctoring_event(db, other, attempt["id"], "tab_switch")
        assert ok is False
    finally:
        store.close()


# ── Stub agents ───────────────────────────────────────────────────────────────

def test_stub_spot_returns_string():
    q = quiz_agents.stub_spot(1, "Algebra", 1, [])
    assert isinstance(q, str) and len(q) > 0


def test_stub_gate_pass():
    v = quiz_agents.stub_gate(1, "Algebra", "Q?", "A.", [], None, {})
    assert v["status"] == "PASS"
    assert v["prerequisite_id"] is None


def test_stub_gate_block():
    graph = {2: {"id": 2, "name": "Arithmetic", "prereq_id": None}}
    v = quiz_agents.stub_gate_block(1, "Algebra", "Q?", "A.", [], 2, graph)
    assert v["status"] == "BLOCK"
    assert v["prerequisite_id"] == 2


# ── Prerequisites ─────────────────────────────────────────────────────────────

def test_prereq_set_and_list(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,2,'manual')",
                   (sid, "Arithmetic", "Math > Arithmetic"))
        tid2 = db.execute("SELECT id FROM topics WHERE name='Arithmetic'").fetchone()["id"]
        repo = Repo(db)
        ok = repo.set_prereq(uid, sid, tid, tid2)
        assert ok is True
        prereqs = repo.list_prereqs(uid, sid)
        assert len(prereqs) == 1
        assert prereqs[0]["topic_name"]  == "Algebra"
        assert prereqs[0]["prereq_name"] == "Arithmetic"
    finally:
        store.close()


def test_prereq_cycle_rejected(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,2,'manual')",
                   (sid, "Arithmetic", "Math > Arithmetic"))
        tid2 = db.execute("SELECT id FROM topics WHERE name='Arithmetic'").fetchone()["id"]
        repo = Repo(db)
        repo.set_prereq(uid, sid, tid, tid2)           # Algebra → Arithmetic
        ok = repo.set_prereq(uid, sid, tid2, tid)      # would create cycle
        assert ok is False
    finally:
        store.close()


def test_prereq_self_loop_rejected(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        repo = Repo(db)
        ok = repo.set_prereq(uid, sid, tid, tid)   # topic → itself
        assert ok is False
    finally:
        store.close()


def test_can_step_back_true(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,2,'manual')",
                   (sid, "Arithmetic", "Math > Arithmetic"))
        tid2 = db.execute("SELECT id FROM topics WHERE name='Arithmetic'").fetchone()["id"]
        db.execute("INSERT INTO topic_prereqs(topic_id,prereq_id,confirmed) VALUES (?,?,1)", (tid, tid2))
        graph = load_graph(db, sid)
        assert can_step_back(graph, tid, depth=0, verified_ids=[]) is True
    finally:
        store.close()


def test_can_step_back_false_at_max_depth(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,2,'manual')",
                   (sid, "Arithmetic", "Math > Arithmetic"))
        tid2 = db.execute("SELECT id FROM topics WHERE name='Arithmetic'").fetchone()["id"]
        db.execute("INSERT INTO topic_prereqs(topic_id,prereq_id,confirmed) VALUES (?,?,1)", (tid, tid2))
        graph = load_graph(db, sid)
        assert can_step_back(graph, tid, depth=3, verified_ids=[]) is False
    finally:
        store.close()


def test_can_step_back_false_already_verified(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,2,'manual')",
                   (sid, "Arithmetic", "Math > Arithmetic"))
        tid2 = db.execute("SELECT id FROM topics WHERE name='Arithmetic'").fetchone()["id"]
        db.execute("INSERT INTO topic_prereqs(topic_id,prereq_id,confirmed) VALUES (?,?,1)", (tid, tid2))
        graph = load_graph(db, sid)
        assert can_step_back(graph, tid, depth=0, verified_ids=[tid2]) is False
    finally:
        store.close()


# ── Repo quiz methods ─────────────────────────────────────────────────────────

def test_repo_list_attempts_empty(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        assert Repo(store.db).list_attempts(uid, sid) == []
    finally:
        store.close()


def test_repo_get_active_attempt(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        active = Repo(db).get_active_attempt(uid, sid)
        assert active is not None
        assert active["id"] == attempt["id"]
    finally:
        store.close()


def test_repo_get_active_attempt_other_user_none(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        other = auth.register(db, "zzz", PW)
        active = Repo(db).get_active_attempt(other, sid)
        assert active is None
    finally:
        store.close()


def test_repo_weak_topics_empty(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        assert Repo(store.db).weak_topics(uid, sid) == []
    finally:
        store.close()


def test_repo_proctoring_summary_full_score(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        s = Repo(db).proctoring_summary(uid, sid, attempt["id"])
        assert s["trust_score"]        == 100
        assert s["total_tab_switches"] == 0
    finally:
        store.close()


def test_repo_list_attempt_answers(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        scoring.record_answer(db, uid, attempt["id"], item_id, 1, 5.0, 0)
        answers = Repo(db).list_attempt_answers(uid, sid, attempt["id"])
        # list_attempt_answers returns all rows; filter to those actually answered
        answered = [a for a in answers if a.get("chosen_index") is not None]
        assert len(answered) == 1
        assert answered[0]["is_correct"] == 1
    finally:
        store.close()


# ── finish_attempt ────────────────────────────────────────────────────────────

def test_finish_attempt(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        finished = scoring.finish_attempt(db, uid, attempt["id"])
        assert finished["is_active"]   == 0
        assert finished["finished_at"] is not None
    finally:
        store.close()


def test_expire_stale_attempts(isolated):  # noqa: F811
    store, uid, sid, tid, item_id = _fresh()
    try:
        db = store.db
        attempt = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item_id])
        db.execute("UPDATE quiz_attempts SET started_at=? WHERE id=?",
                   (time.time() - 7200, attempt["id"]))
        n = Repo(db).expire_stale_attempts(3600)
        assert n == 1
        row = db.execute("SELECT is_active FROM quiz_attempts WHERE id=?", (attempt["id"],)).fetchone()
        assert row["is_active"] == 0
    finally:
        store.close()


# ── HTTP smoke tests (unauthenticated → redirect) ─────────────────────────────

