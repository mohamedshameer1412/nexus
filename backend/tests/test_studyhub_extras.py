"""Account controls, saved answers, flashcards, search across subjects, exports, streak. Ownership and confirmation rules."""
from __future__ import annotations

import json

import studyhub.web.app as appmod
from studyhub import cards
from test_studyhub_api import API, PW, Api, is_error, quiet, signed_in, use_models  # noqa: F401
from test_studyhub_api_quiz import answer_all, seed, start  # noqa: F401
from test_studyhub_web import env  # noqa: F401


def login(name, pw):
    fresh = Api()
    r = fresh.c.post(f"{API}/login", json={"username": name, "password": pw}, headers={"X-CSRF-Token": fresh.csrf})
    return r.status_code


def test_changing_the_password_needs_the_current_one_and_signs_other_devices_out(env):  # noqa: F811
    a = signed_in("alice")
    other = Api()
    other.c.post(f"{API}/login", json={"username": "alice", "password": PW}, headers={"X-CSRF-Token": other.csrf})
    assert other.req("GET", "/me").status_code == 200
    assert is_error(a.req("POST", "/account/password", json={"current": "nope nope nope", "new": "another long password"}), 400, "wrong_password")
    assert is_error(a.req("POST", "/account/password", json={"current": PW, "new": "short"}), 400, "invalid")
    assert is_error(a.req("POST", "/account/password", json={"current": PW, "new": PW}), 400, "invalid")
    assert is_error(a.req("POST", "/account/password", csrf=False, json={"current": PW, "new": "another long password"}), 403, "csrf")
    assert a.req("POST", "/account/password", json={"current": PW, "new": "another long password"}).status_code == 200
    assert a.req("GET", "/me").status_code == 200                                # this device stays signed in
    assert other.req("GET", "/me").status_code == 401                            # the other one does not
    assert login("alice", PW) == 400 and login("alice", "another long password") == 200


