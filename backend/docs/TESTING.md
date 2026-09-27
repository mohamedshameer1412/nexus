# Testing Guide

What is tested, how to run each layer, and - separately - what was actually
observed. **Every number in "Actual results" was produced by running the command
next to it**; anything not run is listed under "Not tested".

Commands use the project venv from the repo root (PowerShell):
`.\.venv\Scripts\python.exe`. Nothing below needs a network or a key unless it says so.

---

## Quick reference

| What | Command |
|---|---|
| Everything | `python -m pytest -v` |
| Unit | `pytest tests/test_study_unit.py tests/test_providers.py tests/test_budget.py tests/test_store.py tests/test_runner.py tests/test_callback.py` |
| Integration | `pytest tests/test_study.py tests/test_study_integration.py tests/test_study_api.py tests/test_study_cli.py` |
| End-to-end (12 scenarios) | `pytest tests/test_study_e2e.py -v` |
| Provider tests (mocked HTTP) | `pytest tests/test_providers.py -v` |
| **Real** local model (opt-in) | `$env:RUN_LIVE_OLLAMA="1"; pytest tests/test_providers.py -k live -s` |
| Frontend + JSON API | `pytest tests/test_frontend.py tests/test_study_ui.py -v` |
| Environment check | `python scripts/doctor.py` |
| Syntax of every file | `python -m compileall -q -x "[\\/]\.venv[\\/]" .` |
| ARCHITECTURE.md line refs | `python scripts/sync_architecture.py` (`--write` to fix drift) |
| Fixture demo (no key, no model) | `python scripts/demo_fixture.py` |
| Live demo, local model | `python scripts/study.py run --provider ollama` |
| Live demo, cloud | `python scripts/study.py run` (needs `OPENROUTER_API_KEY`) |

---

## The layers

### A. Unit - one piece, no I/O

| File | Covers |
|---|---|
| `test_study_unit.py` | Pydantic schemas (`StudyPack`, `MCQ`, `Verdict`), `checks.py` (injection screen, quote location, duplicate options, fabricated quotes), input guards, revision count |
| `test_providers.py` | `OllamaProvider`, `OpenRouterProvider`, `FixtureProvider`, `get_provider` - all HTTP mocked, and the mock records the **URL** so a test can prove where a request went |
| `test_budget.py` | token and attempt fences, and that they survive a restart |
| `test_store.py`, `test_callback.py`, `test_runner.py` | the spine: append-only history, suspend/resume/timeout, state transitions, `no_progress`/`no_handler` |

### B. Integration - pieces together, still no network

| File | Covers |
|---|---|
| `test_study.py` (71) | the orchestrator on scripted replies: approval, rejection with structured feedback, regeneration **from that feedback**, the revision limit, the human-review state and all its outcomes, restart, malformed output, invalid citations, injection, repeated output, API failure |
| `test_study_api.py` | the real `slice/llm.py` client with only the network faked: fallback model, the repair pass, truncation, both 402s, the token fence - and a whole flow through it |
| `test_study_integration.py` | generator -> validator -> revision -> approval; persistence across `Store.close()`; a `ModelError` recorded, not raised; the JSON API |
| `test_study_cli.py` | the CLI in-process: every command, exit codes, provider selection, "Ollama not running" and "model not pulled" messages |

### C. End-to-end - the twelve scenarios

`tests/test_study_e2e.py`, one test per scenario, all on scripted replies:

| # | Scenario | Outcome asserted |
|---|---|---|
| 1 | valid input | approved |
| 2 | invalid content | rejected |
| 3 | rejected, then revised | approved after 2 drafts |
| 4 | three failed revisions | human review |
| 5 | malformed model output | failed, reason recorded |
| 6 | empty input | rejected before any model call |
| 7 | invalid source references | rejected: `quote_not_in_source` |
| 8 | prompt injection in the source | refused: `source_injection`, no model called |
| 9 | duplicate output | escalated, not an infinite loop |
| 10 | timeout / provider unavailable | failed, reason recorded |
| 11 | resume from persisted state | run continues after the store is reopened |
| 12 | fixture mode | completes with no key and no model |

### D. Quality checks

`python -m pytest -v`, `python scripts/doctor.py`, `python -m compileall`. **No
formatter or linter is configured in this repository** (no `pyproject.toml`,
`ruff.toml`, `setup.cfg`), and `ruff` is not installed in the venv, so none was run.

