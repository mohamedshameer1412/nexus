# Nexus: frontend plan (Next.js)

**Nexus** is the product name a student sees. The Python package and the repo keep the internal name `studyhub`; only user-facing text
(logo, page titles, emails, docs for students) says Nexus. This plan replaces the earlier server-rendered plan: the frontend becomes a
**Next.js app** with a component library and full responsiveness. Facts about today's code are from 2026-09-20.

**Status legend:** ✅ exists and was tested in a real browser · 🟡 exists, not browser-tested (the quiz feature: written by another agent,
uncommitted, integrity-fixed on 2026-09-20) · ⬜ to build.

---

## 1. Decisions (I made these; veto any)

| Area | Choice | Why | Alternatives considered |
|---|---|---|---|
| Framework | **Next.js (App Router) + JavaScript** (modern ES, `.js`/`.jsx`; current stable Next.js, pinned at scaffold) | You asked for JavaScript; file routing, layouts, middleware for CSP. | Vite SPA (simpler, but you asked for Next). |
| UI library | **shadcn/ui on Radix UI primitives + Tailwind CSS** | Radix gives accessible dialogs, tabs, selects, tooltips, radio groups, collapsibles out of the box; the components are copied into the repo (no runtime dependency lock-in), light and dark are CSS variables, tiny bundle. | **Material UI**: fine, heavier, opinionated look, more runtime CSS. Choose it only if you want Google's look. |
| Icons | lucide-react | Matches shadcn. | |
| Data | **TanStack Query** (fetch, cache, **polling** for background jobs) + a small API client (JSDoc-typed) | Our long jobs are "start, then poll every 3 s"; Query does this with `refetchInterval`. | SWR. |
| Forms | react-hook-form + zod | Client checks that mirror the server's rules; the server stays the authority. | |
| Toasts | sonner | Non-blocking confirmations. | |
| Charts / graph | Recharts for mastery bars; the prerequisite graph as an accessible **nested list first**, a visual graph later | A graph is a nice-to-have; a list is testable and screen-reader friendly. | react-flow (later). |
| Tests | Vitest + React Testing Library (+ MSW), **Playwright** (Edge channel, already available) + `@axe-core/playwright` | Same real-browser method used so far, now with a proper runner. | |
| Safety without TypeScript | **JSDoc types + `jsconfig.json` with `checkJs`** (the editor and CI check them), **zod schemas that validate every API response at runtime**, ESLint with the strict React and accessibility rules, and shape types generated from FastAPI's OpenAPI document (`openapi-typescript` emits `.d.ts` files that JSDoc can import; they are not TypeScript source) | Plain JavaScript has no compiler to catch a wrong field name. The runtime check turns an API/UI mismatch into one clear error instead of a blank screen. | Hand-written shapes (drift). |
| Where the app lives | `frontend/` next to `studyhub/` | | |
| Legacy HTML UI | **Kept until Nexus reaches parity**, then removed | Nothing breaks while the new UI is built; its tests keep guarding the backend. | Delete now (no). |

## 2. Architecture

```
Browser ── Next.js (frontend/, :3000) ──same-origin /api/* rewrite──▶ FastAPI (studyhub/, :8100) ──▶ Repo ▶ SQLite (+ spine)
                                                                          │
                                                                          └──▶ Ollama (local) ▶ OpenRouter (only with key + consent + guards)
```

- **Same origin through a rewrite** (`/api/*` → FastAPI). No CORS, cookies just work, and the CSRF story stays simple.
- **Session:** the existing `sh_session` cookie (HttpOnly, SameSite=Lax, Secure in production). The client never sees or stores the token. `localStorage` is not used for auth.
- **CSRF:** `GET /api/session` returns the session's CSRF token; every mutating request sends it as `X-CSRF-Token`. Login/register use the existing
  double-submit cookie until a session exists. A wrong or missing token is a 403 and changes nothing (as today).