def test_the_data_export_has_only_the_users_own_data(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    assert is_error(Api().req("GET", "/account/export"), 401, "unauthenticated")
    a = signed_in("alice")
    sid = a.subject("Mine")
    a.upload(sid)
    b = signed_in("bob")
    b.subject("Secret")
    r = a.req("GET", "/account/export")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = json.loads(r.text)
    assert data["account"]["username"] == "alice" and [s["name"] for s in data["subjects"]] == ["Mine"]
    assert data["subjects"][0]["documents"][0]["passages"] and "Secret" not in r.text and "pw_hash" not in r.text


def test_deleting_the_account_needs_the_password_and_the_word_and_removes_everything(env, monkeypatch):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Mine")
    a.upload(sid)
    b = signed_in("bob")
    bsid = b.subject("Bobs")
    assert is_error(a.req("POST", "/account/delete", json={"password": PW, "confirm": "delete"}), 400, "invalid")
    assert is_error(a.req("POST", "/account/delete", json={"password": "wrong wrong wrong", "confirm": "DELETE"}), 400, "wrong_password")
    assert is_error(a.req("POST", "/account/delete", csrf=False, json={"password": PW, "confirm": "DELETE"}), 403, "csrf")
    assert a.req("GET", "/me").status_code == 200
    assert a.req("POST", "/account/delete", json={"password": PW, "confirm": "DELETE"}).status_code == 204
    assert a.req("GET", "/me").status_code == 401 and login("alice", PW) == 400
    assert b.req("GET", f"/subjects/{bsid}").status_code == 200                  # nobody else is touched


def test_saved_answers_belong_to_their_owner(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    use_models(monkeypatch)                                                     # no model: never reach out to a real one in a test
    a = signed_in("alice")
    sid = a.subject("Mine")
    a.upload(sid)
    qid = a.req("POST", f"/subjects/{sid}/questions", json={"question": "how does the enqueue operation work in a queue"}).json()["id"]
    assert a.req("GET", "/saved").json()["saved"] == []
    assert a.req("PUT", f"/subjects/{sid}/questions/{qid}/saved", json={"saved": True}).json() == {"saved": True}
    assert [x["id"] for x in a.req("GET", "/saved").json()["saved"]] == [qid]
    assert a.req("GET", f"/subjects/{sid}/questions/{qid}").json()["saved"] is True
    b = signed_in("bob")
    assert b.req("GET", "/saved").json()["saved"] == []
    assert is_error(b.req("PUT", f"/subjects/{sid}/questions/{qid}/saved", json={"saved": True}), 404, "not_found")
    assert is_error(a.req("PUT", f"/subjects/{sid}/questions/{qid}/saved", csrf=False, json={"saved": False}), 403, "csrf")
    a.req("PUT", f"/subjects/{sid}/questions/{qid}/saved", json={"saved": False})
    assert a.req("GET", "/saved").json()["saved"] == []


def test_spaced_repetition_schedules_later_when_known_and_soon_when_missed():
    now = 1_000_000.0
    first = cards.schedule(2.5, 0, 0, 0, "good", now)
    second = cards.schedule(first["ease"], first["interval_days"], first["reps"], 0, "good", now)
    third = cards.schedule(second["ease"], second["interval_days"], second["reps"], 0, "good", now)
    assert first["interval_days"] == 1 and second["interval_days"] == 3 and third["interval_days"] > 7           # gaps grow
    missed = cards.schedule(third["ease"], third["interval_days"], third["reps"], 0, "again", now)
    assert missed["due"] == now + 600 and missed["reps"] == 0 and missed["lapses"] == 1 and missed["ease"] < third["ease"]
    assert cards.schedule(2.5, 3, 2, 0, "easy", now)["interval_days"] > cards.schedule(2.5, 3, 2, 0, "hard", now)["interval_days"]


def test_flashcards_come_back_by_their_schedule_and_only_for_the_owner(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    a = signed_in("alice")
    sid = a.subject("Math")
    seed(sid)
    d = a.req("GET", f"/subjects/{sid}/flashcards").json()
    assert d["total"] == 3 and d["due"] == 0 and len(d["cards"]) == 3 and all(c["is_new"] for c in d["cards"])
    assert "answer_index" not in json.dumps(d)
    first = d["cards"][0]["item_id"]
    assert a.req("POST", f"/subjects/{sid}/flashcards/{first}/review", json={"grade": "good"}).status_code == 200
    d = a.req("GET", f"/subjects/{sid}/flashcards").json()
    assert [c["item_id"] for c in d["cards"]].count(first) == 0 and d["next_due"]         # not due again for a day
    a.req("POST", f"/subjects/{sid}/flashcards/{first}/review", json={"grade": "again"})
    assert is_error(a.req("POST", f"/subjects/{sid}/flashcards/{first}/review", json={"grade": "meh"}), 400, "invalid")
    assert is_error(a.req("POST", f"/subjects/{sid}/flashcards/99999/review", json={"grade": "good"}), 404, "not_found")
    assert is_error(a.req("POST", f"/subjects/{sid}/flashcards/{first}/review", csrf=False, json={"grade": "good"}), 403, "csrf")
    b = signed_in("bob")
    assert is_error(b.req("GET", f"/subjects/{sid}/flashcards"), 404, "not_found")
    assert is_error(b.req("POST", f"/subjects/{b.subject('Mine')}/flashcards/{first}/review", json={"grade": "good"}), 404, "not_found")


def test_search_across_subjects_finds_only_the_users_own_passages(env, monkeypatch):  # noqa: F811
    a = signed_in("alice")
    a.upload(a.subject("Data Structures"))
    a.upload(a.subject("Second"), name="other.txt", data=b"The enqueue operation adds an element at the rear of a queue.")
    r = a.req("GET", "/search", params={"q": "enqueue operation queue"}).json()
    assert {x["subject"] for x in r["results"]} == {"Data Structures", "Second"} and r["results"][0]["matched"]
    assert a.req("GET", "/search", params={"q": ""}).json()["results"] == []
    b = signed_in("bob")
    assert b.req("GET", "/search", params={"q": "enqueue operation queue"}).json()["results"] == []
    assert is_error(Api().req("GET", "/search", params={"q": "queue"}), 401, "unauthenticated")


def test_practice_questions_export_csv_and_a_quiz_can_be_ended_early(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    a = signed_in("alice")
    sid = a.subject("Math")
    seed(sid)
    csv = a.req("GET", f"/subjects/{sid}/mcq.csv")
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv") and "Question 0?" in csv.text and ",B," in csv.text
    b = signed_in("bob")
    assert is_error(b.req("GET", f"/subjects/{sid}/mcq.csv"), 404, "not_found")
    aid = start(a, sid)
    assert is_error(b.req("POST", f"/subjects/{b.subject('Mine')}/quiz/attempts/{aid}/finish"), 404, "not_found")
    assert a.req("POST", f"/subjects/{sid}/quiz/attempts/{aid}/finish").status_code == 200
    assert a.req("GET", f"/subjects/{sid}/quiz/attempts/{aid}").json()["state"] == "complete"


def test_the_dashboard_counts_a_study_streak_and_todays_answers(env, monkeypatch):  # noqa: F811
    monkeypatch.setattr(appmod, "_get_provider", lambda user, db: None)
    a = signed_in("alice")
    sid = a.subject("Math")
    seed(sid)
    assert a.req("GET", "/dashboard").json()["streak"] == {"days": 0, "today": 0, "goal": 10}
    answer_all(a, sid, start(a, sid))
    assert a.req("GET", "/dashboard").json()["streak"] == {"days": 1, "today": 3, "goal": 10}
