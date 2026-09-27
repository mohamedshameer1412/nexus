"""StudyHub web app (Phase A1: accounts, sessions, subjects. Phase A2: materials and search).

Run:  uvicorn studyhub.web.app:app --port 8100
      STUDYHUB_DB=path/to/file.db   STUDYHUB_COOKIE_SECURE=1 (when served over HTTPS)

Security notes
  * Every state-changing request needs a CSRF token: the session's for signed-in forms, a double-submit cookie for the
    login/register forms. A wrong or missing token is a 403 and changes nothing.
  * All SQL goes through studyhub.repo, which puts user_id in every WHERE clause. Someone else's subject is a 404,
    exactly like one that does not exist.
  * No JavaScript anywhere, so the Content-Security-Policy forbids scripts entirely.
  * There is no `next=` redirect parameter (no open redirect).
"""
from __future__ import annotations

import json
import secrets
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager

from pydantic import BaseModel
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from studyhub import auth, ingest, mcq, models, qa, retrieval, settings
from studyhub import db as studydb
from studyhub import scoring, quiz_flow, quiz_agents, roadmap, career, tutor
from studyhub.repo import Repo, SubjectError
from studyhub.web import api as api_module
from studyhub.web import api_ext as api_ext_module
from studyhub.web import ui

SESSION_COOKIE, PRE_COOKIE = "sh_session", "sh_pre"


@asynccontextmanager
async def _lifespan(_app):
    """Questions still 'pending' when the process starts were cut off by the previous shutdown."""
    store = studydb.open_db()
    try:
        Repo(store.db).expire_pending_doubts(0)
        Repo(store.db).expire_pending_mcq_jobs(0)
        Repo(store.db).expire_stale_attempts(3600)   # Phase C: mark abandoned attempts finished
    finally:
        store.close()
    from studyhub import digest, semantic
    digest.start_scheduler()                          # the weekly summary e-mail (off under tests)
    semantic.schedule(studydb.open_db)                # embed anything uploaded before semantic search was switched on
    yield


app = FastAPI(title="Nexus", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_lifespan)

app.include_router(api_module.router)
app.include_router(api_ext_module.router)

from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402

app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)   # large JSON (analytics, twin, roadmap) compresses 5-10x


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/"):
        return api_module.err(422, "validation", "The request was not understood.")
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(Exception)
async def _unexpected_error(request: Request, exc: Exception):
    """Never show a bare "Internal Server Error": log what happened (data/server-errors.log) and give the student a reference."""
    import logging
    import traceback
    ref = secrets.token_hex(3)
    try:
        from pathlib import Path
        path = Path(settings.db_path()).parent / "server-errors.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ref {ref} {request.method} {request.url.path}\n{''.join(traceback.format_exception(exc))}\n")
    except Exception:
        logging.getLogger("uvicorn.error").exception("unexpected error %s", ref)
    if request.url.path.startswith("/api/"):
        return api_module.err(500, "server_error", f"Something went wrong on our side. Please try again in a moment. (reference {ref})")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(f"Something went wrong. Reference {ref}.", status_code=500)


# Which models answer a question. A function so tests (and other deployments) can swap it: (db, user) -> (tiers, notes).
tier_factory = models.build_tiers


def tiers_for(db, user, task: str = "answer"):
    """The models for one kind of work. Tests replace `tier_factory` with a two-argument function, which is still accepted."""
    try:
        return tier_factory(db, user, task=task)
    except TypeError:
        return tier_factory(db, user)
_worker: ThreadPoolExecutor | None = None
_worker_lock = threading.Lock()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    path = request.url.path
    if not settings.legacy_ui() and not path.startswith("/api/") and path != "/healthz":
        # The old HTML pages are switched off: the web app lives at the Next.js address. Browsers are sent there, everything else gets a 404.
        from fastapi.responses import JSONResponse
        from studyhub import mailer
        response = (RedirectResponse(mailer.public_url() + "/", status_code=302) if request.method == "GET"
                    else JSONResponse({"error": {"code": "not_found", "message": "Not found."}}, status_code=404))
        response.headers["Cache-Control"] = "no-store"
        return response
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > settings.max_upload_bytes() + 64 * 1024:
        response = _html("Too large", "<h1>That upload is too large</h1><p class='sub'>The limit is "
                         f"{settings.max_upload_bytes() / 1048576:.3g} MB per file.</p>", status=413)   # before parsing the body
    else:
        response = await call_next(request)
    nonce = getattr(request.state, "script_nonce", "")          # only the quiz question page sets one
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'unsafe-inline'; script-src " + (f"'nonce-{nonce}'" if nonce else "'none'")
        + "; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if response.headers.get("X-Nexus-Frameable") == "1":       # the student's own uploaded file, shown by our own viewer: same origin only
        del response.headers["X-Nexus-Frameable"]
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@contextmanager
def _open():
    """One connection per request, in the thread that uses it (sqlite3 connections are thread-bound)."""
    store = studydb.open_db()
    try:
        yield store.db
    finally:
        store.close()


def _html(title: str, body: str, *, status: int = 200, user: dict | None = None, csrf: str | None = None):
    return HTMLResponse(ui.page(title, body, username=user["username"] if user else None, csrf=csrf),
                        status_code=status)


