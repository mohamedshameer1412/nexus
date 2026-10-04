"""StudyHub web app (Phase A1), driven through real HTTP routes with cookies. (FRONTEND HTTP test, no model.)"""
from __future__ import annotations

import re
import sqlite3

import pytest
from django_client import TestClient

from django_client import app

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

# ------------------------------------------------------------------ register and login

# ------------------------------------------------------------------------------ CSRF

# ------------------------------------------------------- sessions, logout, replay

# ---------------------------------------------------------------------------- subjects

# ------------------------------------------------------------------------------ leakage

# --------------------------------------------------------------- headers and escaping