### E. Local LLM tests

Mocked (`test_providers.py`, always on) pin down: the request is shaped for a small
local model (schema-constrained `format`, `num_predict`, `num_ctx`); a malformed reply
is repaired **by Ollama and never by the cloud** (regression test - this was a real
bug); fallback on not-pulled / timeout / truncation / schema failure; no fallback when
the server is down; a model that is not pulled is reported and **never downloaded**.

One **real** call is opt-in so the default suite stays fast and deterministic:
`RUN_LIVE_OLLAMA=1 pytest tests/test_providers.py -k live -s` (skipped unless Ollama is
running and `llama3.1:latest` is pulled).

### F. Fixture mode

`python scripts/demo_fixture.py` runs all four scenarios (`revise`, `clean`, `stuck`,
`repeat`) with scripted replies. Every trace header says `scripted replies - no model is
called`. For the two scenarios that end at human review, the script answers **on the
reviewer's behalf and says so** (`scripted-reviewer`), so both human outcomes are shown
without a person in the room.

### G. Frontend

`test_frontend.py` and `test_study_ui.py` drive the app with FastAPI's `TestClient`:
all four screens, the JSON API, the human-review form and its API, HTML escaping of
user text, input errors, the database path being read per request, and - with a
deliberately slow provider - that a live run returns at once, reports `active`,
refreshes until it finishes, then stops refreshing.

---

## Provider configuration

```
LLM_PROVIDER=openrouter    # default. Needs OPENROUTER_API_KEY
LLM_PROVIDER=ollama        # local. Needs Ollama 0.5+ running; nothing leaves the machine
LLM_PROVIDER=fixture       # scripted; only via --stub / the demo scripts / the web UI
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:latest
OLLAMA_FALLBACK_MODEL=          # optional, must already be pulled
OLLAMA_NUM_CTX=8192
OLLAMA_TIMEOUT=600              # seconds per reply
```

Pull models yourself - the app never does: `ollama pull llama3.1:latest` (~4.9 GB,
~8 GB RAM) or `ollama pull qwen2.5:7b` (~4.7 GB, ~6 GB). If Ollama is down the CLI says
`ollama serve`; if the model is missing it prints the exact `ollama pull` line.

---

## Actual results

Machine: Windows 11, Python 3.13.3, RTX 2050 (4 GB VRAM), Ollama 0.34.2, `llama3.1:latest`.
Run on 2026-09-19.

### Automated suite

`python -m pytest -v` -> **297 passed, 4 skipped, 2 warnings in 15.3 s.**

| File | Passed | Skipped |
|---|---:|---|
| `test_architecture.py` | 38 | |
| `test_budget.py` | 5 | |
| `test_callback.py` | 4 | |
| `test_frontend.py` | 13 | |
| `test_integration.py` | 0 | 3 (need a live OpenRouter key) |
| `test_providers.py` | 36 | 1 (real Ollama, opt-in) |
| `test_runner.py` | 6 | |
| `test_smoke.py` | 10 | |
| `test_store.py` | 8 | |
| `test_study.py` | 74 | |
| `test_study_api.py` | 12 | |
| `test_study_cli.py` | 16 | |
| `test_study_e2e.py` | 12 | |
| `test_study_integration.py` | 14 | |
| `test_study_ui.py` | 24 | |
| `test_study_unit.py` | 25 | |

The 2 warnings are upstream deprecation notices from the test client (Starlette wants
`httpx2`; an `anyio` alias moved). They do not affect results.

### Quality checks

| Command | Result |
|---|---|
| `python -m compileall -q -x "[\\/]\.venv[\\/]" .` | exit 0 (1.9 s) |
| `python scripts/sync_architecture.py` | `all references current` (it had drifted by 3 lines after `slice/config.py` gained settings; fixed with `--write`) |
| `python scripts/doctor.py`, `LLM_PROVIDER=ollama`, this machine | no failures; Ollama running, `llama3.1:latest` available; the OpenRouter checks skipped (no key) |
| `python scripts/doctor.py`, defaults, no `.env` | 1 failure (`.env not found`) - correct for the OpenRouter default; it now **keeps going** instead of exiting at line one |
| `python scripts/doctor.py`, `LLM_PROVIDER=fixture`, Ollama unreachable | exit 0 - Ollama is optional |
| `python scripts/doctor.py`, `LLM_PROVIDER=ollama`, Ollama unreachable / model not pulled | fails, and prints `ollama serve` / the `ollama pull` line |
| Linter / formatter | **none configured; `ruff` not installed - not run** |

