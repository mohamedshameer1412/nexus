"""The one place StudyHub reads configuration. Read at call time, so a test (or an operator) can change it."""
from __future__ import annotations

import os


def db_path() -> str:
    return os.environ.get("STUDYHUB_DB", "data/studyhub.db")


def cookie_secure() -> bool:
    """Set STUDYHUB_COOKIE_SECURE=1 when serving over HTTPS, so the session cookie is never sent over HTTP."""
    return os.environ.get("STUDYHUB_COOKIE_SECURE", "0") == "1"


def session_days() -> int:
    return int(os.environ.get("STUDYHUB_SESSION_DAYS", "7"))


def upload_dir() -> str:
    """Where original uploads are kept: <upload_dir>/<user id>/<sha256>. Defaults to next to the database."""
    return os.environ.get("STUDYHUB_UPLOADS") or os.path.join(os.path.dirname(db_path()) or ".", "uploads")


def max_upload_bytes() -> int:
    return int(os.environ.get("STUDYHUB_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))


def max_pages() -> int:
    return int(os.environ.get("STUDYHUB_MAX_PAGES", "1500"))


def max_subject_chars() -> int:
    """Total characters of material one subject may hold."""
    return int(os.environ.get("STUDYHUB_MAX_SUBJECT_CHARS", str(8_000_000)))


def qa_inline() -> bool:
    """Answer questions inside the request instead of in the background worker. For tests and scripts."""
    return os.environ.get("STUDYHUB_QA_INLINE", "0") == "1"


def max_pending_questions() -> int:
    return int(os.environ.get("STUDYHUB_MAX_PENDING_QUESTIONS", "2"))


def scrypt_n() -> int:
    """scrypt cost. 2**15 (32 MB, ~100 ms) by default; tests lower it for speed. Each user's hash stores the
    parameters it was made with, so changing this never locks anyone out."""
    return int(os.environ.get("STUDYHUB_SCRYPT_N", str(2 ** 15)))


def legacy_ui() -> bool:
    """The old server-rendered pages (the Next.js app replaced them). Off unless STUDYHUB_LEGACY_UI=1; the test suite keeps them on
    because much of it still exercises them."""
    default = "1" if os.environ.get("PYTEST_CURRENT_TEST") else "0"
    return os.environ.get("STUDYHUB_LEGACY_UI", default) == "1"

