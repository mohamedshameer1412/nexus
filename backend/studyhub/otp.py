"""One-time codes by e-mail (password reset, e-mail verification) with limits against guessing and against mail-bombing.

Codes: 6 digits from `secrets`, valid 10 minutes, single use, only ONE live code per address and purpose (a new request cancels the old).
Storage: an HMAC of the code with a server-side key and a per-code salt. The code itself is never stored or logged.
Guessing: 5 wrong tries kill a code; wrong tries are also counted per address and per network address, and past the limit every check
is refused for a while, even with the right code.
Mail-bombing / flooding: requests are limited per address (with a cooldown), per network address, and overall per hour.
Refusals say only how long to wait. Counters live in the database, so they survive restarts and are shared by all workers.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path

CODE_LEN = 6
TTL = 600.0
MAX_TRIES = 5

# (kind, key scope, max events, window seconds)
REQUEST_LIMITS = [("req_email", 3, 900), ("req_email", 6, 86400), ("req_ip", 10, 3600), ("req_all", 400, 3600)]
COOLDOWN = 60.0
CHECK_LIMITS = [("fail_email", 10, 3600), ("fail_ip", 20, 900)]


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        super().__init__("rate limited")
        self.retry_after = max(1, int(retry_after))


def _secret() -> bytes:
    env = os.environ.get("STUDYHUB_OTP_KEY")
    if env:
        return env.encode()
    path = Path(os.environ.get("STUDYHUB_DB", "data/studyhub.db")).parent / "otp.key"
    try:
        return path.read_bytes()
    except OSError:
        path.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        try:
            with open(path, "xb") as f:
                f.write(key)
            return key
        except FileExistsError:
            return path.read_bytes()


def _mac(code: str, salt: bytes, email: str, purpose: str) -> str:
    return hmac.new(_secret(), salt + f"|{purpose}|{email}|{code}".encode(), hashlib.sha256).hexdigest()


def _events(db: sqlite3.Connection, kind: str, key: str, window: float, now: float) -> list[float]:
    return [r[0] for r in db.execute("SELECT at FROM security_events WHERE kind=? AND key=? AND at>? ORDER BY at", (kind, key, now - window))]


def _note(db: sqlite3.Connection, kind: str, key: str, now: float) -> None:
    db.execute("INSERT INTO security_events(kind, key, at) VALUES (?,?,?)", (kind, key, now))


def _guard(db, limits, keys: dict[str, str], now: float) -> None:
    for kind, maximum, window in limits:
        seen = _events(db, kind, keys.get(kind, "*"), window, now)
        if len(seen) >= maximum:
            raise RateLimited(seen[-maximum] + window - now)


def purge(db: sqlite3.Connection, now: float | None = None) -> None:
    now = time.time() if now is None else now
    db.execute("DELETE FROM security_events WHERE at<?", (now - 2 * 86400,))
    db.execute("DELETE FROM email_otps WHERE created_at<?", (now - 2 * 86400,))


def throttle_request(db: sqlite3.Connection, email: str, ip: str, now: float | None = None) -> None:
    """Count one request and refuse it when a limit is reached. Called for every request, whether or not the address is known,
    so the answer never reveals which addresses have accounts."""
    now = time.time() if now is None else now
    keys = {"req_email": email, "req_ip": ip or "?", "req_all": "*"}
    last = _events(db, "req_email", email, COOLDOWN, now)
    if last:
        raise RateLimited(last[-1] + COOLDOWN - now)
    _guard(db, REQUEST_LIMITS, keys, now)
    for kind, key in keys.items():
        _note(db, kind, key, now)
    if secrets.randbelow(50) == 0:
        purge(db, now)


def throttle_signup(db: sqlite3.Connection, ip: str, now: float | None = None) -> None:
    """The address-check code sent when an account is created: limited per network address and overall, but it does not start the per-address
    cooldown, so the student can ask for another code straight away if the first one goes astray."""
    now = time.time() if now is None else now
    keys = {"req_ip": ip or "?", "req_all": "*"}
    _guard(db, REQUEST_LIMITS, keys, now)
    for kind, key in keys.items():
        _note(db, kind, key, now)


def issue(db: sqlite3.Connection, purpose: str, email: str, user_id: int | None, ip: str, now: float | None = None) -> str:
    """A new code for this address and purpose; any earlier live code stops working."""
    now = time.time() if now is None else now
    code = "".join(str(secrets.randbelow(10)) for _ in range(CODE_LEN))
    salt = secrets.token_bytes(16)
    db.execute("UPDATE email_otps SET consumed_at=? WHERE email=? AND purpose=? AND consumed_at IS NULL", (now, email, purpose))
    db.execute("INSERT INTO email_otps(purpose, user_id, email, code_hash, salt, created_at, expires_at, ip) VALUES (?,?,?,?,?,?,?,?)",
               (purpose, user_id, email, _mac(code, salt, email, purpose), salt, now, now + TTL, ip[:64]))
    return code


def check(db: sqlite3.Connection, purpose: str, email: str, code: str, ip: str, now: float | None = None, user_id: int | None = None) -> dict | None:
    """The code's row if it is right, unused and not expired (it is then used up); otherwise None. Raises RateLimited when too many
    wrong tries were made for this address or from this network address."""
    now = time.time() if now is None else now
    _guard(db, CHECK_LIMITS, {"fail_email": email, "fail_ip": ip or "?"}, now)
    code = (code or "").strip()
    q = ("SELECT * FROM email_otps WHERE email=? AND purpose=? AND consumed_at IS NULL AND expires_at>? "
         + ("AND user_id=? " if user_id is not None else "") + "ORDER BY id DESC LIMIT 1")
    row = db.execute(q, (email, purpose, now) + ((user_id,) if user_id is not None else ())).fetchone()
    salt = row["salt"] if row else b"\0" * 16
    good = hmac.compare_digest(_mac(code if code.isdigit() and len(code) == CODE_LEN else "x", salt, email, purpose), row["code_hash"] if row else "0" * 64)
    if row is not None and good and row["attempts"] < MAX_TRIES:
        db.execute("UPDATE email_otps SET consumed_at=? WHERE id=?", (now, row["id"]))
        return dict(row)
    _note(db, "fail_email", email, now)
    _note(db, "fail_ip", ip or "?", now)
    if row is not None:
        tries = row["attempts"] + 1
        db.execute("UPDATE email_otps SET attempts=?, consumed_at=CASE WHEN ?>=? THEN ? ELSE consumed_at END WHERE id=?", (tries, tries, MAX_TRIES, now, row["id"]))
    return None