- **CSP:** Next middleware creates a **nonce per request**: `script-src 'nonce-…' 'strict-dynamic'`, `object-src 'none'`, `base-uri 'none'`,
  `frame-ancestors 'none'`, **no `unsafe-inline` and no `unsafe-eval` in production**. (This is what protects us now that JavaScript is allowed.)
- **No `dangerouslySetInnerHTML`.** Search highlighting and quotes are rendered as React nodes. Model and document text is data.
- **Ownership:** unchanged and still enforced in SQL by `repo.py`. A foreign resource is a **404**, never 403. The frontend shows the same "Not found" page.
- **Rendering:** the shell and route guards are server-side; screens are client components using TanStack Query. (Simple, and it matches polling.)
  An unauthenticated visit to any app route redirects to `/login`; the real check is `/api/me` returning 401.
- **Errors:** every API failure is `{ "error": { "code": "...", "message": "..." } }` with the right HTTP status; the client maps `code` to a friendly message.

## 3. The backend gap (the biggest task)

**Today no JSON API exists**: every route returns server-rendered HTML and redirects. Nexus needs a JSON API that **reuses the same Python functions**
(`Repo`, `ingest`, `retrieval`, `qa`, `mcq`, `quiz_flow`, `scoring`) so no business rule is duplicated. Proposed under `/api/v1`:

| Area | Endpoints | Reuses | Status |
|---|---|---|---|
| Session | `GET /me`, `GET /session` (csrf), `POST /register`, `/login`, `/logout` | `auth` | ⬜ |
| Subjects | `GET/POST /subjects`, `GET/PATCH/DELETE /subjects/{id}` (+ counts, progress summary) | `Repo` | ⬜ |
| Materials | `POST /subjects/{id}/materials` (multipart; upload progress), `GET …/materials`, `GET/DELETE …/materials/{doc}`, `GET …/topics`, ⬜ `POST …/materials/url` | `ingest`, `Repo` | ⬜ |
| Search | `GET …/search?q=` | `retrieval` | ⬜ |
| Ask | `POST …/questions` → `{id, status: "pending"}`; `GET …/questions`, `GET …/questions/{id}` (poll until not pending); `POST …/feedback`; `DELETE` | `qa`, `explain` | ⬜ |
| Practice (MCQ) | `POST …/mcq/jobs`, `GET …/mcq/jobs/{id}` (poll), `GET …/mcq?topic=`, `DELETE …/mcq/{id}` | `mcq` | ⬜ |
| Quiz | `POST …/quiz/attempts`, `GET …/quiz/attempts/{id}` (current question / diagnostic / callback / done), `POST …/answer`, `POST …/diagnostic`, `POST …/callback`, `POST …/proctor`, `GET …/result` | `quiz_flow`, `scoring` | ⬜ (🟡 logic) |
| Progress | `GET …/progress`, `PUT/DELETE …/prereqs` | `scoring`, `prereq` | ⬜ (🟡 logic) |
| Account | `GET /account`, `PUT /account/cloud` | `Repo`, `models` | ⬜ |

Rules for the API: pydantic response models (so OpenAPI is exact); list endpoints paginate (`limit`, `cursor`); dates as ISO 8601; the answer to a
practice question is **not** sent until the student asks for it (`GET …/mcq/{id}/answer`), so it cannot be read from the network tab by mistake
before the student chooses to look; the quiz never sends the correct index before an answer is recorded.
FastAPI's `/docs` stays disabled in production; the OpenAPI JSON is exported by a script for type generation.
The existing backend tests (ownership, CSRF, escaping, limits) are re-run against the API layer, one for one.

## 4. Design system and responsiveness

**Tokens (CSS variables, light and dark):** background, surface, border, text, muted, primary (teal, continuing the current accent), success, warning,
danger, focus ring; radius 8 px; spacing scale 4/8/12/16/24/32; type: system sans, 16 px base, 1.6 line height, headings 24/20/16.
Dark mode follows the system and has a manual toggle; contrast is checked with axe (AA).

**Breakpoints (mobile first):** `sm` 640 · `md` 768 · `lg` 1024 · `xl` 1280. Tested widths: **360, 390, 768, 1024, 1440**.

