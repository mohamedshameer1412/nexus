"""The weekly summary e-mail: what the student did in the last 7 days, from their own records only, sent once a week to a verified
address they opted in with. The scheduler is one background thread started with the app."""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time

from . import cards, insights, mail_templates, mailer
from .repo import Repo

log = logging.getLogger("nexus.digest")
WEEK = 7 * 86400.0


def build(db: sqlite3.Connection, user_id: int, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    since = now - WEEK
    one = lambda sql, *a: db.execute(sql, a).fetchone()[0]                           # noqa: E731
    correct = one("SELECT COALESCE(SUM(aa.is_correct),0) FROM attempt_answers aa JOIN quiz_attempts a ON a.id=aa.attempt_id WHERE a.user_id=? AND aa.is_correct IS NOT NULL AND aa.answered_at>=?", user_id, since)
    answers = one("SELECT COUNT(*) FROM attempt_answers aa JOIN quiz_attempts a ON a.id=aa.attempt_id WHERE a.user_id=? AND aa.is_correct IS NOT NULL AND aa.answered_at>=?", user_id, since)
    asked = one("SELECT COUNT(*) FROM doubts WHERE user_id=? AND created_at>=?", user_id, since)
    days = {r[0] for r in db.execute("SELECT date(created_at,'unixepoch') FROM doubts WHERE user_id=? AND created_at>=?", (user_id, now - 60 * 86400))}
    days |= {r[0] for r in db.execute("SELECT date(aa.answered_at,'unixepoch') FROM attempt_answers aa JOIN quiz_attempts a ON a.id=aa.attempt_id WHERE a.user_id=? AND aa.chosen_index IS NOT NULL AND aa.answered_at>=?", (user_id, now - 60 * 86400))}
    day, streak = int(now // 86400), 0
    fmt = lambda n: time.strftime("%Y-%m-%d", time.gmtime(n * 86400))              # noqa: E731
    if fmt(day) not in days:
        day -= 1
    while fmt(day) in days and streak <= 60:
        streak, day = streak + 1, day - 1
    repo = Repo(db)
    subjects, weak, due = [], [], 0
    for s in repo.list_subjects(user_id):
        conf = insights.topic_confidence(db, user_id, s["id"])
        subjects.append({"name": s["name"], "confidence": conf["overall"]["confidence"] if conf["overall"] else None})
        names = {t["id"]: t["name"] for t in repo.list_topics(user_id, s["id"])}
        weak += [{"name": names[t], "subject": s["name"], "confidence": e["confidence"]} for t, e in conf["topics"].items() if t in names and e["label"] == "shaky"]
        due += cards.due_cards(db, user_id, s["id"], now)["due"]
    weak.sort(key=lambda w: w["confidence"])
    return {"answers": answers, "accuracy": round(100 * correct / answers) if answers else 0, "asked": asked, "streak": streak,
            "subjects": subjects[:6], "weak": weak[:3], "due_cards": due}


def send_to(db: sqlite3.Connection, user: dict, now: float | None = None) -> str:
    """Build and send this user's summary. Returns the mailer's status ("sent", "outbox", "unconfigured", "failed")."""
    now = time.time() if now is None else now
    subject, text, html = mail_templates.digest_email(user["username"], build(db, user["id"], now), mailer.public_url())
    status = mailer.send(user["email"], subject, text, html)
    if status in ("sent", "outbox"):
        db.execute("UPDATE users SET last_digest_at=? WHERE id=?", (now, user["id"]))
    return status


def due_users(db: sqlite3.Connection, now: float | None = None) -> list[dict]:
    now = time.time() if now is None else now
    rows = db.execute(
        "SELECT id, username, email FROM users WHERE weekly_email=1 AND email_verified=1 AND email IS NOT NULL "
        "AND COALESCE(last_digest_at, created_at) <= ?", (now - WEEK,)).fetchall()
    return [dict(r) for r in rows]


def run_once(now: float | None = None) -> int:
    from . import db as studydb
    store = studydb.open_db()
    sent = 0
    try:
        for u in due_users(store.db, now):
            if send_to(store.db, u, now) in ("sent", "outbox"):
                sent += 1
    finally:
        store.close()
    return sent


def start_scheduler(interval: float = 1800.0) -> threading.Thread | None:
    """One daemon thread that looks for due summaries every 30 minutes. Off under tests or with STUDYHUB_SCHEDULER=off."""
    if os.environ.get("STUDYHUB_SCHEDULER", "on") == "off" or os.environ.get("PYTEST_CURRENT_TEST"):
        return None

    def loop():
        while True:
            try:
                run_once()
            except Exception as e:                # never let the thread die
                log.warning("weekly summary run failed: %s", type(e).__name__)
            time.sleep(interval)

    t = threading.Thread(target=loop, name="nexus-digest", daemon=True)
    t.start()
    return t
