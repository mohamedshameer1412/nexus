# NEXUS

An AI-assisted skill and learning platform for officers of India's Official Statistical System (SIH 2026, PS 26101, MoSPI), built on a learning engine that works from the officer's own material.

Upload notes, slides or a scanned handout, then ask questions, practise, take quizzes and follow a plan. Every answer is taken only from what was uploaded and shows the passage it came from. When the material does not cover a question, NEXUS says so instead of guessing.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15 (App Router), React 19, Tailwind CSS, Radix UI, Recharts, TanStack Table, Framer Motion, Lucide |
| Backend | Django 5 JSON API (`/api/v1`), Pydantic request validation, Django admin |
| Learning engine | Plain Python (`backend/studyhub`): ingestion, retrieval, answers, quizzes, IRT scoring, agents, reports |
| Database | SQLite by default. MySQL/MariaDB with `DB_ENGINE=mysql` |
| Search | SQLite FTS5 (BM25) plus fastembed vectors in sqlite-vec |
| Models | Local Ollama first, then an allowlisted OpenRouter model within a spend cap |
| OCR / reports | EasyOCR (Tesseract fallback), ReportLab, openpyxl |

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
- There is **no administrator dashboard** and no role-based access yet; there is a single signed-in user type.

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

`/login` and `/register` → `/dashboard`. Officer views: `/competency`, `/diagnosis`, `/learn` and `/learn/[course]`, `/assess`, `/ai-tutor`, `/profile`. Study workspace: `/subjects` → a subject with tabs for Materials, Ask, Practice, Quiz, Progress, Roadmap, Outlook, Notes, Learner twin, Agents and Report. Also `/career`, `/search`, `/saved` and `/account`. `Ctrl K` opens the command palette.

## Running it

You need Python 3.11+ and Node 20+.

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-ocr.txt      # optional: EasyOCR for scanned PDFs and photos
cp .env.example .env                     # then add your own settings; never commit this file
python manage.py migrate                 # Django's tables (audit log, admin)
python manage.py runserver 8100
python manage.py createsuperuser         # optional: Django admin at http://127.0.0.1:8100/admin/
```

The first time semantic search runs, fastembed downloads the `BAAI/bge-small-en-v1.5` model (about 70 MB). Without network access the app keeps working on keyword search. For answers and practice questions install [Ollama](https://ollama.com) and pull a model, or set an OpenRouter key.

### 2. Demo data (optional)

With the backend running:

```bash
cd backend
python scripts/seed_demo.py
```

This creates the account `demo@nexus.local` with password `nexus-demo-2026` (a public demo credential: do not reuse it), two subjects, practice questions, quiz history, notes and a career goal.

### 3. Frontend

```bash
cd frontend_src
npm install
npm run dev            # http://localhost:3000
```

The frontend proxies `/api` to `API_ORIGIN` (default `http://127.0.0.1:8100`). For production use `npm run build && npm start`.

### Using MySQL / MariaDB (e.g. XAMPP)

Create an empty database, set `DB_ENGINE=mysql` and the `DB_*` values in `backend/.env`, then run `python manage.py migrate`. Django's own tables move to MySQL. The learning engine's keyword and vector search still use SQLite-only features, so a full move of the learning data to MySQL is not done yet.

## Configuration

Set these in `backend/.env` (see `backend/.env.example`) or the environment.

| Variable | Default | What it does |
| --- | --- | --- |
| `STUDYHUB_DB` | `data/studyhub.db` | SQLite database path |
| `STUDYHUB_UPLOADS` | `data/uploads` | Where uploaded files are kept |
| `STUDYHUB_MAX_UPLOAD_BYTES` | 50 MB | Largest accepted upload |
| `DB_ENGINE` | `sqlite` | `mysql` to use MySQL/MariaDB for Django's tables |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | `nexus`, `root`, empty, `localhost`, `3306` | MySQL connection |
| `DJANGO_SECRET_KEY` | generated | Generated once into `data/django-secret.key` if unset |
| `DJANGO_DEBUG` | `1` | Set `0` in production |
| `DJANGO_ALLOWED_HOSTS` | local only | Comma-separated hostnames |
| `STUDYHUB_COOKIE_SECURE` | `0` | `1` over HTTPS: secure cookies, HTTPS redirect and HSTS |
| `STUDYHUB_LOCAL_MODEL` | `on` | `off` to skip the local Ollama model |
| `OPENROUTER_API_KEY` | unset | Cloud fallback, used only after the user opts in |
| `STUDYHUB_SEMANTIC` | `auto` | `off` for keyword search only |
| `STUDYHUB_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed model name |
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

`tests/test_integration.py` calls live models and is skipped by default. The backend suite runs against the Django app in-process.

## Security notes

- Sessions use HTTP-only cookies and every change needs the `X-CSRF-Token` header.
- Ownership is checked in SQL. Asking for something that belongs to another account returns 404, never 403.
- Uploads are limited by size and type and read as text, never executed.
- State-changing requests are recorded in an audit log; request bodies are never stored.
- Security headers are set on every API response; with `STUDYHUB_COOKIE_SECURE=1` the backend forces HTTPS with HSTS.
- Keep `.env`, databases and uploads out of version control. The `.gitignore` covers them. Never put credentials in `.env.example`.
