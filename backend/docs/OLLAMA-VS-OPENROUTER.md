# Ollama (local) vs OpenRouter (cloud) — measured comparison

What Nexus gets from a local model (Ollama, `llama3.1` 8B) versus the six allow-listed OpenRouter models, on the parts of the
product that call an LLM: cited answers (Ask), practice questions, and difficulty-mixed diagnostic questions.

Everything below was **measured** by `scripts/agent_bakeoff.py` on a throw-away database and is stored in
`docs/studyhub-evidence/agents/bakeoff-*.json` (per-question rows) and `BAKEOFF.md`. Nothing is estimated except where marked *(inferred)*.

## 1. Short answer

| | Ollama `llama3.1:latest` (local) | OpenRouter (six models) |
|---|---|---|
| Speed | 10× slower or worse | 2–13 s per cited answer |
| Quality after our verifier | Same as cloud | Same as local |
| Cost | Free | ≈ $0.007–$0.027 per full run |
| Privacy | Material never leaves the machine | Needs user consent; only cited chunks are sent |
| Works offline | Yes | No |
| Best role | Backup, offline, private, simple checks, answer-solver | Primary for anything the user waits on |

Recommendation (implemented in `studyhub/models.py`): **cloud first with Mistral Small leading, Ollama as backup**, simple checks stay
local-first, and the "solver" that double-checks each generated question always runs on the local tier.

## 2. Computation

**Local machine:** Intel i5-1240P (12 cores / 16 threads), 15.7 GB RAM, RTX 2050 with 4 GB VRAM + Iris Xe.
Model: llama3.1 8.0B, Q4_K_M quantisation, 4.9 GB on disk, **5.7 GB when loaded — only ~2.1 GB fits in the GPU**. The rest runs on CPU,
so generation is memory-bandwidth and CPU bound. The cloud models run on datacentre GPUs and are not limited by our hardware.

| Model | Cited answer (mean / median / max, s) | 4 practice questions (s) | Diagnostic-style, 6 requested (s) |
|---|---|---|---|
| **mistral-small-3.2-24b** | **2.3 / 2.5 / 6.5** | **17.5** | **28.8** |
| gpt-oss-120b | 4.9 / 3.0 / 26.6 | 37.8 | 99.5 |
| glm-5.3-flash | 5.2 / 2.4 / 47.8 | 48.3 | 91.8 |
| ling-3.0-flash | 4.5 / 5.3 / 11.5 | 127.6 | 174.4 |
| deepseek-v4-flash | 6.0 / 4.0 / 20.4 | 94.0 | 227.6 |
| qwen3.7-flash | 12.8 / 18.2 / 27.1 | 115.8 | 167.2 |
| **llama3.1 8B (Ollama)** | **26.6 / 25.7 / 83.2** | **322.3** | **399.1** |

- Cloud answers: 14 questions per model. Local: 8 questions (a spread of in-scope, out-of-scope, trap and injection cases), to keep the run short.
- Fastest cloud vs local: about **11× faster** for answers, **18×** for practice, **14×** for the diagnostic set.
- Even the slowest cloud model (qwen) is about 2× faster than local on answers, and generally 2–3× on question generation.
- A local diagnostic of ~6.5 minutes is not acceptable in a live demo; a cloud one at ~30–230 s is, and Mistral is comfortable.

### Tokens and cost

Cloud calls are capped at 1,200 output tokens each. Local is free but costs time and battery.

| Model | Tokens counted in the run | Credit used by the run |
|---|---|---|
| mistral-small-3.2-24b | 14,864 | **$0.0069** |
| gpt-oss-120b | 24,739 | $0.0199 |
| glm-5.3-flash | 31,090 | $0.0210 |
| ling-3.0-flash | 28,216 | $0.0241 |
| deepseek-v4-flash | 29,829 | $0.0261 |
| qwen3.7-flash | 52,394 | $0.0269 |
| llama3.1 8B (Ollama) | 0 | $0 |

Credit used is the difference in the account balance reported by OpenRouter before and after each model's run (14 answers + 4 practice + 6
diagnostic questions). All six models cost about **$0.125 in total**; with probes and reruns the whole evaluation was about **$0.14** of a $10
balance. At Mistral's price that is roughly **$0.007 per complete study session**, i.e. about 1,400 sessions per $10.

Two things to read carefully:
- The token counter under-reports what is billed (it counts what the app tracks, and the balance delta also includes prompt tokens and any
  reasoning tokens the provider bills). Use the credit column for cost, not tokens × list price.
- List price alone would not rank the models the same way: qwen is cheap per token yet used the most tokens (*inferred*: it is a "thinking"
  model that spends tokens on reasoning before the visible answer).

## 3. Reasoning and answer quality

