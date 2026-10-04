"""Quiz answer integrity and the security of the quiz page. (UNIT + HTTP, no model.)

Written from a review of the quiz feature: an answer must UPDATE the queued row (not add a second one, which left the
question "unanswered" forever), must be tied to the row and item it was queued for, and can only be given once. The one page
that needs JavaScript gets a per-response nonce; every other page keeps `script-src 'none'`; the proctoring POST needs the CSRF token.
"""
from __future__ import annotations

import json
import re
import time
from types import SimpleNamespace

import pytest
from django_client import TestClient

import studyhub.jobs as appmod
from studyhub import quiz_flow
from studyhub import auth, quiz_flow, scoring
from studyhub.db import open_db
from studyhub.repo import Repo
from test_studyhub_qa import isolated  # noqa: F401
from test_studyhub_quiz import PW, _fresh
from test_studyhub_web import env, new_client, session_csrf, sign_up, subject_id, add_subject  # noqa: F401


def rows(db, attempt_id):
    return [dict(r) for r in db.execute("SELECT * FROM attempt_answers WHERE attempt_id=? ORDER BY id", (attempt_id,))]


def second_item(db, sid, tid, answer_index=2):
    db.execute("INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at) "
               "VALUES (?,?,?,?,?,?,?,?,?,?)",
               (sid, tid, "Math > Algebra", "What is 3+3?", json.dumps(["5", "7", "6", "8"]), answer_index, "", "3+3=6", "k2", time.time()))
    return db.execute("SELECT id FROM mcq_items WHERE subject_id=? ORDER BY id DESC LIMIT 1", (sid,)).fetchone()["id"]


# ================================================================================================ scoring layer

def test_answering_updates_the_queued_row_instead_of_adding_a_second_one(isolated):  # noqa: F811
    store, uid, sid, tid, item = _fresh()
    db = store.db
    att = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item])
    queued = rows(db, att["id"])
    assert len(queued) == 1 and queued[0]["answered_at"] is None
    scoring.record_answer(db, uid, att["id"], item, 1, 5.0, 0)
    after = rows(db, att["id"])
    assert len(after) == 1, "one question, one row"
    assert after[0]["id"] == queued[0]["id"] and after[0]["chosen_index"] == 1 and after[0]["is_correct"] == 1
    assert after[0]["answered_at"] is not None
    assert db.execute("SELECT COUNT(*) FROM attempt_answers WHERE attempt_id=? AND answered_at IS NULL", (att["id"],)).fetchone()[0] == 0
    store.close()


def test_an_answer_can_only_be_given_once_and_the_score_does_not_double(isolated):  # noqa: F811
    store, uid, sid, tid, item = _fresh()
    db = store.db
    att = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item])
    first = scoring.record_answer(db, uid, att["id"], item, 1, 5.0, 0)
    again = scoring.record_answer(db, uid, att["id"], item, 1, 5.0, 0)
    assert first["score"] == 1 and again is None
    now = scoring._own_attempt(db, uid, att["id"])
    assert (now["score"], now["max_score"], now["correct_answers"]) == (1, 1, 1) and len(rows(db, att["id"])) == 1
    store.close()


def test_an_item_that_was_not_queued_for_this_attempt_is_refused_and_changes_nothing(isolated):  # noqa: F811
    store, uid, sid, tid, item = _fresh()
    db = store.db
    extra = second_item(db, sid, tid)                                        # same subject, but not in this attempt
    att = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item])
    assert scoring.record_answer(db, uid, att["id"], extra, 2, 5.0, 0) is None
    other = auth.register(db, "mallory", PW)
    osid = Repo(db).create_subject(other, "Theirs")
    db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,1,'manual')", (osid, "T", "T"))
    otid = db.execute("SELECT id FROM topics WHERE subject_id=?", (osid,)).fetchone()["id"]
    foreign = second_item(db, osid, otid)                                    # another user's question bank
    assert scoring.record_answer(db, uid, att["id"], foreign, 2, 5.0, 0) is None
    now = scoring._own_attempt(db, uid, att["id"])
    assert (now["score"], now["max_score"], now["correct_answers"], now["incorrect_answers"]) == (0, 0, 0, 0)
    assert len(rows(db, att["id"])) == 1 and rows(db, att["id"])[0]["answered_at"] is None
    assert db.execute("SELECT COUNT(*) FROM topic_progress").fetchone()[0] == 0
    store.close()


