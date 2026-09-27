"""Which models may answer a question, in what order, and under what limits.

Order (the default, STUDYHUB_PRIMARY=cloud): the cloud (OpenRouter) first, the local Ollama model as the backup. The cloud is used only
when EVERY guard below allows it; otherwise the local model answers alone. Which cloud models, and how many, depends on the task:
real work (answers with quotes, writing questions, planning) goes to the stronger models first; simple checks (the independent
reader that double-checks a practice question) go to the local model first, because they are cheap and do not need the cloud.
STUDYHUB_PRIMARY=local restores "local first, cloud only if it fails".

  * an API key exists (in .env, never in the repo),
  * THIS user ticked "allow cloud" (their retrieved passages leave the computer on that path),
  * the configured model is on the allow-list (a small list, to protect the credit),
  * the user's and the app's daily token caps are not used up,
  * OpenRouter still reports credit left (when it can be asked).

Every request is capped at 1,200 output tokens no matter what the environment says. Anything that blocks the cloud is
returned as a plain-words note so the question's trace can say why the cloud was not used.
"""
from __future__ import annotations

import dataclasses
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from slice import config as slice_config
from slice.config import Settings
from slice.providers import OllamaProvider, OpenRouterProvider

from .repo import Repo

CLOUD_TOKEN_CAP = 1200
DEFAULT_ALLOWED = ("inclusionai/ling-3.0-flash,mistralai/mistral-small-3.2-24b-instruct,openai/gpt-oss-120b,"
                   "deepseek/deepseek-v4-flash-0731,z-ai/glm-5.3-flash,qwen/qwen3.7-flash")
MIN_CREDIT_USD = 1.0
MAX_CLOUD_TIERS = 2            # at most two cloud models are tried for one task: the credit is small and shared

# Preferred cloud models per task, best fit first. Only models on the allow-list are ever used. Override one with
# STUDYHUB_CLOUD_ORDER_<TASK>=model,model (for example STUDYHUB_CLOUD_ORDER_WRITE).
CLOUD_ORDER = {   # ordered by the measured bake-off (scripts/agent_bakeoff.py): quality was equal, speed and token use were not
    "answer": ["mistralai/mistral-small-3.2-24b-instruct", "openai/gpt-oss-120b", "inclusionai/ling-3.0-flash", "z-ai/glm-5.3-flash", "deepseek/deepseek-v4-flash-0731", "qwen/qwen3.7-flash"],
    "write": ["mistralai/mistral-small-3.2-24b-instruct", "openai/gpt-oss-120b", "z-ai/glm-5.3-flash", "inclusionai/ling-3.0-flash", "qwen/qwen3.7-flash", "deepseek/deepseek-v4-flash-0731"],
    "plan": ["mistralai/mistral-small-3.2-24b-instruct", "z-ai/glm-5.3-flash", "inclusionai/ling-3.0-flash", "openai/gpt-oss-120b", "deepseek/deepseek-v4-flash-0731", "qwen/qwen3.7-flash"],
    "simple": ["mistralai/mistral-small-3.2-24b-instruct", "inclusionai/ling-3.0-flash", "z-ai/glm-5.3-flash", "openai/gpt-oss-120b", "deepseek/deepseek-v4-flash-0731", "qwen/qwen3.7-flash"],
}
LOCAL_FIRST_TASKS = {"simple"}
_credit_cache: dict[str, tuple[float, float | None]] = {}


@dataclass
class Tier:
    name: str                                     # "local" | "cloud"
    label: str                                    # what the student sees
    model: str
    provider: Callable[..., Any]
    settings: Settings
    timeout: float = 120.0
    on_usage: Callable[[int], None] | None = None


def allowed_cloud_models() -> list[str]:
    return [m.strip() for m in os.environ.get("STUDYHUB_CLOUD_MODELS", DEFAULT_ALLOWED).split(",") if m.strip()]


