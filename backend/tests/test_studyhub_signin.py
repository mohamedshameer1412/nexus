"""Sign up and sign in with an email address (the username is a display name), the profile name, running jobs, and a friendly server error."""
from __future__ import annotations

import re

import pytest

from studyhub import auth, mailer
from studyhub import db as studydb
from studyhub.web import api as apimod
import studyhub.web.app as appmod
from test_studyhub_api import API, PW, Api, is_error, quiet, signed_in  # noqa: F401
from test_studyhub_web import env  # noqa: F401


@pytest.fixture()
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send", lambda to, subject, text, html: sent.append({"to": to, "text": text}) or "sent")
    return sent


def signup(a: Api, username="priya", email="Priya@Example.com", pw=PW):
    return a.c.post(f"{API}/register", json={"username": username, "email": email, "password": pw}, headers={"X-CSRF-Token": a.csrf})


def login(a: Api, who, pw=PW):
    return a.c.post(f"{API}/login", json={"email": who, "password": pw}, headers={"X-CSRF-Token": a.csrf})


def test_sign_up_needs_a_valid_unused_email_and_keeps_the_username(env):  # noqa: F811
    a = Api()
    assert is_error(a.c.post(f"{API}/register", json={"username": "priya", "password": PW}, headers={"X-CSRF-Token": a.csrf}), 400, "invalid")
    for bad in ("nope", "a@b", "two@@example.com", "spa ce@example.com", "x" * 260 + "@example.com"):
        assert is_error(signup(a, email=bad), 400, "invalid"), bad
    r = signup(a)
    assert r.status_code == 201 and r.json()["user"]["username"] == "priya" and r.json()["user"]["email"] == "priya@example.com"     # the address is kept in lower case
    b = Api()
    assert is_error(signup(b, username="someone", email="PRIYA@example.com"), 400, "invalid")                                  # the same address, any case, is refused
    assert "already registered" in signup(b, username="someone", email="priya@example.com").json()["error"]["message"]
    assert is_error(signup(b, username="priya", email="new@example.com"), 400, "invalid")                                       # the username is still unique
    assert signup(b, username="someone", email="new@example.com").status_code == 201


def test_sign_in_uses_the_email_in_any_case_and_an_old_username_still_works(env):  # noqa: F811
    a = Api()
    signup(a)
    for who in ("priya@example.com", "PRIYA@EXAMPLE.COM", "  priya@example.com "):
        assert login(Api(), who).status_code == 200, who
    assert login(Api(), "priya").status_code == 200                                    # accounts made before email sign-in keep working by username
    legacy = Api()
    store = studydb.open_db()
    try:
        auth.register(store.db, "olduser", PW)                                         # no email at all
    finally:
        store.close()
    assert login(legacy, "olduser").status_code == 200


def test_a_wrong_email_or_password_gives_one_generic_message_and_locks_out(env):  # noqa: F811
    a = Api()
    signup(a)
    unknown, wrong = login(Api(), "nobody@example.com"), login(Api(), "priya@example.com", "not the password")
    assert unknown.status_code == wrong.status_code == 400 and unknown.json() == wrong.json()
    assert wrong.json()["error"]["message"] == "Invalid email or password."
    b = Api()
    codes = [login(b, "priya@example.com", "still wrong").status_code for _ in range(8)]
    assert 429 in codes                                                                 # repeated failures are throttled


def test_signing_up_sends_an_address_check_code_and_does_not_block_a_new_one(env, outbox):  # noqa: F811
    a = Api()
    a.register("mira")                                                                  # the shared helper signs up with mira@example.com
    assert [m["to"] for m in outbox] == ["mira@example.com"] and re.search(r"\b\d{6}\b", outbox[0]["text"])
    acc = a.req("GET", "/account").json()["email"]
    assert acc["login"] == "mira@example.com" and acc["verified"] is False and acc["pending"] == "mira@example.com"
    assert a.req("PUT", "/account/email", json={"email": "mira@example.com"}).status_code == 200       # a fresh code straight away: no cooldown from sign-up
    assert len(outbox) == 2


def test_the_login_address_cannot_be_removed_and_the_name_can_be_changed(env):  # noqa: F811
    a = signed_in("dana")
    assert is_error(a.req("DELETE", "/account/email"), 400, "invalid")
    assert a.req("GET", "/session").json()["user"]["email"] == "dana@example.com"
    assert a.req("PUT", "/account/profile", json={"username": "Dana.K"}).json() == {"username": "dana.k"}
    assert a.req("GET", "/session").json()["user"]["username"] == "dana.k"
    for bad in ("x", "has space", "!bang", "y" * 40):
        assert is_error(a.req("PUT", "/account/profile", json={"username": bad}), 400, "invalid"), bad
    other = signed_in("eli")
    assert is_error(other.req("PUT", "/account/profile", json={"username": "dana.k"}), 409, "username_taken")
    assert is_error(a.req("PUT", "/account/profile", csrf=False, json={"username": "dana2"}), 403, "csrf")


def test_running_jobs_are_listed_for_the_owner_only(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "")
    monkeypatch.setattr(appmod, "_submit_mcq", lambda *a, **k: None)                    # the worker never runs, so the job stays pending
    a = signed_in("alice")
    sid = a.subject("Signals")
    assert a.upload(sid).status_code == 201
    assert a.req("GET", "/jobs/active").json() == {"jobs": []}
    job = a.req("POST", f"/subjects/{sid}/mcq/jobs", json={"count": 3})
    assert job.status_code == 202
    jobs = a.req("GET", "/jobs/active").json()["jobs"]
    assert [(j["id"], j["subject_id"], j["subject"], j["count"]) for j in jobs] == [(job.json()["id"], sid, "Signals", 3)]
    assert signed_in("bob").req("GET", "/jobs/active").json() == {"jobs": []}
    assert Api().c.get(f"{API}/jobs/active").status_code == 401


def test_an_unexpected_error_is_a_friendly_json_message_with_a_reference_and_a_log_line(env, monkeypatch):  # noqa: F811
    a = signed_in("alice")
    a.subject("Boom")
    monkeypatch.setattr(apimod, "_counts", lambda db, sid: 1 / 0)
    from fastapi.testclient import TestClient
    quiet_client = TestClient(appmod.app, raise_server_exceptions=False, follow_redirects=False)     # answer with the 500 instead of re-raising it
    quiet_client.cookies.update(a.c.cookies)
    r = quiet_client.get(f"{API}/subjects")
    assert r.status_code == 500 and r.json()["error"]["code"] == "server_error" and "reference" in r.json()["error"]["message"]
    ref = re.search(r"reference (\w+)", r.json()["error"]["message"]).group(1)
    log = (env.parent / "server-errors.log").read_text(encoding="utf-8")
    assert ref in log and "ZeroDivisionError" in log
