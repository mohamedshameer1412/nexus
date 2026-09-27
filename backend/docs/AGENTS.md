# NEXUS Agents: what each one is, how it is built, how it runs

This document explains every agent in the NEXUS codebase. For each one it gives the purpose, the files, the input, the flow, the output, and the safety rules. It was written from reading the code, not from the older design notes. Where the two differ, the code wins.

**How to read it.** Start with section 1 (what "agent" means here) and section 2 (the shared machinery). Every agent in section 3 uses that machinery in the same way, so once you know it, each agent is short.

---

## 1. What "agent" means in NEXUS

An agent here is **a model call wrapped in code that decides what to trust**. The model proposes. Plain code checks, and plain code decides what the student sees.

Three rules hold for every agent:

1. **The model never controls the flow.** Code moves a run from step to step. The model only supplies judgement inside a step.
2. **Nothing the model says is shown until code has verified it.** Quotes must exist word for word in the student's own material. Answer positions are set by the app, not the model.
3. **Every agent has a fallback.** If no model answers, the student still gets something honest, such as the closest passages, a rule-based summary, or an empty result with a stated reason. Nothing is invented.

There are **9 model-backed agents** in the product, **1 rule-based planner**, and **2 demo agents** kept from the hackathon starter kit.

| # | Agent | Kind | File |
|---|---|---|---|
| 1 | Q&A answerer | Model + verifier | `studyhub/qa.py` |
| 2 | MCQ writer | Model + verifier | `studyhub/mcq.py` |
| 3 | MCQ solver | Model (independent check) | `studyhub/mcq.py` |
| 4 | Worked-example tutor | Model + verifier | `studyhub/tutor.py` |
| 5 | Roadmap coach | Model + verifier | `studyhub/roadmap.py` |
| 6 | Career skills extractor | Model + verifier | `studyhub/career.py` |
| 7 | Spot agent (legacy UI only) | Model | `studyhub/quiz_agents.py` |
| 8 | Gate agent (legacy UI only) | Model + code override | `studyhub/quiz_agents.py` |
| 9 | Doubt runner | Wrapper around agent 1 | `studyhub/qa.py` |
| P | Planner and backtracker | Rules only, no model | `studyhub/tutor.py`, `studyhub/twin.py`, `studyhub/insights.py` |
| D1 | Study Agent: generator and validator | Demo | `demo/study/` |
| D2 | Smoke agents: spot and gate | Demo | `demo/smoke/` |

Agent 9 only stores the result of agent 1 against a saved question, so you can also count 8 distinct agents.

---

## 2. Shared machinery every agent uses

### 2.1 The spine (`slice/`)

The `slice/` folder is a small orchestration kit from the hackathon starter.

| Piece | File | What it does |
|---|---|---|
| Store | `slice/store.py` | SQLite. Every step of every run is appended as a new row in a `versions` table. Database triggers block UPDATE and DELETE on it, so history cannot be edited. |
| Runner | `slice/runner.py` | A state machine. Code, not the model, decides the next state. A run can suspend and resume from the database. |
| Budget | `slice/budget.py` | Token and attempt limits kept in the database, so a limit survives a restart. |
| LLM call | `slice/llm.py` | The one place a model is called. It parses the reply into a typed schema, repairs bad JSON once, checks the budget first, and classifies cost errors. |
| Providers | `slice/providers.py` | Ollama (local), OpenRouter (cloud), and a fixture provider for tests. All share one call signature. |
| Callback | `slice/callback.py` | Human-in-the-loop as a saved state: ask, answer, timeout sweep. |

### 2.2 Model tiers (`studyhub/models.py`)

Each agent is handed a list of **tiers** built by `build_tiers(db, user, task=...)`. A tier is one model plus its provider and settings.

- **Local tier.** Ollama, default `llama3.1`. Nothing leaves the machine.
- **Cloud tier.** OpenRouter. It is added only if every check passes: an API key exists, the student ticked cloud consent, the model is on the allow-list, the per-user and app-wide daily token caps are not reached, and at least $1.00 of credit is left.
- **Order.** Cloud is tried first by default. Set `STUDYHUB_PRIMARY=local` to reverse it. Tasks in `LOCAL_FIRST_TASKS` (currently `simple`) always go local first.
- **Task types.** `answer`, `write`, `plan`, `simple`. Each has its own preferred cloud model order, chosen from a measured bake-off.
- **Limits.** At most 2 cloud models are tried per task, and cloud output is capped at 1200 tokens.

An agent walks the list in order. If the first tier errors or cannot produce a verifiable result, it moves to the next.

