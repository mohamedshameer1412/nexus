"""E-mail one-time codes: password reset, address verification, limits against guessing and flooding, the templates, the weekly summary."""
from __future__ import annotations

import re
import smtplib

import pytest

from studyhub import digest, mail_templates, mailer, otp
from studyhub.web import api as apimod
from test_studyhub_api import API, PW, Api, is_error, quiet, signed_in  # noqa: F401
from test_studyhub_web import env  # noqa: F401

NEW_PW = "another long password"


@pytest.fixture()
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send", lambda to, subject, text, html: sent.append({"to": to, "subject": subject, "text": text, "html": html}) or "sent")
    return sent


@pytest.fixture(autouse=True)
def no_cooldown(monkeypatch):
    monkeypatch.setattr(otp, "COOLDOWN", 0.0)          # the test that needs it turns it back on


def code_of(msg) -> str:
    return re.search(r"\b(\d{6})\b", msg["text"]).group(1)


def verified(name="alice", address="alice@example.com"):
    a = signed_in(name)
    a.req("PUT", "/account/email", json={"email": address})
    return a


def confirm(a, box, address="alice@example.com"):
    code = code_of([m for m in box if m["to"] == address][-1])
    r = a.req("POST", "/account/email/verify", json={"code": code})
    assert r.status_code == 200, r.text
    return r


def forgot(email, client=None):
    c = client or Api()
    return c, c.c.post(f"{API}/auth/password/forgot", json={"email": email}, headers={"X-CSRF-Token": c.csrf})


def reset(c, email, code, pw=NEW_PW):
    return c.c.post(f"{API}/auth/password/reset", json={"email": email, "code": code, "new_password": pw}, headers={"X-CSRF-Token": c.csrf})


def login_status(name, pw):
    f = Api()
    return f.c.post(f"{API}/login", json={"username": name, "password": pw}, headers={"X-CSRF-Token": f.csrf}).status_code


def test_an_address_is_verified_with_a_code_before_it_counts(env, outbox):  # noqa: F811
    a = verified()
    assert outbox[-1]["to"] == "alice@example.com" and "Verify" in outbox[-1]["subject"]
    acc = a.req("GET", "/account").json()["email"]
    assert acc["verified"] is False and acc["address"] is None and acc["pending"] == "alice@example.com"
    assert is_error(a.req("POST", "/account/email/verify", json={"code": "000000"}), 400, "invalid_code")
    confirm(a, outbox)
    acc = a.req("GET", "/account").json()["email"]
    assert acc["verified"] is True and acc["address"] == "alice@example.com"
    assert is_error(a.req("PUT", "/account/email", json={"email": "not an address"}), 400, "invalid")
    assert is_error(a.req("PUT", "/account/email", csrf=False, json={"email": "x@example.com"}), 403, "csrf")


def test_the_same_address_cannot_be_verified_by_two_accounts(env, outbox):  # noqa: F811
    a = verified("alice", "shared@example.com")
    confirm(a, outbox, "shared@example.com")
    b = verified("bob", "shared@example.com")
    r = b.req("POST", "/account/email/verify", json={"code": code_of(outbox[-1])})
    assert is_error(r, 409, "email_in_use")


def test_forgot_password_answers_the_same_for_known_and_unknown_addresses(env, outbox):  # noqa: F811
    a = verified()
    confirm(a, outbox)
    outbox.clear()
    _, known = forgot("alice@example.com")
    _, unknown = forgot("nobody@example.com")
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert [m["to"] for m in outbox] == ["alice@example.com"]                       # only the real account got a message
    assert "password reset code" in outbox[0]["subject"] and code_of(outbox[0]) in outbox[0]["html"].replace(" ", "")
    assert forgot("bad address")[1].status_code == 400
    f = Api()
    assert is_error(f.req("POST", "/auth/password/forgot", csrf=False, json={"email": "alice@example.com"}), 403, "csrf")
    assert is_error(f.req("POST", "/auth/password/reset", csrf=False, json={"email": "a@example.com", "code": "123456", "new_password": NEW_PW}), 403, "csrf")


def test_the_code_resets_the_password_once_and_signs_every_device_out(env, outbox):  # noqa: F811
    a = verified()
    confirm(a, outbox)
    other = Api()
    other.c.post(f"{API}/login", json={"username": "alice", "password": PW}, headers={"X-CSRF-Token": other.csrf})
    assert other.req("GET", "/me").status_code == 200
    outbox.clear()
    c, _ = forgot("alice@example.com")
    code = code_of(outbox[0])
    assert reset(c, "alice@example.com", code, "short").status_code == 400          # a weak password does not use up the code
    assert reset(c, "alice@example.com", code).status_code == 200
    assert reset(c, "alice@example.com", code).status_code == 400                   # single use
    assert login_status("alice", PW) == 400 and login_status("alice", NEW_PW) == 200
    assert other.req("GET", "/me").status_code == 401 and a.req("GET", "/me").status_code == 401
    assert "password was changed" in outbox[-1]["subject"] and outbox[-1]["to"] == "alice@example.com"
    assert code not in outbox[-1]["text"]


