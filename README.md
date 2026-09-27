# Nexus StudyHub

Nexus helps a student study from their own material. Upload notes, slides or a scanned handout, then ask questions, practise, take quizzes and follow a plan. Every answer is taken only from what was uploaded and shows the passage it came from. When the material does not cover a question, Nexus says so instead of guessing.

The project combines the StudyHub engine and agents from the deadlock codebase with the Nexus product flow and brand.

## What is in here

```
backend/    FastAPI + SQLite. Ingest, retrieval, answers, quizzes, IRT scoring, agents, analytics, reports
frontend/   Next.js 15 App Router, Tailwind, Radix UI, Recharts, TanStack Table, framer-motion
docs/       Nexus product documents
legacy/     The earlier Nexus Django backend, kept for reference only (not used at runtime)
```

### Backend highlights

- Ingest PDF, Word (.docx), plain text and photos of notes. Scanned PDF pages and images are read with EasyOCR, with Tesseract as a fallback.
- Hybrid retrieval: SQLite FTS5 (BM25) plus fastembed vectors in sqlite-vec, merged with reciprocal-rank fusion. If the embedding model cannot be loaded, search falls back to keywords and the System card says so.
- Answers from a local Ollama model first, then an allowlisted OpenRouter model within a spend cap. Each claim must quote the material or it is dropped.
- Quizzes with count, difficulty, adaptive selection and a scored mode with proctoring. Ability is estimated per topic with a 3-parameter IRT model and a Normal(0, 1.2) prior.
- Six agents run after each quiz: Evaluator (traces misses back through the prerequisite graph to the root cause), Analytics, Predictor, Planner, Tutor and Mentor. Each run is stored and shown step by step.
- Smart notes per topic, extracted word for word from the material with page references.
- Analytics tables with CSV, Excel and PDF export, and branded ReportLab PDF reports for a subject, a quiz attempt and the whole account.

### Frontend flow

`/login` or `/register` → `/dashboard` → `/subjects` → a subject workspace with tabs for Materials, Ask, Practice, Quiz, Progress, Roadmap, Outlook, Notes, Learner twin, Agents and Report. Account-wide pages: `/analytics`, `/career`, `/search`, `/saved`, `/account`. `Ctrl K` opens the command palette.

## Running it

You need Python 3.11+ and Node 20+.

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-ocr.txt      # optional: EasyOCR for scanned PDFs and photos
cp .env.example .env                     # optional: add your own keys, never commit this file
python -m uvicorn studyhub.web.app:app --port 8100
```

The first time semantic search runs, fastembed downloads the `BAAI/bge-small-en-v1.5` model (about 70 MB). Without network access the app keeps working on keyword search.

### 2. Demo data (optional)

With the backend running:

```bash
cd backend
python scripts/seed_demo.py
```

This creates the account `demo@nexus.local` with password `nexus-demo-2026`, two subjects, practice questions, three weeks of quiz history, notes and a career goal.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

The frontend proxies `/api` to `API_ORIGIN` (default `http://127.0.0.1:8100`). For production use `npm run build && npm start`.

## Configuration

| Variable | Default | What it does |
| --- | --- | --- |
| `STUDYHUB_DB` | `data/studyhub.db` | SQLite database path |
| `STUDYHUB_UPLOADS` | `data/uploads` | Where uploaded files are kept |
| `STUDYHUB_LOCAL_MODEL` | unset | Ollama model to try first |
| `OPENROUTER_API_KEY` | unset | Cloud fallback, used only after the student opts in |
| `STUDYHUB_SEMANTIC` | `auto` | `off` for keyword search only |
| `STUDYHUB_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed model name |
| `STUDYHUB_OCR` | `auto` | `easyocr`, `tesseract` or `off` |
| `STUDYHUB_OCR_LANGS` | `en` | EasyOCR languages, comma separated |
| `STUDYHUB_OCR_GPU` | `0` | `1` to let EasyOCR use a GPU |
| `STUDYHUB_OCR_MAX_PAGES` | `40` | Most scanned pages read per PDF |
| `API_ORIGIN` | `http://127.0.0.1:8100` | Backend address used by the frontend proxy |

## Tests

```bash
cd backend
python -m pytest -q --deselect tests/test_integration.py
cd ../frontend
npx eslint . && npx next build
```

`tests/test_integration.py` calls live models and is skipped by default.

## Security notes

- Sessions use HTTP-only cookies and every change needs the `X-CSRF-Token` header.
- Ownership is checked in SQL. Asking for something that belongs to another account returns 404, never 403.
- Keep `.env`, databases and uploads out of version control. The `.gitignore` covers them.
