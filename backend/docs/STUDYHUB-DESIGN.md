# StudyHub — design for approval

**Status:** proposal. No code is written from this yet. Approve it, or change the parts you disagree with (§13).

A multi-user study platform. Each student registers, creates **subjects**, uploads materials into a subject, asks
doubts that are answered **only from that subject's materials, with verified citations**, generates and takes quizzes, and
has **progress tracked per subject and per topic**. Everything is stored in SQLite.

---

## 1. Goals and non-goals (version 1)

**Goals**
1. Accounts: register, log in, log out. Every row belongs to a user; users never see each other's data.
2. Subjects: any number per user. Every feature below is scoped to exactly one subject.
3. Materials: **TXT, PDF, DOCX, and web URLs** → text with page/heading locators → searchable chunks.
4. Cited Q&A that **abstains** instead of guessing.
5. Quizzes from the materials, with the validate → revise → (human/abstain) loop we already have.
6. Assessments with deterministic scoring; progress and weak-topic tracking; **backward pass** to prerequisite topics.
7. Local-first models; OpenRouter only as a budget-guarded fallback.

**Non-goals (v1):** OCR for scanned PDFs (detected and reported instead), teacher/admin roles, email verification and
password reset, non-English content, real-time collaboration, mobile app.

## 2. Principles (each one is testable)

| Principle | How it is enforced |
|---|---|
| **A claim is shown only if code verified it.** | Every claim carries `chunk_id` + `quote`; code checks the quote is verbatim in that chunk and the chunk was retrieved. Failing claims are dropped; nothing left → abstain. |
| **Scoping lives in SQL, not in the UI.** | One `Repo` layer; every method takes `user_id` and the query filters by it (and by `subject_id`). Leakage tests try to break it. |
| **Models propose, code decides.** | Routing, scoring, mastery, budgets and prerequisites are plain code. |
| **Materials are untrusted input.** | Injection screen + quote verification + no tool access for the model. |
| **Local first, cloud last, cost-capped.** | §9. |
| **Append-only history for anything we may need to explain.** | Answers, attempts and pipeline runs are append-only (reusing `slice/store.py`). |

## 3. Architecture

```
studyhub/                      NEW package (slice/ is not edited)
  db.py        schema + migrations (schema_version), one connection helper
  repo.py      the ONLY place SQL lives; every function takes user_id
  auth.py      scrypt hashing, sessions, CSRF, login throttling
  ingest/      txt.py pdf.py docx.py url.py  → common Document(text, locators, warnings)
  chunker.py   heading-aware chunks with page + heading path
  retrieval.py subject-scoped FTS5 (BM25); vector search added later behind the same function
  qa.py        the `ask` Flow: retrieve → answer → verify → revise → answer | abstain
  quiz.py      the `quiz` Flow: per-topic generation → validate → question bank
  scoring.py   attempts, scoring, mastery, backward pass (no LLM anywhere)
  llm_chain.py provider chain + cloud budget guard (uses slice/providers.py)
  web/         FastAPI app: pages + JSON API
```

Reused as-is: `slice/store.py` (each Q&A or quiz generation is a **run** with an execution trace), `slice/runner.py`
(deterministic state machine), `slice/providers.py`, `slice/budget.py`, and from `demo/study`: `checks.py` (verbatim quotes,
injection screen, duplicate options), `trace.py`, `feedback.py`. One SQLite file holds both the spine tables and the new ones.

## 4. Data model (SQLite)