| Element | Phone (< 640) | Tablet (640 – 1023) | Desktop (≥ 1024) |
|---|---|---|---|
| App shell | top bar (logo, subject switcher, avatar menu); **bottom tab bar** inside a subject | top bar; tabs under the title | left rail listing subjects + top bar; tabs under the title |
| Subject sections | one screen per tab (Materials · Ask · Practice · Quiz · Progress) | same, wider cards | same tabs; Ask/Practice show a **two-column** layout (form left, history right) |
| Answer page | stacked; citations `[1]` open a **bottom sheet** with the quote | stacked, inline quote cards | answer left, **sticky evidence panel** right |
| Dialogs (delete, consent) | full-width **bottom sheet** | centred dialog | centred dialog |
| Tables (attempts, mastery) | rendered as **cards** | table | table |
| MCQ options | full-width tappable rows (≥ 44 px) | same | same, keyboard 1–4 / A–D |
| Upload | button + file picker | dropzone | dropzone |

Rules: no horizontal scroll at 360 px (long words and code use `overflow-wrap:anywhere`); touch targets ≥ 44 px; text scales to 200 % without loss;
`prefers-reduced-motion` respected; safe-area insets for the bottom bar; images none, so nothing to lazy-load.

**Component inventory.** From shadcn/Radix: Button, Input, Textarea, Select, Checkbox, RadioGroup, Tabs, Dialog, Sheet, DropdownMenu, Tooltip,
Collapsible/Accordion, Progress, Badge, Alert, Skeleton, Table, ScrollArea, sonner Toaster.
Ours (built once, reused everywhere): **StatusBadge**, **EvidenceQuote** (quote + "✓ found word for word"), **CitationChip** (`[1]` → sheet/panel),
**VerificationList**, **StepLog** (collapsed "How this was produced"), **PassageCard** (with highlighted words), **McqCard** (options, hidden answer, source),
**JobProgress** (elapsed time, "safe to leave"), **MasteryBar**, **PrereqTree**, **UploadDropzone** (progress, per-file result), **EmptyState**, **ErrorState**.

## 5. Accessibility (WCAG 2.2 AA)

Radix primitives for focus trapping and roving focus; a skip link; one `h1` per page; `aria-live="polite"` for job status changes; icons never carry
meaning alone; errors are announced and linked to their field; visible focus ring; colour is never the only signal (status badges carry text);
answer options are a real radio group. Checked with axe in Playwright on every screen and by a keyboard-only pass.

## 6. Screens and flow, start to end (Nexus)

Routes are Next paths; the API each calls is in section 3.

1. **`/login`, `/register`** — form validation mirrors the server (username 3–32, password 8–128); one generic login error; the lock message after 5 failures; show/hide password; success → `/subjects`. `/` redirects.
2. **`/subjects`** — cards with name, description, counts and (G7) a mastery summary; **New subject** in a dialog; empty state. Search across subjects is not needed yet.
3. **`/subjects/[id]` (workspace)** — header with name and actions menu (rename, delete with typed-name confirmation), then **tabs**: **Materials · Ask · Practice · Quiz · Progress**. The tab row is the fix for gap G1 (today Quiz and Progress cannot be reached).
4. **Materials tab** — dropzone (PDF, DOCX, TXT, ≤ 20 MB) with real upload progress; ⬜ "Add a web address" field; list of documents with type, pages, passage count, status badges; **warnings** as alerts (scanned PDF, no bookmarks, instruction-like passages set aside); document page with passages (heading, PDF page) and Remove; **search** box with highlighted results and "weaker matches" section; topics list.
5. **Ask tab** — composer (3–500 chars, counter, Enter to send); history list with status badges. **Answer page** (`/subjects/[id]/questions/[qid]`):
   pending skeleton with elapsed time → **Answer** (numbered statements, `[n]` chips) · **Sources and evidence** (file · section · PDF page, exact quote, ✓) · **Explanation, step by step** (labelled "the model's reasoning") · **Verification** ticks · **This helped / This looks wrong** · collapsed **How this was produced**.
   Other outcomes keep their own badge and copy: *Not answered: nothing was guessed* (closest passages), *No model: matching passages only*, *Your materials disagree* (both sides), *Something went wrong* (retry).