### 2.3 The citation verifier (`studyhub/citations.py`)

Pure code, no model. A statement survives only if **every** citation passes:

1. The passage number is one the model was actually given.
2. The quote appears word for word, in one piece, in that passage. Whitespace and typographic quotes and dashes are normalised. Case and wording are not.
3. The quote is long enough to mean something.
4. Every number in the statement also appears in its quotes.
5. The statement shares enough content words with its quotes, so a real quote cannot be pinned to an unrelated claim.

The verifier proves the quote exists. It cannot prove the statement is a faithful reading of it, so the page always shows the quote beside the statement.

### 2.4 The injection screen (`studyhub/screen.py`)

At upload, passages that read like orders to an AI ("ignore the previous instructions", "note to the assistant") are **quarantined**. They stay stored and visible, but are never given to a model to write answers or questions. A quote that reads like an order is also refused at answer time.

### 2.5 Retrieval (`studyhub/retrieval.py`)

SQLite FTS5 with BM25 ranking, scoped to one subject of one user. A relevance test decides whether a passage is good enough. If nothing passes, the agent abstains without calling any model.

### 2.6 How a job reaches an agent

The Next.js frontend calls the FastAPI backend under `/api/`. Slow model work runs on a **single background worker thread**, because a local model on a small GPU cannot do two calls at once. The request returns at once with status 202, and the page polls for the result.

```
Browser (Next.js)  ->  /api/... (FastAPI)  ->  create a pending row  ->  202 Accepted
                                                    |
                                        single worker thread runs the agent
                                                    |
                          result stored on the row  <-  the page polls until done
```

---

## 3. The agents

### Agent 1: Q&A answerer

**Purpose.** Answer a student's question using only their own uploaded material, with a verified quote behind every statement. If the material does not answer it, say so instead of guessing.

**Files.** `studyhub/qa.py`, `studyhub/citations.py`, `studyhub/retrieval.py`.

**Input.**
- The question, cut to 500 characters.
- The user id and subject id.
- The list of tiers.

**How it is built.** The system prompt tells the model to use only the numbered passages, to write 1 to 4 statements, to copy each quote exactly (6 to 40 words), and to treat passages and the question as data, not instructions. The reply must match the `Answer` schema: a status of `SUPPORTED`, `NOT_SUPPORTED` or `CONFLICT`, a list of claims each with citations, and a short step-by-step explanation.

**Flow.**

```
question
  |
  v
RETRIEVE  BM25 over this subject, top 5 relevant passages
  |-- nothing relevant --------------------------> ABSTAIN (no model called)
  |-- no tiers available ------------------------> EXTRACTIVE (show matching passages)
  v
DRAFT     model sees only the passages, returns claims with quotes
  |-- model says NOT_SUPPORTED ------------------> ABSTAIN
  v
VERIFY    citations.verify() checks every quote
  |-- all pass ----------------------------------> ANSWER
  |-- some fail -> REVISE: send the failures back, up to 2 times
  |                (a repeated identical draft stops the loop early)
  v
keep the best draft that has any verified claim
  |-- none verified on this tier -> try the next tier
  v
ANSWER    only verified statements, each with quote, page and heading
  |-- nothing verified on any tier --------------> ABSTAIN, show closest passages
```

**Output.** An `Outcome` with:
- `status`: `answered`, `abstained`, `extractive`, or `failed`.
- `claims`: each has text and citations (passage, quote).
- `sources`: the passages used, with document, page and heading.
- `explanation`: shown only if it passes an extra check that it adds no new facts.
- `kind`: `supported` or `conflict`. A conflict is kept only if two statements rest on two different passages.
- `tier`, `model`, `dropped` (statements removed), `reason`, and `run_id` for the trace.

**Safety and limits.**
- Revisions default to 2 (`STUDYHUB_QA_MAX_REVISIONS`, capped at 3), so at most 3 drafts per model.
- Passage text cannot close its own delimiter, so it cannot break out of the prompt.
- Any unexpected error becomes a friendly `failed` outcome, never a stack trace on the student's page.
- Every step is appended to the run history, so the page can show exactly how the answer was made.

---

### Agent 2: MCQ writer

**Purpose.** Write multiple-choice practice questions from a subject's material. Each question must rest on a real quote.

**Files.** `studyhub/mcq.py`, `studyhub/citations.py`.

**Input.**
- User, subject, optional topic, and a count (default 5, maximum 10).
- Tiers, a random seed, and a purpose (`practice` or `diagnostic`).
- Existing questions, so it does not repeat them.

