"""
Provider abstraction for LLM calls.

Every call in this kit goes through one function with one signature - the one
in slice/llm.py. This file adds the other providers behind that same signature,
so a flow written against `call(settings=, budget=, messages=, schema=, step=)`
does not change when the model does:

    LLMProvider
    |- OpenRouterProvider   cloud; the existing complete(), unchanged
    |- OllamaProvider       local; nothing leaves the machine
    `- FixtureProvider      scripted replies; no network, no key, no model

Chosen with LLM_PROVIDER (openrouter | ollama | fixture) - see get_provider().

OllamaProvider, and why it is not a thin copy of complete():

  * It never touches the internet. llm._repair() posts to OpenRouter, so a local
    provider that reused it would send the user's text to the cloud the first
    time a small model garbled its JSON. The repair pass here goes to Ollama.
  * It uses Ollama's native /api/chat and passes the Pydantic JSON schema as
    `format`, so decoding is constrained to the schema. That is what makes a
    7-8B model usable for structured output at all; `response_format:
    json_object` only promises "some JSON". Needs Ollama 0.5 or newer.
  * It sets num_predict (the output cap - complete() sets max_tokens; without
    this a local model can ramble until the context is full) and num_ctx (the
    default window is small enough to silently cut the START of a long prompt,
    which is where the instructions are).
  * Model fallback: OLLAMA_FALLBACK_MODEL, tried when the first model is not
    pulled, times out, is cut off, or cannot hold the schema. It must already be
    pulled: this app NEVER downloads a model. A dead server is not retried - the
    fallback lives on the same server.

Requirements (Ollama ships quantised weights; these are the published sizes):

    llama3.1:latest   8B   ~4.9 GB disk   ~8 GB RAM (or VRAM for full GPU speed)
    qwen2.5:7b        7B   ~4.7 GB disk   ~6 GB RAM (or VRAM for full GPU speed)

Too little VRAM is not an error, it is slow: layers spill to the CPU. Expect
minutes, not seconds, per call on a small GPU - hence OLLAMA_TIMEOUT.
"""
from __future__ import annotations

import json
from typing import Any, Protocol, Type, runtime_checkable

import httpx
from pydantic import BaseModel

from .budget import Budget
from .config import Settings
from .llm import ModelError, SchemaFailure, Truncated, _parse, _strip_fence
from .llm import complete as _openrouter_complete


class ModelNotFound(ModelError):
    """The model is not pulled. Pulling is the user's decision, not ours."""


class ProviderTimeout(ModelError):
    """The provider did not answer in time."""


@runtime_checkable
class LLMProvider(Protocol):
    """What every provider is: a callable with complete()'s signature."""

    def __call__(self, *, settings: Settings, budget: Budget, messages: list[dict],
                 schema: Type[BaseModel] | None = None, model: str | None = None,
                 step: str = "call", timeout: float = 120.0) -> Any: ...


# ---------------------------------------------------------------------------
# OpenRouterProvider - the existing complete(), wrapped for interface parity

class OpenRouterProvider:
    """Delegates to slice/llm.py:complete. Existing behaviour is unchanged."""

    def __call__(self, *, settings: Settings, budget: Budget, messages: list[dict],
                 schema: Type[BaseModel] | None = None, model: str | None = None,
                 step: str = "call", timeout: float = 120.0) -> Any:
        return _openrouter_complete(
            settings=settings, budget=budget, messages=messages,
            schema=schema, model=model, step=step, timeout=timeout,
        )


# ---------------------------------------------------------------------------
# OllamaProvider - local inference