6. **Practice tab** — generate panel (topic select, count 1–10, "Generate"); a **job card** that polls and survives navigation; results ("N of M kept", reasons); **bank** with topic filter chips; McqCard with **Show answer and source** (loads the answer only on request); delete with undo toast.
7. **Quiz tab** — home: topic choice, **notice about what is measured** (gap G3), Start, *Continue your quiz (4 of 10)* (G4), weak topics, recent attempts. **Question screen:** progress, one MCQ, keyboard A–D, submit; a hook records response time, answer changes, tab switches and full-screen exits and sends them with the CSRF header (copy and paste are blocked **only in Assessment mode**, never in Practice mode; see section 12). Then the **diagnostic** (open answer), and on a BLOCK the **prerequisite check** ("Step back to Y" / "Try X again", depth limit 3). **Result:** score, behaviour and trust scores with explanations, topics to review, per-question breakdown with the source of each.
8. **Progress tab** — per-topic mastery bars with state (unknown, learning, mastered, weak) and the trend across attempts; the **prerequisite tree** (list first) with an edit dialog; weak topics link to a practice run. ⬜ Per-topic page (G8).
9. **`/account`** — cloud consent switch with the plain-language warning (passages, never whole files, go to OpenRouter), off by default; shows whether a key is configured and which models are allowed; theme toggle; sign out.
10. **Global** — 404 page identical for "missing" and "not yours"; session-expired toast → `/login`; offline banner; error boundary per tab.

**State matrix (each screen implements all):** loading = skeleton; background job = JobProgress with polling and "you can leave"; empty = one sentence and one action; validation error = field errors, input preserved; model unavailable = the status badge says so and the student's own passages are shown, nothing invented; forbidden/absent = the shared 404; server restarted mid-job = "interrupted, try again".

## 7. Security checklist for the Next app

Nonce CSP with `strict-dynamic`, no inline event handlers · cookies HttpOnly + SameSite=Lax + Secure in production · CSRF header on every mutation · no
tokens or user data in `localStorage` · no secrets in client bundles (only `NEXT_PUBLIC_*` that are safe) · dependencies pinned, `npm audit` in CI ·
no `dangerouslySetInnerHTML` (lint rule) · upload size and type checked on the client for friendliness, on the server for safety · the API's rate limits and
login throttle stay authoritative · `X-Frame-Options`/`frame-ancestors` kept.

## 8. Repository layout

```
frontend/                Next.js app
  app/                   routes (login, register, subjects, subjects/[id]/..., account)
  components/ui/         shadcn components
  components/nexus/      EvidenceQuote, CitationChip, McqCard, JobProgress, ...
  lib/api/               API client + zod schemas + generated .d.ts (from openapi.json), used through JSDoc
  lib/hooks/             useJob (polling), useProctor, useSession
  middleware.js          nonce CSP + route guard
  tests/                 vitest; e2e/ playwright
studyhub/                Python backend (unchanged package name); studyhub/web/ = legacy HTML UI until parity; studyhub/api/ = new JSON API
scripts/export_openapi.py
```
Dev: `uvicorn studyhub.web.app:app --port 8100` (with the API mounted) and `npm run dev` in `frontend/` (proxying `/api`). Production: `next start` and uvicorn behind one origin.

## 9. Testing plan