**How it is built.** For each topic, the code picks a random window of 3 consecutive passages (each at least 120 characters, never quarantined) and asks for up to 3 questions at once. The model writes the question, the correct answer, exactly three wrong answers, a quote, the passage number, an explanation and a difficulty. It never writes which letter is correct.

**Flow.**

```
pick topics with material   (questions are shared out across topics)
  |
  v
for each batch of up to 3 questions:
  DRAFT    model writes questions from a 3-passage window
  VERIFY   code checks every rule (below)
  SOLVE    agent 3 answers each surviving question without seeing the key
  REVISE   rejected questions go back with the reasons (up to 2 rounds)
  |
  v
STORE    the app shuffles the options and records the answer position
```

**What `verify` rejects.** These are all plain code checks.
- Question not 12 to 300 characters, or it mentions "the passage" or "the text".
- Correct answer contained in the question.
- Not exactly 3 wrong answers, labels such as "A)", or "all of the above".
- Two options identical or nearly identical.
- Correct answer far longer than the wrong ones, which gives it away.
- A duplicate of an existing question.
- Quote missing from the named passage, too short, too long, or reading like an instruction.
- Correct answer not stated by the quote, or numbers not in the quote.
- A wrong answer that nearly copies the source. It might also be true, so it is refused.

**Output.** A stored question item with the question, four shuffled options, the answer index, the explanation, the quote, the source chunk, page and heading, the difficulty, and a `solver` flag of `agreed` or `skipped`. The overall result also reports the count rejected and why any topic under-delivered.

**Safety and limits.**
- With no model available it returns an empty result and says so. It never makes questions up.
- A diagnostic asks for a spread of easy, medium and hard, and uses one revision round so a slow local model finishes in minutes.
- The system trades quantity for correctness. The code comments say a wrong answer key is worse than fewer questions.

---

### Agent 3: MCQ solver

**Purpose.** An independent reader that catches ambiguous questions and wrong keys.

**File.** `studyhub/mcq.py`, the `_solve` function.

**Input.** The same passages and the surviving questions, **without** the answer key.

**How it is built.** A separate call with its own prompt. The model picks a letter for each question or answers `NONE` if no option, or more than one option, is clearly supported.

**Flow.** If the chosen letter matches the intended one, the question is marked `agreed`. If not, the question is rejected and sent back to the writer with the reason.

**Output.** One pair per question: letter chosen and letter intended. If the call fails, that question is kept and marked as not independently checked.

**Design note.** This job is simple, so it runs on the **local** model when one exists. That keeps cloud credit for the writing.

---

### Agent 4: Worked-example tutor

**Purpose.** Write one step-by-step worked example for a topic, pitched at the student's level, using only that topic's own passages.

**Files.** `studyhub/tutor.py`, with the runner `_process_example` in `studyhub/web/app.py`.

**Input.**
- The topic and up to 6 non-quarantined passages, each cut to 900 characters.
- The student's level (`new`, `intermediate`, `professional`), which sets the wording style.

**How it is built.** The reply schema is `ExampleOut`: a problem, 3 to 6 steps (each with text and a quote), an answer, and a follow-up check question.

**Flow.**

```
student asks for a worked example -> a pending "intervention" row is created
  |
  v
for each tier (task "answer"): model writes the example
  |
  v
clean_example(): keep only steps whose quote is really in the passages;
                 refuse links and markup; need at least 2 good steps
  |-- passes -> store it
  |-- fails on every tier -> key_passages(): a plain walk-through of the
                             topic's own passages, labelled as not model-written
```

**Output.** A stored payload with the problem, verified steps, answer, check question, and a `from_model` flag. The result is recorded as a study action, so the planner can later see whether it helped.

---

### Agent 5: Roadmap coach

**Purpose.** Write a short plain-text study plan for a subject from the student's own numbers.

**Files.** `studyhub/roadmap.py`, with the runner `_process_coach` in `studyhub/web/app.py`.

**Input.** A JSON summary of up to 12 topics in priority order. It holds each topic's status, confidence percent, answer count, trend and weak prerequisites, plus the target, weekly hours, goal and this week's focus.

**How it is built.** The prompt asks for at most 120 words in three parts: where the student stands, the two most important things this week, and one habit tip. It may use only the topic names and numbers given.

**Flow.**

```
tiers (task "plan"): model writes {"text": "..."}
  |
  v
clean_coach(): accept only if 40 to 1400 characters, no links, no markup
  |-- ok -> store text, model name, and a hash of the inputs
  |-- no tier gives an acceptable text -> rule_coach(): a plain summary
                                          built from the same numbers
```

