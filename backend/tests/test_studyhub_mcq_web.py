"""StudyHub multiple-choice generation through the real HTTP routes. (FRONTEND HTTP test with SCRIPTED models.)"""
from __future__ import annotations

import re
import time

import pytest
from django_client import TestClient

import studyhub.jobs as appmod
from studyhub.db import open_db
from studyhub.repo import Repo
from test_studyhub_materials_web import upload, visible  # noqa: F401
from test_studyhub_mcq import QUEUE_Q, STACK_Q, TRUTH, TREE_Q, McqModel, draft
from test_studyhub_qa import tier
from test_studyhub_qa_web import alice_ready, use_models
from test_studyhub_web import add_subject, env, new_client, session_csrf, sign_up, subject_id  # noqa: F401


@pytest.fixture(autouse=True)
def quiet(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    for k in ("OPENROUTER_API_KEY", "STUDYHUB_LOCAL_MODEL"):
        monkeypatch.delenv(k, raising=False)


# one question in each of the three topics of SAMPLE_TXT (Stacks, Queues, Trees)
TREE_IN_TREES = draft(TREE_Q["question"], TREE_Q["correct_answer"], TREE_Q["distractors"], TREE_Q["quote"], 1)


def three_topic_model():
    return McqModel([STACK_Q], [QUEUE_Q], [TREE_IN_TREES], truth=TRUTH)


def generate(c, sid, topic="", count="3", csrf=None):
    return c.post(f"/subjects/{sid}/mcq/generate",
                  data={"topic": topic, "count": count, "csrf": session_csrf(c) if csrf is None else csrf})


# ---------------------------------------------------------------------------------------------- happy path

# ------------------------------------------------------------------------------------------ honest failures

# --------------------------------------------------------------------------------------------- validation

# ------------------------------------------------------------------------------ CSRF, sign-in, ownership

# --------------------------------------------------------------------------------------------- hostile