| Layer | Tool | What |
|---|---|---|
| API | pytest (existing style) | every endpoint: status, ownership → 404, CSRF → 403, limits, escaping; contract test that every response validates against its zod schema and that the schemas match the exported OpenAPI document |
| Components | Vitest + RTL + MSW | each Nexus component: states (loading, empty, error), keyboard, no HTML injection (a quote containing `<script>` renders as text) |
| End to end | Playwright (Edge), real backend with **scripted models**; plus one run with the **real local model** | the whole journey in section 6, second account gets 404, CSP header present without `unsafe-inline`, 0 console errors |
| Responsive | Playwright screenshots at 360 / 390 / 768 / 1024 / 1440 | no horizontal scroll, bottom tab bar on phones, sheet vs dialog, evidence panel on desktop; screenshots are read, not just taken |
| Accessibility | axe in every E2E page + keyboard-only script | zero serious/critical violations |
| Performance | Lighthouse budgets | LCP < 2.5 s on the local build, JS per route within budget |

## 10. Delivery phases

| Phase | Scope | Done when |
|---|---|---|
| **F0 API** | `/api/v1` for session, subjects, materials, search, account; OpenAPI export; CORS not needed | existing HTTP tests have API twins and pass; OpenAPI exports; zod schemas and `.d.ts` shapes generate and `checkJs` is clean |
| **F1 Shell** | Next scaffold, tokens, dark mode, app shell (responsive), login/register/subjects, **Nexus branding** | Playwright: register → create subject at 360 and 1440 px; axe clean; CSP has no `unsafe-inline` |
| **F2 Materials** | dropzone with progress, list, document page, search, warnings | upload the sample files (TXT, PDF, DOCX, scanned, `.exe`), search, remove; screenshots at all widths |
| **F3 Ask** | API for questions + polling; composer, answer page components, history | scripted-model answer, abstain, conflict; real-model run; every quote on screen found in the source file |
| **F4 Practice** | MCQ jobs + bank; McqCard; answer-on-request | generate with a real model; answers not in the network response until requested |
| **F5 Quiz** | quiz API (after the quiz backend is reviewed and browser-tested), question screen, diagnostic, prerequisite check, result, notice | full flow incl. step back and return; integrity tests still pass; Practice and Assessment modes behave as decided in section 12 |
| **F6 Progress** | mastery, prerequisite tree/editor, per-topic page | numbers equal the backend's; a weak topic leads to a practice run |
| **F7 Polish** | a11y and mobile pass, performance budgets, empty/error copy, remove the legacy HTML UI, rename remaining "StudyHub" text | all checklists ticked; legacy tests removed only after parity |

Carried over from the earlier plan: G1 tab navigation (F1/F3), G2 browser tests for quiz (F5), G3 monitoring notice (F5), G4 resume a quiz (F5),
G5 clear rejection messages (F0/F5), G6 consistent words: **Question** (asked), **Practice question** (MCQ), **Quiz** (attempt) (F1 onward),
G7 subject cards show mastery (F6), G8 per-topic page (F6), G9 pagination (F0), G10 web URLs (Phase D, after F2), G11 mobile and keyboard (every phase).

## 11. Risks and open points

1. **The API layer is the largest piece** (about 35 endpoints). Doing it first (F0) keeps the frontend honest; the alternative, a Next.js server that talks to SQLite directly, would duplicate the ownership rules and is rejected.
2. **The quiz backend is unreviewed** beyond the fixes made on 2026-09-20. Do not build F5 on it before its own browser test and review.
3. **JavaScript enlarges the attack surface** compared with the current no-JS pages. The nonce CSP, no raw HTML, and the CSRF header are what compensate; treat any loosening as a bug.
4. **Assessment mode is deterrence, not security.** Blocking copy/paste and counting focus events can be bypassed (a second device, a screenshot). The student is told this is a self-check, not a guarantee, and nothing in it changes mastery.
5. **Local-model latency** (10 s to minutes) shapes the UI: polling, elapsed time, "safe to leave", and never a frozen screen.
6. **Node and browsers:** Node 22 and Edge are installed here; Playwright will use the `msedge` channel. Firefox and Safari are untested.
7. **No compile-time types (JavaScript).** A renamed API field would only fail at runtime. Compensation: the response zod schemas, the contract test, `checkJs`, and Playwright E2E on every screen. If the frontend grows large, converting files to TypeScript one by one stays possible.
8. **Material UI instead of shadcn** is a one-day decision now and an expensive one later; say so before F1 starts.