**Output.** Coach text, the model used (or "rules"), and a hash. If the plan inputs change, the hash no longer matches, so the app knows the text is stale.

**Note.** The gap and plan numbers themselves come from code (`skill_gaps`, `build`), not from the model. The model only phrases them.

---

### Agent 6: Career skills extractor

**Purpose.** Read a pasted job description and list the skills it asks for. The app then checks each skill against what the student has actually shown.

**Files.** `studyhub/career.py`, with the runner `_process_career` in `studyhub/web/app.py`.

**Input.** A job title and the description text, cleaned and cut to 8000 characters.

**How it is built.** The reply schema is a list of skills, each with a name, an importance (`required` or `preferred`) and the quote it came from.

**Flow.**

```
tiers (task "plan"): model lists skills with quotes
  |
  v
_valid(): keep a skill only if its quote is really in the description;
          drop repeats; cap at 15
  |-- none survive on any tier -> rule_skills(): bullet lines and lists
                                  under requirement-like headings
  v
assess() matches each skill to the student's own topics and answers:
   verified     enough answers on a matching topic, confidence at least 70%
   developing   a matching topic with answers, not yet solid
   not_tested   material covers it, but no answers yet
   no_evidence  nothing in the materials and no answers
```

**Output.** The skill list with statuses, a weighted readiness score (required skills count double), and suggested next steps. A skill with no evidence is shown as "no evidence", never as "weak". Suggestions are labelled as templates.

---

### Agent 7: Spot agent (legacy UI only)

**Purpose.** Write one open-ended diagnostic question for a topic at a given difficulty from 1 to 3.

**File.** `studyhub/quiz_agents.py`, `spot_agent`.

**Input.** Topic name, difficulty, and the student's earlier objections on that topic, so the question targets known gaps.

**Flow.** One call returns `{"content": "question"}`. If the call fails, a generic question is used: "Explain the core idea of X in your own words." The quiz never crashes because the question generator failed.

**Output.** One question string.

### Agent 8: Gate agent (legacy UI only)

**Purpose.** Judge the student's written answer as `PASS` or `BLOCK`.

**File.** `studyhub/quiz_agents.py`, `gate_agent`.

**Input.** Topic, question, the student's answer, earlier verdicts on this topic, and the prerequisite topic from the graph.

**Flow.** One call returns a status, up to three objections, and a suggested prerequisite. Code then applies these rules:
- The model decides only PASS or BLOCK and the objections.
- The prerequisite is **always resolved from the topic graph in code**. If the model names an unknown one, it is overridden.
- If the model cannot be reached, the result is a conservative `BLOCK` with the graph prerequisite.

**Output.** `{topic_id, status, objections, prerequisite_id}`.

**Where they run.** Agents 7 and 8 are driven by the state machine in `studyhub/quiz_flow.py` through the old server-rendered pages in `studyhub/web/app.py`. Those pages are **switched off** unless `STUDYHUB_LEGACY_UI=1`. The current Next.js quiz is multiple choice only and does not call them. In tests they use stubs (`stub_spot`, `stub_gate`).

---

### Agent 9: Doubt runner

**Purpose.** Answer a question that the student saved as a "doubt", and store the outcome on that record.

**File.** `studyhub/qa.py`, `run_doubt`.

**Flow.** It loads the pending doubt, calls agent 1, links the run id to the doubt, and writes the status, claims, sources, model and reason. It is written to be safe on a worker thread with its own database connection.

---

### Planner and backtracker (rules only, no model)

These make decisions that could have used a model, but do not. They are deterministic on purpose.

**Planner** (`tutor.next_actions`, used by `twin.py`). It ranks topics below target by gap size, weight in past papers, drift (slipping topics) and deadline pressure. If a topic builds on a weak one, it aims at the root. It then picks an action from the ladder: worked example, flashcards, revision, practice. If an action was followed by no improvement, it switches to a different one.

**Improvement loop** (`tutor.verify`, `tutor.memory`). After 3 or more new answers on a topic, it records whether confidence improved, stayed the same, or fell. It remembers which kinds of action have worked for this student.

**Backtracker** (`insights.backtrack`). This is what runs in the current frontend quiz. After a wrong answer it queues questions from the topic's prerequisite, to be asked next. Limits: 2 questions per prerequisite, depth of 2, at most 8 backtrack questions per quiz, and one step back per missed topic.

**Ability estimate** (`insights.estimate`). An item-response style estimate of ability per topic, which feeds difficulty advice and the planner.

