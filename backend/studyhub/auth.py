"""Accounts, passwords, sessions, and login throttling.

  * Passwords: hashlib.scrypt with a per-user random salt; the parameters used are stored with the hash.
  * Login: an unknown username costs the same time as a wrong password, and both give the SAME message.
  * Throttling: failed attempts are counted per username and per IP in a sliding window.
  * Sessions: a random token in an HttpOnly cookie; only its SHA-256 is stored. A logout deletes the row,
    so a stolen or replayed cookie stops working server-side.

Every AuthError message is safe to show to a user.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass

from . import settings

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
MIN_PASSWORD, MAX_PASSWORD = 8, 128
MAX_FAILS_PER_USER, MAX_FAILS_PER_IP, WINDOW_SECONDS = 5, 20, 15 * 60
GENERIC_FAILURE = "Invalid username or password."
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")
_DUMMY_SALT = os.urandom(16)


class AuthError(ValueError):
    """A problem the user can be told about."""


# ------------------------------------------------------------------ passwords

def _params() -> dict:
    return {"n": settings.scrypt_n(), "r": 8, "p": 1, "dklen": 32}


def _derive(password: str, salt: bytes, params: dict) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=params["n"], r=params["r"], p=params["p"],
                          dklen=params["dklen"], maxmem=128 * params["n"] * params["r"] * 2)


def normalise_username(username: str) -> str:
    return (username or "").strip().lower()


def check_username(username: str) -> None:
    if not USERNAME_RE.match(username):
        raise AuthError("Username must be 3-32 characters: lowercase letters, digits, dot, dash or underscore, "
                        "starting with a letter or digit.")


def normalise_email(email: str) -> str:
    return (email or "").strip().lower()


def check_email(email: str) -> None:
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address.")


def check_password(password: str, username: str = "") -> None:
    if len(password or "") < MIN_PASSWORD:
        raise AuthError(f"Password must be at least {MIN_PASSWORD} characters.")
    if len(password) > MAX_PASSWORD:
        raise AuthError(f"Password must be at most {MAX_PASSWORD} characters.")
    if username and password.lower() == username.lower():
        raise AuthError("Password must not be the same as the username.")


def register(db: sqlite3.Connection, username: str, password: str, now: float | None = None, email: str | None = None) -> int:
    """Create an account and return its id. `email` is the login address (required by the web app, optional for older callers)."""
    name = normalise_username(username)
    check_username(name)
    check_password(password, name)
    address = None
    if email is not None:
        address = normalise_email(email)
        check_email(address)
        if db.execute("SELECT 1 FROM users WHERE lower(email)=?", (address,)).fetchone():
            raise AuthError("That email is already registered. Log in instead.")
    salt, params = os.urandom(16), _params()
    try:
        cur = db.execute(
            "INSERT INTO users(username, pw_salt, pw_hash, scrypt_params, created_at, email) VALUES (?,?,?,?,?,?)",
            (name, salt, _derive(password, salt, params), json.dumps(params),
             time.time() if now is None else now, address))
    except sqlite3.IntegrityError:
        raise AuthError("That username is already taken.") from None
    return int(cur.lastrowid)


def _throttled(db: sqlite3.Connection, username: str, ip: str, now: float) -> bool:
    since = now - WINDOW_SECONDS
    by_user = db.execute("SELECT COUNT(*) FROM login_attempts WHERE username=? AND at>? AND ok=0",
                         (username[:64], since)).fetchone()[0]
    by_ip = db.execute("SELECT COUNT(*) FROM login_attempts WHERE ip=? AND at>? AND ok=0",
                       (ip[:64], since)).fetchone()[0] if ip else 0
    return by_user >= MAX_FAILS_PER_USER or by_ip >= MAX_FAILS_PER_IP


def authenticate(db: sqlite3.Connection, username: str, password: str, ip: str = "",
                 now: float | None = None) -> int:
    """Return the user id, or raise AuthError. Failed attempts are recorded and throttled."""
    now = time.time() if now is None else now
    name = normalise_username(username)
    if _throttled(db, name, ip, now):
        raise AuthError("Too many failed attempts. Please wait 15 minutes and try again.")
    password = password or ""

    if "@" in name:                                          # the email address is the login; an older account without one still signs in by username
        row = db.execute("SELECT id, pw_salt, pw_hash, scrypt_params FROM users WHERE lower(email)=? ORDER BY email_verified DESC, id LIMIT 1", (name,)).fetchone()
    else:
        row = db.execute("SELECT id, pw_salt, pw_hash, scrypt_params FROM users WHERE username=?", (name,)).fetchone()
    if row is None or len(password) > MAX_PASSWORD:
        _derive(password[:MAX_PASSWORD], _DUMMY_SALT, _params())         # same cost as a real check
        ok = False
    else:
        ok = hmac.compare_digest(_derive(password, row["pw_salt"], json.loads(row["scrypt_params"])),
                                 row["pw_hash"])
    db.execute("INSERT INTO login_attempts(username, ip, at, ok) VALUES (?,?,?,?)",
               (name[:64], ip[:64], now, int(ok)))
    if not ok:
        raise AuthError(GENERIC_FAILURE)
    db.execute("DELETE FROM login_attempts WHERE username=? AND ok=0", (name[:64],))
    return int(row["id"])


def change_password(db: sqlite3.Connection, user_id: int, username: str, current: str, new: str, ip: str = "") -> None:
    """Set a new password after checking the current one (failed checks are throttled like a login)."""
    if authenticate(db, username, current, ip) != user_id:
        raise AuthError(GENERIC_FAILURE)
    check_password(new, username)
    if new == current:
        raise AuthError("Choose a different password from the current one.")
    salt, params = os.urandom(16), _params()
    db.execute("UPDATE users SET pw_salt=?, pw_hash=?, scrypt_params=? WHERE id=?", (salt, _derive(new, salt, params), json.dumps(params), user_id))


def set_password(db: sqlite3.Connection, user_id: int, username: str, new: str) -> None:
    """Set a new password without asking for the old one (only after a verified e-mail code)."""
    check_password(new, username)
    salt, params = os.urandom(16), _params()
    db.execute("UPDATE users SET pw_salt=?, pw_hash=?, scrypt_params=? WHERE id=?", (salt, _derive(new, salt, params), json.dumps(params), user_id))


# ------------------------------------------------------------------ sessions

@dataclass(frozen=True)
class Session:
    user_id: int
    csrf: str
    expires_at: float


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: sqlite3.Connection, user_id: int, now: float | None = None) -> tuple[str, Session]:
    """A NEW token every login (no session fixation). Returns (token for the cookie, session)."""
    now = time.time() if now is None else now
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    expires = now + settings.session_days() * 86400
    db.execute("INSERT INTO sessions(token_hash, user_id, csrf, created_at, expires_at) VALUES (?,?,?,?,?)",
               (_hash(token), user_id, csrf, now, expires))
    return token, Session(user_id, csrf, expires)


def get_session(db: sqlite3.Connection, token: str | None, now: float | None = None) -> Session | None:
    if not token or len(token) > 200:
        return None
    now = time.time() if now is None else now
    row = db.execute("SELECT user_id, csrf, expires_at FROM sessions WHERE token_hash=?", (_hash(token),)).fetchone()
    if row is None:
        return None
    if row["expires_at"] <= now:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (_hash(token),))
        return None
    return Session(int(row["user_id"]), row["csrf"], float(row["expires_at"]))


def delete_session(db: sqlite3.Connection, token: str | None) -> None:
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (_hash(token),))


def purge_expired(db: sqlite3.Connection, now: float | None = None) -> int:
    now = time.time() if now is None else now
    n = db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,)).rowcount
    db.execute("DELETE FROM login_attempts WHERE at<?", (now - WINDOW_SECONDS,))
    return n


def same_token(a: str | None, b: str | None) -> bool:
    """Constant-time comparison for CSRF tokens."""
    return bool(a) and bool(b) and hmac.compare_digest(a.encode(), b.encode())