def _signed_in(request: Request, db):
    """(user, session) or None."""
    session = auth.get_session(db, request.cookies.get(SESSION_COOKIE))
    if session is None:
        return None
    user = Repo(db).get_user(session.user_id)
    return (user, session) if user else None


def _set_session_cookie(response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, max_age=settings.session_days() * 86400, httponly=True,
                        samesite="lax", secure=settings.cookie_secure(), path="/")


def _forbidden():
    return _html("Forbidden", "<h1>Request refused</h1><p class='sub'>The form expired or was not sent from this site. "
                              "Go back, reload the page and try again.</p>", status=403)


def _pre_token(request: Request) -> tuple[str, bool]:
    existing = request.cookies.get(PRE_COOKIE)
    if existing and 20 <= len(existing) <= 100:
        return existing, False
    return secrets.token_urlsafe(24), True


def _with_pre_cookie(response, token: str, is_new: bool):
    if is_new:
        response.set_cookie(PRE_COOKIE, token, httponly=True, samesite="lax", secure=settings.cookie_secure(), path="/")
    return response


def _int(text: str) -> int | None:
    return int(text) if text.isdigit() and len(text) < 12 else None


# ---------------------------------------------------------------------------- basics

@app.get("/healthz")
def healthz():
    return PlainTextResponse("ok")


@app.get("/")
def home(request: Request):
    with _open() as db:
        return RedirectResponse("/subjects" if _signed_in(request, db) else "/login", status_code=303)


# ---------------------------------------------------------------------- register / login

def _auth_page(request: Request, kind: str, *, error: str | None = None, username: str = "", status: int = 200):
    token, is_new = _pre_token(request)
    response = _html("Register" if kind == "register" else "Log in",
                     ui.auth_form(kind, token, error=error, username=username), status=status)
    return _with_pre_cookie(response, token, is_new)


@app.get("/register")
def register_form(request: Request):
    return _auth_page(request, "register")


@app.get("/login")
def login_form(request: Request):
    return _auth_page(request, "login")


@app.post("/register")
def register(request: Request, username: str = Form(""), password: str = Form(""), password2: str = Form(""),
             csrf: str = Form("")):
    if not auth.same_token(csrf, request.cookies.get(PRE_COOKIE)):
        return _forbidden()
    if password != password2:
        return _auth_page(request, "register", error="The two passwords do not match.", username=username, status=400)
    with _open() as db:
        try:
            user_id = auth.register(db, username, password)
        except auth.AuthError as e:
            return _auth_page(request, "register", error=str(e), username=username, status=400)
        auth.purge_expired(db)
        token, _ = auth.create_session(db, user_id)
    response = RedirectResponse("/subjects", status_code=303)
    _set_session_cookie(response, token)
    return response


@app.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form(""), csrf: str = Form("")):
    if not auth.same_token(csrf, request.cookies.get(PRE_COOKIE)):
        return _forbidden()
    ip = request.client.host if request.client else ""
    with _open() as db:
        try:
            user_id = auth.authenticate(db, username, password, ip=ip)
        except auth.AuthError as e:
            return _auth_page(request, "login", error=str(e), username=username, status=400)
        token, _ = auth.create_session(db, user_id)          # a fresh token on every login
    response = RedirectResponse("/subjects", status_code=303)
    _set_session_cookie(response, token)
    return response


@app.post("/logout")
def logout(request: Request, csrf: str = Form("")):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        if not auth.same_token(csrf, ctx[1].csrf):
            return _forbidden()
        auth.delete_session(db, request.cookies.get(SESSION_COOKIE))     # server-side: the cookie is now dead
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# ----------------------------------------------------------------------------- subjects

@app.get("/subjects")
def subjects(request: Request):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        user, session = ctx
        return _html("Subjects", ui.subjects_page(Repo(db).list_subjects(user["id"]), session.csrf),
                     user=user, csrf=session.csrf)


@app.post("/subjects")
def create_subject(request: Request, name: str = Form(""), description: str = Form(""), csrf: str = Form("")):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        user, session = ctx
        if not auth.same_token(csrf, session.csrf):
            return _forbidden()
        repo = Repo(db)
        try:
            subject_id = repo.create_subject(user["id"], name, description)
        except SubjectError as e:
            return _html("Subjects", ui.subjects_page(repo.list_subjects(user["id"]), session.csrf, error=str(e),
                                                      name=name, description=description),
                         status=400, user=user, csrf=session.csrf)
    return RedirectResponse(f"/subjects/{subject_id}", status_code=303)


@app.get("/subjects/{subject_id}")
def subject(request: Request, subject_id: str):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        user, session = ctx
        row = Repo(db).get_subject(user["id"], _int(subject_id) or -1)
        if row is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        return _subject_html(db, user, session, row)