## 12. Decisions (owner, 2026-09-20)

**1. Quiz modes and monitoring: two modes.**
- **Practice mode (default): nothing is blocked and nothing is monitored** beyond the answer and how long it took. Copy and paste work normally.
- **Assessment mode (the student chooses it): monitoring on, and copy/paste blocked.** The owner's rule: *if it is proctoring, block; otherwise don't.*
  - Before Start, a notice says exactly what happens: tab switches and leaving full screen are counted, copy and paste are blocked on the question, and this is a
    self-check that is not a guarantee. The student ticks "I understand" to start.
  - Blocked copy and paste attempts are counted with the other events. The **answer field for the open diagnostic keeps working for typing**; only paste and
    copy of the question text are blocked. Screen readers must still be able to read the question (blocking uses events, never hides or images the text).
  - **Accessibility path:** a student who cannot use Assessment mode as designed simply uses Practice mode; nothing else depends on it.
- **How the counts are shown ("focus events"):** on the result page, in plain words ("You left this tab 2 times and exited full screen once"), with the same
  wording every time. My recommendation, accepted as the default since the owner asked for it: **never call them cheating, drop the phrase "trust score",
  never let them change mastery, store counts only (no details), delete them with the attempt.** The existing behaviour score becomes the "focus" summary only.
- The monitoring script exists **only** on the Assessment question screen (nonce CSP, CSRF header). Practice screens ship no monitoring code at all.

**2. Order of work: quiz screens wait for the quiz backend review.** Build F0 to F4 first. Before F5, give the existing quiz pages the same treatment as
every earlier phase: review, a real-browser test, a short report, and a written definition of the mastery rule (now 70 % correct = mastered, under 40 % =
weak, at least 2 answers). F5 starts only when that report exists. (Owner asked for my suggestion; this is it.)

## 13. Status (2026-09-20, end of this build)

Built and running: F0 (API incl. quiz and progress endpoints), F1, F2, F3 (Ask, now a chat layout), F4 Practice, F5 Quiz (Practice and Assessment modes), F6 Progress. F7 polish is not done.

Deviations from the plan above, on purpose:
- **Folder is `frontend/`**, not `web/`. No TypeScript: every API response is checked at runtime with zod (`frontend/lib/schemas.js`).
- **Ask is a chat** (owner request): question bubbles on the right, Nexus replies on the left with typing dots, `[n]` chips that open the quoted evidence inline, feedback and delete per reply. The single-answer page `/ask/[qid]` is kept as a full view.
- **Without a model the quiz ends after the multiple-choice questions.** The backend's follow-up question then is a test stub (`[STUB] Explain...`); showing it would be a fake question, so the API finishes the attempt instead. With a model, the follow-up and the step-back-to-prerequisite flow are used; the step-back screen needs a topic prerequisite to be set on the Progress tab.
- **Assessment mode** requires an acknowledged notice; it counts tab switches, full-screen exits and copy/paste attempts and blocks copy/paste. Results show these as "focus events". The backend still stores a behaviour score, but the API and UI never show a trust score.
- Citation chips scroll to and focus the evidence card in place (no bottom sheet).

Known limits: tested in Microsoft Edge only (no Firefox/Safari); dark mode axe-checked on a few pages; the quiz follow-up question with a real model, and the OpenRouter fallback, have not been run in the browser; web URLs as materials (Phase D) are not built.

## 14. Changes after owner feedback (2026-09-20)