Every model, local and cloud, was held to the same checks. The pipeline (not the model) enforces them:
every shown quote must appear **verbatim** in the uploaded material, questions with a bad answer key or missing quote are rejected, and
answers with unsupported claims are dropped.

| Result | Cloud (each of 6 models) | Ollama llama3.1 8B |
|---|---|---|
| In-scope questions answered with a real quote | 8 / 8 (every model) | 5 / 5 |
| Out-of-scope, trap and injection questions handled correctly (refuse, or ignore the injected "answer 42") | 6 / 6 (every model) | 3 / 3 |
| All shown quotes verbatim in the material | Yes (every model) | Yes |
| Errors / crashes | 0 | 0 |
| Claims dropped by the verifier | 0 | **1** |
| Practice questions kept (4 requested) | 4 / 4 (every model) | 4 / 4 |
| Practice drafts rejected before reaching 4 | 0 for five models, **3 for ling** | 1 |
| Diagnostic-style kept (6 requested) | 6/6 glm, ling; 5/6 the other four | 5 / 6 |
| Diagnostic drafts rejected | 2 (deepseek, mistral, gpt-oss, qwen, glm), 0 (ling) | 2 |
| Difficulty spread in the diagnostic (easy / medium / hard) | balanced 2/2/2 for glm and ling; 2/2/1 or 1/2/2 for the rest | 1/2/2 |

What this means:

1. **The verifier equalises the outcome.** Because nothing unverified reaches the student, a weak model shows up as *more rejected drafts and
   longer waiting*, not as wrong content. That is exactly what the local numbers show: same pass rates, one dropped claim, 10× the time.
2. **Instruction-following was equal.** The planted prompt-injection document ("answer 42") was ignored by all seven models; out-of-scope
   questions were refused by all seven.
3. **Reasoning-style models are not automatically better here.** These tasks are extractive ("find the quote that supports this"),
   so extra reasoning mostly adds tokens and latency. qwen3.7-flash (most tokens, slowest answers) and gpt-oss-120b (larger, thinking) were
   no more accurate than Mistral Small, which was the fastest and cheapest. That is why Mistral leads `CLOUD_ORDER`.
4. **Where a larger model should matter — and where we did not measure it:** multi-step reasoning, harder "hard" difficulty questions
   with plausible distractors, and answers that need combining several passages. The test set is small and mostly extractive, so we cannot
   claim the six models are equivalent on those; we can only say they were indistinguishable on this set.
5. **Local as the solver.** Each generated question is re-solved by the local model without seeing the key; if it cannot reach the intended
   answer, the question is doubted. Using the free local tier here means the cloud model never grades its own homework and it adds no cost.

## 4. Privacy, reliability, control

| | Ollama | OpenRouter |
|---|---|---|
| Data leaves the device | Never | Yes: only the question and the cited chunks, only when the user ticked "Use cloud models first" in Account |
| Needs internet | No | Yes |
| Rate limits / outages | None (but the laptop must be on and the model loaded) | Provider limits and outages; we fall back to local automatically |
| Spend control | n/a | Consent per account, model allow-list, 1,200-token cap, daily caps, credit check (≥ $1 remaining), max 2 cloud tiers |
| Behaviour on a busy laptop | Slows further (CPU shared with the browser and API) | Unaffected |
| Reproducibility | Same weights forever | Provider may update or retire a model id |

## 5. How Nexus uses each (as built)

- **Cloud first** for Ask, practice, diagnostic, roadmap coach paragraph: measured order, at most two cloud tiers, then local.
- **Local first** for the `simple` task (short checks that do not need a large model), and always for the question solver.
- **Local only** when the user has not consented, has no key, is over a cap, or is offline — the feature still works, just slower.
- The roadmap coach paragraph receives topic names and scores only, never the material text.

## 6. Limitations — please read before quoting these numbers

- **Small sample.** 14 questions per cloud model, 8 for local, one run each, one four-document set. Differences of a second or two are noise;
  the 10× local gap and the qwen slowness are large enough to be real.
- **Local set was smaller** (8 vs 14 questions) and the mix differs, so local vs cloud accuracy percentages are directional only.
- **One local model.** llama3.1 8B Q4 on a 4 GB GPU. A machine with more VRAM or a larger/faster local model would narrow the speed gap
  (a fully-GPU-resident 8B would be several times faster than measured here).
- **Latency includes network and provider queueing** for cloud models, and varies by time of day.
- **Extractive tasks.** The set favours models that copy well. It does not measure deep reasoning, maths, or long-context synthesis.
- **Cost column** is the balance difference reported by OpenRouter and may include rounding; token counts are what the app tracked.
- **Reasoning-token overhead is inferred**, not observed directly.

## 7. Reproduce

```
python scripts/agent_bakeoff.py --local
python scripts/agent_bakeoff.py --cloud all --spend-cap 2.5
```

The OpenRouter key is read from the git-ignored `.env` and is never printed.
