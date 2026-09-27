"""StudyHub accounts: password hashing, login throttling, sessions. (UNIT - no network, no model.)"""
from __future__ import annotations

import json

import pytest

from studyhub import auth, settings
from studyhub.db import open_db

PW = "correct horse battery"


@pytest.fixture(autouse=True)
def fast_scrypt(monkeypatch):
    monkeypatch.setenv("STUDYHUB_SCRYPT_N", "1024")          # speed only; production default is checked below


@pytest.fixture()
def db(tmp_path):
    store = open_db(str(tmp_path / "auth.db"))
    yield store.db
    store.close()


# ---------------------------------------------------------------- passwords

def test_the_production_scrypt_cost_is_not_the_test_cost(monkeypatch):
    monkeypatch.delenv("STUDYHUB_SCRYPT_N")
    assert settings.scrypt_n() >= 2 ** 15


def test_passwords_are_salted_hashed_and_never_stored(db):
    a, b = auth.register(db, "alice", PW), auth.register(db, "bob", PW)
    ra, rb = (db.execute("SELECT * FROM users WHERE id=?", (i,)).fetchone() for i in (a, b))
    assert ra["pw_salt"] != rb["pw_salt"] and ra["pw_hash"] != rb["pw_hash"], "same password, different hash"
    assert PW.encode() not in ra["pw_hash"] and len(ra["pw_hash"]) == 32
    assert PW not in "".join(db.iterdump()), "the plaintext must not be anywhere in the database"
    params = json.loads(ra["scrypt_params"])
    assert params["n"] == 1024 and params["r"] == 8, "the hash records the cost it was made with"


def test_a_hash_made_with_old_parameters_still_verifies_after_the_cost_changes(db, monkeypatch):
    auth.register(db, "alice", PW)
    monkeypatch.setenv("STUDYHUB_SCRYPT_N", "2048")
    assert auth.authenticate(db, "alice", PW) > 0


@pytest.mark.parametrize("name", ["alice", "a1b", "user.name-1_x", "ALICE", "  bob  "])
def test_valid_usernames_are_accepted_and_lowercased(db, name):
    uid = auth.register(db, name, PW)
    assert db.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()[0] == name.strip().lower()


@pytest.mark.parametrize("name", ["", "ab", "a b", "-abc", "x" * 33, "alice!", "<script>", "alïce",
                                  "a'; DROP TABLE users;--", "../etc"])
def test_invalid_usernames_are_refused(db, name):
    with pytest.raises(auth.AuthError, match="Username"):
        auth.register(db, name, PW)
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_usernames_are_unique_ignoring_case(db):
    auth.register(db, "alice", PW)
    with pytest.raises(auth.AuthError, match="taken"):
        auth.register(db, "ALICE", PW)


@pytest.mark.parametrize("pw,fragment", [("short", "at least"), ("x" * 129, "at most"), ("alice", "at least"),
                                         ("alicealice", "same as the username")])
def test_weak_passwords_are_refused(db, pw, fragment):
    with pytest.raises(auth.AuthError, match=fragment):
        auth.register(db, "alice" if pw != "alicealice" else "alicealice", pw)


# -------------------------------------------------------------------- login

def test_login_succeeds_with_the_right_password_only(db):
    uid = auth.register(db, "alice", PW)
    assert auth.authenticate(db, "Alice", PW) == uid                     # case-insensitive username
    with pytest.raises(auth.AuthError):
        auth.authenticate(db, "alice", PW + "x")


def test_a_wrong_password_and_an_unknown_user_are_indistinguishable(db):
    auth.register(db, "alice", PW)
    msgs = set()
    for name, pw in [("alice", "wrong-password"), ("nobody", "wrong-password"), ("alice", ""), ("alice", "x" * 500)]:
        with pytest.raises(auth.AuthError) as e:
            auth.authenticate(db, name, pw)
        msgs.add(str(e.value))
    assert msgs == {auth.GENERIC_FAILURE}, "no username enumeration"


def test_sql_injection_in_login_is_inert(db):
    auth.register(db, "alice", PW)
    for evil in ("alice' OR '1'='1", "' OR 1=1 --", "alice'; DROP TABLE users; --"):
        with pytest.raises(auth.AuthError):
            auth.authenticate(db, evil, evil)
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


