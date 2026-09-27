"""
Provider abstraction tests. No real network: every HTTP call is mocked, and the
mock records the URL so a test can prove WHERE a request went, not only that a
reply came back.

The one live test (Ollama) is opt-in:  RUN_LIVE_OLLAMA=1 pytest tests/test_providers.py -k live -s
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

from slice.budget import Budget, BudgetExceeded
from slice.config import Settings
from slice.llm import ModelError, SchemaFailure, Truncated
from slice.providers import (
    FixtureProvider,
    LLMProvider,
    ModelNotFound,
    OllamaProvider,
    OpenRouterProvider,
    ProviderTimeout,
    get_provider,
)
from slice.store import Store

LOCAL = "http://localhost:11434"


class Simple(BaseModel):
    status: str
    value: int


def _settings(**kwargs):
    base = dict(
        api_key="sk-test", model="cloud/primary", fallback_model="cloud/fallback",
        escalation_model="", max_tokens=100, max_tokens_per_run=10000,
        max_attempts_per_step=3, expert_timeout_minutes=45, langfuse_public="",
        langfuse_secret="", langfuse_host="", llm_provider="openrouter",
        ollama_base_url=LOCAL, ollama_model="llama3.1:latest",
    )
    base.update(kwargs)
    return Settings(**base)


def _budget(tmp_path, **kwargs):
    s = Store(str(tmp_path / "b.db"))
    return Budget(s, s.create_run("test"), _settings(**kwargs))


class Http:
    """A scripted httpx.post that remembers every request."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, url, **kw):
        self.calls.append({"url": url, **kw})
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r

    @property
    def urls(self):
        return [c["url"] for c in self.calls]

    @property
    def models(self):
        return [c["json"]["model"] for c in self.calls]


def ollama_reply(content, done_reason="stop", prompt=30, evals=20, status=200):
    if isinstance(content, dict):
        content = json.dumps(content)
    r = MagicMock()
    r.status_code = status
    r.text = content if isinstance(content, str) else ""
    r.json.return_value = {"message": {"role": "assistant", "content": content}, "done": True,
                           "done_reason": done_reason, "prompt_eval_count": prompt,
                           "eval_count": evals}
    return r


def error_reply(status, text="error"):
    r = MagicMock()
    r.status_code, r.text = status, text
    return r


GOOD = {"status": "ok", "value": 7}


def ask(provider, http, tmp_path, schema=Simple, settings=None, **kw):
    # Settings are the source of truth for the model (get_provider builds the provider
    # FROM them), so by default hand over settings that agree with the provider under test.
    settings = settings or _settings(ollama_model=getattr(provider, "model", "llama3.1:latest"),
                                     ollama_fallback_model=getattr(provider, "fallback_model", ""))
    with patch("httpx.post", new=http):
        return provider(settings=settings, budget=_budget(tmp_path),
                        messages=[{"role": "user", "content": "go"}], schema=schema,
                        step="call", **kw)


# ================================================================ FixtureProvider

class TestFixtureProvider:
    def test_returns_parsed_schema(self, tmp_path):
        fp = FixtureProvider({"gen": [{"status": "ok", "value": 42}]})
        result = fp(settings=_settings(), budget=_budget(tmp_path), messages=[],
                    schema=Simple, step="gen")
        assert isinstance(result, Simple) and (result.status, result.value) == ("ok", 42)

    def test_returns_raw_string_when_no_schema(self, tmp_path):
        fp = FixtureProvider({"gen": ["hello"]})
        assert fp(settings=_settings(), budget=_budget(tmp_path), messages=[],
                  schema=None, step="gen") == "hello"

    def test_raises_exception_item(self, tmp_path):
        fp = FixtureProvider({"gen": [ModelError("boom")]})
        with pytest.raises(ModelError, match="boom"):
            fp(settings=_settings(), budget=_budget(tmp_path), messages=[], step="gen")

    def test_unexpected_call_raises_assertion(self, tmp_path):
        with pytest.raises(AssertionError, match="no reply"):
            FixtureProvider({"gen": []})(settings=_settings(), budget=_budget(tmp_path),
                                         messages=[], step="gen")

    def test_counts_calls_and_records_budget(self, tmp_path):
        fp, b = FixtureProvider({"gen": ["a", "b"]}), _budget(tmp_path)
        fp(settings=_settings(), budget=b, messages=[], step="gen")
        fp(settings=_settings(), budget=b, messages=[], step="gen")
        assert fp.count("gen") == 2 and b.tokens_used() > 0