```
users(id, username UNIQUE, pw_salt, pw_hash, scrypt_params, cloud_consent DEFAULT 0, created_at)
sessions(token_hash PK, user_id, csrf, created_at, expires_at)
login_attempts(username, ip, at)                                  -- throttling

subjects(id, user_id, name, description, created_at, UNIQUE(user_id, name))
documents(id, subject_id, kind: txt|pdf|docx|url, title, source, sha256, bytes, pages,
          status: parsed|empty|failed, warnings_json, created_at, UNIQUE(subject_id, sha256))
topics(id, subject_id, parent_id, name, path, ordinal, origin: heading|manual|model)
topic_prereqs(topic_id, prereq_id, origin: manual|suggested, confirmed)   -- only confirmed edges are ever used
chunks(id, subject_id, document_id, topic_id, ordinal, page_start, page_end, heading_path, text, sha256)
chunks_fts  FTS5 over chunks.text                                  -- always joined with subject_id

questions(id, subject_id, topic_id, payload_json, source_chunk_id, source_quote,
          status: approved|rejected|retired, run_id, model_tier, created_at)      -- the question bank
quizzes(id, user_id, subject_id, topic_ids_json, mode: practice|assessment, time_limit_s, created_at)
quiz_items(quiz_id, ordinal, question_id, option_order_json)       -- options shuffled per attempt
attempts(id, quiz_id, user_id, started_at, finished_at, score, max_score)
attempt_answers(attempt_id, question_id, chosen, correct, confidence, seconds, answered_at)   -- append-only
topic_progress(user_id, topic_id, answered, correct, mastery, state, updated_at)  -- derived; recomputable

doubts(id, user_id, subject_id, question, run_id, status: answered|abstained, tier, created_at)
doubt_claims(doubt_id, ordinal, text, chunk_id, quote, verified)   -- what was shown, and what was dropped
cloud_usage(id, user_id, day, provider, model, tokens, cost_usd, at)
feedback -> reuse the existing `feedback` record kind on the run
```

Uploaded originals are kept on disk under `data/uploads/<user>/<sha256>` (git-ignored), never inside SQLite.

## 5. Ingestion

`upload → sniff type → size/page limits → extract → clean → chunk → dedupe by sha256 → index (FTS5) → topics`

| Type | Method | Notes |
|---|---|---|
| TXT | decode UTF-8 (fallback cp1252) | headings from Markdown `#` and ALL-CAPS/numbered lines |
| PDF | `pypdf`, per page | page number kept; **no text → status `empty` + "scanned PDF, OCR not supported"**; encrypted → `failed` |
| DOCX | `python-docx` | heading styles → topics; guard the decompressed size (zip bombs) |
| URL (phase D) | `httpx` + `beautifulsoup4` | see §10; keep `<h1-3>` structure, drop nav/script |

Chunks are ~900 characters split on paragraph boundaries, keep `heading_path` ("Ch 3 › Trees › Traversal") and
`page_start/end`, so every citation can say *where*. Limits (configurable): 20 MB per file, 400 pages, 2 M characters per subject.

**Topics come from structure:** PDF outline / headings / DOCX heading styles / Markdown headings. Students can rename,
merge, split. A model is used only when a document has no structure, and its suggestions are shown for confirmation.
**Prerequisites** are edges between topics: suggested (by heading order or the model), **used only after the student confirms**.

## 6. Cited Q&A (the anti-hallucination core)

```
RETRIEVING → DRAFTING → GATING (verify) ─pass→ COMPLETE (answered)
                 ▲            │fail, ≤3 tries
                 └── revise ──┘ ── still failing / nothing found → ABSTAINED
```

1. **Retrieve** (`retrieval.py`): top-k chunks by BM25, **`WHERE subject_id = ?`**. If the best score is below a threshold → abstain now.
2. **Draft**: the model sees only those chunks and returns
   `Answer{claims:[{text, citations:[{chunk_id, quote}]}]}` (≤5 claims; fits the 1,200-token cap).
3. **Verify (code, not a model):** each citation's `chunk_id` must be one that was retrieved, and `quote` must appear
   **verbatim** (whitespace/typography-normalised, case kept) in that chunk; a claim needs ≥1 valid citation; a cheap
   lexical-overlap check between claim and quote catches a real quote attached to an unrelated claim.
4. **Revise** with the list of failures (existing backward edge, max 3). Then either show the verified claims or abstain.
5. **Abstain, helpfully:** "This isn't in your materials for *Subject*. Closest passages: … Upload something on X or rephrase."
   These passages are shown verbatim, so even the fallback cannot hallucinate.

