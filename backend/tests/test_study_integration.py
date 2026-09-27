"""
Integration tests for the study domain.
Full flow end-to-end using Scripted fixtures and the FastAPI TestClient.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from demo.study.flow import MAX_REVISIONS, build_flow
from demo.study.samples import SAMPLE
from demo.study.stub import SCENARIOS, Scripted, V1, V2, audit_v1, never_right, ok_audit
from slice import runner
from slice.config import settings as load_settings
from slice.llm import ModelError
from slice.records import RunState
from slice.store import Store


def _run(tmp_path, call, source=SAMPLE):
    store = Store(str(tmp_path / "t.db"))
    run_id = store.create_run("study")
    store.append(run_id, "input", {"text": source}, produced_by="test")
    final = runner.advance(store, run_id, build_flow(call=call), load_settings())
    return store, run_id, final


# ================================================================ flow integration

def test_clean_flow_completes(tmp_path):
    _, factory = SCENARIOS["clean"]
    _, _, final = _run(tmp_path, factory())
    assert final is RunState.COMPLETE


def test_revise_flow_completes_after_rejection(tmp_path):
    _, factory = SCENARIOS["revise"]
    store, run_id, final = _run(tmp_path, factory())
    assert final is RunState.COMPLETE
    assert len(store.history(run_id, "draft")) == 2
    verdicts = [v.payload["status"] for v in store.history(run_id, "verdict")]
    assert verdicts == ["REJECTED", "APPROVED"]


def test_stuck_flow_escalates_to_human_review(tmp_path):
    _, factory = SCENARIOS["stuck"]
    store, run_id, final = _run(tmp_path, factory())
    assert final is RunState.AWAITING_EXPERT
    escalation = store.latest(run_id, "escalation")
    assert escalation is not None
    assert escalation["reason"] == "max_revisions"


def test_repeat_flow_escalates(tmp_path):
    _, factory = SCENARIOS["repeat"]
    store, run_id, final = _run(tmp_path, factory())
    assert final is RunState.AWAITING_EXPERT
    escalation = store.latest(run_id, "escalation")
    assert escalation is not None
    assert escalation["reason"] == "repeated_output"


def test_persistence_across_store_reopen(tmp_path):
    """Run data survives closing and reopening the store."""
    _, factory = SCENARIOS["stuck"]
    call = factory()
    db = str(tmp_path / "t.db")

    # First advance: run to AWAITING_EXPERT
    s1 = Store(db)
    run_id = s1.create_run("study")
    s1.append(run_id, "input", {"text": SAMPLE}, produced_by="test")
    final1 = runner.advance(s1, run_id, build_flow(call=call), load_settings())
    assert final1 is RunState.AWAITING_EXPERT
    draft_count = len(s1.history(run_id, "draft"))
    s1.close()

    # Reopen - state and records must persist exactly
    s2 = Store(db)
    assert s2.get_state(run_id) is RunState.AWAITING_EXPERT
    assert len(s2.history(run_id, "draft")) == draft_count
    escalation = s2.latest(run_id, "escalation")
    assert escalation is not None, "escalation record must persist"


def test_model_error_is_recorded_not_raised(tmp_path):
    """A ModelError from the provider fails the run cleanly."""
    call = Scripted(generate=[ModelError("network failure")], audit=[])
    store, run_id, final = _run(tmp_path, call)
    assert final is RunState.FAILED
    failure = store.latest(run_id, "failure")
    assert failure is not None
    assert "network failure" in failure["detail"] or failure["kind"] in ("model", "no_handler", "max_steps", "unexpected_error")


# ================================================================ API integration

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient wired to a temp DB and a fixture provider."""
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    from web.study_ui import app
    return TestClient(app)


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Study Pack Generator" in r.text


def test_generate_api_creates_run(client, tmp_path, monkeypatch):
    """POST /api/generate returns a run_id and a state."""
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    from web.study_ui import app
    with TestClient(app) as c:
        r = c.post("/api/generate", json={"source": SAMPLE, "title": "Test"})
    assert r.status_code == 200
    data = r.json()
    assert "run_id" in data
    assert "state" in data


def test_generate_api_rejects_empty_source(client):
    r = client.post("/api/generate", json={"source": ""})
    assert r.status_code == 422
    assert "error" in r.json()


def test_run_page_returns_200_for_valid_run(client, tmp_path, monkeypatch):
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    from web.study_ui import app
    with TestClient(app) as c:
        gen = c.post("/api/generate", json={"source": SAMPLE})
        run_id = gen.json()["run_id"]
        r = c.get(f"/run/{run_id}")
    assert r.status_code == 200


def test_trace_page_returns_200_for_valid_run(client, tmp_path, monkeypatch):
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    from web.study_ui import app
    with TestClient(app) as c:
        gen = c.post("/api/generate", json={"source": SAMPLE})
        run_id = gen.json()["run_id"]
        r = c.get(f"/run/{run_id}/trace")
    assert r.status_code == 200
    assert "Execution Trace" in r.text


def test_revision_page_returns_200_for_valid_run(client, tmp_path, monkeypatch):
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    from web.study_ui import app
    with TestClient(app) as c:
        gen = c.post("/api/generate", json={"source": SAMPLE})
        run_id = gen.json()["run_id"]
        r = c.get(f"/run/{run_id}/revision")
    assert r.status_code == 200


def test_run_page_404_for_unknown_run(client):
    r = client.get("/run/run_doesnotexist")
    assert r.status_code == 200     # server-rendered, shows error page
    assert "not found" in r.text.lower()


def test_api_run_404_for_unknown(client):
    r = client.get("/api/run/run_doesnotexist")
    assert r.status_code == 404
