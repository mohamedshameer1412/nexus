"""StudyHub materials through the real HTTP routes: upload, view, search, delete, and other users. (FRONTEND HTTP test.)"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from studyhub_files import SAMPLE_TXT, encrypt_pdf, make_blank_pdf, make_docx, make_pdf
from test_studyhub_web import (add_subject, csrf_of, env, new_client, session_csrf, sign_in, sign_up,  # noqa: F401
                               subject_id)


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "uploads"))
    return tmp_path / "uploads"


def upload(client, sid, name="ds.txt", data=SAMPLE_TXT.encode(), csrf=None, ctype="application/octet-stream"):
    token = session_csrf(client) if csrf is None else csrf
    return client.post(f"/subjects/{sid}/materials", data={"csrf": token}, files={"file": (name, data, ctype)})


def alice_with_subject():
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    return c, sid


def visible(html: str) -> str:
    """The text a person sees: tags removed (search now wraps matched words in <mark>)."""
    return __import__("html").unescape(re.sub(r"<[^>]+>", "", html))


def doc_path(response) -> str:
    assert response.status_code == 303, response.text
    return response.headers["location"]


def stored_files(uploads: Path):
    return [p for p in uploads.rglob("*") if p.is_file()] if uploads.exists() else []


# --------------------------------------------------------------------------------------------- happy path

# ------------------------------------------------------------------------------------------- refusals

# --------------------------------------------------------------------------------------- other users

# ------------------------------------------------------------------------------------------- hostile input

