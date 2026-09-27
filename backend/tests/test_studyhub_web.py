"""StudyHub web app (Phase A1), driven through real HTTP routes with cookies. (FRONTEND HTTP test, no model.)"""
from __future__ import annotations

import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from studyhub.web.app import app

PW = "correct horse battery"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_DB", str(tmp_path / "web.db"))
    monkeypatch.setenv("STUDYHUB_SCRYPT_N", "1024")
    monkeypatch.delenv("STUDYHUB_COOKIE_SECURE", raising=False)
    return tmp_path / "web.db"


def new_client():
    return TestClient(app, follow_redirects=False)


def csrf_of(html: str) -> str:
    return re.search(r"name='csrf' value='([^']+)'", html).group(1)


def sign_up(client, name="alice", pw=PW):
    token = csrf_of(client.get("/register").text)
    r = client.post("/register", data={"username": name, "password": pw, "password2": pw, "csrf": token})
    assert r.status_code == 303 and r.headers["location"] == "/subjects", r.text
    return r


def sign_in(client, name="alice", pw=PW):
    token = csrf_of(client.get("/login").text)
    return client.post("/login", data={"username": name, "password": pw, "csrf": token})


def session_csrf(client) -> str:
    return csrf_of(client.get("/subjects").text)


def add_subject(client, name="Databases", description=""):
    return client.post("/subjects", data={"name": name, "description": description, "csrf": session_csrf(client)})


def subject_id(response) -> int:
    return int(response.headers["location"].rsplit("/", 1)[1])


# ------------------------------------------------------------- basics and access control

def test_health_and_home(env):
    c = new_client()
    assert c.get("/healthz").text == "ok"
    assert c.get("/").headers["location"] == "/login"
    sign_up(c)
    assert c.get("/").headers["location"] == "/subjects"


@pytest.mark.parametrize("method,path", [("get", "/subjects"), ("get", "/subjects/1"), ("post", "/subjects"),
                                         ("post", "/subjects/1/edit"), ("post", "/subjects/1/delete")])
def test_everything_private_redirects_to_login_when_signed_out(env, method, path):
    r = getattr(new_client(), method)(path)
    assert r.status_code == 303 and r.headers["location"] == "/login"


# ------------------------------------------------------------------ register and login

def test_register_creates_a_session_with_safe_cookie_flags(env):
    c = new_client()
    token = csrf_of(c.get("/register").text)
    r = c.post("/register", data={"username": "alice", "password": PW, "password2": PW, "csrf": token})
    cookie = r.headers["set-cookie"]
    assert "sh_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Your subjects" in c.get("/subjects").text and "alice" in c.get("/subjects").text


def test_the_session_cookie_is_secure_when_served_over_https(env, monkeypatch):
    monkeypatch.setenv("STUDYHUB_COOKIE_SECURE", "1")
    c = TestClient(app, base_url="https://testserver", follow_redirects=False)     # Secure cookies need https
    first = c.get("/register")
    assert "Secure" in first.headers["set-cookie"], "even the pre-login cookie is Secure"
    r = c.post("/register", data={"username": "alice", "password": PW, "password2": PW,
                                  "csrf": csrf_of(first.text)})
    assert r.status_code == 303 and "Secure" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]


@pytest.mark.parametrize("fields,message", [
    ({"username": "alice", "password": PW, "password2": PW + "x"}, "do not match"),
    ({"username": "alice", "password": "short", "password2": "short"}, "at least 8"),
    ({"username": "a b", "password": PW, "password2": PW}, "Username must be"),
])
def test_bad_registrations_explain_themselves_and_never_echo_the_password(env, fields, message):
    c = new_client()
    r = c.post("/register", data={**fields, "csrf": csrf_of(c.get("/register").text)})
    assert r.status_code == 400 and message in r.text
    assert fields["password"] not in r.text, "the password must never be sent back"
    assert "sh_session" not in r.headers.get("set-cookie", "")