- **Theme:** new blue palette (deep #1561AD, mid #0291E0, bright #00BBFF, pale #BAE2F7; hex read off a screenshot, to be confirmed). Light theme only. Sidebar plus navbar added; a Dashboard with charts added.
- **Quizzes are multiple choice only.** The written "explain in your own words" follow-up and the step-back-to-prerequisite screen were removed from the API and UI (the owner asked for MCQs). The prerequisite editor on Progress was removed with it; the backend tables and `/prerequisites` endpoints remain, unused by the UI.
- **Assessment protection strengthened:** full screen requested on start, text selection off, copy/cut/paste, right-click and the matching shortcuts blocked and counted, leaving the page or full screen counted; a live "focus events so far" count is shown. It cannot see other devices or photos of the screen.
- **Error boundary** (`app/error.js`): a page left open across an update now offers a reload instead of Next's bare "Application error" screen.

## 15. Added on 2026-09-20 (owner request)

- **Topic-wise confidence with IRT** (`studyhub/insights.py`): 3-parameter model (discrimination 1, guessing 0.25), Normal(0, 1.2) prior, ability per topic and overall; confidence = P(ability above the proficient line); item difficulty from the student's own other answers to the same question. Shown on Progress, the Report and the Dashboard data. Ported idea from `ai_learnmate` (`irt_probability`, ability update); the implementation is new (Bayesian, with uncertainty).
- **Backtracking:** a wrong answer pulls forward or adds questions from the topic it builds on (confirmed prerequisite links, else the nearest earlier topic), once per missed topic, depth 2, at most 8 per quiz. Migration 8.
- **Quiz kinds:** standard, diagnostic (two per topic), revision (latest mistakes plus shaky topics). **Time limit** option. Migration 8 also stores `kind`.
- **Report** (`/subjects/[id]/report`, print to PDF, CSV) and confidence charts on Progress.
- **Extras:** command palette (Ctrl K), search across subjects, saved answers, answer export (Markdown), practice-question CSV export, flashcards with spaced repetition (SM-2, migration 9), study streak and daily goal, onboarding checklist, change password, export all data, delete account, installable app manifest.
- **Not built:** ask across subjects, web URLs as materials (needs an SSRF-safe fetcher), document viewer beside the chat, weekly e-mail (needs an e-mail service), offline mode. `ai_learnmate` has no "compatibility score" in its code; nothing was ported for it.

## 16. Added on 2026-09-20 (second round)

- **Experience level and diagnostic** (`LevelPrompt`): after the first upload the student says new learner / intermediate / professional. Anything but "new" writes ten questions of different difficulty (easy/medium/hard, requested per call and stored per question, migration 10) and offers a diagnostic test; the result page concludes accuracy per difficulty, a suggested level, and the strongest and weakest topics. Difficulty also seeds the IRT question difficulty.
- **Study roadmap and skill gaps** (`studyhub/roadmap.py`, tab "Roadmap", migration 12): ideas from JobGenie (skill-gap analysis, weekly roadmap with milestones and mini-projects, match score, profile) rebuilt for studying. Gap = target confidence (by level) minus IRT confidence, with evidence per kind of test (diagnostic, regular, revision, assessment, flashcards), root-cause topics (weak prerequisite), trend, and a weekly plan fitted to hours per week and an optional target date. A "coach" paragraph is written from topic names and scores only (never passages).
- **Model routing** (`studyhub/models.py`): OpenRouter first when the key exists AND the student allowed cloud models, then the local Ollama model; per-task model order over the six allowed models, at most two cloud models per task, 1,200-token cap, daily caps and a credit check kept. Simple checks (the independent reader for practice questions) run on Ollama first. `STUDYHUB_PRIMARY=local` restores the old order. Tests never read `.env` and never call the cloud.
- **Materials and reading:** web pages as materials (SSRF-safe fetcher: public addresses only, pinned connection, redirects re-checked, 5 MB cap), a document viewer beside the chat (PDF in the page's own viewer, other files as passages with the cited words marked), notes (own or from chat answers), offline reading through a service worker (data cache emptied on log in/out).
- **Accounts and e-mail:** forgot-password by e-mail one-time code (6 digits, 10 minutes, keyed hash, 5 tries, limits per address, per network address and overall, no account enumeration), e-mail verification, password-changed notice, weekly summary. Migration 11. SMTP settings live in the git-ignored `.env`.
- Known limits: the local model is slow for the diagnostic (about ten minutes on this machine); PDFs are shown by the browser's own viewer, so jumping to the cited page depends on it; Firefox/Safari untested; the OpenRouter path has never been run (no live calls were made, by request).