What this guarantees, precisely: **every displayed claim has a quote that really exists in the student's materials.** It does
*not* guarantee the quote is interpreted correctly (an entailment gap). So the UI always shows the quote, page and
heading beside each claim, and a "this looks wrong" button that records the doubt for review. An optional model
"does this quote support this claim?" pass is advisory (our 8B validator was unreliable at semantic checks), never a gate.

Answers use only the materials. A labelled "outside your materials (unverified)" mode is **not** in v1.

## 7. Quizzes

- Generated **per topic from that topic's chunks** (never the whole subject at once), 2–3 questions per call.
- Each question stores `source_chunk_id` + verbatim `source_quote`; validated by the existing code checks plus three
  fixes our QA found: near-duplicate options, a verified quote for every note/claim, and deterministic option shuffling
  (keys were clustering on "B").
- Approved questions go into the **question bank**. Building a quiz from the bank calls **no model**; attempts and scoring cost nothing.
- Revision loop unchanged: reject → structured feedback → regenerate (≤3) → discard. (For a bank, "discard" replaces "human review".)

## 8. Assessment, progress, backward pass

- **Attempt:** practice (immediate feedback) or assessment (feedback at the end, optional time limit). Each answer stores
  choice, correctness, confidence (1–5) and seconds. Wrong answers show the stored explanation **and its source quote**.
- **Mastery per topic (simple and explainable):** weighted accuracy over the last 10 answers, newest weighted highest.
  State: `new` (<3 answers) · `weak` (<0.5) · `learning` · `mastered` (≥0.8 with ≥5 answers). The dashboard shows the
  answers behind every number.
- **Backward pass (from your NEXUS design):** when a topic turns `weak`, the app selects its **confirmed** prerequisite topics
  (code, from `topic_prereqs`) ordered by their own mastery, queues a short quiz on the weakest, and re-tests the original topic
  after the prerequisite improves. A model may explain *why*, but never chooses the route.
- **Dashboard per subject:** coverage (topics with materials / practised), mastery by topic, weak topics, recent attempts,
  time spent, and "study next".
- Spaced repetition (Leitner boxes) is phase D.

## 9. Models and cost (OpenRouter budget: $10, 1,200-token cap)

Provider chain, config-driven, with the tier that answered shown in the UI:

`Ollama llama3.1` → *(optional second local model)* → `OpenRouter` → **extractive (no generation)**

- OpenRouter is used **only if** a key exists **and** the user ticked cloud consent **and** the budget guard allows it.
  (Materials leave the machine on that path; this is why consent exists.)
- Cloud sees only retrieved chunks (about 2,000 tokens), never a whole document. Each request is capped at 1,200 output tokens.
- **Budget guard** (`cloud_usage`): per-user and global daily token caps, and refuse when remaining credit (from OpenRouter's
  `/key`, the same call `doctor.py` uses) drops below $1. Identical (question, chunk-set) pairs reuse the stored answer.
- Suggested cloud roles from the earlier bake-off (*measured on the old verdict task, not on these tasks*):
  `inclusionai/ling-3.0-flash` main, `mistralai/mistral-small-3.2-24b-instruct` second family, `openai/gpt-oss-120b` rare hard
  cases, avoid `qwen/qwen3.7-flash`; re-test `z-ai/glm-5.3-flash` and `deepseek/deepseek-v4-flash-0731` on cited answers
  and quiz generation before trusting any of them (about 20 calls, cents).
- Local reality: on the 4 GB GPU one generation is ~75–105 s. Q&A will be slow locally; the UI shows progress and never blocks a request.

## 10. Security

- **Passwords:** `hashlib.scrypt` with a per-user salt; constant-time comparison; login throttling per username and IP.
- **Sessions:** random token, only its hash stored in SQLite; `HttpOnly` + `SameSite=Lax` cookie; CSRF token on every state-changing request; expiry.
- **Ownership:** all SQL goes through `repo.py`; leakage tests cover user A→B and subject A→B for every read route.
- **Uploads:** extension **and** content sniffing, size limits, random storage names (no path traversal), zip-bomb guard for DOCX.
- **URLs (phase D):** http/https only; resolve the hostname and **block private/loopback/link-local ranges (including cloud metadata
  addresses) and re-check after every redirect**; limit redirects, size and time; no cookies forwarded.