def test_a_duplicate_username_is_refused(env):
    sign_up(new_client())
    other = new_client()
    token = csrf_of(other.get("/register").text)
    r = other.post("/register", data={"username": "ALICE", "password": PW, "password2": PW, "csrf": token})
    assert r.status_code == 400 and "already taken" in r.text


def test_login_works_and_a_wrong_password_gets_the_generic_message(env):
    sign_up(new_client())
    c = new_client()
    ok = sign_in(c)
    assert ok.status_code == 303 and "sh_session=" in ok.headers["set-cookie"]
    bad_pw, ghost = new_client(), new_client()
    r1, r2 = sign_in(bad_pw, "alice", "wrong-password"), sign_in(ghost, "nobody", "wrong-password")
    assert r1.status_code == r2.status_code == 400
    assert "Invalid username or password." in r1.text and "Invalid username or password." in r2.text


def test_repeated_wrong_passwords_lock_the_login(env):
    sign_up(new_client())
    c = new_client()
    for _ in range(5):
        assert "Invalid" in sign_in(c, "alice", "wrong-password").text
    r = sign_in(c, "alice", PW)
    assert r.status_code == 400 and "Too many failed attempts" in r.text


def test_there_is_no_open_redirect(env):
    sign_up(new_client())
    c = new_client()
    token = csrf_of(c.get("/login?next=http://evil.example/").text)
    r = c.post("/login?next=http://evil.example/", data={"username": "alice", "password": PW, "csrf": token})
    assert r.headers["location"] == "/subjects"


# ------------------------------------------------------------------------------ CSRF

@pytest.mark.parametrize("path,data", [
    ("/register", {"username": "mallory", "password": PW, "password2": PW}),
    ("/login", {"username": "alice", "password": PW}),
])
def test_signed_out_forms_need_their_csrf_token(env, path, data):
    sign_up(new_client())
    c = new_client()
    c.get(path)                                                     # gets the cookie, but we send no/wrong field
    assert c.post(path, data=data).status_code == 403
    assert c.post(path, data={**data, "csrf": "forged"}).status_code == 403
    assert new_client().post(path, data={**data, "csrf": "x" * 30}).status_code == 403, "no cookie at all"


def test_every_signed_in_post_needs_the_sessions_csrf_token(env):
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    for path, data in [("/subjects", {"name": "Evil"}), (f"/subjects/{sid}/edit", {"name": "Evil"}),
                       (f"/subjects/{sid}/delete", {"confirm": "yes"}), ("/logout", {})]:
        assert c.post(path, data=data).status_code == 403, path
        assert c.post(path, data={**data, "csrf": "forged"}).status_code == 403, path
    assert "Databases" in c.get(f"/subjects/{sid}").text, "nothing was changed"
    assert "Signed in as" in c.get("/subjects").text, "and the failed logout did not log us out"


def test_one_users_csrf_token_does_not_work_for_another_session(env):
    a, b = new_client(), new_client()
    sign_up(a, "alice")
    sign_up(b, "bobby")
    sid = subject_id(add_subject(a))
    assert a.post(f"/subjects/{sid}/delete", data={"confirm": "yes", "csrf": session_csrf(b)}).status_code == 403


# ------------------------------------------------------- sessions, logout, replay

def test_logout_ends_the_session_on_the_server_so_a_replayed_cookie_fails(env):
    c = new_client()
    sign_up(c)
    stolen = c.cookies.get("sh_session")
    r = c.post("/logout", data={"csrf": session_csrf(c)})
    assert r.headers["location"] == "/login"
    thief = new_client()
    thief.cookies.set("sh_session", stolen)
    assert thief.get("/subjects").headers["location"] == "/login", "the old token must be dead"


def test_an_expired_session_is_refused(env):
    c = new_client()
    sign_up(c)
    with sqlite3.connect(env) as db:
        db.execute("UPDATE sessions SET expires_at=1")
    assert c.get("/subjects").headers["location"] == "/login"


def test_each_login_issues_a_different_session_token(env):
    sign_up(new_client())
    tokens = set()
    for _ in range(3):
        c = new_client()
        sign_in(c)
        tokens.add(c.cookies.get("sh_session"))
    assert len(tokens) == 3


