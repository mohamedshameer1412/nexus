"""The CLI, in-process, on scripted replies. No key, no network."""
from __future__ import annotations

import re

import pytest

from scripts import study
from slice.records import RunState
from slice.store import Store


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.chdir("/")            # so a stray .env in the cwd cannot leak a key in


def cli(tmp_path, capsys, *argv):
    code = study.main(["--db", str(tmp_path / "cli.db"), *argv])
    return code, capsys.readouterr().out


def run_id(out):
    return re.search(r"run (run_\w+)", out).group(1)


def test_the_default_stub_run_shows_the_whole_arc(tmp_path, capsys):
    code, out = cli(tmp_path, capsys, "run", "--stub")
    assert code == 0
    for needle in ("mode: stub:revise (scripted replies - no model is called)", "DRAFT 1",
                   "VALIDATOR  REJECTED", "DRAFT 2  (revision 1)", "VALIDATOR  APPROVED",
                   "path    drafting -> gating -> drafting -> gating -> complete"):
        assert needle in out, needle


def test_a_run_that_needs_a_human_exits_3_and_can_be_reviewed(tmp_path, capsys):
    code, out = cli(tmp_path, capsys, "run", "--stub", "--scenario", "stuck")
    assert code == 3 and "HUMAN REVIEW REQUIRED" in out
    rid = run_id(out)
    code, out = cli(tmp_path, capsys, "review", rid, "--approve", "--notes", "ok", "--who", "sam")
    assert code == 0 and "approved by human:sam" in out and "HUMAN DECISION  APPROVED" in out
    assert Store(tmp_path / "cli.db").get_state(rid) is RunState.COMPLETE


def test_a_review_can_reject(tmp_path, capsys):
    _, out = cli(tmp_path, capsys, "run", "--stub", "--scenario", "repeat")
    code, out = cli(tmp_path, capsys, "review", run_id(out), "--reject", "--notes", "bad quotes")
    assert code == 1 and "human_rejected" in out and "bad quotes" in out


def test_reviewing_a_run_that_is_not_waiting_is_refused(tmp_path, capsys):
    _, out = cli(tmp_path, capsys, "run", "--stub", "--scenario", "clean")
    code, out = cli(tmp_path, capsys, "review", run_id(out), "--approve")
    assert code == 2 and "nothing is waiting" in out


def test_a_poisoned_source_is_refused_and_exits_1(tmp_path, capsys):
    code, out = cli(tmp_path, capsys, "run", "--stub", "--case", "injection")
    assert code == 1 and "source_injection" in out and "DRAFT 1" not in out


def test_empty_text_is_refused(tmp_path, capsys):
    code, out = cli(tmp_path, capsys, "run", "--stub", "--text", "")
    assert code == 1 and "empty_input" in out


def test_the_trace_can_be_rebuilt_later(tmp_path, capsys):
    _, out = cli(tmp_path, capsys, "run", "--stub")
    rid = run_id(out)
    code, again = cli(tmp_path, capsys, "trace", rid)
    assert code == 0 and "RESULT  APPROVED" in again and rid in again
    assert rid in cli(tmp_path, capsys, "runs")[1]


def test_live_mode_without_a_key_says_so_instead_of_crashing(tmp_path, capsys):
    code, out = cli(tmp_path, capsys, "run")
    assert code == 2 and "OPENROUTER_API_KEY" in out and "--stub" in out


# ------------------------------------------------------------- provider selection

class _Tags:
    """A stand-in for GET /api/tags."""

    def __init__(self, *models):
        self.models = models

    def json(self):
        return {"models": [{"name": m} for m in self.models]}


def test_a_local_model_that_is_not_running_is_explained_before_a_run_is_created(tmp_path, capsys, monkeypatch):
    import httpx

    def refuse(*a, **k):
        raise httpx.ConnectError("refused")
    monkeypatch.setattr(httpx, "get", refuse)
    code, out = cli(tmp_path, capsys, "run", "--provider", "ollama")
    assert code == 2 and "Cannot reach Ollama" in out and "ollama serve" in out
    assert not (tmp_path / "cli.db").exists(), "no run should exist for a request that could not start"


def test_a_model_that_is_not_pulled_says_how_and_never_downloads(tmp_path, capsys, monkeypatch):
    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Tags("qwen2.5:7b"))
    code, out = cli(tmp_path, capsys, "run", "--provider", "ollama")
    assert code == 2 and "ollama pull llama3.1:latest" in out
    assert "never downloads" in out and "qwen2.5:7b" in out


def test_a_live_local_run_needs_no_key_and_labels_its_mode(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(study, "_ollama_problem", lambda st: None)
    monkeypatch.setattr(study, "get_provider", lambda st: study.SCENARIOS["revise"][1]())
    code, out = cli(tmp_path, capsys, "run", "--provider", "ollama")
    assert code == 0 and "mode: live (ollama: llama3.1:latest" in out
    assert "scripted" not in out, "a live run must not be labelled as a stub"


def test_the_provider_defaults_to_llm_provider_from_the_environment(tmp_path, capsys, monkeypatch):
    seen = []
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setattr(study, "_ollama_problem", lambda st: None)
    monkeypatch.setattr(study, "get_provider",
                        lambda st: seen.append(st.llm_provider) or study.SCENARIOS["clean"][1]())
    assert cli(tmp_path, capsys, "run")[0] == 0 and seen == ["ollama"]


def test_the_fixture_provider_points_at_stub_instead_of_crashing(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    code, out = cli(tmp_path, capsys, "run")
    assert code == 2 and "--stub" in out


def test_an_unknown_provider_is_refused(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gpt5")
    code, out = cli(tmp_path, capsys, "run")
    assert code == 2 and "Unknown provider" in out


def test_openrouter_can_be_chosen_explicitly_and_still_needs_its_key(tmp_path, capsys):
    code, out = cli(tmp_path, capsys, "run", "--provider", "openrouter")
    assert code == 2 and "OPENROUTER_API_KEY" in out and "--provider ollama" in out


def test_a_human_review_needs_no_model_even_when_the_provider_is_fixture(tmp_path, capsys, monkeypatch):
    _, out = cli(tmp_path, capsys, "run", "--stub", "--scenario", "stuck")
    monkeypatch.setenv("LLM_PROVIDER", "fixture")       # get_provider() would refuse this
    code, out = cli(tmp_path, capsys, "review", run_id(out), "--approve", "--who", "sam")
    assert code == 0 and "approved by human:sam" in out