---

## 4. The callback (human-in-the-loop) mechanism

There are two implementations of one idea: **asking a person is a saved state, not a blocking call.**

**Spine version** (`slice/callback.py`)

| Function | What it does |
|---|---|
| `ask` | Saves the question, sets the run to `AWAITING_EXPERT`, returns at once. |
| `answer` | Saves the answer as an `expert_answer` record, then wakes the run. Answers are write-once. |
| `sweep` | Expires unanswered questions into `unresolved_no_expert`, so the run continues. |

The demo Study Agent uses this for its human review step.

**Quiz version** (`studyhub/quiz_flow.py`, legacy UI only). After a BLOCK, if a prerequisite exists, the attempt gets `callback_state = waiting` and the student chooses **Step back** or **Retry**. After 60 seconds it auto-picks Step back and records a timeout. Step back pushes the prerequisite onto the topic stack. Retry stays on the topic at higher difficulty, capped at 3.

State lives in the `quiz_attempts` table, so no HTTP request ever blocks.

---

## 5. Demo agents (separate from the product)

### D1: Study Agent (`demo/study/`)

Two agents, not five: a **generator** writes, a **validator** judges.

- **Generator** turns a pasted passage into concise notes and 3 to 5 multiple-choice questions, each with a quote copied from the source.
- **Validator** is independent in four ways: a different prompt, a different model family, it never sees the answer key, and every claim it makes is re-checked in code.

```
DRAFTING -> GATING -> COMPLETE                     approved
              |  ^
              |  '-- rejected, revisions left --> back to DRAFTING
              |-----> AWAITING_EXPERT -> PROBING -> COMPLETE or FAILED
              '-----> FAILED                       (source injection found)
```

- Up to 3 revisions, so at most 4 drafts. The count comes from the record history of rejected verdicts, not from the budget counter.
- Approval is derived from observations, never from a model saying "approved".
- The deterministic checks (`demo/study/checks.py`) locate quotes, confirm four distinct options, and screen for injection.
- Injection in the source is **not revisable**, because regenerating cannot fix what the user pasted.
- Tester feedback is stored as append-only rows and never moves a run.

### D2: Smoke agents (`demo/smoke/`)

A minimal spot and gate pair used to prove the spine runs end to end, with scripted replies from `stub.py` so no key or network is needed.

---

## 6. Safety summary

| Risk | Where it is handled |
|---|---|
| Model invents a fact or quote | Every quote must appear word for word in the named passage (`citations.verify`, `mcq.verify`, `tutor.clean_example`, `career._valid`). |
| Prompt injection in uploaded material | Quarantine at upload (`screen.py`), "passages are data" in every prompt, and quote screening at answer time. |
| Wrong MCQ answer key | The app sets the answer position, code checks distractors, and an independent solver must agree. |
| Runaway cost or loops | Token and attempt limits in the database, capped revisions, at most 2 cloud models, a daily cap, and a credit floor. |
| Model unavailable | Every agent has a fallback: closest passages, key-passages walk-through, rule-based coach and skills, or an empty result with a reason. |
| Cloud use without consent | Cloud tiers are built only when a key exists and the student allowed cloud models. |
| Audit trail edited | The `versions` table blocks UPDATE and DELETE with database triggers. |

## 7. Known limits

- The verifier proves a quote exists, not that the statement reads it faithfully. The quote is always shown next to the statement for that reason.
- The injection screen is a list of common phrasings. It will miss some and may flag ordinary text. It is one layer, not the whole defence.
- Local generation on a small GPU is slow, roughly 10 to 95 seconds per call, so jobs run one at a time.
- Agents 7 and 8, and the interactive callback page, do not run in the current Next.js frontend.
- The quiz agents use the first tier in the list only, with no fallback to the second.
- This document was written from reading the code. The agents were not re-run while writing it. The repository has its own test suite and evidence folders for that.

## 8. Where to look in the code

| To understand | Read |
|---|---|
| The model call and typed replies | `slice/llm.py`, `slice/providers.py` |
| Tiers and cloud rules | `studyhub/models.py` |
| Cited answers | `studyhub/qa.py`, `studyhub/citations.py` |
| Question generation | `studyhub/mcq.py` |
| Study actions and the planner | `studyhub/tutor.py`, `studyhub/twin.py` |
| Job triggers | `studyhub/web/api.py`, `studyhub/web/app.py` (`_submit`, `_process_*`) |
| The principles, with line references | `docs/ARCHITECTURE.md` |