# ---------------------------------------------------------------------------- subjects

def test_subject_lifecycle_through_the_forms(env):
    c = new_client()
    sign_up(c)
    r = add_subject(c, "Databases", "SQL and design")
    sid = subject_id(r)
    page = c.get(f"/subjects/{sid}").text
    assert "Databases" in page and "SQL and design" in page
    e = c.post(f"/subjects/{sid}/edit", data={"name": "Database Systems", "description": "x", "csrf": session_csrf(c)})
    assert e.status_code == 303 and "Database Systems" in c.get("/subjects").text
    d = c.post(f"/subjects/{sid}/delete", data={"confirm": "yes", "csrf": session_csrf(c)})
    assert d.headers["location"] == "/subjects" and "Database Systems" not in c.get("/subjects").text


def test_deleting_needs_the_confirmation_box(env):
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    r = c.post(f"/subjects/{sid}/delete", data={"csrf": session_csrf(c)})
    assert r.status_code == 400 and "confirm" in r.text
    assert c.get(f"/subjects/{sid}").status_code == 200


def test_subject_form_errors_are_shown(env):
    c = new_client()
    sign_up(c)
    add_subject(c, "Databases")
    dup = add_subject(c, "databases")
    assert dup.status_code == 400 and "already have a subject" in dup.text
    empty = add_subject(c, "   ")
    assert empty.status_code == 400 and "Give the subject a name" in empty.text


@pytest.mark.parametrize("path", ["/subjects/abc", "/subjects/99999999999999999", "/subjects/-1", "/subjects/1.5"])
def test_malformed_and_missing_subject_ids_are_a_404_page(env, path):
    c = new_client()
    sign_up(c)
    assert c.get(path).status_code == 404 and "Not found" in c.get(path).text


# ------------------------------------------------------------------------------ leakage

def test_another_users_subject_is_a_404_on_every_route(env):
    a, b = new_client(), new_client()
    sign_up(a, "alice")
    sign_up(b, "bobby")
    sid = subject_id(add_subject(a, "Secret notes", "private words"))
    assert b.get(f"/subjects/{sid}").status_code == 404
    assert "Secret notes" not in b.get(f"/subjects/{sid}").text
    assert "Secret notes" not in b.get("/subjects").text
    edit = b.post(f"/subjects/{sid}/edit", data={"name": "hacked", "csrf": session_csrf(b)})
    dele = b.post(f"/subjects/{sid}/delete", data={"confirm": "yes", "csrf": session_csrf(b)})
    assert edit.status_code == 404 and dele.status_code == 404
    page = a.get(f"/subjects/{sid}").text
    assert "Secret notes" in page and "private words" in page, "alice's subject is intact"


def test_two_users_can_use_the_same_subject_name_independently(env):
    a, b = new_client(), new_client()
    sign_up(a, "alice")
    sign_up(b, "bobby")
    assert add_subject(a, "Databases").status_code == 303
    assert add_subject(b, "Databases").status_code == 303
    assert b.get("/subjects").text.count("Databases") == 1


# --------------------------------------------------------------- headers and escaping

def test_security_headers_are_on_every_response(env):
    c = new_client()
    for path in ["/login", "/register", "/healthz", "/nope"]:
        h = c.get(path).headers
        assert "script-src 'none'" in h["content-security-policy"] and "frame-ancestors 'none'" in h["content-security-policy"]
        assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
        assert h["cache-control"] == "no-store"



def test_the_pages_contain_no_javascript(env):
    c = new_client()
    sign_up(c)
    for path in ["/login", "/register", "/subjects"]:
        assert "<script" not in c.get(path).text.lower()


def test_user_supplied_text_is_html_escaped(env):
    c = new_client()
    sign_up(c)
    evil = "<script>alert(1)</script>"
    sid = subject_id(add_subject(c, evil, "<img src=x onerror=alert(1)>"))
    for path in ["/subjects", f"/subjects/{sid}"]:
        html = c.get(path).text
        assert evil not in html and "<img src=x" not in html
        assert "&lt;script&gt;" in html
