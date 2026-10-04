# NEXUS

An AI-assisted skill and learning platform for officers of India's Official Statistical System (SIH 2026, PS 26101, MoSPI), built on a learning engine that works from the officer's own material.

Upload notes, slides or a scanned handout, then ask questions, practise, take quizzes and follow a plan. Every answer is taken only from what was uploaded and shows the passage it came from. When the material does not cover a question, NEXUS says so instead of guessing.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15 (App Router), React 19, Tailwind CSS, Radix UI, Recharts, TanStack Table, Framer Motion, Lucide |
| Backend | Django 5 JSON API (`/api/v1`) with role-based access (officer, faculty), Pydantic request validation, Django admin |
| Learning engine | Plain Python (`backend/studyhub`): ingestion, retrieval, answers, quizzes, IRT scoring, BKT mastery, agents, reports |
| Database | PostgreSQL: officer records, scores, contests and the audit trail. SQLite with `DB_ENGINE=sqlite` for a single local file |
| Search | PostgreSQL full-text search (`tsvector`, GIN index) plus Sentence-BERT (`all-MiniLM-L6-v2`) vectors in a FAISS index |
| Models | Llama 3.1 8B served locally by Ollama, then an allowlisted OpenRouter model within a spend cap |
| Question checks | Exact-quote check, an independent second reader, and SymPy recomputing every computed numeric key |
| Mastery | Bayesian Knowledge Tracing per skill, used by the root-cause trace and the verified re-test |
| Background jobs | Celery with Redis as the broker; an in-process worker thread when Redis is not running |
| OCR / reports | EasyOCR (Tesseract fallback), ReportLab, openpyxl |

Docker is not used. Llama runs through Ollama because the Hugging Face transformers build of an 8B model needs about 16 GB of GPU memory.

## What is in the repository

```
backend/
  nexus_api/    Django project: settings, URLs, WSGI/ASGI
  core/         Platform pieces: security middleware, audit log, request/response conventions
  learning/     The /api/v1 views and URL table
  studyhub/     The learning engine (no web framework inside)
  slice/        The model-call layer the engine uses (budgets, providers, retries)
  scripts/      Demo seeding and utilities
  tests/        pytest suite
frontend_src/   The web application (the only frontend)
```

Product documents, design reference images and demo videos are kept out of this repository.

## What is real and what is demo data

Be clear about this when you present it.

- **Live, produced by the running backend:** a subject's materials, ask, notes, practice questions, quizzes, agents, progress, outlook, learner twin, roadmap, report, search, career goals, account.
- **Demo data in this prototype** (filled from `frontend_src/lib/nexus-data.js`): the officer dashboard, competency profile, root-cause diagnosis, learning path and course pages, assessment, AI tutor conversation and profile.
- **iGOT Karmayogi and NSSTA TPAC:** the courses shown are a **sample catalogue**. There is no live integration.
- There are two roles. **Officers** learn, take quizzes and can contest a score. **Faculty** review AI-drafted questions before officers see them, resolve contests and read the NSSTA insights. Administration stays in the Django admin.

### The question pipeline and the officer loop

1. Material is uploaded and split into passages; Sentence-BERT + FAISS find the source paragraph for each question.
2. Llama 3.1 8B (Ollama) drafts MCQs. Code checks the quote word for word, an independent reader answers without the key, and SymPy recomputes any computed numeric answer and refuses a wrong key.
3. Each question that passes waits as **pending** until a faculty member approves, edits or rejects it (`/faculty`). Only approved questions reach officers.
4. The officer takes a diagnostic quiz and rates each answer (guessing, unsure, sure). A confident wrong answer is flagged as a misconception.
5. The Evaluator traces each miss through the prerequisite graph using BKT mastery to find the root gap; the planner and tutor build the learning path.
6. A **verified re-test** uses only questions the officer has never seen. If BKT mastery reaches 95% the gap is closed; if not, the next root gap is shown.
7. An officer can **contest a score** on any answer marked wrong. Faculty uphold it (the answer is re-marked correct, the score and mastery are recomputed, and the question is withdrawn) or reject it with a reason.
8. NSSTA insights aggregate across officers which interventions closed which gaps, without naming anyone.

### Backend highlights

- Ingest PDF, Word (.docx), plain text and photos of notes. Scanned pages and images are read with EasyOCR, with Tesseract as a fallback.
- Hybrid retrieval: BM25 plus vector search merged with reciprocal-rank fusion. If the embedding model cannot be loaded, search falls back to keywords and the System card says so.
- Each claim in an answer must quote the material or it is dropped. A question the material does not cover is answered with "not in your materials".
- Practice questions are written from the material, each with its answer, an explanation, the quoted passage, and an independent second check.
- Quizzes with count, difficulty, adaptive selection and a scored mode with proctoring. Ability is estimated per topic with a 3-parameter IRT model.
- Six agents run after a quiz: Evaluator (traces misses back through the prerequisite graph to the root cause), Analytics, Predictor, Planner, Tutor and Mentor. Each run is stored and shown step by step.
- Smart notes per topic, extracted word for word, with page references.
- CSV, Excel and branded PDF reports for a subject, a quiz attempt and the whole account.
- An audit log of every state-changing API request (who, what, result, IP), viewable in the Django admin.

### Frontend routes

`/login` and `/register` → `/dashboard`. Faculty: `/faculty` (review queue, contests, NSSTA insights). Officer views: `/competency`, `/diagnosis`, `/learn` and `/learn/[course]`, `/assess`, `/ai-tutor`, `/profile`. Study workspace: `/subjects` → a subject with tabs for Materials, Ask, Practice, Quiz, Progress, Roadmap, Outlook, Notes, Learner twin, Agents and Report. Also `/career`, `/search`, `/saved` and `/account`. `Ctrl K` opens the command palette.