def test_a_code_dies_after_five_wrong_guesses_even_if_the_right_one_follows(env, outbox):  # noqa: F811
    a = verified()
    confirm(a, outbox)
    outbox.clear()
    c, _ = forgot("alice@example.com")
    real = code_of(outbox[0])
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(5):
        assert is_error(reset(c, "alice@example.com", wrong), 400, "invalid_code")
    assert is_error(reset(c, "alice@example.com", real), 400, "invalid_code")


def test_too_many_wrong_guesses_lock_the_address_and_the_network_address_out(env, outbox, monkeypatch):  # noqa: F811
    a = verified()
    confirm(a, outbox)
    outbox.clear()
    c, _ = forgot("alice@example.com")
    for _ in range(10):
        reset(c, "alice@example.com", "000001")
    r = reset(c, "alice@example.com", code_of(outbox[0]))
    assert is_error(r, 429, "rate_limited") and int(r.headers["retry-after"]) > 0        # even the right code is refused now
    assert "wait" in r.json()["error"]["message"]
    monkeypatch.setattr(otp, "CHECK_LIMITS", [("fail_email", 10 ** 6, 3600), ("fail_ip", 3, 900)])
    other = Api()
    for _ in range(3):
        reset(other, "someone@example.com", "000001")
    assert is_error(reset(other, "third@example.com", "000001"), 429, "rate_limited")    # guessing across many accounts from one address stops too


def test_requests_are_limited_per_address_per_network_address_and_overall(env, outbox, monkeypatch):  # noqa: F811
    for _ in range(3):
        assert forgot("flood@example.com")[1].status_code == 202
    r = forgot("flood@example.com")[1]
    assert is_error(r, 429, "rate_limited") and "Retry-After" in r.headers
    monkeypatch.setattr(otp, "REQUEST_LIMITS", [("req_email", 100, 900), ("req_ip", 7, 3600), ("req_all", 400, 3600)])
    for i in range(4):
        assert forgot(f"user{i}@example.com")[1].status_code == 202
    assert is_error(forgot("user9@example.com")[1], 429, "rate_limited")               # a mail-bombing run stops
    monkeypatch.setattr(otp, "REQUEST_LIMITS", [("req_email", 100, 900), ("req_ip", 100, 3600), ("req_all", 7, 3600)])
    assert is_error(forgot("more@example.com")[1], 429, "rate_limited")                # the overall hourly cap counts everything so far


def test_the_cooldown_stops_a_second_request_within_a_minute(env, outbox, monkeypatch):  # noqa: F811
    monkeypatch.setattr(otp, "COOLDOWN", 60.0)
    assert forgot("cool@example.com")[1].status_code == 202
    r = forgot("cool@example.com")[1]
    assert is_error(r, 429, "rate_limited") and 1 <= r.json()["error"]["retry_after"] <= 60


def test_a_new_code_cancels_the_old_one_and_the_code_is_never_stored(env, outbox):  # noqa: F811
    a = verified()
    confirm(a, outbox)
    outbox.clear()
    c, _ = forgot("alice@example.com")
    forgot("alice@example.com", c)
    first, second = code_of(outbox[0]), code_of(outbox[1])
    if first != second:
        assert is_error(reset(c, "alice@example.com", first), 400, "invalid_code")
    from studyhub.db import open_db
    store = open_db()
    rows = [dict(r) for r in store.db.execute("SELECT * FROM email_otps")]
    store.close()
    assert rows and all(second not in str(v) for r in rows for k, v in r.items() if k not in ("id", "user_id", "created_at", "expires_at", "attempts", "consumed_at"))


def test_the_client_address_behind_our_proxy_is_the_one_the_proxy_added():
    class Req:
        def __init__(self, host, xff=None):
            self.client = type("C", (), {"host": host})()
            self.headers = {"x-forwarded-for": xff} if xff else {}
    assert apimod._ip(Req("127.0.0.1", "6.6.6.6, 203.0.113.9")) == "203.0.113.9"          # the forged first entry is ignored
    assert apimod._ip(Req("127.0.0.1")) == "127.0.0.1"
    assert apimod._ip(Req("198.51.100.4", "6.6.6.6")) == "198.51.100.4"                   # not our proxy: the header is not trusted