# ============================================================ OpenRouterProvider

def openrouter_reply(content):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                           "usage": {"total_tokens": 40}}
    return r


class TestOpenRouterProvider:
    def test_goes_to_openrouter_with_the_key_and_returns_a_parsed_schema(self, tmp_path):
        http = Http(openrouter_reply(json.dumps(GOOD)))
        result = ask(OpenRouterProvider(), http, tmp_path)
        assert result == Simple(**GOOD)
        assert http.urls == ["https://openrouter.ai/api/v1/chat/completions"]
        assert http.calls[0]["headers"]["Authorization"] == "Bearer sk-test"
        assert http.models == ["cloud/primary"]

    def test_falls_back_to_the_other_model_when_throttled(self, tmp_path):
        http = Http(error_reply(429), openrouter_reply(json.dumps(GOOD)))
        assert ask(OpenRouterProvider(), http, tmp_path).value == 7
        assert http.models == ["cloud/primary", "cloud/fallback"]


# ================================================================ OllamaProvider

class TestOllamaProvider:
    def test_returns_parsed_schema(self, tmp_path):
        http = Http(ollama_reply(GOOD))
        result = ask(OllamaProvider(LOCAL, "llama3.1:latest"), http, tmp_path)
        assert isinstance(result, Simple) and result.value == 7

    def test_returns_raw_text_when_no_schema(self, tmp_path):
        http = Http(ollama_reply("hello world"))
        assert ask(OllamaProvider(LOCAL, "m"), http, tmp_path, schema=None) == "hello world"
        assert "format" not in http.calls[0]["json"]

    def test_the_request_is_shaped_for_a_small_local_model(self, tmp_path):
        http = Http(ollama_reply(GOOD))
        ask(OllamaProvider(LOCAL, "llama3.1:latest"), http, tmp_path,
            settings=_settings(max_tokens=321))
        body = http.calls[0]["json"]
        assert http.urls == [f"{LOCAL}/api/chat"] and body["stream"] is False
        assert body["format"] == Simple.model_json_schema(), "decoding must be schema-constrained"
        assert body["options"] == {"temperature": 0, "num_ctx": 8192, "num_predict": 321}

    def test_tokens_are_recorded(self, tmp_path):
        b = _budget(tmp_path)
        with patch("httpx.post", new=Http(ollama_reply(GOOD, prompt=30, evals=20))):
            OllamaProvider(LOCAL, "m")(settings=_settings(), budget=b, messages=[],
                                       schema=Simple, step="call")
        assert b.tokens_used() == 50

    def test_the_token_fence_stops_the_request_before_it_is_sent(self, tmp_path):
        b = _budget(tmp_path, max_tokens_per_run=10)
        b.record_tokens(10)
        http = Http()
        with patch("httpx.post", new=http), pytest.raises(BudgetExceeded):
            OllamaProvider(LOCAL, "m")(settings=_settings(max_tokens_per_run=10), budget=b,
                                       messages=[], schema=Simple, step="call")
        assert http.calls == []

    # ----------------------------------------------------------- failures

    def test_connection_refused_is_a_model_error_and_is_not_retried(self, tmp_path):
        http = Http(httpx.ConnectError("refused"), ollama_reply(GOOD))
        provider = OllamaProvider(LOCAL, "a", fallback_model="b")
        with pytest.raises(ModelError, match="Cannot connect to Ollama"):
            ask(provider, http, tmp_path)
        assert len(http.calls) == 1, "the fallback lives on the same dead server"

    def test_timeout_is_a_provider_timeout(self, tmp_path):
        with pytest.raises(ProviderTimeout, match="timed out"):
            ask(OllamaProvider(LOCAL, "m"), Http(httpx.ReadTimeout("slow")), tmp_path)

    def test_the_timeout_is_the_local_budget_not_the_cloud_default(self, tmp_path):
        http = Http(ollama_reply(GOOD))
        ask(OllamaProvider(LOCAL, "m", timeout=450.0), http, tmp_path)
        assert http.calls[0]["timeout"].read == 450.0
        assert http.calls[0]["timeout"].connect == 5.0, "a dead server must fail fast"

    def test_a_model_that_is_not_pulled_says_so_and_never_downloads(self, tmp_path):
        http = Http(error_reply(404))
        with pytest.raises(ModelNotFound, match="ollama pull no-such-model"):
            ask(OllamaProvider(LOCAL, "no-such-model"), http, tmp_path)
        assert all("/api/pull" not in u for u in http.urls)

    def test_other_http_errors_carry_the_servers_reason(self, tmp_path):
        with pytest.raises(ModelError, match="HTTP 500.*requires more system memory"):
            ask(OllamaProvider(LOCAL, "m"),
                Http(error_reply(500, "model requires more system memory")), tmp_path)

    def test_an_old_server_that_rejects_a_schema_format_is_told_to_upgrade(self, tmp_path):
        with pytest.raises(ModelError, match="0.5 or newer"):
            ask(OllamaProvider(LOCAL, "m"), Http(error_reply(400, "invalid format")), tmp_path)

    def test_a_body_that_is_not_json_is_a_model_error(self, tmp_path):
        r = error_reply(200, "<html>proxy error</html>")
        r.json.side_effect = ValueError("no json")
        with pytest.raises(ModelError, match="not JSON"):
            ask(OllamaProvider(LOCAL, "m"), Http(r), tmp_path)

    def test_a_reply_cut_off_at_the_cap_is_truncated(self, tmp_path):
        with pytest.raises(Truncated, match="cut off"):
            ask(OllamaProvider(LOCAL, "m"), Http(ollama_reply("partial", "length")), tmp_path,
                schema=None)

    # ------------------------------------------------------ repair stays local

    def test_a_malformed_reply_is_repaired_by_ollama_never_by_the_cloud(self, tmp_path):
        """Regression. slice/llm.py's _repair() posts to OpenRouter, so reusing it sent the
        user's text to the internet whenever a small model garbled its JSON."""
        http = Http(ollama_reply("Sure! Here you go"), ollama_reply(GOOD))
        result = ask(OllamaProvider(LOCAL, "m"), http, tmp_path,
                     settings=_settings(api_key="sk-must-not-leak"))
        assert result.value == 7
        assert http.urls == [f"{LOCAL}/api/chat", f"{LOCAL}/api/chat"]
        assert not any("openrouter" in u for u in http.urls)
        assert all("sk-must-not-leak" not in json.dumps(c, default=str) for c in http.calls)
        assert "did not match the required schema" in http.calls[1]["json"]["messages"][-1]["content"]

    def test_unrepairable_output_is_a_schema_failure_after_one_local_repair(self, tmp_path):
        http = Http(ollama_reply("nope"), ollama_reply("still nope"))
        with pytest.raises(SchemaFailure, match="Simple"):
            ask(OllamaProvider(LOCAL, "m"), http, tmp_path)
        assert len(http.calls) == 2 and not any("openrouter" in u for u in http.urls)

    # ----------------------------------------------------------- model fallback

    @pytest.mark.parametrize("first", [
        error_reply(404),                              # not pulled
        httpx.ReadTimeout("slow"),                     # too slow
        ollama_reply("cut", "length"),                 # cut off
    ], ids=["not-pulled", "timeout", "truncated"])
    def test_the_fallback_model_takes_over(self, tmp_path, first):
        http = Http(first, ollama_reply(GOOD))
        result = ask(OllamaProvider(LOCAL, "big:8b", fallback_model="small:3b"), http, tmp_path)
        assert result.value == 7 and http.models == ["big:8b", "small:3b"]

    def test_a_model_that_cannot_hold_the_schema_falls_back(self, tmp_path):
        http = Http(ollama_reply("x"), ollama_reply("y"), ollama_reply(GOOD))
        result = ask(OllamaProvider(LOCAL, "big", fallback_model="small"), http, tmp_path)
        assert result.value == 7 and http.models == ["big", "big", "small"]

    def test_when_every_model_fails_the_error_names_them_all(self, tmp_path):
        http = Http(error_reply(404), error_reply(404))
        with pytest.raises(ModelNotFound) as e:
            ask(OllamaProvider(LOCAL, "aaa", fallback_model="bbb"), http, tmp_path)
        assert "aaa" in str(e.value) and "bbb" in str(e.value)

    def test_the_fallback_is_never_the_same_model(self, tmp_path):
        http = Http(error_reply(404), ollama_reply(GOOD))
        with pytest.raises(ModelNotFound):
            ask(OllamaProvider(LOCAL, "same", fallback_model="same"), http, tmp_path)
        assert len(http.calls) == 1

    # ----------------------------------------------------- which model is used

    def test_settings_choose_the_model_per_call(self, tmp_path):
        """This is what lets the validator run on a different local model: the flow
        hands it different settings."""
        http = Http(ollama_reply(GOOD))
        ask(OllamaProvider(LOCAL, "constructor"), http, tmp_path,
            settings=_settings(ollama_model="from-settings"))
        assert http.models == ["from-settings"]

    def test_an_explicit_model_argument_wins(self, tmp_path):
        http = Http(ollama_reply(GOOD))
        ask(OllamaProvider(LOCAL, "c"), http, tmp_path, model="explicit")
        assert http.models == ["explicit"]

    def test_a_fallback_from_settings_is_used(self, tmp_path):
        http = Http(error_reply(404), ollama_reply(GOOD))
        ask(OllamaProvider(LOCAL, "a"), http, tmp_path,
            settings=_settings(ollama_model="a", ollama_fallback_model="b"))
        assert http.models == ["a", "b"]


