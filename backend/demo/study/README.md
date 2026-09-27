# demo/study - the Study & Assessment Agent

Paste in study material. Get back concise notes and 3-5 multiple-choice
questions, each with four options, one answer, an explanation, and a passage
copied word for word from your text. A validator that did not write them tries
to reject them. If it cannot be satisfied in three revisions, a person decides.

It runs on `slice/` exactly as shipped. Nothing in the spine was edited.

## The workflow

```
source ─▶ DRAFTING ─▶ GATING ──APPROVED──────────────▶ COMPLETE
             ▲           │
             └─REJECTED──┤  revisions left (max 3)
                         ├─ same draft twice, or revisions used up ─▶ AWAITING_EXPERT
                         │                                              │ APPROVE / REJECT
                         │                                              ▼
                         │                                           PROBING ─▶ COMPLETE | FAILED
                         └─ source gives orders to the AI ──────────▶ FAILED
```

`PROBING` is a borrowed name: the spine defines the states, so the step that
applies a human's decision uses the one that was free. Empty, too-short or
too-long input, and a source that tries to instruct the AI, stop the run
**before any model is called**.

## Two agents and an orchestrator

| | does | never does |
|---|---|---|
| **Generator** | writes the study pack from the source; revises from structured feedback | judge its own work |
| **Validator** | rejects or approves, with issues that name the place and the reason | see the answer key or the generator's quotes |
| **Orchestrator** (`flow.py`) | sequencing, limits, persistence, failure records, the human step | call a model to decide what happens next |

The validator is independent in four ways: its own prompt, the other model
family (primary and fallback are swapped for its calls), no answer key, and
every claim it makes is re-checked in code.

| checked by | what |
|---|---|
| **code** (`checks.py`) | schema, four distinct options, the cited quote is in the source (whitespace and typography forgiven, case is not), duplicate questions, instruction-like wording in the source or the output |
| **model auditor** | which options the *source* supports (code compares that with the key: exactly one, and it must be the marked one), question clarity, explanation validity, notes faithful to the source, and a quote of any injection - which code verifies is really in the source |

The auditor returns observations; **code derives APPROVED or REJECTED**. A model
cannot approve anything by saying so.

## What is recorded

Everything is a row in `run.db`, append-only. `python scripts/study.py trace <run_id>`
rebuilds the execution trace from those rows at any time.

`input` · `draft` (one per version) · `verdict` (issues, each tagged `code` or
`model`) · `step` (state, next state, tokens, seconds) · `escalation` ·
`question` / `expert_answer` · `human_review` (typed) · `result` · `failure`

## Run it

Three ways to run it, and the CLI and the web page are the same machinery.

```powershell
# 1. Fixture mode - no key, no network, no model. Every run says "scripted replies".
.\.venv\Scripts\python.exe scripts\demo_fixture.py                         # all four scenarios, both human outcomes
.\.venv\Scripts\python.exe scripts\study.py run --stub                     # rejected, revised, approved
.\.venv\Scripts\python.exe scripts\study.py run --stub --scenario stuck    # waits for a human
.\.venv\Scripts\python.exe scripts\study.py review <run_id> --approve --notes "checked the quotes"
.\.venv\Scripts\python.exe scripts\study.py run --stub --case injection    # refused up front

# 2. Local model - Ollama, no key, no internet (see "Local LLM" below)
.\.venv\Scripts\python.exe scripts\study.py run --provider ollama --file notes.txt

# 3. Cloud - OPENROUTER_API_KEY in .env
.\.venv\Scripts\python.exe scripts\study.py run --file notes.txt
.\.venv\Scripts\python.exe scripts\study.py resume <run_id>                # after a crash
```

Exit codes: `0` approved · `1` failed (the trace says why) · `3` waiting for a
human · `2` could not start.

Scenarios for `--stub`: `revise` (default), `clean`, `stuck`, `repeat`.

### The web page

```powershell
$env:LLM_PROVIDER = "fixture"      # or ollama, or openrouter
.\.venv\Scripts\python.exe -m uvicorn web.study_ui:app --port 8080
```

Four screens: **input** (with a loading state and errors), **content** (notes, quiz,
answers, explanations, each quote re-verified against the source), **trace** (generator
and validator status, feedback, revision count, workflow state, outcome), and
**revision** (each draft, what the validator objected to, what changed, the limit). When
a run needs a person, the content screen has the approve/reject form. Live providers run
in a background thread and the page refreshes itself, so a slow local model never holds
a request open. **There is no authentication** - do not put a live provider on a public URL.

### Local LLM (Ollama)

`LLM_PROVIDER=ollama`, with `OLLAMA_MODEL` (default `llama3.1:latest`) and optionally
`OLLAMA_FALLBACK_MODEL`. The app never downloads a model and never uses the internet on
this path (including the repair pass). Needs Ollama 0.5+ for structured output.
`scripts/doctor.py` reports whether Ollama is running and the model is pulled.

| model | disk | memory | note |
|---|---|---|---|
| `llama3.1:latest` (8B) | ~4.9 GB | ~8 GB RAM, or VRAM for full GPU speed | the one tested here |
| `qwen2.5:7b` (7B) | ~4.7 GB | ~6 GB | not tested here |

Too little VRAM is slow, not broken: on the reference machine (RTX 2050, 4 GB) one
generation took ~100 s, hence `OLLAMA_TIMEOUT=600`. See `docs/TESTING.md` for what was
actually run.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_study.py tests/test_study_api.py tests/test_study_cli.py
```

No key needed. `test_study.py` covers the flow (approval, rejection, feedback,
the revision limit, human review, restart, malformed output, empty input, invented
citations, injection, repeated output, API failure). `test_study_api.py` drives
the real `slice/llm.py` with only the network faked: fallback, the repair pass,
truncation, both 402s, the token fence.

## What this does not do, and what is not yet proven

- **Live evidence is thin.** The prompts have run against one real model
  (`llama3.1:latest` locally) - see `docs/TESTING.md` for the runs and what they showed.
  **The OpenRouter path has never been run live** (no key was available), and no live run
  has yet exercised the *backward* edge: real first drafts were approved. That arc is proven
  by the scripted scenarios only.
- **The injection screen is a heuristic**, deliberately narrow because a false
  positive stops the run. It is one layer; the auditor's verified quote is another.
- **Independence needs two models.** If `SLICE_FALLBACK_MODEL` is empty or equal
  to `SLICE_MODEL` (cloud), or `OLLAMA_FALLBACK_MODEL` is empty (local), the validator
  uses the same model as the generator - independent by prompt and by code checks, but
  not by model. With one local model pulled, that is the situation here.
- **`SLICE_MAX_ATTEMPTS_PER_STEP` is not enforced anywhere in the kit.**
  `Budget.attempt()` exists and is tested but nothing calls it. This slice is
  bounded by the revision limit (from history), the per-run token fence, and
  `max_steps`.
- **`advance()` does not record unexpected exceptions.** `flow.py` wraps its
  handlers so they become a `failure` record; the spine is unchanged.
- **The generator gets 2,400 output tokens** (the kit default of 1,200 truncates
  five questions). Set in `flow.py` for that call only.
- **The old `web/expert.py` form does not resume a run** after answering, and needs
  `python-multipart` (now in `requirements.txt`). The study page has its own review form
  that answers and resumes in one step; from the CLI use `review` or `resume`.
- **Nobody has tested this with real users yet.**