def test_repeated_failures_lock_the_account_even_against_the_right_password(db):
    auth.register(db, "alice", PW)
    for _ in range(auth.MAX_FAILS_PER_USER):
        with pytest.raises(auth.AuthError, match="Invalid"):
            auth.authenticate(db, "alice", "wrong-password", ip="1.1.1.1", now=1000)
    with pytest.raises(auth.AuthError, match="Too many"):
        auth.authenticate(db, "alice", PW, ip="2.2.2.2", now=1000 + 60)
    assert auth.authenticate(db, "alice", PW, ip="2.2.2.2", now=1000 + auth.WINDOW_SECONDS + 1) > 0, \
        "the lock expires"


def test_a_successful_login_clears_the_failure_count(db):
    auth.register(db, "alice", PW)
    for _ in range(3):
        with pytest.raises(auth.AuthError):
            auth.authenticate(db, "alice", "nope-nope", now=1000)
    assert auth.authenticate(db, "alice", PW, now=1001) > 0
    for _ in range(auth.MAX_FAILS_PER_USER - 1):
        with pytest.raises(auth.AuthError, match="Invalid"):
            auth.authenticate(db, "alice", "nope-nope", now=1002)          # still allowed: counter was cleared


def test_one_ip_guessing_many_usernames_is_throttled(db):
    for i in range(auth.MAX_FAILS_PER_IP):
        with pytest.raises(auth.AuthError, match="Invalid"):
            auth.authenticate(db, f"user{i:03d}", "guess-guess", ip="9.9.9.9", now=1000)
    with pytest.raises(auth.AuthError, match="Too many"):
        auth.authenticate(db, "brand-new-name", "guess-guess", ip="9.9.9.9", now=1001)
    with pytest.raises(auth.AuthError, match="Invalid"):                     # another IP is unaffected
        auth.authenticate(db, "brand-new-name", "guess-guess", ip="8.8.8.8", now=1001)


# ----------------------------------------------------------------- sessions

def test_only_a_hash_of_the_session_token_is_stored(db):
    uid = auth.register(db, "alice", PW)
    token, session = auth.create_session(db, uid)
    stored = db.execute("SELECT token_hash FROM sessions").fetchone()[0]
    assert stored != token and len(stored) == 64 and token not in "".join(db.iterdump())
    assert auth.get_session(db, token) == session


def test_every_login_gets_a_new_token_and_csrf(db):
    uid = auth.register(db, "alice", PW)
    (t1, s1), (t2, s2) = auth.create_session(db, uid), auth.create_session(db, uid)
    assert t1 != t2 and s1.csrf != s2.csrf


def test_sessions_expire_and_are_deleted(db):
    uid = auth.register(db, "alice", PW)
    token, session = auth.create_session(db, uid, now=1000)
    assert auth.get_session(db, token, now=session.expires_at - 1) is not None
    assert auth.get_session(db, token, now=session.expires_at + 1) is None
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_logout_kills_the_session_server_side(db):
    uid = auth.register(db, "alice", PW)
    token, _ = auth.create_session(db, uid)
    auth.delete_session(db, token)
    assert auth.get_session(db, token) is None, "a replayed cookie must not work"


@pytest.mark.parametrize("token", [None, "", "not-a-token", "x" * 500])
def test_garbage_tokens_are_rejected(db, token):
    assert auth.get_session(db, token) is None


def test_purge_removes_only_expired_sessions(db):
    uid = auth.register(db, "alice", PW)
    old, _ = auth.create_session(db, uid, now=1000)
    fresh, _ = auth.create_session(db, uid)
    assert auth.purge_expired(db, now=1000 + 8 * 86400) == 1
    assert auth.get_session(db, old) is None and auth.get_session(db, fresh) is not None


def test_csrf_tokens_compare_safely():
    assert auth.same_token("abc", "abc")
    assert not auth.same_token("abc", "abd") and not auth.same_token("abc", None)
    assert not auth.same_token(None, None) and not auth.same_token("", "")