## Running it

You need Python 3.11+, Node 20+ and PostgreSQL 14+ (Redis is optional).

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-ocr.txt      # optional: EasyOCR for scanned PDFs and photos
cp .env.example .env                     # set DB_PASSWORD and your own settings; never commit this file
psql -U postgres -c "CREATE DATABASE nexus;"
python manage.py migrate                 # Django's tables; the learning engine creates its own on first start
python manage.py runserver 8100
python manage.py createsuperuser         # optional: Django admin at http://127.0.0.1:8100/admin/
python manage.py set_role <username> faculty   # give an account the faculty role
```

Background jobs (question generation, answers) go to Celery when Redis is reachable at `CELERY_BROKER_URL`. On Windows use Memurai or Redis under WSL, then run `celery -A nexus_api worker --pool=solo -c 1`. Without Redis the same jobs run on a worker thread inside the server.

The first time semantic search runs, sentence-transformers downloads `all-MiniLM-L6-v2` (about 90 MB). Without network access the app keeps working on keyword search. For answers and practice questions install [Ollama](https://ollama.com) and pull a model, or set an OpenRouter key.

### 2. Demo data (optional)

With the backend running:

```bash
cd backend
python scripts/seed_demo.py
```

This creates two demo accounts. These are public demo credentials: do not reuse them.

- Officer `demo@nexus.local` / `nexus-demo-2026`: two subjects, practice questions, quiz history, notes, a career goal and one open contest.
- Faculty `faculty@nexus.local` / `nexus-faculty-2026`: AI-drafted questions waiting for review (one with a SymPy-checked key) and intervention outcomes for the insights page.

### 3. Frontend

```bash
cd frontend_src
npm install
npm run dev            # http://localhost:3000
```

The frontend proxies `/api` to `API_ORIGIN` (default `http://127.0.0.1:8100`). For production use `npm run build && npm start`.

### How PostgreSQL is used

The learning engine's SQL runs through `backend/slice/pg.py`, a small adapter that gives it the sqlite3 interface on top of psycopg2: placeholders, `lastrowid`, error types and a connection pool. Keyword search uses a generated `tsvector` column with a GIN index, ranked by `ts_rank_cd`. Vectors are stored in `chunk_embeddings` and searched with a FAISS index per subject. With `DB_ENGINE=sqlite` the same code runs on one SQLite file (FTS5 for keywords).

## Configuration

Set these in `backend/.env` (see `backend/.env.example`) or the environment.

| Variable | Default | What it does |
| --- | --- | --- |
| `DB_ENGINE` | `sqlite` | `postgresql` (recommended; `.env.example` sets it), `sqlite`, or `mysql` for Django's tables only |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | `nexus`, `postgres`, empty, `localhost`, `5432` | Database connection |
| `STUDYHUB_DB` | `data/studyhub.db` | SQLite database path (when `DB_ENGINE=sqlite`) |
| `STUDYHUB_UPLOADS` | `data/uploads` | Where uploaded files are kept |
| `STUDYHUB_MAX_UPLOAD_BYTES` | 50 MB | Largest accepted upload |
| `DJANGO_SECRET_KEY` | generated | Generated once into `data/django-secret.key` if unset |
| `DJANGO_DEBUG` | `1` | Set `0` in production |
| `DJANGO_ALLOWED_HOSTS` | local only | Comma-separated hostnames |
| `STUDYHUB_COOKIE_SECURE` | `0` | `1` over HTTPS: secure cookies, HTTPS redirect and HSTS |
| `STUDYHUB_LOCAL_MODEL` | `on` | `off` to skip the local Ollama model |
| `OPENROUTER_API_KEY` | unset | Cloud fallback, used only after the user opts in |
| `STUDYHUB_SEMANTIC` | `auto` | `off` for keyword search only |
| `STUDYHUB_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence-BERT model (a `bge` name uses fastembed) |
| `STUDYHUB_FACULTY_REVIEW` | `on` | `off` puts verified questions straight into the bank without faculty approval |
| `STUDYHUB_BKT` | `0.2,0.15,0.1,0.25` | BKT initial, learn, slip and guess probabilities |
| `CELERY_BROKER_URL` | `redis://127.0.0.1:6379/0` | Celery broker; unreachable means the in-process worker is used |
| `STUDYHUB_OCR` | `auto` | `easyocr`, `tesseract` or `off` |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | unset | SMTP for sign-in codes and password reset |
| `API_ORIGIN` | `http://127.0.0.1:8100` | Backend address used by the frontend proxy |

## Tests

```bash
cd backend
python -m pytest -q --ignore=tests/test_integration.py
cd ../frontend_src
npx eslint . && npx next build
```

`tests/test_integration.py` calls live models and is skipped by default. The backend suite runs against the Django app in-process, on PostgreSQL when `backend/.env` says `DB_ENGINE=postgresql`. It uses a separate `<DB_NAME>_test` database and gives each test its own emptied schema. Set `NEXUS_TEST_DB=sqlite` to run the suite on SQLite instead. `tests/test_faculty.py` covers SymPy, BKT, faculty review, contests, verified re-tests and Celery dispatch.

## Security notes

- Sessions use HTTP-only cookies and every change needs the `X-CSRF-Token` header.
- Ownership is checked in SQL. Asking for something that belongs to another account returns 404, never 403.
- Uploads are limited by size and type and read as text, never executed.
- State-changing requests are recorded in an audit log; request bodies are never stored.
- Security headers are set on every API response; with `STUDYHUB_COOKIE_SECURE=1` the backend forces HTTPS with HSTS.
- Keep `.env`, databases and uploads out of version control. The `.gitignore` covers them. Never put credentials in `.env.example`.