# ================================================================ get_provider

class TestGetProvider:
    def test_openrouter(self):
        assert isinstance(get_provider(_settings(llm_provider="openrouter")), OpenRouterProvider)

    def test_ollama_carries_every_local_setting(self):
        p = get_provider(_settings(llm_provider="ollama", ollama_base_url="http://box:11434/",
                                   ollama_model="qwen2.5:7b", ollama_fallback_model="llama3.1:8b",
                                   ollama_num_ctx=4096, ollama_timeout=90))
        assert isinstance(p, OllamaProvider)
        assert (p.base_url, p.model, p.fallback_model, p.num_ctx, p.timeout) == \
            ("http://box:11434", "qwen2.5:7b", "llama3.1:8b", 4096, 90.0)

    def test_fixture_needs_a_script(self):
        with pytest.raises(ValueError, match="fixture"):
            get_provider(_settings(llm_provider="fixture"))

    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            get_provider(_settings(llm_provider="gpt5"))

    def test_every_provider_is_an_llm_provider(self):
        assert all(isinstance(p, LLMProvider) for p in
                   (OpenRouterProvider(), OllamaProvider(LOCAL, "m"), FixtureProvider({})))


# ============================================== live Ollama (opt-in, real model)

def _ollama_ready(model: str = "llama3.1:latest") -> bool:
    try:
        r = httpx.get(f"{LOCAL}/api/tags", timeout=2.0)
        return r.status_code == 200 and model in [m["name"] for m in r.json().get("models", [])]
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(os.environ.get("RUN_LIVE_OLLAMA") != "1",
                    reason="opt-in: set RUN_LIVE_OLLAMA=1 (calls a real local model)")
@pytest.mark.skipif(not _ollama_ready(), reason="Ollama is not running or llama3.1:latest is not pulled")
def test_ollama_live(tmp_path):
    """A real call to a real local model, schema-constrained."""
    result = OllamaProvider(LOCAL, "llama3.1:latest", timeout=600.0)(
        settings=_settings(max_tokens=200), budget=_budget(tmp_path),
        messages=[{"role": "user", "content": 'Set status to "ok" and value to 1.'}],
        schema=Simple, step="live")
    assert isinstance(result, Simple) and result.status and isinstance(result.value, int)