def cloud_models_for(task: str) -> list[str]:
    """Allowed cloud models for a task, in order of preference."""
    allowed = allowed_cloud_models()
    custom = [m.strip() for m in os.environ.get(f"STUDYHUB_CLOUD_ORDER_{task.upper()}", "").split(",") if m.strip()]
    ordered = [m for m in custom + CLOUD_ORDER.get(task, CLOUD_ORDER["answer"]) if m in allowed]
    return list(dict.fromkeys(ordered)) + [m for m in allowed if m not in ordered]


def daily_cap(scope: str) -> int:
    return int(os.environ.get("STUDYHUB_CLOUD_DAILY_TOKENS_USER" if scope == "user" else "STUDYHUB_CLOUD_DAILY_TOKENS_ALL",
                              "30000" if scope == "user" else "150000"))


def today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def credit_remaining(api_key: str, *, now: float | None = None, client: httpx.Client | None = None) -> float | None:
    """Dollars left on the key, from OpenRouter's /key, cached for 10 minutes. None if it cannot be read."""
    now = time.time() if now is None else now
    hit = _credit_cache.get(api_key)
    if hit and now - hit[0] < 600:
        return hit[1]
    value: float | None = None
    try:
        c = client or httpx.Client(timeout=8)
        data = c.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {api_key}"}).json().get("data", {})
        left = data.get("limit_remaining")
        value = float(left) if left is not None else None
    except Exception:
        value = None
    _credit_cache[api_key] = (now, value)
    return value


def cloud_block_reason(db, user: dict, s: Settings, *, credit: Callable[[str], float | None] | None = None) -> str | None:
    """Why the cloud may not be used right now (plain words), or None if it may."""
    repo = Repo(db)
    if not s.api_key:
        return "no OpenRouter key is configured"
    if not user.get("cloud_consent"):
        return "you have not allowed cloud models (Account page)"
    if not allowed_cloud_models():
        return "no cloud model is on the allow-list"
    day = today()
    if repo.cloud_tokens_today(day, user["id"]) >= daily_cap("user"):
        return "your daily cloud token limit has been reached"
    if repo.cloud_tokens_today(day) >= daily_cap("all"):
        return "the app's daily cloud token limit has been reached"
    left = (credit or credit_remaining)(s.api_key)
    if left is not None and left < MIN_CREDIT_USD:
        return f"the OpenRouter credit is nearly used up (${left:.2f} left)"
    return None


def build_tiers(db, user: dict, *, base: Settings | None = None,
                credit: Callable[[str], float | None] | None = None, task: str = "answer") -> tuple[list[Tier], list[str]]:
    """(tiers in order of use, notes about tiers that were left out). `task` picks the cloud models and the order (see CLOUD_ORDER)."""
    s = base or slice_config.settings()
    notes: list[str] = []
    local: list[Tier] = []
    cloud: list[Tier] = []
    if os.environ.get("STUDYHUB_LOCAL_MODEL", "on").lower() != "off":
        local.append(Tier("local", f"{s.ollama_model} (on this computer)", s.ollama_model,
                          OllamaProvider(s.ollama_base_url, s.ollama_model, s.ollama_fallback_model, s.ollama_num_ctx,
                                         float(s.ollama_timeout)),
                          dataclasses.replace(s, llm_provider="ollama")))
    else:
        notes.append("the local model is switched off (STUDYHUB_LOCAL_MODEL=off)")
    why = cloud_block_reason(db, user, s, credit=credit)
    if why is None:
        repo, uid, day = Repo(db), user["id"], today()
        for model in cloud_models_for(task)[:MAX_CLOUD_TIERS]:
            cloud.append(Tier("cloud", f"{model} (OpenRouter)", model, OpenRouterProvider(),
                              dataclasses.replace(s, llm_provider="openrouter", model=model, max_tokens=min(s.max_tokens, CLOUD_TOKEN_CAP)),
                              on_usage=lambda n, model=model: repo.record_cloud_usage(uid, day, model, n)))
    else:
        notes.append(f"cloud not used: {why}")
    cloud_first = os.environ.get("STUDYHUB_PRIMARY", "cloud").lower() != "local" and task not in LOCAL_FIRST_TASKS
    return (cloud + local if cloud_first else local + cloud), notes