def test_weekly_summary_needs_a_verified_address_and_is_rate_limited(env, outbox):  # noqa: F811
    a = verified()
    assert is_error(a.req("PUT", "/account/weekly", json={"enabled": True}), 400, "no_email")
    assert is_error(a.req("POST", "/account/digest/send-now"), 400, "no_email")
    confirm(a, outbox)
    assert a.req("PUT", "/account/weekly", json={"enabled": True}).json() == {"weekly": True}
    outbox.clear()
    assert a.req("POST", "/account/digest/send-now").json()["ok"] is True
    assert outbox[0]["to"] == "alice@example.com" and "Your week in Nexus" in outbox[0]["html"] and "Open Nexus" in outbox[0]["text"]
    a.req("POST", "/account/digest/send-now")
    a.req("POST", "/account/digest/send-now")
    assert is_error(a.req("POST", "/account/digest/send-now"), 429, "rate_limited")
    assert is_error(a.req("DELETE", "/account/email"), 400, "invalid")                   # the address is the login: it cannot be removed
    acc = a.req("GET", "/account").json()["email"]
    assert acc["verified"] is True and acc["weekly"] is True                              # nothing changed: the login address stays


def test_the_scheduler_sends_a_summary_only_to_opted_in_verified_users_once_a_week(env, outbox):  # noqa: F811
    a = verified()
    confirm(a, outbox)
    a.req("PUT", "/account/weekly", json={"enabled": True})
    from studyhub.db import open_db
    store = open_db()
    now = 10_000_000_000.0
    assert [u["username"] for u in digest.due_users(store.db, now)] == ["alice"]
    assert digest.send_to(store.db, digest.due_users(store.db, now)[0], now) == "sent"
    assert digest.due_users(store.db, now + 3 * 86400) == [] and [u["username"] for u in digest.due_users(store.db, now + 8 * 86400)] == ["alice"]
    b = verified("bob", "bob@example.com")                                                  # verified but opted out
    confirm(b, outbox, "bob@example.com")
    assert "bob" not in [u["username"] for u in digest.due_users(store.db, now + 30 * 86400)]
    store.close()


def test_templates_escape_everything_and_have_a_plain_text_twin():
    subject, text, html = mail_templates.otp_email("reset", "123456", 10, "20 Sep 2026, 10:00 UTC", "203.0.x.x")
    assert "1 2 3 4 5 6" in html and "123456" in text and "expires in <b>10 minutes</b>" in html and "<script" not in html
    data = {"answers": 3, "accuracy": 66, "asked": 1, "streak": 2, "due_cards": 4, "subjects": [{"name": "<script>alert(1)</script>", "confidence": 0.5}],
            "weak": [{"name": "<img src=x onerror=alert(1)>", "subject": "S", "confidence": 0.2}]}
    _, t2, h2 = mail_templates.digest_email("<b>Eve</b>", data, "http://localhost:3000")
    assert "<script>" not in h2 and "<img src=x" not in h2 and "&lt;script&gt;" in h2 and "&lt;b&gt;Eve" in h2 and "Open Nexus" in t2


def test_the_mailer_refuses_header_injection_uses_starttls_and_writes_a_debug_outbox(monkeypatch, tmp_path):
    monkeypatch.setattr(mailer, "_loaded", True)
    for k in ("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "EMAIL_PORT", "EMAIL_USE_TLS", "DEFAULT_FROM_EMAIL", "EMAIL_DEBUG"):
        monkeypatch.delenv(k, raising=False)
    assert mailer.send("a@example.com", "x\nBcc: evil@example.com", "t", "<p>h</p>") == "failed"
    assert mailer.send("a@example.com\nBcc: evil@example.com", "s", "t", "<p>h</p>") == "failed"
    assert mailer.send("a@example.com", "s", "t", "<p>h</p>") == "unconfigured"
    monkeypatch.setenv("STUDYHUB_DB", str(tmp_path / "db" / "s.db"))
    monkeypatch.setenv("EMAIL_DEBUG", "True")
    assert mailer.send("a@example.com", "s", "body", "<p>h</p>") == "outbox" and list((tmp_path / "db" / "outbox").glob("*.eml"))
    monkeypatch.delenv("EMAIL_DEBUG")
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def ehlo(self):
            calls.append("ehlo")

        def starttls(self, context=None):
            calls.append("starttls")

        def login(self, user, pw):
            calls.append(("login", user))

        def send_message(self, msg):
            calls.append(("send", msg["To"], msg["Auto-Submitted"]))

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("EMAIL_HOST", "smtp.example.com")
    monkeypatch.setenv("EMAIL_HOST_USER", "user@example.com")
    monkeypatch.setenv("EMAIL_HOST_PASSWORD", "secret")
    monkeypatch.setenv("EMAIL_PORT", "587")
    monkeypatch.setenv("EMAIL_USE_TLS", "True")
    assert mailer.send("a@example.com", "s", "t", "<p>h</p>") == "sent"
    assert ("connect", "smtp.example.com", 587) in calls and "starttls" in calls and ("send", "a@example.com", "auto-generated") in calls
    assert calls.index("starttls") < calls.index(("login", "user@example.com"))                # TLS before the password is sent