class OllamaProvider:
    """Calls a local Ollama server. Returns a parsed `schema` instance, or text.

    Which model: an explicit `model=` argument, else settings.ollama_model, else
    the constructor's. Reading it per call is what lets a flow ask for its
    validator on a different model by handing over different settings.

    Errors, all ModelError so the runner records them instead of crashing:
        server not running    ModelError           (no fallback: same server)
        model not pulled      ModelNotFound        (never downloaded for you)
        no answer in time     ProviderTimeout
        cut off at the cap    Truncated
        JSON the schema rejects, even after one repair   SchemaFailure
    """

    def __init__(self, base_url: str, model: str, fallback_model: str = "",
                 num_ctx: int = 8192, timeout: float = 600.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model, self.fallback_model = model, fallback_model
        self.num_ctx, self.timeout = num_ctx, timeout

    def __call__(self, *, settings: Settings, budget: Budget, messages: list[dict],
                 schema: Type[BaseModel] | None = None, model: str | None = None,
                 step: str = "call", timeout: float = 120.0) -> Any:
        # `timeout` is the caller's default, sized for a cloud API. A local model
        # has its own budget: self.timeout.
        budget.check_tokens()
        primary = model or settings.ollama_model or self.model
        fallback = settings.ollama_fallback_model or self.fallback_model
        models = [primary] + ([fallback] if fallback and fallback != primary else [])

        failures: list[str] = []
        for mid in models:
            try:
                return self._attempt(mid, settings, budget, messages, schema)
            except (ModelNotFound, ProviderTimeout, Truncated, SchemaFailure) as e:
                failures.append(f"{mid}: {e}")
                last = e
        if len(models) == 1:
            raise last
        raise type(last)("Every configured Ollama model failed - " + " | ".join(failures))

    # -------------------------------------------------------------- one model

    def _attempt(self, mid, settings, budget, messages, schema):
        text = self._chat(mid, messages, schema, settings, budget)
        if schema is None:
            return text
        parsed = _parse(text, schema)
        if parsed is not None:
            return parsed
        repaired = self._repair(mid, messages, text, schema, settings, budget)
        if repaired is not None:
            return repaired
        raise SchemaFailure(
            f"Ollama model {mid} did not produce valid {schema.__name__} after a repair "
            f"pass. Last reply began: {text[:200]!r}")

    def _chat(self, mid, messages, schema, settings, budget) -> str:
        body: dict[str, Any] = {
            "model": mid, "messages": messages, "stream": False,
            "options": {"temperature": 0, "num_ctx": self.num_ctx,
                        "num_predict": settings.max_tokens},
        }
        if schema is not None:
            body["format"] = schema.model_json_schema()

        try:
            r = httpx.post(f"{self.base_url}/api/chat", json=body,
                           timeout=httpx.Timeout(self.timeout, connect=5.0))
        except httpx.ConnectError as e:
            raise ModelError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Start it with: ollama serve\n"
                f"  (original error: {e})") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeout(
                f"Ollama request timed out after {self.timeout:g}s. The model may still be "
                "loading, or too big for this machine - raise OLLAMA_TIMEOUT, or use a "
                f"smaller model.\n  (original error: {e})") from e
        except httpx.RequestError as e:
            raise ModelError(f"Ollama request failed: {e}") from e

        if r.status_code == 404:
            raise ModelNotFound(
                f"Model '{mid}' not found in Ollama. Pull it first (outside this app): "
                f"ollama pull {mid}\nThis app does not download models automatically.")
        if r.status_code != 200:
            hint = (" Structured output needs Ollama 0.5 or newer."
                    if r.status_code == 400 and schema is not None else "")
            raise ModelError(f"Ollama returned HTTP {r.status_code}: {r.text[:300]}{hint}")
        try:
            data = r.json()
        except ValueError as e:
            raise ModelError(f"Ollama returned a body that is not JSON: {r.text[:200]!r}") from e

        used = (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
        budget.record_tokens(used or 1)
        text = (data.get("message") or {}).get("content") or ""

        if data.get("done_reason") == "length":
            raise Truncated(
                f"Ollama model {mid} was cut off at {settings.max_tokens} tokens before "
                "finishing. Raise SLICE_MAX_TOKENS, or ask for a shorter answer.")
        return text

    def _repair(self, mid, messages, bad: str, schema, settings, budget):
        """One pass showing the model its own output and the error. Goes to
        OLLAMA - never through llm._repair, which would call the cloud."""
        budget.check_tokens()
        try:
            schema.model_validate_json(_strip_fence(bad))
        except Exception as e:
            why = str(e)[:600]
        else:
            return None
        fix = messages + [
            {"role": "assistant", "content": bad[:2000]},
            {"role": "user", "content":
                f"That did not match the required schema.\n\nError:\n{why}\n\n"
                "Reply with the corrected JSON object and nothing else."},
        ]
        try:
            return _parse(self._chat(mid, fix, schema, settings, budget), schema)
        except (ProviderTimeout, Truncated):
            return None


# ---------------------------------------------------------------------------
# FixtureProvider - deterministic scripted replies, no network

class FixtureProvider:
    """Drop-in for complete() that replays a script, no network required.

    script = {"generate": [...], "audit": [...], ...}
    Each item is a dict, a JSON string, or an exception instance (which is raised).
    """

    def __init__(self, script: dict[str, list[Any]]) -> None:
        self._script = {k: list(v) for k, v in script.items()}
        self._n: dict[str, int] = {}
        self.calls: list[dict] = []

    def __call__(self, *, settings: Settings, budget: Budget, messages: list[dict],
                 schema: Type[BaseModel] | None = None, model: str | None = None,
                 step: str = "call", timeout: float = 120.0) -> Any:
        i = self._n.get(step, 0)
        self._n[step] = i + 1
        self.calls.append({"step": step, "i": i})
        try:
            item = self._script[step][i]
        except (KeyError, IndexError):
            raise AssertionError(
                f"FixtureProvider: no reply {i} for step {step!r}. "
                "The flow made an unexpected call.")
        if isinstance(item, BaseException):
            raise item
        raw = item if isinstance(item, str) else json.dumps(item)
        budget.record_tokens(len(raw) // 4 + 1)
        return raw if schema is None else schema.model_validate_json(raw)

    def count(self, step: str) -> int:
        return self._n.get(step, 0)


# ---------------------------------------------------------------------------
# Factory

def get_provider(s: Settings) -> LLMProvider:
    """The provider callable for these settings.

    Raises ValueError for an unrecognised LLM_PROVIDER, and for "fixture", which
    cannot be built from settings alone: it needs a script.
    """
    p = s.llm_provider
    if p == "openrouter":
        return OpenRouterProvider()
    if p == "ollama":
        return OllamaProvider(s.ollama_base_url, s.ollama_model, s.ollama_fallback_model,
                              s.ollama_num_ctx, float(s.ollama_timeout))
    if p == "fixture":
        raise ValueError(
            "LLM_PROVIDER=fixture requires a script. Use FixtureProvider({...}) directly, "
            "or run a demo with --stub / scripts/demo_fixture.py.")
    raise ValueError(f"Unknown LLM_PROVIDER={p!r}. Valid values: openrouter, ollama, fixture.")
