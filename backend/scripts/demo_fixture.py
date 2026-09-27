#!/usr/bin/env python
"""
Fixture demo: run all four study-pack scenarios with no API key and no Ollama.

Each scenario drives the full state machine against a temporary SQLite database,
using the hand-written Scripted responses from demo/study/stub.py.
The execution trace is printed to the terminal.

Usage:
    python scripts/demo_fixture.py

No environment variables required. The .env file is intentionally not loaded.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Make the project root importable when run as a script.
sys.path.insert(0, str(Path(__file__).parent.parent))

from demo.study import trace as study_trace
from demo.study.flow import build_flow
from demo.study.samples import SAMPLE
from demo.study.stub import SCENARIOS
from slice import callback, runner
from slice.config import Settings
from slice.records import RunState
from slice.store import Store

# A minimal Settings with no keys: everything defaults to 0 / empty.
# The Scripted fixture does not use the API key, the model name, or any budget
# that would care about tokens in a meaningful way.
_SETTINGS = Settings(
    api_key="", model="", fallback_model="", escalation_model="",
    max_tokens=9999, max_tokens_per_run=999_999, max_attempts_per_step=10,
    expert_timeout_minutes=45, langfuse_public="", langfuse_secret="",
    langfuse_host="", llm_provider="fixture",
    ollama_base_url="", ollama_model="",
)

SEP = "-" * 80

# A run that needs a person stops at AWAITING_EXPERT. To show BOTH outcomes without a
# person in the room, the demo answers on their behalf - and says so, out loud, in the
# trace itself (the reviewer's name). Nothing here is a real review.
SCRIPTED_REVIEWERS = {
    "stuck":  ("APPROVE the quotes were checked by hand", "scripted-reviewer"),
    "repeat": ("REJECT the generator is repeating itself", "scripted-reviewer"),
}


def run_scenario(name: str, description: str, factory) -> None:
    print(f"\n{SEP}")
    print(f"  SCENARIO: {name!r}")
    print(f"  {description}")
    print(SEP)

    call = factory()
    with tempfile.TemporaryDirectory() as d:
        store = Store(str(Path(d) / "demo.db"))
        run_id = store.create_run(
            "study", meta={"title": name,
                           "mode": f"stub:{name} (scripted replies - no model is called)"})
        store.append(run_id, "input", {"text": SAMPLE}, produced_by="demo")
        try:
            final = runner.advance(store, run_id, build_flow(call=call), _SETTINGS)
            note = ""
            if final is RunState.AWAITING_EXPERT and name in SCRIPTED_REVIEWERS:
                answer, who = SCRIPTED_REVIEWERS[name]
                pending = callback.pending(store, run_id)[0]
                callback.answer(store, pending.id, answer, who=who)
                # After a decision nothing calls a model, so an empty script is safe - and
                # would fail loudly if the flow ever tried.
                final = runner.advance(store, run_id, build_flow(call=type(call)([], [])), _SETTINGS)
                note = f"\n  (the reviewer above is scripted: {who!r} - no person was involved)"
            trace_text = study_trace.render_text(store, run_id, color=sys.stdout.isatty())
        finally:
            store.close()   # release the SQLite file before cleanup (Windows)
    print(trace_text + note)
    print(f"\n  => {final.value.upper()}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print("\nStudy Pack Generator — Fixture Demo")
    print("Runs all four scenarios with no API key, no Ollama, no network.")
    for name, (desc, factory) in SCENARIOS.items():
        run_scenario(name, desc, factory)
    print(f"\n{SEP}")
    print("  All four scenarios complete.")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