- **Prompt injection:** documents and pages are untrusted; the injection screen runs at ingest, retrieved text is delimited as data,
  and citations are verified in code, so a poisoned passage can mislead wording but cannot fabricate a citation.
- **Output:** everything HTML-escaped. **Secrets:** `.env` only; never in the repo or logs. Do not expose this on a public URL without HTTPS.

## 11. Testing (the claim must be measurable)

| Suite | What it proves |
|---|---|
| Unit | schema, repo, auth, chunker, scoring/mastery, verification, budget guard |
| **Hallucination suite** | answerable questions (verified citations), **unanswerable questions (must abstain)**, a document with injected instructions, fake-quote attempts, cross-subject retrieval |
| **Leakage suite** | user A cannot read/modify user B; subject A's text never appears in subject B's answers |
| Ingestion fuzz | empty/scanned/encrypted PDF, huge file, malformed DOCX, zip bomb, weird encodings |
| URL safety | localhost, `169.254.169.254`, redirect-to-private, oversized page, slow server |
| Fixture / live Ollama | whole flows with scripted replies, and real-model runs recorded like `docs/qa-evidence/` |
| Browser (Edge, real) | register → subject → upload → ask → quiz → progress, with real clicks |

Reported as **demonstrated / implemented but unverified / planned**, as in `docs/FULL_TEST_REPORT.md`.

## 12. Phases and "done when"

| Phase | Scope | Done when |
|---|---|---|
| **A1** | users, sessions, subjects, `repo.py`, pages | register/login/logout work in a real browser; leakage tests pass |
| **A2** | TXT/PDF/DOCX ingestion, chunks, FTS5, topics from headings | files become searchable chunks with pages; scanned PDF is reported, not silently empty |
| **A3** | cited Q&A + verification + abstain + UI | hallucination suite passes; every shown claim verifies; unanswerable questions abstain |
| **B** | per-topic quiz generation, strengthened validator, question bank | approved questions have verified quotes; a quiz is built with zero model calls |
| **C** | attempts, scoring, mastery, dashboard, backward pass | a weak topic triggers a graph-valid prerequisite quiz and a re-test; numbers are explainable |
| **D** | URLs, vectors/hybrid retrieval, spaced repetition, cost meter, live OpenRouter tests | SSRF tests pass; cloud spend visible and capped |

Each phase ends with the test suite green, a short test report, and a commit. New dependencies (`python-multipart`, `pypdf`,
`python-docx`, later `beautifulsoup4`) are added to `requirements.txt` and installed only with your say-so.

## 13. Decisions I made for you (please veto any)

1. Student-only accounts; no teacher/admin role. 2. English only. 3. No OCR. 4. Materials-only answers, no "general knowledge" mode.
5. Structure-first topics, prerequisites confirmed by the student. 6. Keyword retrieval (FTS5) first, vectors later.
7. Ollama first; OpenRouter only with key + consent + budget. 8. No email verification / password reset.
9. New code in `studyhub/`; `slice/` untouched. 10. SQLite file in a git-ignored `data/` folder.

## 14. How this maps to your review criteria (from the NEXUS report)

| Criterion | What the design produces |
|---|---|
| Working agentic slice (35) | traces for Q&A and quiz runs, including the backward edge and the prerequisite backward pass |
| Real people used it (35) | per-user accounts and logs, existing feedback capture, attempts by testers, an evidence export |
| Whether it helped (20) | per-topic mastery before/after a backward pass, repeated-attempt comparison |
| How we worked (10) | one commit per phase, a test report per phase |

Nothing here counts as evidence until real people have actually used it; the tooling only makes that evidence easy to collect and honest.