### Clean setup

A brand-new venv built **only** from `requirements.txt`, with `OPENROUTER_API_KEY` and
`LLM_PROVIDER` unset: `pytest` -> 294 passed, 4 skipped, and `scripts/demo_fixture.py` ran
all four scenarios. (This was run before the last 3 tests were added; it was not repeated.)

### Real model runs (Ollama, `llama3.1:latest`, nothing left the machine)

| # | What | Result | Time | Tokens |
|---|---|---|---:|---:|
| 1 | Provider as first inherited, sample text | **FAILED `model`**: timed out at 120 s (recorded cleanly). `demo_live.py` then crashed on exit (`PermissionError`, unclosed SQLite file) | 122 s | 0 |
| 2 | Rewritten provider, sample text | approved, 1 draft | 129 s (gen 101 s, audit 29 s) | 3,385 |
| 3 | Same, through the **web UI** (`uvicorn`, `POST /api/generate`, polled) | POST returned in 1 s; `drafting -> gating -> complete` observed while polling; approved | 156 s | 3,385 |
| 4 | Harder text (mitosis vs meiosis), CLI | approved, 1 draft - **but** every option read `A. A. ...` (the model wrote the letter inside the option) and the same-model validator did not notice | 181 s | 3,425 |
| 5 | Same text after adding the `option_label_in_text` check and a prompt line | approved, 1 draft, options clean | 132 s | 3,360 |
| 6 | `RUN_LIVE_OLLAMA=1 pytest -k live` | passed (9.6 s and 25.6 s on two runs) | | |

What these show: the local path works end to end, and a real model can hold the schema
with schema-constrained decoding. Runs 2 and 3 used the same input and produced identical
token counts (temperature 0). Run 4 is why the label check exists: a deterministic check
caught, on the model's actual draft, what a same-model validator missed.

**No real run has yet exercised the backward revision loop**: every real first draft was
approved. That loop is proven by the scripted scenarios and the mocked tests only.

---

## Known limitations

- **Live evidence is one model on one machine.** The OpenRouter path has never been run
  live (no key). `OLLAMA_FALLBACK_MODEL` and the validator-on-a-different-model swap are
  tested with mocks only: just one model is pulled here.
- **The validator is not independent by model when one local model is pulled.** It is
  independent by prompt and by the code checks, which is what caught run 4's defect.
- **Speed.** On 4 GB VRAM one generation is ~100 s and one audit ~30 s. A worst case of
  four drafts is therefore roughly 9 minutes (an extrapolation, not a measurement).
- **The frontend's JavaScript has never run in a browser.** `TestClient` does not execute
  JS. The inline scripts were syntax-checked with Node (all parse); the Generate,
  Approve/Reject and Resume click handlers were not exercised. The pages were fetched by
  `curl` and `TestClient` only.
- **No authentication.** A live provider on a public URL lets anyone spend your tokens.
  Background runs live in the server process; a restart mid-run leaves a run the page
  offers to resume.
- **The old `web/expert.py` form** needs `python-multipart` (now in `requirements.txt`) and
  does not resume a run. The study page has its own review form.
- **The injection screen is a heuristic**; a false positive stops a run.
- **The title field is display-only**; it is not passed to the generator.
- **Kit-wide, unchanged:** `Budget.attempt()` is never called, so
  `SLICE_MAX_ATTEMPTS_PER_STEP` is not enforced; `runner.advance` does not record
  unexpected exceptions (the study flow wraps its handlers so it does).
- **Windows:** an open SQLite file cannot be deleted. The demo scripts close their stores;
  tests use `tmp_path`.
- **One unexplained slowness:** a single combined command (live test, full suite,
  `compileall`, `doctor`) ran past a 400 s tool limit although each step succeeded. Timed
  separately: live test 26 s, suite 15 s, `compileall` 1.9 s. I could not reproduce it.

## Not tested

Any user or reviewer feedback (nobody has used this); OpenRouter live; a second local
model; a browser; a public tunnel; a long source near the 12,000-character limit on a
real model; a real revision on a real model.
