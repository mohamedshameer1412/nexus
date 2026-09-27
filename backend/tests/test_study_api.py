"""API failure and fallback, through the REAL slice/llm.py client.

Only the network is faked (httpx.post). Everything else - request building,
fallback, the repair pass, 402 classification, the token fence - is the code that
would run live. tests/test_study.py uses scripted replies for the flow; this file
proves the client underneath it does what the flow relies on.
"""
from __future__ import annotations

import json

import httpx
import pytest
from pydantic import BaseModel

from demo.study.flow import build_flow
from demo.study.samples import SAMPLE
from demo.study.stub import V2, ok_audit
from slice import runner
from slice.budget import Budget, BudgetExceeded
from slice.config import Settings
from slice.llm import CapExhausted, ModelError, PoolExhausted, SchemaFailure, Truncated, complete
from slice.records import RunState
from slice.store import Store

S = Settings(api_key="x", model="primary/m", fallback_model="fallback/m",
             escalation_model="e", max_tokens=100, max_tokens_per_run=1000,
             max_attempts_per_step=3, expert_timeout_minutes=45,
             langfuse_public="", langfuse_secret="", langfuse_host="")


class Tiny(BaseModel):
    ok: bool


class Resp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body = status, body
        self.text = text or json.dumps(body or {})

    def json(self):
        if self._body is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._body


def ok(content, finish="stop", tokens=10):
    return Resp(200, {"choices": [{"message": {"content": content}, "finish_reason": finish}],
                      "usage": {"total_tokens": tokens}})


class Net:
    """A scripted httpx.post. Replies come back in order; every request is kept."""

    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []

    def __call__(self, url, **kw):
        self.requests.append(kw["json"])
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r

    @property
    def models(self):
        return [r["model"] for r in self.requests]


@pytest.fixture()
def budget(tmp_path):
    store = Store(tmp_path / "a.db")
    return Budget(store, store.create_run("t"), S)


def call(budget, net, monkeypatch, settings=S):
    monkeypatch.setattr(httpx, "post", net)
    return complete(settings=settings, budget=budget, messages=[{"role": "user", "content": "go"}],
                    schema=Tiny, step="t")


# ------------------------------------------------------------------ fallback

def test_a_rate_limited_primary_falls_back_to_the_other_model(budget, monkeypatch):
    net = Net(Resp(429, {}), ok('{"ok": true}'))
    assert call(budget, net, monkeypatch) == Tiny(ok=True)
    assert net.models == ["primary/m", "fallback/m"]


def test_a_network_error_falls_back_and_two_are_a_model_error(budget, monkeypatch):
    net = Net(httpx.ConnectError("down"), ok('{"ok": true}'))
    assert call(budget, net, monkeypatch).ok is True
    with pytest.raises(ModelError, match="unreachable"):
        call(budget, Net(httpx.ConnectError("down"), httpx.ConnectError("down")), monkeypatch)


def test_both_providers_throttled_is_a_model_error_not_a_crash(budget, monkeypatch):
    with pytest.raises(ModelError, match="429"):
        call(budget, Net(Resp(429, {}), Resp(429, {}, "rate limited")), monkeypatch)


# ------------------------------------------------------------------ malformed

def test_malformed_output_gets_one_repair_pass_showing_the_error(budget, monkeypatch):
    net = Net(ok("Sure! Here you go"), ok('{"ok": true}'))
    assert call(budget, net, monkeypatch).ok is True
    assert net.models == ["primary/m", "primary/m"], "the repair goes to the same model"
    assert "did not match the required schema" in net.requests[1]["messages"][-1]["content"]


def test_unrepairable_output_is_a_schema_failure_after_both_models_try(budget, monkeypatch):
    net = Net(ok("nope"), ok("nope"), ok("nope"), ok("nope"))
    with pytest.raises(SchemaFailure):
        call(budget, net, monkeypatch)
    assert net.models == ["primary/m", "primary/m", "fallback/m", "fallback/m"]


def test_a_truncated_reply_is_not_repaired_it_falls_back(budget, monkeypatch):
    net = Net(ok('{"ok": tr', finish="length"), ok('{"ok": true}'))
    assert call(budget, net, monkeypatch).ok is True
    assert net.models == ["primary/m", "fallback/m"]
    with pytest.raises(Truncated):
        call(budget, Net(ok("{", finish="length"), ok("{", finish="length")), monkeypatch)


# ----------------------------------------------------------------- the fences

def test_a_key_cap_402_is_cap_exhausted_and_is_not_retried(budget, monkeypatch):
    body = {"error": {"message": "limit", "metadata": {"limit_source": "openrouter_key_limit"}}}
    net = Net(Resp(402, body))
    with pytest.raises(CapExhausted):
        call(budget, net, monkeypatch)
    assert len(net.requests) == 1


def test_any_other_402_is_treated_as_the_shared_pool_running_dry(budget, monkeypatch):
    with pytest.raises(PoolExhausted):
        call(budget, Net(Resp(402, {"error": {"message": "insufficient credits"}})), monkeypatch)


def test_the_token_fence_stops_the_request_before_it_is_sent(budget, monkeypatch):
    budget.record_tokens(1000)
    net = Net()
    with pytest.raises(BudgetExceeded):
        call(budget, net, monkeypatch)
    assert net.requests == []


# ---------------------------------------------- the whole flow, real client, fake network

def _flow_run(tmp_path, net, monkeypatch):
    monkeypatch.setattr(httpx, "post", net)
    store = Store(tmp_path / "f.db")
    run = store.create_run("study", {"mode": "fake-network"})
    store.append(run, "input", {"text": SAMPLE}, produced_by="user")
    return store, run, runner.advance(store, run, build_flow(complete), S)


def test_the_whole_flow_runs_through_the_real_client(tmp_path, monkeypatch):
    fenced = "```json\n" + json.dumps(V2) + "\n```"          # models love a markdown fence
    net = Net(ok(fenced, tokens=300), ok(json.dumps(ok_audit(V2)), tokens=80))
    store, run, final = _flow_run(tmp_path, net, monkeypatch)
    assert final is RunState.COMPLETE, store.latest(run, "failure")
    assert net.models == ["primary/m", "fallback/m"], "generate on the primary, audit on the other family"
    assert net.requests[0]["max_tokens"] == 2400 and net.requests[1]["max_tokens"] == S.max_tokens
    assert net.requests[0]["response_format"] == {"type": "json_object"}
    assert store.counter(run, "tokens") == 380


def test_a_provider_returning_html_with_a_200_is_a_recorded_failure(tmp_path, monkeypatch):
    """Not a ModelError the client raises - a bare ValueError from r.json(). The
    flow's wrapper turns it into a record instead of a stack trace."""
    store, run, final = _flow_run(tmp_path, Net(Resp(200, None, "<html>captive portal</html>")),
                                  monkeypatch)
    assert final is RunState.FAILED
    f = store.latest(run, "failure")
    assert f["kind"] == "unexpected_error" and f["detail"].startswith("ValueError")


def test_a_cap_exhausted_mid_run_keeps_the_draft_and_says_why(tmp_path, monkeypatch):
    body = {"error": {"message": "limit", "metadata": {"limit_source": "openrouter_key_limit"}}}
    net = Net(ok(json.dumps(V2), tokens=300), Resp(402, body))
    store, run, final = _flow_run(tmp_path, net, monkeypatch)
    assert final is RunState.FAILED
    assert store.latest(run, "failure")["kind"] == "cap_exhausted"
    assert len(store.history(run, "draft")) == 1, "the work done before the failure is not lost"
