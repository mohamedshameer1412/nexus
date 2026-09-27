"""
Frontend route tests via FastAPI TestClient.
All tests use fixture mode - no real model needed.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from demo.study.samples import SAMPLE


@pytest.fixture(autouse=True)
def _fixture_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fixture")


@pytest.fixture()
def client():
    from web.study_ui import app
    return TestClient(app)


# ---------------------------------------------------------------- screen 1

def test_home_page_loads(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Study Pack Generator" in r.text


def test_home_page_has_textarea(client):
    r = client.get("/")
    assert "<textarea" in r.text


def test_home_page_has_generate_button(client):
    r = client.get("/")
    assert "Generate study pack" in r.text


# ---------------------------------------------------------------- api

def test_api_generate_accepts_valid_source(client):
    r = client.post("/api/generate", json={"source": SAMPLE})
    assert r.status_code == 200
    data = r.json()
    assert "run_id" in data
    assert data["state"] in ("complete", "awaiting_expert", "failed")


def test_api_generate_rejects_empty_source(client):
    r = client.post("/api/generate", json={"source": ""})
    assert r.status_code == 422
    assert r.json()["error"]


def test_api_generate_rejects_missing_body_field(client):
    r = client.post("/api/generate", json={})
    assert r.status_code == 422


def test_api_generate_includes_title(client):
    r = client.post("/api/generate", json={"source": SAMPLE, "title": "My Topic"})
    assert r.status_code == 200


def test_api_run_returns_state(client, tmp_path, monkeypatch):
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui2.db"))
    from web.study_ui import app
    with TestClient(app) as c:
        gen = c.post("/api/generate", json={"source": SAMPLE})
        run_id = gen.json()["run_id"]
        r = c.get(f"/api/run/{run_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == run_id
    assert "state" in data
    assert "summary" in data


def test_api_run_unknown_returns_404(client):
    r = client.get("/api/run/run_doesnotexist000")
    assert r.status_code == 404


# ---------------------------------------------------------------- screens 2-4

def test_run_page_unknown_run_shows_error(client):
    r = client.get("/run/run_doesnotexist000")
    assert r.status_code == 200
    assert "not found" in r.text.lower()


def test_trace_page_unknown_run_shows_error(client):
    r = client.get("/run/run_doesnotexist000/trace")
    assert r.status_code == 200
    assert "not found" in r.text.lower()


def test_revision_page_unknown_run_shows_error(client):
    r = client.get("/run/run_doesnotexist000/revision")
    assert r.status_code == 200
    assert "not found" in r.text.lower()


def test_full_flow_screens_accessible(client, tmp_path, monkeypatch):
    """After generating, all three screens load without error."""
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui3.db"))
    from web.study_ui import app
    with TestClient(app) as c:
        gen = c.post("/api/generate", json={"source": SAMPLE})
        run_id = gen.json()["run_id"]
        assert c.get(f"/run/{run_id}").status_code == 200
        assert c.get(f"/run/{run_id}/trace").status_code == 200
        assert c.get(f"/run/{run_id}/revision").status_code == 200