def _subject_html(db, user, session, row, *, status: int = 200, error: str | None = None, upload_error: str | None = None,
                  ask_error: str | None = None, question: str = "", mcq_error: str | None = None):
    repo = Repo(db)
    body = ui.subject_page(row, session.csrf, error=error, upload_error=upload_error, ask_error=ask_error, question=question,
                           mcq_error=mcq_error, bank_size=len(repo.list_mcq(user["id"], row["id"])),
                           documents=repo.list_documents(user["id"], row["id"]), topics=repo.list_topics(user["id"], row["id"]),
                           doubts=repo.list_doubts(user["id"], row["id"], 8))
    return _html(row["name"], body, status=status, user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/edit")
def edit_subject(request: Request, subject_id: str, name: str = Form(""), description: str = Form(""),
                 csrf: str = Form("")):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        user, session = ctx
        if not auth.same_token(csrf, session.csrf):
            return _forbidden()
        repo, sid = Repo(db), _int(subject_id) or -1
        row = repo.get_subject(user["id"], sid)
        if row is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        try:
            repo.update_subject(user["id"], sid, name, description)
        except SubjectError as e:
            return _subject_html(db, user, session, row, status=400, error=str(e))
    return RedirectResponse(f"/subjects/{sid}", status_code=303)


@app.post("/subjects/{subject_id}/delete")
def delete_subject(request: Request, subject_id: str, confirm: str = Form(""), csrf: str = Form("")):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        user, session = ctx
        if not auth.same_token(csrf, session.csrf):
            return _forbidden()
        repo, sid = Repo(db), _int(subject_id) or -1
        row = repo.get_subject(user["id"], sid)
        if row is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        if confirm != "yes":
            return _subject_html(db, user, session, row, status=400, error="Tick the box to confirm the deletion.")
        ingest.delete_subject(db, user["id"], sid)
    return RedirectResponse("/subjects", status_code=303)


# ---------------------------------------------------------------------------------------- materials

def _member(request: Request, db, subject_id: str, *, form_csrf: str | None = None):
    """Common gate for subject pages: (user, session, subject) or a ready response. A form_csrf of None = read-only."""
    ctx = _signed_in(request, db)
    if ctx is None:
        return None, RedirectResponse("/login", status_code=303)
    user, session = ctx
    if form_csrf is not None and not auth.same_token(form_csrf, session.csrf):
        return None, _forbidden()
    row = Repo(db).get_subject(user["id"], _int(subject_id) or -1)
    if row is None:
        return None, _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
    return (user, session, row), None


@app.post("/subjects/{subject_id}/materials")
def upload_material(request: Request, subject_id: str, file: UploadFile = File(...), csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        limit = settings.max_upload_bytes()
        data = file.file.read(limit + 1)
        try:
            result = ingest.ingest(db, user["id"], row["id"], file.filename or "upload", data)
        except ingest.IngestError as e:
            return _subject_html(db, user, session, row, status=400, upload_error=str(e))
    return RedirectResponse(f"/subjects/{row['id']}/materials/{result.document_id}" + ("?dup=1" if result.duplicate else ""),
                            status_code=303)


@app.get("/subjects/{subject_id}/materials/{document_id}")
def material(request: Request, subject_id: str, document_id: str, dup: str = ""):
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        doc = repo.get_document(user["id"], row["id"], _int(document_id) or -1)
        if doc is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        chunks = repo.document_chunks(user["id"], row["id"], doc["id"])
        notice = "This exact file was already in this subject, so nothing was added." if dup == "1" else None
        return _html(doc["title"], ui.document_page(row, doc, chunks, session.csrf, notice=notice),
                     user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/materials/{document_id}/delete")
def delete_material(request: Request, subject_id: str, document_id: str, csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        if not ingest.delete_document(db, user["id"], row["id"], _int(document_id) or -1):
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
    return RedirectResponse(f"/subjects/{row['id']}", status_code=303)


@app.get("/subjects/{subject_id}/search")
def search_materials(request: Request, subject_id: str, q: str = ""):
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        q = " ".join(q.split())[:200]
        results = retrieval.search(db, user["id"], row["id"], q, k=8) if q else []
        return _html("Search", ui.search_page(row, q, results), user=user, csrf=session.csrf)


# ------------------------------------------------------------------------------------------------ questions

@contextmanager
def _open_store():
    store = studydb.open_db()
    try:
        yield store
    finally:
        store.close()


def _process(doubt_id: int, user_id: int) -> None:
    """Answer one pending question. Runs in the worker thread, with its own connection."""
    with _open_store() as store:
        repo = Repo(store.db)
        try:
            tiers, notes = tiers_for(store.db, repo.get_user(user_id), "answer")
            qa.run_doubt(store, user_id, doubt_id, tiers, notes)
        except Exception as e:                                # the student must never be left on a spinner
            repo.finish_doubt(user_id, doubt_id, status="failed", tier=None, model=None, dropped=0, claims=[], sources=[],
                              reason=f"Something went wrong while answering ({type(e).__name__}). Please try again.")


def _submit(doubt_id: int, user_id: int) -> None:
    global _worker
    if settings.qa_inline():
        _process(doubt_id, user_id)
        return
    with _worker_lock:
        if _worker is None:                                   # one at a time: a local model on a small GPU cannot do two
            _worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qa")
        _worker.submit(_process, doubt_id, user_id)


@app.post("/subjects/{subject_id}/ask")
def ask(request: Request, subject_id: str, question: str = Form(""), csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        q = " ".join(question.split())
        error = None
        if len(q) < 3:
            error = "Type your question first."
        elif len(q) > qa.MAX_QUESTION_CHARS:
            error = f"Please keep the question under {qa.MAX_QUESTION_CHARS} characters."
        else:
            repo.expire_pending_doubts(1800)
            if repo.pending_doubts(user["id"]) >= settings.max_pending_questions():
                error = "You already have questions being answered. Wait for one to finish, then ask again."
        if error:
            return _subject_html(db, user, session, row, status=400, ask_error=error, question=question[:600])
        doubt_id = repo.create_doubt(user["id"], row["id"], q)
    _submit(doubt_id, user["id"])
    return RedirectResponse(f"/subjects/{row['id']}/questions/{doubt_id}", status_code=303)


@app.get("/subjects/{subject_id}/questions/{doubt_id}")
def question_page(request: Request, subject_id: str, doubt_id: str):
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        repo.expire_pending_doubts(1800)
        d = repo.get_doubt(user["id"], row["id"], _int(doubt_id) or -1)
        if d is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        trace = repo.doubt_trace(user["id"], row["id"], d["id"]) if d["status"] != "pending" else []
        return _html(d["question"][:60], ui.doubt_page(row, d, trace, session.csrf), user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/questions/{doubt_id}/feedback")
def question_feedback(request: Request, subject_id: str, doubt_id: str, value: str = Form(""), csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        if not Repo(db).set_doubt_feedback(user["id"], row["id"], _int(doubt_id) or -1, value):
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
    return RedirectResponse(f"/subjects/{row['id']}/questions/{int(doubt_id)}", status_code=303)


@app.post("/subjects/{subject_id}/questions/{doubt_id}/delete")
def question_delete(request: Request, subject_id: str, doubt_id: str, csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        if not Repo(db).delete_doubt(user["id"], row["id"], _int(doubt_id) or -1):
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
    return RedirectResponse(f"/subjects/{row['id']}", status_code=303)


# ------------------------------------------------------------------------------------------------- account

@app.get("/account")
def account(request: Request):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        user, session = ctx
        s = models.slice_config.settings(reload=False)
        return _html("Account", ui.account_page(user, session.csrf, key_configured=bool(s.api_key),
                                                allowed=models.allowed_cloud_models() if s.api_key else []),
                     user=user, csrf=session.csrf)


@app.post("/account/cloud")
def account_cloud(request: Request, consent: str = Form(""), csrf: str = Form("")):
    with _open() as db:
        ctx = _signed_in(request, db)
        if ctx is None:
            return RedirectResponse("/login", status_code=303)
        user, session = ctx
        if not auth.same_token(csrf, session.csrf):
            return _forbidden()
        Repo(db).set_cloud_consent(user["id"], consent == "yes")
    return RedirectResponse("/account", status_code=303)


# ---------------------------------------------------------------------------- multiple-choice questions

def _process_mcq(job_id: int, user_id: int) -> None:
    """Write the questions of one pending job. Runs in the worker thread, with its own connection."""
    with _open_store() as store:
        repo = Repo(store.db)
        try:
            tiers, notes = tiers_for(store.db, repo.get_user(user_id), "write")
            mcq.run_job(store, user_id, job_id, tiers, notes)
        except Exception as e:
            store.db.execute("UPDATE mcq_jobs SET status='failed', reason=?, finished_at=strftime('%s','now') "
                             "WHERE id=? AND user_id=? AND status='pending'",
                             (f"Something went wrong while writing questions ({type(e).__name__}). Please try again.", job_id, user_id))


def _submit_task(fn, *args) -> None:
    """Run a slow job (a model call) on the same single worker as questions and practice generation."""
    global _worker
    if settings.qa_inline():
        fn(*args)
        return
    with _worker_lock:
        if _worker is None:
            _worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qa")
        _worker.submit(fn, *args)


class _CoachOut(BaseModel):
    text: str


def _process_coach(user_id: int, subject_id: int) -> None:
    """Write the coach paragraph for a subject's roadmap: the cloud first when the student allowed it, then the local model, then plain rules."""
    from slice.budget import Budget
    from slice.records import RunState
    store = studydb.open_db()
    try:
        repo = Repo(store.db)
        user, subject = repo.get_user(user_id), repo.get_subject(user_id, subject_id)
        if user is None or subject is None:
            return
        profile = roadmap.get_profile(store.db, user_id, subject_id)
        info = roadmap.skill_gaps(store.db, user_id, subject_id, subject.get("level"))
        plan = roadmap.build(info, subject_id, profile["hours_per_week"], profile["target_date"])
        digest_ = roadmap.plan_hash(info, profile)
        run_id = store.create_run("roadmap", {"subject_id": subject_id})
        text, model = None, None
        tiers, _notes = tiers_for(store.db, user, "plan")
        for tier in tiers:
            try:
                out = mcq._call(tier, Budget(store, run_id, tier.settings), [{"role": "system", "content": roadmap.COACH_SYSTEM},
                                {"role": "user", "content": roadmap.coach_prompt(subject["name"], info, plan, profile)}], _CoachOut, f"roadmap_coach_{tier.name}")
                text = roadmap.clean_coach(out.text, info)
                if text:
                    model = tier.model
                    break
            except Exception:
                continue
        if not text:
            text, model = roadmap.rule_coach(info, plan), "rules (no model answered)"
        store.db.execute("UPDATE study_plans SET coach_status='done', coach_text=?, coach_model=?, coach_hash=?, coach_at=? WHERE subject_id=? AND user_id=?",
                         (text, model, digest_, time.time(), subject_id, user_id))
        store.set_state(run_id, RunState.COMPLETE)
    except Exception:
        store.db.execute("UPDATE study_plans SET coach_status='failed' WHERE subject_id=? AND user_id=?", (subject_id, user_id))
    finally:
        store.close()


class _SkillOut(BaseModel):
    skill: str
    importance: str = "required"
    quote: str = ""


class _SkillsOut(BaseModel):
    skills: list[_SkillOut]


def _process_career(user_id: int, goal_id: int) -> None:
    """Read the skills out of a job description: the cloud first when the student allowed it, then the local model, then plain rules. Only skills whose quote is really in the text are kept."""
    from slice.budget import Budget
    from slice.records import RunState
    store = studydb.open_db()
    try:
        repo = Repo(store.db)
        user, goal = repo.get_user(user_id), career.get(store.db, user_id, goal_id)
        if user is None or goal is None:
            return
        run_id = store.create_run("career", {"goal_id": goal_id})
        skills, model = [], None
        tiers, _notes = tiers_for(store.db, user, "plan")
        for tier in tiers:
            try:
                out = mcq._call(tier, Budget(store, run_id, tier.settings), [{"role": "system", "content": career.SYSTEM},
                                {"role": "user", "content": career.prompt(goal["title"], goal["jd_text"])}], _SkillsOut, f"career_skills_{tier.name}")
                skills = career._valid([s.model_dump() for s in out.skills], goal["jd_text"])
                if skills:
                    model = tier.model
                    break
            except Exception:
                continue
        if not skills:
            skills, model = career.rule_skills(goal["jd_text"]), "rules (no model answered)"
        store.db.execute("UPDATE career_goals SET status=?, skills_json=?, model=?, updated_at=? WHERE id=? AND user_id=?",
                         ("done" if skills else "failed", json.dumps(skills), model, time.time(), goal_id, user_id))
        store.set_state(run_id, RunState.COMPLETE)
    except Exception:
        store.db.execute("UPDATE career_goals SET status='failed', updated_at=? WHERE id=? AND user_id=?", (time.time(), goal_id, user_id))
    finally:
        store.close()


def _process_example(user_id: int, subject_id: int, iid: int) -> None:
    """Write a worked example from a topic's own passages: the cloud first when the student allowed it, then the local model, then the plain key-passages walk-through."""
    from slice.budget import Budget
    from slice.records import RunState
    store = studydb.open_db()
    try:
        repo = Repo(store.db)
        user, row = repo.get_user(user_id), tutor.get(store.db, user_id, subject_id, iid)
        if user is None or row is None:
            return
        texts = tutor.passages(store.db, subject_id, row["topic_id"])
        run_id = store.create_run("worked_example", {"subject_id": subject_id, "topic_id": row["topic_id"]})
        example, model = None, None
        tiers, _notes = tiers_for(store.db, user, "answer")
        for tier in tiers:
            try:
                out = mcq._call(tier, Budget(store, run_id, tier.settings), [{"role": "system", "content": tutor.SYSTEM},
                                {"role": "user", "content": tutor.prompt(row["topic"], row["level"], texts)}], tutor.ExampleOut, f"worked_example_{tier.name}")
                example = tutor.clean_example(out, texts)
                if example:
                    model = tier.model
                    break
            except Exception:
                continue
        if not example:
            example, model = tutor.key_passages(row["topic"], texts), "rules (no model answered)"
        now = time.time()
        store.db.execute("UPDATE interventions SET status=?, payload_json=?, model=?, updated_at=? WHERE id=? AND user_id=?",
                         ("done" if example else "failed", json.dumps(example or {}), model, now, iid, user_id))
        store.set_state(run_id, RunState.COMPLETE)
    except Exception:
        store.db.execute("UPDATE interventions SET status='failed', updated_at=? WHERE id=? AND user_id=?", (time.time(), iid, user_id))
    finally:
        store.close()


def _submit_mcq(job_id: int, user_id: int) -> None:
    global _worker
    if settings.qa_inline():
        _process_mcq(job_id, user_id)
        return
    with _worker_lock:
        if _worker is None:
            _worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qa")
        _worker.submit(_process_mcq, job_id, user_id)


@app.post("/subjects/{subject_id}/mcq/generate")
def mcq_generate(request: Request, subject_id: str, topic: str = Form(""), count: str = Form("5"), csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        repo.expire_pending_mcq_jobs(3600)
        n = _int(count.strip())
        topic_id = _int(topic.strip()) if topic.strip() else None
        topics = {t["id"]: t for t in repo.list_topics(user["id"], row["id"]) if t["chunks"]}
        error = None
        if n is None or not 1 <= n <= mcq.MAX_COUNT:
            error = f"Choose a number of questions from 1 to {mcq.MAX_COUNT}."
        elif topic.strip() and (topic_id is None or topic_id not in topics):
            error = "That topic is not part of this subject."
        elif repo.pending_mcq_jobs(user["id"]) >= 1:
            error = "Questions are already being written for you. Wait for that to finish, then generate again."
        elif not topics:
            error = "Upload some material first."
        if error:
            return _subject_html(db, user, session, row, status=400, mcq_error=error)
        scope = f"{n} question{'s' if n != 1 else ''} from " + (f"the topic \"{topics[topic_id]['path']}\"" if topic_id else "the whole subject")
        job_id = repo.create_mcq_job(user["id"], row["id"], topic_id, scope, n)
    _submit_mcq(job_id, user["id"])
    return RedirectResponse(f"/subjects/{row['id']}/mcq/jobs/{job_id}", status_code=303)


@app.get("/subjects/{subject_id}/mcq/jobs/{job_id}")
def mcq_job(request: Request, subject_id: str, job_id: str):
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        repo.expire_pending_mcq_jobs(3600)
        job = repo.get_mcq_job(user["id"], row["id"], _int(job_id) or -1)
        if job is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        items = repo.list_mcq(user["id"], row["id"], job_id=job["id"]) if job["status"] != "pending" else []
        trace = repo.mcq_trace(user["id"], row["id"], job["id"]) if job["status"] != "pending" else []
        return _html("Writing questions", ui.mcq_job_page(row, job, items, trace, session.csrf), user=user, csrf=session.csrf)


@app.get("/subjects/{subject_id}/mcq")
def mcq_bank(request: Request, subject_id: str, topic: str = ""):
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        topic_id = _int(topic) if topic else None
        items = repo.list_mcq(user["id"], row["id"], topic_id)
        return _html("Question bank", ui.mcq_bank_page(row, items, repo.list_topics(user["id"], row["id"]), topic_id, session.csrf),
                     user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/mcq/{item_id}/delete")
def mcq_delete(request: Request, subject_id: str, item_id: str, csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        if not Repo(db).delete_mcq(user["id"], row["id"], _int(item_id) or -1):
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
    return RedirectResponse(f"/subjects/{row['id']}/mcq", status_code=303)


# =========================================================================== Phase C — Quiz taking


def _get_provider(user, db):
    """Return a callable(messages, schema) -> parsed pydantic model.
    Uses the first available tier (local Ollama). Returns None if no tiers available.
    """
    from slice.budget import Budget
    tiers, _ = tier_factory(db, user)
    if not tiers:
        return None
    tier = tiers[0]

    def _call(messages, schema, timeout=90):
        store = studydb.open_db()
        try:
            budget = Budget(store, "quiz-agent", tier.settings)
            return tier.provider(
                settings=tier.settings, budget=budget,
                messages=messages, schema=schema,
                model=tier.model, step="quiz_agent", timeout=float(timeout))
        finally:
            store.close()

    return _call


@app.get("/subjects/{subject_id}/quiz")
def quiz_home(request: Request, subject_id: str):
    """Show quiz start page: pick topic, see past attempts, see weak topics."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        topics     = [t for t in repo.list_topics(user["id"], row["id"]) if t["chunks"]]
        items_count = len(repo.list_mcq(user["id"], row["id"]))
        attempts   = repo.list_attempts(user["id"], row["id"], limit=5)
        weaks      = repo.weak_topics(user["id"], row["id"])
        active_att = repo.get_active_attempt(user["id"], row["id"])
        return _html("Quiz", ui.quiz_home_page(row, topics, items_count, attempts, weaks, active_att, session.csrf),
                     user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/quiz/start")
def quiz_start(request: Request, subject_id: str, topic_id: str = Form(""), csrf: str = Form("")):
    """Create a new quiz attempt and redirect to the first question."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)

        # Abandon any existing active attempt
        active = repo.get_active_attempt(user["id"], row["id"])
        if active:
            db.execute("UPDATE quiz_attempts SET is_active=0, finished_at=? WHERE id=?",
                       (import_time(), active["id"]))

        tid = _int(topic_id.strip()) if topic_id.strip() else None
        items = repo.list_mcq(user["id"], row["id"], topic_id=tid)
        if not items:
            return _subject_html(db, user, session, row, status=400,
                                 error="Generate some questions first before taking a quiz.")

        import random, time as _t
        rng = random.Random(int(_t.time()))
        rng.shuffle(items)
        item_ids = [it["id"] for it in items[:20]]   # cap at 20 Qs per session

        root_topic_id = tid or (items[0]["topic_id"] if items[0]["topic_id"] else None)

        attempt = quiz_flow.start_session(
            db, user["id"], row["id"],
            root_topic_id=root_topic_id or -1,
            item_ids=item_ids,
            attempt_number=(len(repo.list_attempts(user["id"], row["id"], limit=100)) + 1),
        )
        if attempt is None:
            return _subject_html(db, user, session, row, status=400, error="Could not start quiz. Try again.")

    return RedirectResponse(f"/subjects/{row['id']}/quiz/attempt/{attempt['id']}", status_code=303)


def import_time():
    import time
    return time.time()


@app.get("/subjects/{subject_id}/quiz/attempt/{attempt_id}")
def quiz_attempt(request: Request, subject_id: str, attempt_id: str, error: str = ""):
    """QUESTIONING state — show the current MCQ question."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        att = repo.get_attempt(user["id"], row["id"], _int(attempt_id) or -1)
        if att is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        if not att["is_active"]:
            return RedirectResponse(f"/subjects/{row['id']}/quiz/result/{att['id']}", status_code=303)

        # Get next unanswered MCQ item
        unanswered = db.execute(
            "SELECT aa.id AS answer_row_id, aa.item_id, mi.question, mi.options, mi.topic_path "
            "FROM attempt_answers aa JOIN mcq_items mi ON mi.id=aa.item_id "
            "WHERE aa.attempt_id=? AND aa.answered_at IS NULL ORDER BY aa.id LIMIT 1",
            (att["id"],)).fetchone()

        if unanswered is None:
            # All MCQs answered — run backward-pass check via quiz_flow
            provider_fn = _get_provider(user, db)

            def _spot(topic_id, topic_name, difficulty, prior_objections, **_):
                if provider_fn is None:
                    return quiz_agents.stub_spot(topic_id, topic_name, difficulty, prior_objections)
                return quiz_agents.spot_agent(topic_id, topic_name, difficulty, prior_objections, provider_fn)

            result = quiz_flow.current_question(db, user["id"], att["id"], _spot)
            if result.state == "complete":
                scoring.finish_attempt(db, user["id"], att["id"])
                return RedirectResponse(f"/subjects/{row['id']}/quiz/result/{att['id']}", status_code=303)
            if result.state == "backward_pass":
                return RedirectResponse(f"/subjects/{row['id']}/quiz/attempt/{att['id']}/callback", status_code=303)
            # questioning — show the adaptive question (handled below with the diagnostic route)
            nonce = request.state.script_nonce = secrets.token_urlsafe(16)
            return _html("Quiz — Diagnostic", ui.quiz_diagnostic_page(row, att, result, session.csrf, nonce=nonce),
                         user=user, csrf=session.csrf)

        import json
        opts = json.loads(unanswered["options"]) if isinstance(unanswered["options"], str) else unanswered["options"]
        nonce = request.state.script_nonce = secrets.token_urlsafe(16)
        return _html("Quiz", ui.quiz_question_page(
            row, att, unanswered, opts, session.csrf, error=error, nonce=nonce),
            user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/quiz/attempt/{attempt_id}/answer")
def quiz_answer(
    request: Request, subject_id: str, attempt_id: str,
    answer_row_id: str = Form(""), item_id: str = Form(""),
    chosen: str = Form(""), response_time: str = Form("0"),
    hesitations: str = Form("0"), csrf: str = Form(""),
):
    """Submit one MCQ answer, update scoring."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx

        try:
            rt    = max(0.0, float(response_time))
            hes   = max(0, int(hesitations))
            cidx  = int(chosen) if chosen.isdigit() else None
        except (ValueError, TypeError):
            rt, hes, cidx = 0.0, 0, None

        recorded = scoring.record_answer(db, user["id"], _int(attempt_id) or -1, _int(item_id) or -1,
                                         cidx, rt, hes, answer_row_id=_int(answer_row_id))

    if recorded is None:
        return RedirectResponse(f"/subjects/{row['id']}/quiz/attempt/{int(attempt_id)}?error=That+answer+could+not+be+recorded.",
                                status_code=303)
    return RedirectResponse(f"/subjects/{row['id']}/quiz/attempt/{int(attempt_id)}", status_code=303)


@app.post("/subjects/{subject_id}/quiz/attempt/{attempt_id}/diagnostic/answer")
def quiz_diagnostic_answer(
    request: Request, subject_id: str, attempt_id: str,
    question: str = Form(""), answer: str = Form(""),
    topic_id: str = Form(""), csrf: str = Form(""),
):
    """Submit the open-ended diagnostic answer for evaluation."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        att = Repo(db).get_attempt(user["id"], row["id"], _int(attempt_id) or -1)
        if att is None or not att["is_active"]:
            return RedirectResponse(f"/subjects/{row['id']}/quiz", status_code=303)

        provider_fn = _get_provider(user, db)
        graph = __import__("studyhub.prereq", fromlist=["load_graph"]).load_graph(db, row["id"])

        def _evaluate(topic_id, topic_name, question, student_answer, prior_verdicts, prereq_id, graph, **_):
            if provider_fn is None:
                return quiz_agents.stub_gate(topic_id, topic_name, question, student_answer, prior_verdicts, prereq_id, graph)
            return quiz_agents.gate_agent(topic_id, topic_name, question, student_answer, prior_verdicts, prereq_id, graph, provider_fn)

        result = quiz_flow.submit_answer(db, user["id"], att["id"], question, answer.strip(), _evaluate)
        if result.state == "complete":
            scoring.finish_attempt(db, user["id"], att["id"])        # inside the block: the connection is still open

    if result.state == "complete":
        return RedirectResponse(f"/subjects/{row['id']}/quiz/result/{attempt_id}", status_code=303)
    if result.state == "backward_pass":
        return RedirectResponse(f"/subjects/{row['id']}/quiz/attempt/{attempt_id}/callback", status_code=303)
    return RedirectResponse(f"/subjects/{row['id']}/quiz/attempt/{attempt_id}", status_code=303)


@app.get("/subjects/{subject_id}/quiz/attempt/{attempt_id}/callback")
def quiz_callback(request: Request, subject_id: str, attempt_id: str):
    """BACKWARD_PASS state — show the step-back/retry choice."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        att = Repo(db).get_attempt(user["id"], row["id"], _int(attempt_id) or -1)
        if att is None or not att["is_active"]:
            return RedirectResponse(f"/subjects/{row['id']}/quiz", status_code=303)
        return _html("Quiz — Prerequisite Check",
                     ui.quiz_callback_page(row, att, session.csrf), user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/quiz/attempt/{attempt_id}/callback")
def quiz_callback_resolve(
    request: Request, subject_id: str, attempt_id: str,
    decision: str = Form("retry"), csrf: str = Form(""),
):
    """BACKWARD_PASS decision: step_back | retry | timeout."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        d = decision if decision in ("step_back", "retry", "timeout") else "retry"
        quiz_flow.resolve_callback(db, user["id"], _int(attempt_id) or -1, d)
    return RedirectResponse(f"/subjects/{row['id']}/quiz/attempt/{attempt_id}", status_code=303)


@app.post("/subjects/{subject_id}/quiz/attempt/{attempt_id}/proctor")
async def quiz_proctor(request: Request, subject_id: str, attempt_id: str):
    """Receive a proctoring event from the quiz page script. Needs the session CSRF token in X-CSRF-Token."""
    import json as _json
    ctx = None
    with _open() as db:
        si = _signed_in(request, db)
        if si is None:
            from fastapi.responses import JSONResponse
            return JSONResponse({"ok": False}, status_code=401)
        user, session = si
        from fastapi.responses import JSONResponse
        if not auth.same_token(request.headers.get("x-csrf-token"), session.csrf):
            return JSONResponse({"ok": False}, status_code=403)          # a page on another site must not be able to post events
        row = Repo(db).get_subject(user["id"], _int(subject_id) or -1)
        if row is None:
            return JSONResponse({"ok": False}, status_code=404)
        try:
            body = await request.json()
        except Exception:
            body = None
        if not isinstance(body, dict):
            return JSONResponse({"ok": False}, status_code=400)
        event_type = str(body.get("event_type", ""))
        details    = body.get("details", {})
        ok = scoring.record_proctoring_event(db, user["id"], _int(attempt_id) or -1, event_type, details)
    from fastapi.responses import JSONResponse
    return JSONResponse({"ok": ok})


@app.get("/subjects/{subject_id}/quiz/result/{attempt_id}")
def quiz_result(request: Request, subject_id: str, attempt_id: str):
    """COMPLETE — show score, trust score, weak topics, per-question breakdown."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        att = repo.get_attempt(user["id"], row["id"], _int(attempt_id) or -1)
        if att is None:
            return _html("Not found", ui.not_found(), status=404, user=user, csrf=session.csrf)
        answers  = repo.list_attempt_answers(user["id"], row["id"], att["id"])
        proctor  = repo.proctoring_summary(user["id"], row["id"], att["id"])
        weaks    = repo.weak_topics(user["id"], row["id"])
        return _html("Quiz Result", ui.quiz_result_page(row, att, answers, proctor, weaks, session.csrf),
                     user=user, csrf=session.csrf)


@app.get("/subjects/{subject_id}/progress")
def subject_progress(request: Request, subject_id: str):
    """Per-topic mastery view for this subject."""
    with _open() as db:
        ctx, early = _member(request, db, subject_id)
        if early:
            return early
        user, session, row = ctx
        repo = Repo(db)
        progress = repo.topic_progress(user["id"], row["id"])
        prereqs  = repo.list_prereqs(user["id"], row["id"])
        topics   = repo.list_topics(user["id"], row["id"])
        return _html("Progress", ui.progress_page(row, progress, prereqs, topics, session.csrf),
                     user=user, csrf=session.csrf)


@app.post("/subjects/{subject_id}/prereq/set")
def prereq_set(request: Request, subject_id: str,
               topic_id: str = Form(""), prereq_id: str = Form(""), csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        Repo(db).set_prereq(user["id"], row["id"], _int(topic_id) or -1, _int(prereq_id) or -1)
    return RedirectResponse(f"/subjects/{row['id']}/progress", status_code=303)


@app.post("/subjects/{subject_id}/prereq/delete")
def prereq_delete(request: Request, subject_id: str,
                  topic_id: str = Form(""), prereq_id: str = Form(""), csrf: str = Form("")):
    with _open() as db:
        ctx, early = _member(request, db, subject_id, form_csrf=csrf)
        if early:
            return early
        user, session, row = ctx
        Repo(db).delete_prereq(user["id"], row["id"], _int(topic_id) or -1, _int(prereq_id) or -1)
    return RedirectResponse(f"/subjects/{row['id']}/progress", status_code=303)