def test_the_row_id_must_belong_to_this_attempt_and_this_item(isolated):  # noqa: F811
    store, uid, sid, tid, item = _fresh()
    db = store.db
    item2 = second_item(db, sid, tid)
    a1 = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item, item2])
    q = rows(db, a1["id"])
    assert scoring.record_answer(db, uid, a1["id"], item, 1, 5.0, 0, answer_row_id=q[1]["id"]) is None, "row of another item"
    assert scoring.record_answer(db, uid, a1["id"], item, 1, 5.0, 0, answer_row_id=999999) is None
    a2 = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item])
    foreign_row = rows(db, a2["id"])[0]["id"]
    assert scoring.record_answer(db, uid, a1["id"], item, 1, 5.0, 0, answer_row_id=foreign_row) is None, "row of another attempt"
    assert all(r["answered_at"] is None for r in rows(db, a1["id"]) + rows(db, a2["id"]))
    assert scoring.record_answer(db, uid, a1["id"], item, 1, 5.0, 0, answer_row_id=q[0]["id"])["score"] == 1
    store.close()


def test_a_skipped_question_is_marked_answered_so_it_is_not_asked_again(isolated):  # noqa: F811
    store, uid, sid, tid, item = _fresh()
    db = store.db
    att = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item])
    now = scoring.record_answer(db, uid, att["id"], item, None, 30.0, 3)
    r = rows(db, att["id"])[0]
    assert r["chosen_index"] is None and r["is_correct"] is None and r["answered_at"] is not None
    assert (now["correct_answers"], now["incorrect_answers"]) == (0, 0)
    assert scoring.record_answer(db, uid, att["id"], item, 1, 5.0, 0) is None, "a skipped question cannot be answered later for a score"
    store.close()


@pytest.mark.parametrize("bad", [4, 7, -1, 99])
def test_a_choice_outside_the_four_options_is_refused(isolated, bad):  # noqa: F811
    store, uid, sid, tid, item = _fresh()
    db = store.db
    att = quiz_flow.start_session(db, uid, sid, root_topic_id=tid, item_ids=[item])
    assert scoring.record_answer(db, uid, att["id"], item, bad, 5.0, 0) is None
    assert rows(db, att["id"])[0]["answered_at"] is None
    store.close()


# ============================================================================================ HTTP flow

@pytest.fixture()
def quiz_world(env, monkeypatch):
    """A signed-in user with a subject holding three MCQs, a running attempt, and the models switched off."""
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c, "Math"))
    store = open_db()
    db = store.db
    db.execute("INSERT INTO topics(subject_id,name,path,ordinal,origin) VALUES (?,?,?,1,'manual')", (sid, "Algebra", "Math > Algebra"))
    tid = db.execute("SELECT id FROM topics WHERE subject_id=?", (sid,)).fetchone()["id"]
    for i, (q, ans) in enumerate([("What is 2+2?", 1), ("What is 3+3?", 2), ("What is 4+4?", 3)]):
        db.execute("INSERT INTO mcq_items(subject_id,topic_id,topic_path,question,options,answer_index,explanation,quote,key,created_at) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?)", (sid, tid, "Math > Algebra", q, json.dumps(["a", "b", "c", "d"]), ans, "", "quote here", f"k{i}", time.time()))
    store.close()
    r = c.post(f"/subjects/{sid}/quiz/start", data={"topic_id": "", "csrf": session_csrf(c)})
    assert r.status_code == 303, r.text
    return SimpleNamespace(c=c, sid=sid, tid=tid, attempt=r.headers["location"].rsplit("/", 1)[1])


def page(w):
    return w.c.get(f"/subjects/{w.sid}/quiz/attempt/{w.attempt}")


def form_of(html):
    return {k: v for k, v in re.findall(r"<input type='hidden' name='(\w+)' value='([^']*)'>", html)}


def post_answer(w, fields, **over):
    data = {**fields, "chosen": "1", "response_time": "4.2", "hesitations": "0", **over}
    return w.c.post(f"/subjects/{w.sid}/quiz/attempt/{w.attempt}/answer", data=data)


def attempt_row(w):
    store = open_db()
    r = dict(store.db.execute("SELECT * FROM quiz_attempts WHERE id=?", (w.attempt,)).fetchone())
    store.close()
    return r


# ================================================================================================ page security

def events(w):
    store = open_db()
    n = store.db.execute("SELECT COUNT(*) FROM quiz_proctoring_events WHERE attempt_id=?", (w.attempt,)).fetchone()[0]
    store.close()
    return n


