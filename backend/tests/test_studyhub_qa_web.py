"""StudyHub Q&A through the real HTTP routes. (FRONTEND HTTP test with SCRIPTED models: no network, no real model.)"""
from __future__ import annotations

import re
import time

import pytest
from django_client import TestClient

import studyhub.jobs as appmod
from slice.providers import ProviderTimeout
from studyhub.citations import Answer, Citation, Claim
from studyhub.db import open_db
from studyhub.repo import Repo
from studyhub_files import SAMPLE_TXT, make_pdf
from test_studyhub_materials_web import doc_path, stored_files, upload, visible  # noqa: F401
from test_studyhub_qa import GOOD, Q_ENQ, Scripted, tier
from test_studyhub_web import add_subject, env, new_client, session_csrf, sign_up, subject_id  # noqa: F401

QUESTION = "how does the enqueue operation work in a queue"


@pytest.fixture(autouse=True)
def quiet(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    for k in ("OPENROUTER_API_KEY", "STUDYHUB_LOCAL_MODEL"):
        monkeypatch.delenv(k, raising=False)


def use_models(monkeypatch, *tiers, notes=()):
    """Make the app answer with these scripted tiers."""
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: (list(tiers), list(notes)))


def alice_ready(text=SAMPLE_TXT.encode(), name="ds.txt"):
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    upload(c, sid, name, text)
    return c, sid


def ask(c, sid, q=QUESTION, csrf=None):
    return c.post(f"/subjects/{sid}/ask", data={"question": q, "csrf": session_csrf(c) if csrf is None else csrf})


# ------------------------------------------------------------------------------------------ answered

# ------------------------------------------------------------------------------- not answered, honestly

# -------------------------------------------------------------------------------------- background worker

# ------------------------------------------------------------------------------------------- validation

# ---------------------------------------------------------------------------------------------- hostile

# ---------------------------------------------------------------------------------------------- ownership

# ------------------------------------------------------------------------------------ feedback / delete

# ------------------------------------------------------------------------------------------------ account

# ------------------------------------------------------------------------------------------------ search

