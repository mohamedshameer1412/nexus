"""Nexus JSON API (/api/v1). The same Python functions as the HTML pages; no business rule lives here.

Conventions
  * Success: JSON. Failure: {"error": {"code", "message"}} with the right status. Unknown/foreign resources are 404, never 403.
  * Signed-in requests are identified by the HttpOnly `sh_session` cookie. Every mutating request must send the session's CSRF token in
    the `X-CSRF-Token` header (GET /session returns it). Login and register use the pre-session (double-submit) token from GET /session.
  * Correct answers of practice questions are NOT in list responses; they are returned by GET .../answer on request.
"""
from __future__ import annotations

import re
import json
import time
import urllib.parse
from contextlib import contextmanager

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from studyhub import auth, cards, career, digest, foresight, patterns, tutor, twin as twinmod, roadmap as roadmapmod, explain, ingest, insights, mail_templates, mailer, mcq, models, otp, qa, retrieval, settings, webfetch
from studyhub import db as studydb
from studyhub.repo import Repo, SubjectError

router = APIRouter(prefix="/api/v1")


def _app():                                  # lazy: app.py imports this module
    from studyhub.web import app as appmod
    return appmod


def err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def iso(ts) -> str | None:
    return None if ts is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


@contextmanager
def _db():
    store = studydb.open_db()
    try:
        yield store.db
    finally:
        store.close()


class Ctx:
    def __init__(self, db, user, session, subject=None):
        self.db, self.user, self.session, self.subject, self.repo = db, user, session, subject, Repo(db)

    @property
    def uid(self) -> int:
        return self.user["id"]


def guard(request: Request, db, *, mutate: bool = False, subject_id: str | None = None):
    """(Ctx, None) or (None, error response). Checks sign-in, CSRF (for mutations) and subject ownership."""
    appmod = _app()
    si = appmod._signed_in(request, db)
    if si is None:
        return None, err(401, "unauthenticated", "Please sign in.")
    user, session = si
    if mutate and not auth.same_token(request.headers.get("x-csrf-token"), session.csrf):
        return None, err(403, "csrf", "The request was refused. Reload the page and try again.")
    subject = None
    if subject_id is not None:
        subject = Repo(db).get_subject(user["id"], appmod._int(subject_id) or -1)
        if subject is None:
            return None, err(404, "not_found", "Not found.")
    return Ctx(db, user, session, subject), None


def _int(text) -> int | None:
    return _app()._int(str(text))


# --------------------------------------------------------------------------------------------------- session

def _user_json(u: dict) -> dict:
    return {"id": u["id"], "username": u["username"], "cloud_consent": bool(u["cloud_consent"]), "email": u.get("email")}


@router.get("/session")
def session_info(request: Request):
    """Who am I, and the CSRF token to send. Signed out: a pre-session token (also set as a cookie) for login/register."""
    appmod = _app()
    with _db() as db:
        si = appmod._signed_in(request, db)
        if si:
            return {"authenticated": True, "user": _user_json(si[0]), "csrf": si[1].csrf}
    token, is_new = appmod._pre_token(request)
    response = JSONResponse({"authenticated": False, "user": None, "csrf": token})
    return appmod._with_pre_cookie(response, token, is_new)


@router.get("/me")
def me(request: Request):
    with _db() as db:
        ctx, bad = guard(request, db)
        return bad or {"user": _user_json(ctx.user)}


class Credentials(BaseModel):
    username: str = ""
    email: str = ""
    password: str = ""


def _pre_ok(request: Request) -> bool:
    return auth.same_token(request.headers.get("x-csrf-token"), request.cookies.get(_app().PRE_COOKIE))


def _signed_in_response(db, user_id: int, status: int):
    appmod = _app()
    token, session = auth.create_session(db, user_id)
    response = JSONResponse({"user": _user_json(Repo(db).get_user(user_id)), "csrf": session.csrf}, status_code=status)
    appmod._set_session_cookie(response, token)
    return response


@router.post("/register", status_code=201)
def register(request: Request, body: Credentials, background: BackgroundTasks):
    if not _pre_ok(request):
        return err(403, "csrf", "The request was refused. Reload the page and try again.")
    if not body.email.strip():
        return err(400, "invalid", "Enter your email address. You will use it to log in.")
    ip = _ip(request)
    with _db() as db:
        try:
            uid = auth.register(db, body.username, body.password, email=body.email)
        except auth.AuthError as e:
            return err(400, "invalid", str(e))
        auth.purge_expired(db)
        address = auth.normalise_email(body.email)
        try:                                                 # send the address-check code now; the account works without it
            otp.throttle_signup(db, ip)
            background.add_task(_mail_code, "verify", address, otp.issue(db, "verify", address, uid, ip), ip)
        except Exception:
            pass
        return _signed_in_response(db, uid, 201)


@router.post("/login")
def login(request: Request, body: Credentials):
    if not _pre_ok(request):
        return err(403, "csrf", "The request was refused. Reload the page and try again.")
    ip = _ip(request)
    with _db() as db:
        try:
            uid = auth.authenticate(db, body.email or body.username, body.password, ip=ip)
        except auth.AuthError as e:
            msg = "Invalid email or password." if str(e) == auth.GENERIC_FAILURE else str(e)
            return err(429 if "Too many" in msg else 400, "too_many_attempts" if "Too many" in msg else "invalid_login", msg)
        return _signed_in_response(db, uid, 200)


@router.post("/logout", status_code=204)
def logout(request: Request):
    appmod = _app()
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        auth.delete_session(db, request.cookies.get(appmod.SESSION_COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(appmod.SESSION_COOKIE, path="/")
    return response


# -------------------------------------------------------------------------------------------------- subjects

def _counts(db, subject_id: int) -> dict:
    q = lambda sql: db.execute(sql, (subject_id,)).fetchone()[0]          # noqa: E731
    return {"documents": q("SELECT COUNT(*) FROM documents WHERE subject_id=?"),
            "topics": q("SELECT COUNT(*) FROM topics WHERE subject_id=?"),
            "questions": q("SELECT COUNT(*) FROM doubts WHERE subject_id=?"),
            "practice_questions": q("SELECT COUNT(*) FROM mcq_items WHERE subject_id=?")}


def _subject_json(db, s: dict) -> dict:
    return {"id": s["id"], "name": s["name"], "description": s["description"], "created_at": iso(s["created_at"]), "level": s.get("level"),
            "counts": _counts(db, s["id"])}


class SubjectBody(BaseModel):
    name: str = ""
    description: str = ""


@router.get("/subjects")
def list_subjects(request: Request):
    with _db() as db:
        ctx, bad = guard(request, db)
        return bad or {"subjects": [_subject_json(db, s) for s in ctx.repo.list_subjects(ctx.uid)]}


@router.post("/subjects", status_code=201)
def create_subject(request: Request, body: SubjectBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        try:
            sid = ctx.repo.create_subject(ctx.uid, body.name, body.description)
        except SubjectError as e:
            return err(400, "invalid", str(e))
        return JSONResponse(_subject_json(db, ctx.repo.get_subject(ctx.uid, sid)), status_code=201)


@router.get("/subjects/{subject_id}")
def get_subject(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        return bad or _subject_json(db, ctx.subject)


@router.patch("/subjects/{subject_id}")
def update_subject(request: Request, subject_id: str, body: SubjectBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        try:
            ctx.repo.update_subject(ctx.uid, ctx.subject["id"], body.name, body.description)
        except SubjectError as e:
            return err(400, "invalid", str(e))
        return _subject_json(db, ctx.repo.get_subject(ctx.uid, ctx.subject["id"]))


class LevelBody(BaseModel):
    level: str


@router.put("/subjects/{subject_id}/level")
def set_level(request: Request, subject_id: str, body: LevelBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if body.level not in ("new", "intermediate", "professional"):
            return err(400, "invalid", "Choose new learner, intermediate or professional.")
        db.execute("UPDATE subjects SET level=? WHERE id=? AND user_id=?", (body.level, ctx.subject["id"], ctx.uid))
        return {"level": body.level}


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        ingest.delete_subject(db, ctx.uid, ctx.subject["id"])
        return Response(status_code=204)


# -------------------------------------------------------------------------------------------------- materials

def _doc_json(d: dict) -> dict:
    return {"id": d["id"], "kind": d["kind"], "title": d["title"], "source": d["source"], "pages": d["pages"], "status": d["status"],
            "warnings": d["warnings"], "bytes": d["bytes"], "chunks": d["chunks"], "created_at": iso(d["created_at"]), "role": d.get("role", "notes"),
            "ocr_pages": d.get("ocr_pages") or 0}


@router.get("/subjects/{subject_id}/materials")
def list_materials(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        return bad or {"documents": [_doc_json(d) for d in ctx.repo.list_documents(ctx.uid, ctx.subject["id"])]}


@router.post("/subjects/{subject_id}/materials", status_code=201)
def upload_material(request: Request, subject_id: str, file: UploadFile = File(...), role: str = Form("notes")):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        data = file.file.read(settings.max_upload_bytes() + 1)
        try:
            r = ingest.ingest(db, ctx.uid, ctx.subject["id"], file.filename or "upload", data, role=role)
        except ingest.IngestError as e:
            return err(400, "upload_refused", str(e))
        doc = ctx.repo.get_document(ctx.uid, ctx.subject["id"], r.document_id)
        return JSONResponse({"document": _doc_json(doc), "duplicate": r.duplicate}, status_code=200 if r.duplicate else 201)


class UrlBody(BaseModel):
    url: str = Field(max_length=2000)
    role: str = "notes"


class RoleBody(BaseModel):
    role: str


@router.post("/subjects/{subject_id}/materials/url", status_code=201)
def add_web_page(request: Request, subject_id: str, body: UrlBody):
    """Add a web page as material: fetched by the server under the rules in webfetch.py, turned into text, then treated like any upload."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        now = time.time()
        recent = otp._events(db, "url_user", str(ctx.uid), 3600, now)
        if len(recent) >= 20:
            return _limited(otp.RateLimited(recent[-20] + 3600 - now))
        otp._note(db, "url_user", str(ctx.uid), now)
        try:
            final, ctype, raw, charset = webfetch.fetch(body.url)
            title, text = webfetch.html_to_text(raw, charset, ctype)
            if len(text) < 200:
                return err(400, "upload_refused", "That page has too little readable text to study from.")
            name = ((title or urllib.parse.urlsplit(final).hostname or "web page")[:150]) + ".txt"
            r = ingest.ingest(db, ctx.uid, ctx.subject["id"], name, text.encode("utf-8"), source_url=final, role=body.role)
        except (webfetch.FetchError, ingest.IngestError) as e:
            return err(400, "upload_refused", str(e))
        doc = ctx.repo.get_document(ctx.uid, ctx.subject["id"], r.document_id)
        return JSONResponse({"document": _doc_json(doc), "duplicate": r.duplicate}, status_code=200 if r.duplicate else 201)


@router.get("/subjects/{subject_id}/materials/{document_id}")
def get_material(request: Request, subject_id: str, document_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        doc = ctx.repo.get_document(ctx.uid, ctx.subject["id"], _int(document_id) or -1)
        if doc is None:
            return err(404, "not_found", "Not found.")
        chunks = ctx.repo.document_chunks(ctx.uid, ctx.subject["id"], doc["id"])
        return {"document": _doc_json(doc), "passages": [
            {"id": c["id"], "ordinal": c["ordinal"], "page_start": c["page_start"], "page_end": c["page_end"], "heading_path": c["heading_path"],
             "text": c["text"], "quarantined": bool(c["quarantined"]), "flag_reason": c["flag_reason"]} for c in chunks]}


@router.delete("/subjects/{subject_id}/materials/{document_id}", status_code=204)
def delete_material(request: Request, subject_id: str, document_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if not ingest.delete_document(db, ctx.uid, ctx.subject["id"], _int(document_id) or -1):
            return err(404, "not_found", "Not found.")
        return Response(status_code=204)


@router.get("/subjects/{subject_id}/topics")
def list_topics(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        return bad or {"topics": [{"id": t["id"], "name": t["name"], "path": t["path"], "passages": t["chunks"]}
                                  for t in ctx.repo.list_topics(ctx.uid, ctx.subject["id"])]}


@router.get("/subjects/{subject_id}/search")
def search(request: Request, subject_id: str, q: str = ""):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        q = " ".join(q.split())[:200]
        hits = retrieval.search(db, ctx.uid, ctx.subject["id"], q, k=8) if q else []
        return {"query": q, "terms": retrieval.terms(q), "results": [
            {"passage_id": h.id, "document_id": h.document_id, "document": h.doc_title, "heading_path": h.heading_path,
             "page_start": h.page_start, "page_end": h.page_end, "text": h.text, "matched": h.matched, "relevant": h.relevant}
            for h in hits]}


# ------------------------------------------------------------------------------------------------- questions

class QuestionBody(BaseModel):
    question: str = ""


class FeedbackBody(BaseModel):
    value: str = ""


def _citation_json(x: dict) -> dict:
    return {"passage_id": x["chunk_id"], "document_id": x.get("document_id"), "quote": x["quote"], "document": x["doc_title"], "heading_path": x["heading_path"],
            "page_start": x["page_start"], "page_end": x["page_end"]}


def _question_json(ctx: Ctx, d: dict, detail: bool) -> dict:
    out = {"id": d["id"], "question": d["question"], "status": d["status"], "tier": d.get("tier"), "feedback": d.get("feedback"),
           "created_at": iso(d["created_at"]), "saved": bool(d.get("saved"))}
    if not detail:
        return out
    trace = ctx.repo.doubt_trace(ctx.uid, ctx.subject["id"], d["id"]) if d["status"] != "pending" else []
    out.update({
        "model": d["model"], "reason": d["reason"], "kind": d["kind"], "dropped": d["dropped"], "explanation": d["explanation"],
        "claims": [{"text": c["text"], "citations": [_citation_json(x) for x in c["citations"]]} for c in d["claims"]],
        "sources": [{"passage_id": s["chunk_id"], "document_id": s.get("document_id"), "document": s["doc_title"], "heading_path": s["heading_path"], "page_start": s["page_start"],
                     "page_end": s["page_end"], "text": s["text"], "matched": s["matched"]} for s in d["sources"]],
        "verification": explain.verification_rows(d["claims"], d["dropped"], trace) if d["status"] == "answered" else [],
        "steps": [{"by": s["by"], "kind": s["kind"], "text": explain.step_text({"kind": s["kind"], "payload": s["payload"]})} for s in trace],
        "loop": {"sent_back": sum(1 for s in trace if s["kind"] == "revision"), "rejected": sum(len(s["payload"].get("failed", [])) for s in trace if s["kind"] == "verification")}})
    return out


@router.post("/subjects/{subject_id}/questions", status_code=202)
def ask(request: Request, subject_id: str, body: QuestionBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        q = " ".join(body.question.split())
        if len(q) < 3:
            return err(400, "invalid", "Type your question first.")
        if len(q) > qa.MAX_QUESTION_CHARS:
            return err(400, "invalid", f"Please keep the question under {qa.MAX_QUESTION_CHARS} characters.")
        ctx.repo.expire_pending_doubts(1800)
        if ctx.repo.pending_doubts(ctx.uid) >= settings.max_pending_questions():
            return err(429, "too_many_pending", "You already have questions being answered. Wait for one to finish.")
        if not any(d["chunks"] for d in ctx.repo.list_documents(ctx.uid, ctx.subject["id"])):
            return err(400, "no_material", "Upload some material first.")
        did = ctx.repo.create_doubt(ctx.uid, ctx.subject["id"], q)
    _app()._submit(did, ctx.uid)
    return JSONResponse({"id": did, "status": "pending"}, status_code=202)


@router.get("/subjects/{subject_id}/questions")
def list_questions(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        ctx.repo.expire_pending_doubts(1800)
        return {"questions": [_question_json(ctx, d, False) for d in ctx.repo.list_doubts(ctx.uid, ctx.subject["id"], 50)]}


@router.get("/subjects/{subject_id}/questions/{question_id}")
def get_question(request: Request, subject_id: str, question_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        ctx.repo.expire_pending_doubts(1800)
        d = ctx.repo.get_doubt(ctx.uid, ctx.subject["id"], _int(question_id) or -1)
        return err(404, "not_found", "Not found.") if d is None else _question_json(ctx, d, True)


@router.post("/subjects/{subject_id}/questions/{question_id}/feedback")
def question_feedback(request: Request, subject_id: str, question_id: str, body: FeedbackBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if not ctx.repo.set_doubt_feedback(ctx.uid, ctx.subject["id"], _int(question_id) or -1, body.value):
            return err(404, "not_found", "Not found.")
        return {"ok": True}


@router.delete("/subjects/{subject_id}/questions/{question_id}", status_code=204)
def delete_question(request: Request, subject_id: str, question_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if not ctx.repo.delete_doubt(ctx.uid, ctx.subject["id"], _int(question_id) or -1):
            return err(404, "not_found", "Not found.")
        return Response(status_code=204)


# --------------------------------------------------------------------------------- practice (MCQ) generation

class McqJobBody(BaseModel):
    topic_id: int | None = None
    count: int = mcq.DEFAULT_COUNT
    purpose: str = "practice"                # "diagnostic" = ten questions spread over the topics and over easy/medium/hard


def _mcq_json(m: dict) -> dict:
    """A practice question WITHOUT its answer."""
    return {"id": m["id"], "topic_id": m["topic_id"], "topic_path": m["topic_path"], "question": m["question"], "options": m["options"],
            "created_at": iso(m["created_at"])}


@router.post("/subjects/{subject_id}/mcq/jobs", status_code=202)
def create_mcq_job(request: Request, subject_id: str, body: McqJobBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        ctx.repo.expire_pending_mcq_jobs(3600)
        if body.purpose not in ("practice", "diagnostic"):
            return err(400, "invalid", "The purpose must be practice or diagnostic.")
        if body.purpose == "diagnostic":
            body.topic_id, body.count = None, mcq.MAX_COUNT
        topics = {t["id"]: t for t in ctx.repo.list_topics(ctx.uid, ctx.subject["id"]) if t["chunks"]}
        if not 1 <= body.count <= mcq.MAX_COUNT:
            return err(400, "invalid", f"Choose a number of questions from 1 to {mcq.MAX_COUNT}.")
        if body.topic_id is not None and body.topic_id not in topics:
            return err(400, "invalid", "That topic is not part of this subject.")
        if not topics:
            return err(400, "no_material", "Upload some material first.")
        if ctx.repo.pending_mcq_jobs(ctx.uid) >= 1:
            return err(429, "too_many_pending", "Questions are already being written for you. Wait for that to finish.")
        scope = f"{body.count} question{'s' if body.count != 1 else ''} from " + (
            f'the topic "{topics[body.topic_id]["path"]}"' if body.topic_id else "the whole subject")
        job = ctx.repo.create_mcq_job(ctx.uid, ctx.subject["id"], body.topic_id, scope, body.count, body.purpose)
    _app()._submit_mcq(job, ctx.uid)
    return JSONResponse({"id": job, "status": "pending"}, status_code=202)


@router.get("/subjects/{subject_id}/mcq/jobs/{job_id}")
def get_mcq_job(request: Request, subject_id: str, job_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        ctx.repo.expire_pending_mcq_jobs(3600)
        job = ctx.repo.get_mcq_job(ctx.uid, ctx.subject["id"], _int(job_id) or -1)
        if job is None:
            return err(404, "not_found", "Not found.")
        done = job["status"] != "pending"
        items = ctx.repo.list_mcq(ctx.uid, ctx.subject["id"], job_id=job["id"]) if done else []
        trace = ctx.repo.mcq_trace(ctx.uid, ctx.subject["id"], job["id"]) if done else []
        return {"id": job["id"], "purpose": job.get("purpose") or "practice", "status": job["status"], "scope": job["scope"], "requested": job["requested"], "produced": job["produced"],
                "rejected": job["rejected"], "reason": job["reason"], "model": job["model"], "tier": job["tier"],
                "questions": [_mcq_json(m) for m in items],
                "steps": [{"by": s["by"], "kind": s["kind"], "text": explain.mcq_step_text({"kind": s["kind"], "payload": s["payload"]})} for s in trace],
                "loop": {"sent_back": sum(1 for s in trace if s["kind"] == "revision"), "rejected": sum(len(s["payload"].get("failed", [])) for s in trace if s["kind"] == "verification")}}


@router.get("/subjects/{subject_id}/mcq")
def list_mcq(request: Request, subject_id: str, topic_id: str = ""):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        return bad or {"questions": [_mcq_json(m) for m in ctx.repo.list_mcq(ctx.uid, ctx.subject["id"], _int(topic_id) if topic_id else None)]}


@router.get("/subjects/{subject_id}/mcq/{item_id}/answer")
def mcq_answer(request: Request, subject_id: str, item_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        m = next((x for x in ctx.repo.list_mcq(ctx.uid, ctx.subject["id"]) if x["id"] == _int(item_id)), None)
        if m is None:
            return err(404, "not_found", "Not found.")
        return {"id": m["id"], "answer_index": m["answer_index"], "answer": m["options"][m["answer_index"]], "explanation": m["explanation"],
                "quote": m["quote"], "document": m["doc_title"], "heading_path": m["heading_path"], "page_start": m["page_start"],
                "page_end": m["page_end"], "independently_checked": m["solver"] == "agreed"}


@router.delete("/subjects/{subject_id}/mcq/{item_id}", status_code=204)
def delete_mcq(request: Request, subject_id: str, item_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if not ctx.repo.delete_mcq(ctx.uid, ctx.subject["id"], _int(item_id) or -1):
            return err(404, "not_found", "Not found.")
        return Response(status_code=204)


# ---------------------------------------------------------------------------------------------------- account

class CloudBody(BaseModel):
    consent: bool = False


@router.get("/account")
def account(request: Request):
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        s = models.slice_config.settings(reload=False)
        row = db.execute("SELECT email, email_verified, weekly_email, last_digest_at, department, semester FROM users WHERE id=?", (ctx.uid,)).fetchone()
        pending = db.execute("SELECT email FROM email_otps WHERE user_id=? AND purpose='verify' AND consumed_at IS NULL AND expires_at>? ORDER BY id DESC LIMIT 1", (ctx.uid, time.time())).fetchone()
        return {"user": _user_json(ctx.user), "key_configured": bool(s.api_key),
                "allowed_models": models.allowed_cloud_models() if s.api_key else [],
                "academic": {"department": row["department"], "semester": row["semester"]},
                "email": {"login": row["email"], "address": row["email"] if row["email_verified"] else None, "verified": bool(row["email_verified"]), "pending": pending["email"] if pending else None,
                          "weekly": bool(row["weekly_email"]), "last_digest_at": iso(row["last_digest_at"]), "can_send": mailer.configured() or mailer.debug_outbox()}}


@router.put("/account/cloud")
def set_cloud(request: Request, body: CloudBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        ctx.repo.set_cloud_consent(ctx.uid, body.consent)
        return {"cloud_consent": body.consent}


# ------------------------------------------------------------------------------------------------ quiz attempts

MAX_QUIZ_ITEMS = 20


def _log_action(ctx, topic_id: int, kind: str) -> None:
    """Remember a study action on a topic that is below target, with its confidence now, so the loop can check later whether it helped."""
    sid = ctx.subject["id"]
    if ctx.db.execute("SELECT 1 FROM interventions WHERE user_id=? AND subject_id=? AND topic_id=? AND kind=? AND outcome IS NULL AND created_at>?",
                      (ctx.uid, sid, topic_id, kind, time.time() - 7 * 86400)).fetchone():
        return
    e = insights.topic_confidence(ctx.db, ctx.uid, sid)["topics"].get(topic_id)
    if e and e["confidence"] < roadmapmod.target_for(ctx.subject.get("level")):
        tutor.start(ctx.db, ctx.uid, sid, topic_id, kind, e["confidence"], e["answered"])


class QuizStartBody(BaseModel):
    topic_id: int | None = None
    mode: str = "practice"                                   # "practice" | "assessment"
    kind: str = "standard"                                   # "standard" | "diagnostic" | "revision"
    job_id: int | None = None                                # a diagnostic made from one generation job
    adaptive: bool = False                                   # pick the most informative questions for this student instead of a random set
    count: int | None = Field(default=None, ge=3, le=20)     # how many questions (default: up to MAX_QUIZ_ITEMS)
    difficulty: str = "mixed"                                # "mixed" | "easy" | "medium" | "hard" (standard quizzes)


class QuizAnswerBody(BaseModel):
    answer_row_id: int
    item_id: int
    chosen: int
    response_time: float = 0.0
    hesitations: int = 0


class EventBody(BaseModel):
    event_type: str


class TerminateBody(BaseModel):
    reason: str


END_REASONS = {"tab_switch": "You left the assessment page", "full_screen_exit": "You left full screen",
               "no_face": "No face was visible to the camera", "camera_off": "The camera was not available", "multiple_faces": "More than one face was visible to the camera"}


def _attempt_json(a: dict) -> dict:
    correct, wrong = int(a.get("correct_answers") or 0), int(a.get("incorrect_answers") or 0)
    return {"id": a["id"], "mode": a.get("mode") or "practice", "kind": a.get("kind") or "standard", "active": bool(a["is_active"]), "started_at": iso(a.get("started_at")), "finished_at": iso(a.get("finished_at")),
            "correct": correct, "incorrect": wrong, "answered": correct + wrong}


def _weak_json(w: dict) -> dict:
    return {"topic_id": w["topic_id"], "name": w["name"], "path": w["path"], "answered": w["answered"], "correct": w["correct"],
            "mastery": w["mastery"], "state": w["state"]}


@router.get("/subjects/{subject_id}/quiz")
def quiz_home(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        sid = ctx.subject["id"]
        topics = [{"id": t["id"], "path": t["path"]} for t in ctx.repo.list_topics(ctx.uid, sid) if t["chunks"]]
        active = ctx.repo.get_active_attempt(ctx.uid, sid)
        return {"questions_in_bank": len(ctx.repo.list_mcq(ctx.uid, sid)), "topics": topics,
                "active_attempt": active["id"] if active else None, "active_mode": (active.get("mode") or "practice") if active else None,
                "attempts": [_attempt_json(a) for a in ctx.repo.list_attempts(ctx.uid, sid, limit=10)],
                "weak_topics": [_weak_json(w) for w in ctx.repo.weak_topics(ctx.uid, sid)]}


@router.post("/subjects/{subject_id}/quiz/attempts", status_code=201)
def quiz_start(request: Request, subject_id: str, body: QuizStartBody):
    import random
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        sid = ctx.subject["id"]
        if body.mode not in ("practice", "assessment"):
            return err(400, "invalid", "The mode must be practice or assessment.")
        if body.kind not in ("standard", "diagnostic", "revision"):
            return err(400, "invalid", "The kind must be standard, diagnostic or revision.")
        items = ctx.repo.list_mcq(ctx.uid, sid, topic_id=body.topic_id if body.kind == "standard" else None)
        if not items:
            return err(400, "no_questions", "Write some practice questions first; a quiz is made from them.")
        if body.kind == "revision":            # what was answered wrongly last time, plus every question of topics that are still shaky
            wrong_ids = {w["item_id"] for w in insights.wrong_items(db, ctx.uid, sid)}
            shaky = {t for t, e in insights.topic_confidence(db, ctx.uid, sid)["topics"].items() if e["label"] in ("shaky", "few") and e["confidence"] < 0.55}
            items = [i for i in items if i["id"] in wrong_ids or i["topic_id"] in shaky]
            if not items:
                return err(400, "nothing_to_revise", "Nothing to revise yet. Take a quiz first; the questions you miss are collected here.")
        elif body.kind == "diagnostic" and body.job_id is not None:      # the ten questions written for this student's diagnostic
            if ctx.repo.get_mcq_job(ctx.uid, sid, body.job_id) is None:
                return err(404, "not_found", "Not found.")
            items = ctx.repo.list_mcq(ctx.uid, sid, job_id=body.job_id)
            if not items:
                return err(400, "no_questions", "No questions were written for that diagnostic.")
        elif body.kind == "diagnostic":        # a short placement test: up to two questions from every topic
            per: dict = {}
            for i in items:
                per.setdefault(i["topic_id"], []).append(i)
            items = [x for group in per.values() for x in random.sample(group, min(2, len(group)))]
        if body.difficulty not in ("mixed", "easy", "medium", "hard"):
            return err(400, "invalid", "The difficulty must be mixed, easy, medium or hard.")
        if body.kind == "standard" and body.difficulty != "mixed":
            level = [i for i in items if (i.get("difficulty") or "medium") == body.difficulty]
            if not level:
                return err(400, "no_questions", f"There are no {body.difficulty} questions yet. Choose mixed, or generate more practice questions.")
            items = level
        limit = min(body.count or MAX_QUIZ_ITEMS, MAX_QUIZ_ITEMS)
        if body.adaptive and body.kind == "standard":
            items = insights.select_adaptive(db, ctx.uid, sid, items, limit, roadmapmod.target_for(ctx.subject.get("level")), patterns.exam_weights(db, sid))
        active = ctx.repo.get_active_attempt(ctx.uid, sid)
        if active:                                            # starting a new quiz abandons the unfinished one
            db.execute("UPDATE quiz_attempts SET is_active=0, finished_at=? WHERE id=?", (time.time(), active["id"]))
        random.shuffle(items)
        root = body.topic_id or items[0]["topic_id"] or -1
        attempt = _app().quiz_flow.start_session(db, ctx.uid, sid, root_topic_id=root, item_ids=[i["id"] for i in items[:limit]],
                                                 attempt_number=len(ctx.repo.list_attempts(ctx.uid, sid, limit=100)) + 1)
        if attempt is None:
            return err(400, "invalid", "That topic is not part of this subject.")
        db.execute("UPDATE quiz_attempts SET mode=?, kind=? WHERE id=? AND user_id=?", (body.mode, body.kind, attempt["id"], ctx.uid))
        if body.kind == "revision":
            for t in {i["topic_id"] for i in items[:limit] if i["topic_id"]}:
                _log_action(ctx, t, "revision")
        elif body.kind == "standard" and body.topic_id:
            _log_action(ctx, body.topic_id, "practice")
        return JSONResponse({"id": attempt["id"], "mode": body.mode, "kind": body.kind}, status_code=201)


def _own_attempt(ctx, attempt_id: str):
    return ctx.repo.get_attempt(ctx.uid, ctx.subject["id"], _int(attempt_id) or -1)


@router.get("/subjects/{subject_id}/quiz/attempts/{attempt_id}")
def quiz_state(request: Request, subject_id: str, attempt_id: str):
    """Where the quiz is now: the next multiple-choice question, or finished."""
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        att = _own_attempt(ctx, attempt_id)
        if att is None:
            return err(404, "not_found", "Not found.")
        appmod = _app()
        if not att["is_active"]:
            return {"state": "complete", "attempt": _attempt_json(att)}
        total = db.execute("SELECT COUNT(*) FROM attempt_answers WHERE attempt_id=?", (att["id"],)).fetchone()[0]
        nxt = db.execute(
            "SELECT aa.id AS answer_row_id, aa.item_id, aa.backtrack_from, mi.question, mi.options, mi.topic_path, "
            "(SELECT name FROM topics WHERE id=aa.backtrack_from) AS from_name, (SELECT name FROM topics WHERE id=mi.topic_id) AS topic_name "
            "FROM attempt_answers aa JOIN mcq_items mi ON mi.id=aa.item_id WHERE aa.attempt_id=? AND aa.answered_at IS NULL "
            "ORDER BY CASE WHEN aa.backtrack_from IS NULL THEN 1 ELSE 0 END, aa.id LIMIT 1", (att["id"],)).fetchone()
        base = {"attempt": _attempt_json(att), "total_questions": total}
        if nxt is not None:
            import json
            opts = json.loads(nxt["options"]) if isinstance(nxt["options"], str) else nxt["options"]
            done = db.execute("SELECT COUNT(*) FROM attempt_answers WHERE attempt_id=? AND answered_at IS NOT NULL", (att["id"],)).fetchone()[0]
            return {**base, "state": "mcq", "position": done + 1,
                    "item": {"answer_row_id": nxt["answer_row_id"], "item_id": nxt["item_id"], "question": nxt["question"], "options": opts,
                             "topic_path": nxt["topic_path"], "topic": nxt["topic_name"],
                             "backtrack": {"from": nxt["from_name"], "topic": nxt["topic_name"]} if nxt["backtrack_from"] else None}}
        # A quiz is multiple choice only: when the last question is answered it is finished (no written follow-up question).
        appmod.scoring.finish_attempt(db, ctx.uid, att["id"])
        return {"state": "complete", "attempt": _attempt_json(_own_attempt(ctx, attempt_id))}


@router.post("/subjects/{subject_id}/quiz/attempts/{attempt_id}/answer")
def quiz_answer(request: Request, subject_id: str, attempt_id: str, body: QuizAnswerBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        att = _own_attempt(ctx, attempt_id)
        if att is None:
            return err(404, "not_found", "Not found.")
        if not att["is_active"]:
            return err(409, "finished", "This quiz is already finished.")
        rec = _app().scoring.record_answer(db, ctx.uid, att["id"], body.item_id, body.chosen, max(0.0, body.response_time),
                                           max(0, body.hesitations), answer_row_id=body.answer_row_id)
        if rec is None:
            return err(400, "not_recorded", "That answer could not be recorded.")
        missed = db.execute("SELECT is_correct FROM attempt_answers WHERE id=?", (body.answer_row_id,)).fetchone()
        step = insights.backtrack(db, ctx.uid, ctx.subject["id"], att["id"], body.answer_row_id) if missed and missed["is_correct"] == 0 else None
        return {"ok": True, "backtrack": step}                                   # correctness is shown on the result page, not while answering


@router.post("/subjects/{subject_id}/quiz/attempts/{attempt_id}/events")
def quiz_event(request: Request, subject_id: str, attempt_id: str, body: EventBody):
    """Focus events, sent only when the student chose Assessment mode and accepted the notice."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        att = _own_attempt(ctx, attempt_id)
        if att is None:
            return err(404, "not_found", "Not found.")
        return {"ok": bool(_app().scoring.record_proctoring_event(db, ctx.uid, att["id"], body.event_type, {}))}


@router.post("/subjects/{subject_id}/quiz/attempts/{attempt_id}/terminate")
def quiz_terminate(request: Request, subject_id: str, attempt_id: str, body: TerminateBody):
    """An assessment ends at once when the rules were broken (left the page or full screen, no face, more than one face)."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        att = _own_attempt(ctx, attempt_id)
        if att is None:
            return err(404, "not_found", "Not found.")
        if (att.get("mode") or "practice") != "assessment":
            return err(400, "not_assessment", "Only an assessment can be ended this way.")
        if not att["is_active"]:
            return err(409, "finished", "This quiz is already finished.")
        if body.reason not in END_REASONS:
            return err(400, "invalid", "Unknown reason.")
        appmod = _app()
        appmod.scoring.record_proctoring_event(db, ctx.uid, att["id"], "auto_submit", {"reason": body.reason})
        appmod.scoring.finish_attempt(db, ctx.uid, att["id"])
        return {"ok": True, "reason": END_REASONS[body.reason]}


@router.get("/subjects/{subject_id}/quiz/attempts/{attempt_id}/result")
def quiz_result(request: Request, subject_id: str, attempt_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        att = _own_attempt(ctx, attempt_id)
        if att is None:
            return err(404, "not_found", "Not found.")
        if att["is_active"]:
            return err(409, "in_progress", "Finish the quiz to see the answers.")   # correct answers are never sent while it is running
        sid = ctx.subject["id"]
        rows = ctx.repo.list_attempt_answers(ctx.uid, sid, att["id"])
        answered = [r for r in rows if r.get("chosen_index") is not None]
        events = ctx.repo.proctoring_summary(ctx.uid, sid, att["id"]).get("event_counts", {})
        ended = db.execute("SELECT details_json FROM quiz_proctoring_events WHERE attempt_id=? AND event_type='auto_submit' ORDER BY id DESC LIMIT 1", (att["id"],)).fetchone()
        ended_reason = END_REASONS.get(json.loads(ended["details_json"]).get("reason")) if ended else None
        diag = insights.diagnosis(db, ctx.uid, sid, att["id"], ctx.subject.get("level")) if (att.get("kind") == "diagnostic") else None
        return {"attempt": _attempt_json(att), "diagnosis": diag, "ended_reason": ended_reason, "skipped": len(rows) - len(answered),
                "answers": [{"question": r["question"], "topic": r.get("topic_name") or r.get("topic_path") or "", "options": r["options"],
                             "chosen_index": r["chosen_index"], "answer_index": r["answer_index"], "correct": bool(r.get("is_correct")),
                             "explanation": r.get("explanation") or "", "backtrack": r.get("backtrack_from") is not None} for r in answered],
                "focus_events": {k: events.get(k, 0) for k in ("tab_switch", "full_screen_exit", "copy_attempt", "paste_attempt")},
                "weak_topics": [_weak_json(w) for w in ctx.repo.weak_topics(ctx.uid, sid)]}


# ---------------------------------------------------------------------------------------------------- progress

class PrereqBody(BaseModel):
    topic_id: int
    prereq_id: int


@router.get("/subjects/{subject_id}/progress")
def progress(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        sid = ctx.subject["id"]
        done = {p["topic_id"]: p for p in ctx.repo.topic_progress(ctx.uid, sid)}
        conf = insights.topic_confidence(db, ctx.uid, sid)
        topics = []
        for t in ctx.repo.list_topics(ctx.uid, sid):
            if not t["chunks"]:
                continue
            p, e = done.get(t["id"]), conf["topics"].get(t["id"])
            topics.append({"topic_id": t["id"], "name": t["name"], "path": t["path"], "answered": p["answered"] if p else 0,
                           "correct": p["correct"] if p else 0, "mastery": p["mastery"] if p else 0.0, "state": p["state"] if p else "unknown",
                           "confidence": e["confidence"] if e else None, "theta": e["theta"] if e else None, "se": e["se"] if e else None,
                           "expected_accuracy": e["expected_accuracy"] if e else None, "label": e["label"] if e else "untried",
                           "avg_seconds": e["avg_seconds"] if e else None, "recent_accuracy": e["recent_accuracy"] if e else None})
        return {"topics": topics, "weak_topics": [_weak_json(w) for w in ctx.repo.weak_topics(ctx.uid, sid)],
                "overall": conf["overall"], "ability_trend": insights.ability_trend(db, ctx.uid, sid),
                "prerequisites": [{"topic_id": r["topic_id"], "topic": r["topic_name"], "prereq_id": r["prereq_id"], "prereq": r["prereq_name"]}
                                  for r in ctx.repo.list_prereqs(ctx.uid, sid)]}


@router.get("/subjects/{subject_id}/revision")
def revision(request: Request, subject_id: str):
    """Questions still answered wrongly (latest answer), and the topics that need another look."""
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        sid = ctx.subject["id"]
        conf = insights.topic_confidence(db, ctx.uid, sid)["topics"]
        names = {t["id"]: t for t in ctx.repo.list_topics(ctx.uid, sid)}
        shaky = [{"topic_id": t, "name": names[t]["name"], "confidence": e["confidence"], "answered": e["answered"], "correct": e["correct"]}
                 for t, e in conf.items() if t in names and e["label"] == "shaky"]
        return {"wrong": insights.wrong_items(db, ctx.uid, sid), "shaky_topics": sorted(shaky, key=lambda x: x["confidence"])}


def _report_data(ctx) -> dict:
    db, sid = ctx.db, ctx.subject["id"]
    conf = insights.topic_confidence(db, ctx.uid, sid)
    rows = []
    for t in ctx.repo.list_topics(ctx.uid, sid):
        if not t["chunks"]:
            continue
        e = conf["topics"].get(t["id"])
        rows.append({"topic_id": t["id"], "name": t["name"], "answered": e["answered"] if e else 0, "correct": e["correct"] if e else 0,
                     "confidence": e["confidence"] if e else None, "theta": e["theta"] if e else None, "label": e["label"] if e else "untried",
                     "avg_seconds": e["avg_seconds"] if e else None})
    wrong = insights.wrong_items(db, ctx.uid, sid)
    attempts = []
    for a in ctx.repo.list_attempts(ctx.uid, sid, limit=20):
        if a["is_active"]:
            continue
        ended = db.execute("SELECT details_json FROM quiz_proctoring_events WHERE attempt_id=? AND event_type='auto_submit' ORDER BY id DESC LIMIT 1", (a["id"],)).fetchone()
        j = _attempt_json(a)
        j["ended_reason"] = END_REASONS.get(json.loads(ended["details_json"]).get("reason")) if ended else None
        attempts.append(j)
    back = db.execute(
        "SELECT t.name AS name, COUNT(*) AS n, SUM(aa.is_correct) AS c FROM attempt_answers aa JOIN quiz_attempts qa ON qa.id=aa.attempt_id "
        "JOIN mcq_items mi ON mi.id=aa.item_id JOIN topics t ON t.id=mi.topic_id WHERE qa.user_id=? AND qa.subject_id=? AND aa.backtrack_from IS NOT NULL "
        "AND aa.is_correct IS NOT NULL GROUP BY t.id ORDER BY t.ordinal", (ctx.uid, sid)).fetchall()
    return {"generated_at": iso(time.time()), "subject": ctx.subject["name"], "overall": conf["overall"], "topics": rows,
            "ability_trend": insights.ability_trend(db, ctx.uid, sid), "attempts": attempts, "wrong_questions": len(wrong),
            "wrong_sample": wrong[:10],
            "backtracking": [{"topic": r["name"], "asked": r["n"], "correct": int(r["c"] or 0)} for r in back],
            "recommendations": insights.recommendations(rows, conf["overall"], len(wrong)),
            "method": "Confidence is the probability that your ability on a topic is above the proficient line, from a 3-parameter IRT model "
                      "(discrimination 1, guessing 0.25) with a Normal(0,1.2) prior, fitted only to your own answers."}


@router.get("/subjects/{subject_id}/report")
def report(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        return bad or _report_data(ctx)


@router.get("/subjects/{subject_id}/report.csv")
def report_csv(request: Request, subject_id: str):
    import csv
    import io
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        d = _report_data(ctx)
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Nexus report", d["subject"], d["generated_at"]])
        w.writerow([])
        w.writerow(["Topic", "Answered", "Correct", "Confidence %", "Ability (theta)", "Level", "Avg seconds"])
        for t in d["topics"]:
            w.writerow([t["name"], t["answered"], t["correct"], "" if t["confidence"] is None else round(t["confidence"] * 100), t["theta"] if t["theta"] is not None else "", t["label"], t["avg_seconds"] or ""])
        w.writerow([])
        w.writerow(["Quiz", "Finished", "Mode", "Kind", "Correct", "Answered", "Ended early"])
        for a in d["attempts"]:
            w.writerow([a["id"], a["finished_at"], a["mode"], a["kind"], a["correct"], a["answered"], a["ended_reason"] or ""])
        return Response(out.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="nexus-report.csv"'})


@router.post("/subjects/{subject_id}/prerequisites", status_code=201)
def add_prereq(request: Request, subject_id: str, body: PrereqBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if not ctx.repo.set_prereq(ctx.uid, ctx.subject["id"], body.topic_id, body.prereq_id):
            return err(400, "invalid", "Choose two different topics of this subject; the reverse link must not already exist.")
        return JSONResponse({"ok": True}, status_code=201)


@router.delete("/subjects/{subject_id}/prerequisites/{topic_id}/{prereq_id}", status_code=204)
def remove_prereq(request: Request, subject_id: str, topic_id: str, prereq_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if not ctx.repo.delete_prereq(ctx.uid, ctx.subject["id"], _int(topic_id) or -1, _int(prereq_id) or -1):
            return err(404, "not_found", "Not found.")
        return Response(status_code=204)


# -------------------------------------------------------------------------------------------------- dashboard

DASH_DAYS = 14
DASH_TREND = 12


@router.get("/dashboard")
def dashboard(request: Request):
    """Numbers for the charts. Everything is filtered by the signed-in user; nothing is estimated or invented."""
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        uid = ctx.uid
        one = lambda sql, *a: db.execute(sql, a).fetchone()[0]                    # noqa: E731
        subjects = db.execute("SELECT id, name FROM subjects WHERE user_id=? ORDER BY name", (uid,)).fetchall()

        per_subject, topic_counts, weak = [], {"mastered": 0, "learning": 0, "weak": 0, "unknown": 0}, []
        for s in subjects:
            sid = s["id"]
            correct = one("SELECT COALESCE(SUM(correct_answers),0) FROM quiz_attempts WHERE user_id=? AND subject_id=?", uid, sid)
            wrong = one("SELECT COALESCE(SUM(incorrect_answers),0) FROM quiz_attempts WHERE user_id=? AND subject_id=?", uid, sid)
            per_subject.append({
                "id": sid, "name": s["name"],
                "materials": one("SELECT COUNT(*) FROM documents WHERE subject_id=?", sid),
                "questions": one("SELECT COUNT(*) FROM doubts WHERE subject_id=? AND user_id=?", sid, uid),
                "practice_questions": one("SELECT COUNT(*) FROM mcq_items WHERE subject_id=?", sid),
                "quizzes": one("SELECT COUNT(*) FROM quiz_attempts WHERE user_id=? AND subject_id=? AND is_active=0 AND correct_answers+incorrect_answers>0", uid, sid),
                "answered": correct + wrong, "correct": correct,
            })
            progress = {p["topic_id"]: p for p in ctx.repo.topic_progress(uid, sid)}
            for t in ctx.repo.list_topics(uid, sid):
                if not t["chunks"]:
                    continue
                p = progress.get(t["id"])
                state = p["state"] if p else "unknown"
                topic_counts[state] = topic_counts.get(state, 0) + 1
                if p and p["answered"] >= 2 and state in ("weak", "learning"):
                    weak.append({"topic_id": t["id"], "subject_id": sid, "subject": s["name"], "name": t["name"], "answered": p["answered"],
                                 "correct": p["correct"], "mastery": p["mastery"], "state": state})
        weak.sort(key=lambda w: w["mastery"])

        # activity per day (UTC) for the last DASH_DAYS days, zero-filled
        today = int(time.time()) // 86400
        first = today - (DASH_DAYS - 1)
        since = first * 86400
        asked = dict(db.execute("SELECT date(created_at,'unixepoch') d, COUNT(*) FROM doubts WHERE user_id=? AND created_at>=? GROUP BY d", (uid, since)).fetchall())
        answered = dict(db.execute(
            "SELECT date(aa.answered_at,'unixepoch') d, COUNT(*) FROM attempt_answers aa JOIN quiz_attempts a ON a.id=aa.attempt_id "
            "WHERE a.user_id=? AND aa.chosen_index IS NOT NULL AND aa.answered_at>=? GROUP BY d", (uid, since)).fetchall())
        days = []
        for n in range(first, today + 1):
            d = time.strftime("%Y-%m-%d", time.gmtime(n * 86400))
            days.append({"date": d, "asked": asked.get(d, 0), "answered": answered.get(d, 0)})

        trend = db.execute(
            "SELECT a.id, s.id AS subject_id, s.name, a.finished_at, a.correct_answers c, a.incorrect_answers w FROM quiz_attempts a "
            "JOIN subjects s ON s.id=a.subject_id AND s.user_id=a.user_id WHERE a.user_id=? AND a.is_active=0 AND a.correct_answers+a.incorrect_answers>0 "
            "ORDER BY a.finished_at DESC LIMIT ?", (uid, DASH_TREND)).fetchall()
        outcomes = {r[0]: r[1] for r in db.execute("SELECT status, COUNT(*) FROM doubts WHERE user_id=? GROUP BY status", (uid,)).fetchall()}
        feedback = {r[0]: r[1] for r in db.execute("SELECT feedback, COUNT(*) FROM doubts WHERE user_id=? AND feedback IS NOT NULL GROUP BY feedback", (uid,)).fetchall()}
        # streak: consecutive days (UTC) with any study activity; alive while today or yesterday has some
        since60 = (today - 60) * 86400
        days_active = {r[0] for r in db.execute("SELECT date(created_at,'unixepoch') FROM doubts WHERE user_id=? AND created_at>=?", (uid, since60))}
        days_active |= {r[0] for r in db.execute("SELECT date(aa.answered_at,'unixepoch') FROM attempt_answers aa JOIN quiz_attempts a ON a.id=aa.attempt_id WHERE a.user_id=? AND aa.chosen_index IS NOT NULL AND aa.answered_at>=?", (uid, since60))}
        days_active |= {r[0] for r in db.execute("SELECT date(last_at,'unixepoch') FROM card_reviews WHERE user_id=? AND last_at>=?", (uid, since60))}
        cursor, streak = today, 0
        if time.strftime("%Y-%m-%d", time.gmtime(cursor * 86400)) not in days_active:
            cursor -= 1
        while time.strftime("%Y-%m-%d", time.gmtime(cursor * 86400)) in days_active and streak <= 60:
            streak += 1
            cursor -= 1
        today_s = time.strftime("%Y-%m-%d", time.gmtime(today * 86400))
        today_answers = answered.get(today_s, 0) + one("SELECT COUNT(*) FROM card_reviews WHERE user_id=? AND date(last_at,'unixepoch')=?", uid, today_s)
        total_correct = sum(x["correct"] for x in per_subject)
        total_answered = sum(x["answered"] for x in per_subject)
        return {
            "totals": {"subjects": len(subjects), "materials": sum(x["materials"] for x in per_subject), "questions": sum(x["questions"] for x in per_subject),
                       "practice_questions": sum(x["practice_questions"] for x in per_subject), "quizzes": sum(x["quizzes"] for x in per_subject),
                       "answered": total_answered, "correct": total_correct},
            "subjects": per_subject,
            "activity": days,
            "quiz_trend": [{"attempt_id": r["id"], "subject_id": r["subject_id"], "subject": r["name"], "finished_at": iso(r["finished_at"]),
                            "correct": r["c"], "answered": r["c"] + r["w"]} for r in reversed(trend)],
            "topic_states": topic_counts,
            "question_outcomes": {k: outcomes.get(k, 0) for k in ("answered", "extractive", "abstained", "failed", "pending")},
            "feedback": {"helpful": feedback.get("helpful", 0), "wrong": feedback.get("wrong", 0)},
            "weak_topics": weak[:5],
            "streak": {"days": streak, "today": today_answers, "goal": 10},
        }


# ------------------------------------------------------------------------------------------- account controls

class PasswordBody(BaseModel):
    current: str = ""
    new: str = ""


class DeleteAccountBody(BaseModel):
    password: str = ""
    confirm: str = ""


def _ip(request: Request) -> str:
    """The caller's address. Behind our own Next.js proxy (loopback) it is the LAST X-Forwarded-For entry, the one the proxy itself added
    (earlier entries can be forged by the caller); anything else uses the connection's address."""
    host = request.client.host if request.client else ""
    if host in ("127.0.0.1", "::1"):
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[-1].strip()[:64]
    return host


@router.post("/account/password")
def change_password(request: Request, body: PasswordBody):
    appmod = _app()
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        try:
            auth.change_password(db, ctx.uid, ctx.user["username"], body.current, body.new, _ip(request))
        except auth.AuthError as e:
            msg = str(e)
            if msg == auth.GENERIC_FAILURE:
                return err(400, "wrong_password", "Your current password is not right.")
            return err(429 if "Too many" in msg else 400, "invalid", msg)
        keep = auth._hash(request.cookies.get(appmod.SESSION_COOKIE) or "")
        db.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (ctx.uid, keep))      # every other device is signed out
        return {"ok": True}


@router.get("/account/export")
def export_data(request: Request):
    """Everything the account holds, as one JSON file."""
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        uid = ctx.uid
        rows = lambda sql, *a: [dict(r) for r in db.execute(sql, a)]                        # noqa: E731
        subjects = []
        for s in rows("SELECT id, name, description, created_at FROM subjects WHERE user_id=? ORDER BY id", uid):
            sid = s["id"]
            docs = rows("SELECT id, title, kind, source, pages, status, created_at FROM documents WHERE subject_id=? ORDER BY id", sid)
            for d in docs:
                d["passages"] = rows("SELECT ordinal, heading_path, page_start, page_end, text FROM chunks WHERE document_id=? ORDER BY ordinal", d["id"])
            subjects.append({
                **s, "documents": docs,
                "questions_asked": rows("SELECT question, status, feedback, saved, created_at FROM doubts WHERE subject_id=? AND user_id=? ORDER BY id", sid, uid),
                "practice_questions": rows("SELECT topic_path, question, options, answer_index, explanation, quote FROM mcq_items WHERE subject_id=? ORDER BY id", sid),
                "quizzes": rows("SELECT id, mode, kind, started_at, finished_at, correct_answers, incorrect_answers FROM quiz_attempts WHERE subject_id=? AND user_id=? ORDER BY id", sid, uid),
                "notes": rows("SELECT title, body, source, created_at, updated_at FROM notes WHERE subject_id=? AND user_id=? ORDER BY id", sid, uid),
                "quiz_answers": rows("SELECT aa.attempt_id, aa.item_id, aa.chosen_index, aa.is_correct, aa.response_time, aa.answered_at FROM attempt_answers aa "
                                     "JOIN quiz_attempts qa ON qa.id=aa.attempt_id WHERE qa.subject_id=? AND qa.user_id=? AND aa.answered_at IS NOT NULL ORDER BY aa.id", sid, uid)})
        data = {"exported_at": iso(time.time()), "account": {"username": ctx.user["username"], "cloud_consent": bool(ctx.user["cloud_consent"])}, "subjects": subjects}
        return Response(json.dumps(data, indent=2, default=str), media_type="application/json",
                        headers={"Content-Disposition": 'attachment; filename="nexus-my-data.json"'})


@router.post("/account/delete", status_code=204)
def delete_account(request: Request, body: DeleteAccountBody):
    """Permanent. Needs the password and the word DELETE; removes every subject, upload, question and quiz, then the account."""
    appmod = _app()
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        if body.confirm != "DELETE":
            return err(400, "invalid", "Type DELETE to confirm.")
        try:
            auth.authenticate(db, ctx.user["username"], body.password, _ip(request))
        except auth.AuthError as e:
            return err(400, "wrong_password", "Your password is not right.") if str(e) == auth.GENERIC_FAILURE else err(429, "invalid", str(e))
        for s in db.execute("SELECT id FROM subjects WHERE user_id=?", (ctx.uid,)).fetchall():
            ingest.delete_subject(db, ctx.uid, s["id"])
        db.execute("DELETE FROM sessions WHERE user_id=?", (ctx.uid,))
        db.execute("DELETE FROM users WHERE id=?", (ctx.uid,))
    response = Response(status_code=204)
    response.delete_cookie(appmod.SESSION_COOKIE, path="/")
    return response


# ---------------------------------------------------------------------------------------------- saved answers

class SavedBody(BaseModel):
    saved: bool = True


@router.put("/subjects/{subject_id}/questions/{question_id}/saved")
def save_question(request: Request, subject_id: str, question_id: str, body: SavedBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if ctx.repo.get_doubt(ctx.uid, ctx.subject["id"], _int(question_id) or -1) is None:
            return err(404, "not_found", "Not found.")
        db.execute("UPDATE doubts SET saved=? WHERE id=? AND user_id=? AND subject_id=?", (int(body.saved), _int(question_id), ctx.uid, ctx.subject["id"]))
        return {"saved": body.saved}


@router.get("/saved")
def saved_answers(request: Request):
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        rows = db.execute(
            "SELECT d.id, d.subject_id, s.name AS subject, d.question, d.status, d.created_at FROM doubts d JOIN subjects s ON s.id=d.subject_id "
            "WHERE d.user_id=? AND s.user_id=? AND d.saved=1 ORDER BY d.created_at DESC, d.id DESC", (ctx.uid, ctx.uid)).fetchall()
        return {"saved": [{"id": r["id"], "subject_id": r["subject_id"], "subject": r["subject"], "question": r["question"], "status": r["status"],
                           "created_at": iso(r["created_at"])} for r in rows]}


# ---------------------------------------------------------------------------------------------- flashcards

class ReviewBody(BaseModel):
    grade: str


@router.get("/subjects/{subject_id}/flashcards")
def flashcards(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        d = cards.due_cards(db, ctx.uid, ctx.subject["id"])
        d["next_due"] = iso(d["next_due"])
        return d


@router.post("/subjects/{subject_id}/flashcards/{item_id}/review")
def review_flashcard(request: Request, subject_id: str, item_id: str, body: ReviewBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        nxt = cards.review(db, ctx.uid, ctx.subject["id"], _int(item_id) or -1, body.grade)
        if nxt is None:
            return err(404 if body.grade in cards.GRADES else 400, "not_found" if body.grade in cards.GRADES else "invalid", "Not found." if body.grade in cards.GRADES else "Unknown rating.")
        topic = db.execute("SELECT topic_id FROM mcq_items WHERE id=?", (_int(item_id),)).fetchone()
        if topic and topic["topic_id"]:
            _log_action(ctx, topic["topic_id"], "flashcards")
        return {"due": iso(nxt["due"]), "interval_days": round(nxt["interval_days"], 2)}


# --------------------------------------------------------------------------- search across subjects, exports

@router.get("/search")
def search_all(request: Request, q: str = ""):
    """Passages matching the words, across every subject of the signed-in user (only theirs)."""
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        q = " ".join(q.split())[:200]
        out = []
        if q:
            for s in db.execute("SELECT id, name FROM subjects WHERE user_id=? ORDER BY name LIMIT 30", (ctx.uid,)).fetchall():
                for h in retrieval.search(db, ctx.uid, s["id"], q, k=3, relevant_only=True):
                    out.append({"subject_id": s["id"], "subject": s["name"], "passage_id": h.id, "document_id": h.document_id, "document": h.doc_title,
                                "heading_path": h.heading_path, "page_start": h.page_start, "page_end": h.page_end, "text": h.text[:600], "matched": h.matched})
            out.sort(key=lambda r: -len(r["matched"]))
        return {"query": q, "terms": retrieval.terms(q), "results": out[:20]}


@router.get("/subjects/{subject_id}/mcq.csv")
def mcq_csv(request: Request, subject_id: str):
    import csv
    import io
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Topic", "Question", "A", "B", "C", "D", "Answer", "Explanation", "Source quote", "Source document"])
        for m in ctx.repo.list_mcq(ctx.uid, ctx.subject["id"]):
            opts = (m["options"] + ["", "", "", ""])[:4]
            w.writerow([m["topic_path"], m["question"], *opts, "ABCD"[m["answer_index"]], m["explanation"], m["quote"], m.get("doc_title") or ""])
        return Response(out.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="practice-questions.csv"'})


@router.post("/subjects/{subject_id}/quiz/attempts/{attempt_id}/finish")
def quiz_finish(request: Request, subject_id: str, attempt_id: str):
    """End a quiz now (for example when its time limit runs out). Unanswered questions are not counted."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        att = _own_attempt(ctx, attempt_id)
        if att is None:
            return err(404, "not_found", "Not found.")
        if att["is_active"]:
            _app().scoring.finish_attempt(db, ctx.uid, att["id"])
        return {"ok": True}


# ------------------------------------------------------------------------------------- original file (viewer)

_FILE_TYPES = {"pdf": ("application/pdf", "inline"), "txt": ("text/plain; charset=utf-8", "inline"),
               "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "attachment")}


@router.get("/subjects/{subject_id}/materials/{document_id}/file")
def material_file(request: Request, subject_id: str, document_id: str):
    """The uploaded original, for the viewer. Only its owner; a PDF or text file is shown in the page, a Word file is downloaded."""
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        doc = ctx.repo.get_document(ctx.uid, ctx.subject["id"], _int(document_id) or -1)
        if doc is None or doc["kind"] not in _FILE_TYPES and doc["kind"] != "image":
            return err(404, "not_found", "Not found.")
        path = ingest._upload_path(ctx.uid, doc["sha256"])
        if not path.exists():
            return err(404, "not_found", "The original file is not stored.")
        if doc["kind"] == "image":
            from studyhub import ocr
            data = path.read_bytes()
            media, disposition = ocr.MIME.get(ocr.image_kind(data) or "", "application/octet-stream"), "inline"
        else:
            media, disposition = _FILE_TYPES[doc["kind"]]
        name = "".join(c if c.isalnum() or c in " ._-" else "_" for c in (doc["source"] or "material"))[:120] or "material"
        headers = {"Content-Disposition": f'{disposition}; filename="{name}"'}
        if disposition == "inline":
            headers["X-Nexus-Frameable"] = "1"
        return Response(path.read_bytes(), media_type=media, headers=headers)


# ------------------------------------------------------------------------------------------------------ notes

class NoteBody(BaseModel):
    title: str = ""
    body: str = ""


class FromAnswersBody(BaseModel):
    doubt_ids: list[int]
    title: str = ""


def _note_snippet(body: str) -> str:
    """A one-line preview: skip markdown headings and bullets so the first real sentence shows."""
    lines = [re.sub(r"^\s*(?:[-*>]|\d+[.)])\s+", "", ln).strip() for ln in body.splitlines()]
    text = " ".join(ln for ln in lines if ln and not ln.lstrip().startswith("#"))
    return " ".join((text or body).split())[:160]


def _note_json(n: dict, full: bool = True) -> dict:
    out = {"id": n["id"], "title": n["title"], "source": n["source"], "doubt_id": n["doubt_id"], "topic_id": n.get("topic_id"), "created_at": iso(n["created_at"]),
           "updated_at": iso(n["updated_at"]), "snippet": _note_snippet(n["body"])}
    if full:
        out["body"] = n["body"]
    return out


def _clean_note(body: NoteBody):
    title, text = " ".join(body.title.split())[:200], body.body[:50000]
    if not title and not text.strip():
        return None, None
    return title or " ".join(text.split())[:60] or "Untitled", text


def _answer_markdown(d: dict) -> str:
    """A chat answer as note text: the question, each statement with its [n] markers, then the exact quotes and where they are from."""
    order: list[tuple] = []

    def num(x):
        key = (x["chunk_id"], x["quote"])
        if key not in order:
            order.append(key)
        return order.index(key) + 1
    lines = [f"## {d['question']}", ""]
    if d["status"] == "answered":
        for c in d["claims"]:
            lines += [(c["text"] + " " + "".join(f"[{num(x)}]" for x in c["citations"])).strip(), ""]
        srcs = {}
        for c in d["claims"]:
            for x in c["citations"]:
                srcs[(x["chunk_id"], x["quote"])] = x
        if srcs:
            lines += ["**Sources**", ""]
            for i, key in enumerate(order, start=1):
                x = srcs[key]
                where = x["doc_title"] + (f" · section: {x['heading_path']}" if x["heading_path"] else "") + (f" · page {x['page_start']}" if x["page_start"] is not None else "")
                lines += [f"[{i}] > {x['quote']}", f"({where})", ""]
    else:
        lines += [d["reason"] or "Not answered from the materials.", ""]
    return "\n".join(lines).rstrip() + "\n"


@router.get("/subjects/{subject_id}/notes")
def list_notes(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        return bad or {"notes": [_note_json(n, full=False) for n in ctx.repo.list_notes(ctx.uid, ctx.subject["id"])]}


@router.get("/subjects/{subject_id}/notes/{note_id}")
def get_note(request: Request, subject_id: str, note_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        n = ctx.repo.get_note(ctx.uid, ctx.subject["id"], _int(note_id) or -1)
        return _note_json(n) if n else err(404, "not_found", "Not found.")


@router.post("/subjects/{subject_id}/notes", status_code=201)
def create_note(request: Request, subject_id: str, body: NoteBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        title, text = _clean_note(body)
        if title is None:
            return err(400, "invalid", "Write a title or some text first.")
        nid = ctx.repo.add_note(ctx.uid, ctx.subject["id"], title, text)
        return JSONResponse(_note_json(ctx.repo.get_note(ctx.uid, ctx.subject["id"], nid)), status_code=201)


@router.post("/subjects/{subject_id}/notes/from-answers", status_code=201)
def notes_from_answers(request: Request, subject_id: str, body: FromAnswersBody):
    """Turn chat answers into one note. The text is built here from the stored answers, never taken from the browser."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        ids = list(dict.fromkeys(body.doubt_ids))[:20]
        docs = [ctx.repo.get_doubt(ctx.uid, ctx.subject["id"], i) for i in ids]
        if not ids or any(d is None for d in docs):
            return err(404, "not_found", "Not found.")
        docs = [d for d in docs if d["status"] in ("answered", "extractive")]
        if not docs:
            return err(400, "invalid", "Only answered questions can be saved as notes.")
        title = " ".join(body.title.split())[:200] or (docs[0]["question"][:120] if len(docs) == 1 else f"Notes from chat, {time.strftime('%d %b %Y')}")
        text = "\n".join(_answer_markdown(d) for d in docs)
        nid = ctx.repo.add_note(ctx.uid, ctx.subject["id"], title, text, source="chat", doubt_id=docs[0]["id"] if len(docs) == 1 else None)
        return JSONResponse(_note_json(ctx.repo.get_note(ctx.uid, ctx.subject["id"], nid)), status_code=201)


@router.put("/subjects/{subject_id}/notes/{note_id}")
def update_note(request: Request, subject_id: str, note_id: str, body: NoteBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        title, text = _clean_note(body)
        if title is None:
            return err(400, "invalid", "A note cannot be empty.")
        if not ctx.repo.update_note(ctx.uid, ctx.subject["id"], _int(note_id) or -1, title, text):
            return err(404, "not_found", "Not found.")
        return _note_json(ctx.repo.get_note(ctx.uid, ctx.subject["id"], _int(note_id)))


@router.delete("/subjects/{subject_id}/notes/{note_id}", status_code=204)
def delete_note(request: Request, subject_id: str, note_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if not ctx.repo.delete_note(ctx.uid, ctx.subject["id"], _int(note_id) or -1):
            return err(404, "not_found", "Not found.")
        return Response(status_code=204)


# -------------------------------------------------------------------------------- password reset by e-mail code

class ForgotBody(BaseModel):
    email: str = Field(max_length=254)


class ResetBody(BaseModel):
    email: str = Field(max_length=254)
    code: str = Field(max_length=12)
    new_password: str = Field(max_length=200)


class EmailBody(BaseModel):
    email: str = Field(max_length=254)


class CodeBody(BaseModel):
    code: str = Field(max_length=12)


class WeeklyBody(BaseModel):
    enabled: bool


def _limited(r: "otp.RateLimited"):
    mins = max(1, -(-r.retry_after // 60))
    wait = f"{r.retry_after} seconds" if r.retry_after < 60 else f"{mins} minute{'s' if mins != 1 else ''}"
    return JSONResponse({"error": {"code": "rate_limited", "message": f"Too many attempts. Please wait {wait} and try again.", "retry_after": r.retry_after}},
                        status_code=429, headers={"Retry-After": str(r.retry_after)})


def _mask(ip: str) -> str:
    if ":" in ip:
        return ":".join(ip.split(":")[:3]) + ":…"
    parts = ip.split(".")
    return ".".join(parts[:2]) + ".x.x" if len(parts) == 4 else "unknown"


def _stamp() -> str:
    return time.strftime("%d %b %Y, %H:%M UTC", time.gmtime())


def _mail_code(purpose: str, email: str, code: str, ip: str) -> None:
    subject, text, html = mail_templates.otp_email(purpose, code, int(otp.TTL // 60), _stamp(), _mask(ip))
    mailer.send(email, subject, text, html)


def _mail_changed(email: str, ip: str) -> None:
    subject, text, html = mail_templates.password_changed_email(_stamp(), _mask(ip))
    mailer.send(email, subject, text, html)


@router.post("/auth/password/forgot", status_code=202)
def forgot_password(request: Request, body: ForgotBody, background: BackgroundTasks):
    """Send a one-time code to a verified address. The answer is the same whether or not the address has an account."""
    if not _pre_ok(request):
        return err(403, "csrf", "The request was refused. Reload the page and try again.")
    email, ip = body.email.strip().lower(), _ip(request)
    if not mailer.valid_address(email):
        return err(400, "invalid", "Enter a valid email address.")
    with _db() as db:
        try:
            otp.throttle_request(db, email, ip)
        except otp.RateLimited as r:
            return _limited(r)
        row = db.execute("SELECT id FROM users WHERE lower(email)=? AND email_verified=1", (email,)).fetchone()
        if row is not None:
            background.add_task(_mail_code, "reset", email, otp.issue(db, "reset", email, row["id"], ip), ip)
    return {"ok": True, "message": "If that address belongs to an account, a code is on its way. It expires in 10 minutes."}


@router.post("/auth/password/reset")
def reset_password(request: Request, body: ResetBody, background: BackgroundTasks):
    if not _pre_ok(request):
        return err(403, "csrf", "The request was refused. Reload the page and try again.")
    email, ip = body.email.strip().lower(), _ip(request)
    try:
        auth.check_password(body.new_password, "")                 # length rules only, so a weak password never reveals whether the account exists
    except auth.AuthError as e:
        return err(400, "invalid", str(e))
    with _db() as db:
        try:
            row = otp.check(db, "reset", email, body.code, ip)
        except otp.RateLimited as r:
            return _limited(r)
        if row is None:
            return err(400, "invalid_code", "That code is not right or has expired. Request a new one.")
        user = db.execute("SELECT id, username FROM users WHERE id=?", (row["user_id"],)).fetchone()
        try:
            auth.set_password(db, user["id"], user["username"], body.new_password)
        except auth.AuthError as e:
            return err(400, "invalid", str(e))
        db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))      # every device is signed out
        db.execute("DELETE FROM login_attempts WHERE username=?", (user["username"][:64],))
        background.add_task(_mail_changed, email, ip)
    return {"ok": True}


# ------------------------------------------------------------------------------------ e-mail address and weekly summary

@router.put("/account/email")
def set_email(request: Request, body: EmailBody, background: BackgroundTasks):
    """Start verifying an address: a code is sent to it. Nothing changes until the code is entered."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        email, ip = body.email.strip().lower(), _ip(request)
        if not mailer.valid_address(email):
            return err(400, "invalid", "Enter a valid email address.")
        try:
            otp.throttle_request(db, email, ip)
        except otp.RateLimited as r:
            return _limited(r)
        background.add_task(_mail_code, "verify", email, otp.issue(db, "verify", email, ctx.uid, ip), ip)
        return {"ok": True, "pending": email}


@router.post("/account/email/verify")
def verify_email(request: Request, body: CodeBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        pend = db.execute("SELECT email FROM email_otps WHERE user_id=? AND purpose='verify' AND consumed_at IS NULL AND expires_at>? ORDER BY id DESC LIMIT 1", (ctx.uid, time.time())).fetchone()
        if pend is None:
            return err(400, "invalid_code", "That code is not right or has expired. Request a new one.")
        try:
            row = otp.check(db, "verify", pend["email"], body.code, _ip(request), user_id=ctx.uid)
        except otp.RateLimited as r:
            return _limited(r)
        if row is None:
            return err(400, "invalid_code", "That code is not right or has expired. Request a new one.")
        try:
            db.execute("UPDATE users SET email=?, email_verified=1 WHERE id=?", (pend["email"], ctx.uid))
        except Exception:
            return err(409, "email_in_use", "That address is already linked to another account.")
        return {"ok": True, "email": pend["email"]}


@router.delete("/account/email", status_code=204)
def remove_email(request: Request):
    """The email address is how the account is logged into, so it cannot be removed; it can be changed. This turns the weekly summary off."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        return err(400, "invalid", "Your email address is how you log in, so it cannot be removed. Change it to another address instead.")


@router.put("/account/weekly")
def set_weekly(request: Request, body: WeeklyBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        ok = db.execute("UPDATE users SET weekly_email=? WHERE id=? AND email_verified=1", (int(body.enabled), ctx.uid)).rowcount
        return {"weekly": body.enabled} if ok else err(400, "no_email", "Verify an email address first.")


@router.post("/account/digest/send-now")
def send_digest_now(request: Request):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        u = db.execute("SELECT id, username, email FROM users WHERE id=? AND email_verified=1", (ctx.uid,)).fetchone()
        if u is None:
            return err(400, "no_email", "Verify an email address first.")
        now = time.time()
        recent = otp._events(db, "digest_user", str(ctx.uid), 3600, now)
        if len(recent) >= 3:
            return _limited(otp.RateLimited(recent[-3] + 3600 - now))
        otp._note(db, "digest_user", str(ctx.uid), now)
        status = digest.send_to(db, dict(u), now)
        if status in ("sent", "outbox"):
            return {"ok": True, "status": status}
        return err(503 if status == "unconfigured" else 502, "mail_failed", "The email could not be sent. Check the email settings on the server.")


# ------------------------------------------------------------------------------------- skill gaps and the study roadmap

class PlanProfileBody(BaseModel):
    goal: str = Field(default="", max_length=300)
    hours_per_week: float = Field(default=5.0, ge=1, le=40)
    target_date: str | None = None
    exam_date: str | None = None                             # None = leave as it is, "" = clear


def _roadmap_json(ctx) -> dict:
    db, sid = ctx.db, ctx.subject["id"]
    profile = roadmapmod.get_profile(db, ctx.uid, sid)
    info = roadmapmod.skill_gaps(db, ctx.uid, sid, ctx.subject.get("level"))
    plan = roadmapmod.build(info, sid, profile["hours_per_week"], profile["target_date"])
    h = roadmapmod.plan_hash(info, profile)
    status = profile["coach_status"]
    if status == "pending" and (profile["coach_at"] or 0) < time.time() - 3600:
        status = "failed"                                          # the worker went away before it finished
    return {"subject": ctx.subject["name"], "level": ctx.subject.get("level"), "target": info["target"], "readiness": info["readiness"], "counts": info["counts"],
            "source_totals": info["source_totals"], "source_labels": roadmapmod.SOURCE_LABELS, "gaps": info["gaps"], "roadmap": plan,
            "profile": {"goal": profile["goal"], "hours_per_week": profile["hours_per_week"], "target_date": profile["target_date"], "exam_date": profile["exam_date"],
                        "target_date_source": profile["target_date_source"]},
            "coach": {"status": status, "text": profile["coach_text"] if profile["coach_text"] else roadmapmod.rule_coach(info, plan),
                      "from_model": bool(profile["coach_text"]) and not (profile["coach_model"] or "").startswith("rules"), "model": profile["coach_model"], "stale": bool(profile["coach_text"]) and profile["coach_hash"] != h,
                      "at": iso(profile["coach_at"])}}


@router.get("/subjects/{subject_id}/roadmap")
def get_roadmap(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        return bad or _roadmap_json(ctx)


@router.put("/subjects/{subject_id}/roadmap/profile")
def set_roadmap_profile(request: Request, subject_id: str, body: PlanProfileBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        date = (body.target_date or "").strip() or None
        if date:
            try:
                ok = time.strptime(date, "%Y-%m-%d") and time.mktime(time.strptime(date, "%Y-%m-%d")) > time.time() - 86400
            except ValueError:
                ok = False
            if not ok:
                return err(400, "invalid", "Choose a date from today on.")
        if body.exam_date is not None:
            exam = body.exam_date.strip() or None
            if exam:
                try:
                    ok = time.mktime(time.strptime(exam, "%Y-%m-%d")) > time.time() - 86400
                except ValueError:
                    ok = False
                if not ok:
                    return err(400, "invalid", "Choose an exam date from today on.")
            db.execute("UPDATE subjects SET exam_date=? WHERE id=? AND user_id=?", (exam, ctx.subject["id"], ctx.uid))
        roadmapmod.save_profile(db, ctx.uid, ctx.subject["id"], " ".join(body.goal.split()), float(body.hours_per_week), date)
        return _roadmap_json(ctx)


@router.post("/subjects/{subject_id}/roadmap/coach", status_code=202)
def ask_coach(request: Request, subject_id: str):
    """Have the coach paragraph written (in the background). It sends topic names and scores only, never passages."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        now = time.time()
        recent = otp._events(db, "coach_user", str(ctx.uid), 3600, now)
        if len(recent) >= 6:
            return _limited(otp.RateLimited(recent[-6] + 3600 - now))
        otp._note(db, "coach_user", str(ctx.uid), now)
        p = roadmapmod.get_profile(db, ctx.uid, ctx.subject["id"])
        roadmapmod.save_profile(db, ctx.uid, ctx.subject["id"], p["goal"], p["hours_per_week"], p["target_date"] if p["target_date_source"] == "plan" else None)
        db.execute("UPDATE study_plans SET coach_status='pending', coach_at=? WHERE subject_id=? AND user_id=?", (now, ctx.subject["id"], ctx.uid))
    _app()._submit_task(_app()._process_coach, ctx.uid, ctx.subject["id"])
    return JSONResponse({"status": "pending"}, status_code=202)


# --------------------------------------------------------------------------------------------- outlook: what-if, risk, debt, self-check

class WhatIfBody(BaseModel):
    hours_per_week: float = Field(default=5.0, ge=1, le=40)
    weeks: int = Field(default=4, ge=1, le=foresight.MAX_WEEKS)
    focus: list[int] = Field(default_factory=list, max_length=10)


class SelfCheckBody(BaseModel):
    ratings: dict[int, int] = Field(default_factory=dict, max_length=200)


def _gaps(ctx):
    profile = roadmapmod.get_profile(ctx.db, ctx.uid, ctx.subject["id"])
    info = roadmapmod.skill_gaps(ctx.db, ctx.uid, ctx.subject["id"], ctx.subject.get("level"))
    plan = roadmapmod.build(info, ctx.subject["id"], profile["hours_per_week"], profile["target_date"])
    return profile, info, plan


def _base_weeks(s: dict) -> int:
    return s["weeks_available"] or min(max(1, s["weeks"]), foresight.MAX_WEEKS)


@router.get("/subjects/{subject_id}/outlook")
def outlook(request: Request, subject_id: str):
    """Risk score, learning debt and the numbers the what-if page starts from."""
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        profile, info, plan = _gaps(ctx)
        s = plan["summary"]
        return {"subject": ctx.subject["name"], "target": info["target"], "readiness": info["readiness"], "risk": foresight.risk(info, s), "debt": foresight.debt(info),
                "profile": {"hours_per_week": profile["hours_per_week"], "target_date": profile["target_date"], "weeks": _base_weeks(s)},
                "topics": [{"topic_id": g["topic_id"], "name": g["name"], "status": g["status"]} for g in info["gaps"]]}


@router.post("/subjects/{subject_id}/whatif")
def what_if(request: Request, subject_id: str, body: WhatIfBody):
    """Compare a different plan (hours, weeks, topics first) with the current one. Nothing is saved."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        profile, info, plan = _gaps(ctx)
        return foresight.what_if(info, profile["hours_per_week"], _base_weeks(plan["summary"]), body.hours_per_week, body.weeks, body.focus)


@router.get("/subjects/{subject_id}/self-check")
def get_self_check(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        info = roadmapmod.skill_gaps(db, ctx.uid, ctx.subject["id"], ctx.subject.get("level"))
        return foresight.self_check(info, foresight.get_ratings(db, ctx.uid, ctx.subject["id"]))


@router.put("/subjects/{subject_id}/self-check")
def put_self_check(request: Request, subject_id: str, body: SelfCheckBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        foresight.save_ratings(db, ctx.uid, ctx.subject["id"], body.ratings)
        info = roadmapmod.skill_gaps(db, ctx.uid, ctx.subject["id"], ctx.subject.get("level"))
        return foresight.self_check(info, foresight.get_ratings(db, ctx.uid, ctx.subject["id"]))


# ------------------------------------------------------------------------------------------------------------- career goals

class CareerBody(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    text: str = Field(min_length=40, max_length=career.MAX_TEXT * 2)


def _career_json(db, uid: int, goal: dict) -> dict:
    skills = json.loads(goal["skills_json"] or "[]")
    status = goal["status"]
    if status == "pending" and goal["updated_at"] < time.time() - 1800:
        status = "failed"                                                # the worker went away before it finished
    out = {"id": goal["id"], "title": goal["title"], "status": status, "model": goal["model"], "from_model": bool(goal["model"]) and not (goal["model"] or "").startswith("rules"),
           "created_at": iso(goal["created_at"]), "skills": [], "score": career.score([]), "next_steps": [], "history": []}
    if status == "done":
        assessed = career.assess(db, uid, skills)
        sc = career.score(assessed)
        career.snapshot(db, goal["id"], sc["readiness"], sc["verified"], sc["total"])
        out.update(skills=assessed, score=sc, next_steps=career.next_steps(assessed), history=[{**h, "at": iso(h["at"])} for h in career.history(db, goal["id"])])
    return out


@router.get("/career")
def career_list(request: Request):
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        return {"goals": [{"id": g["id"], "title": g["title"], "status": g["status"], "skills": len(json.loads(g["skills_json"] or "[]")), "created_at": iso(g["created_at"])}
                          for g in career.listing(db, ctx.uid)]}


@router.post("/career", status_code=202)
def career_create(request: Request, body: CareerBody):
    """Save a job description and have its skills read out in the background."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        now = time.time()
        recent = otp._events(db, "career_user", str(ctx.uid), 3600, now)
        if len(recent) >= 8:
            return _limited(otp.RateLimited(recent[-8] + 3600 - now))
        if len(career.listing(db, ctx.uid)) >= 20:
            return err(400, "limit", "You can keep up to 20 career goals. Delete one to add another.")
        text = career.clean_text(body.text)
        if len(text) < 40:
            return err(400, "invalid", "Paste the job description text (at least a few lines).")
        otp._note(db, "career_user", str(ctx.uid), now)
        gid = career.create(db, ctx.uid, " ".join(body.title.split()), text)
    _app()._submit_task(_app()._process_career, ctx.uid, gid)
    return JSONResponse({"id": gid, "status": "pending"}, status_code=202)


@router.get("/career/{goal_id}")
def career_get(request: Request, goal_id: str):
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        goal = career.get(db, ctx.uid, _int(goal_id) or -1)
        return _career_json(db, ctx.uid, goal) if goal else err(404, "not_found", "Not found.")


@router.delete("/career/{goal_id}")
def career_delete(request: Request, goal_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        n = db.execute("DELETE FROM career_goals WHERE id=? AND user_id=?", (_int(goal_id) or -1, ctx.uid)).rowcount
        return {"ok": True} if n else err(404, "not_found", "Not found.")


# ---------------------------------------------------------------------------------- academic setup, document role, the twin, worked examples

class AcademicBody(BaseModel):
    department: str = Field(default="", max_length=80)
    semester: int | None = Field(default=None, ge=1, le=12)


@router.put("/account/academic")
def set_academic(request: Request, body: AcademicBody):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        dept = " ".join(body.department.split())
        db.execute("UPDATE users SET department=?, semester=? WHERE id=?", (dept, body.semester, ctx.uid))
        return {"department": dept, "semester": body.semester}


@router.patch("/subjects/{subject_id}/materials/{doc_id}/role")
def set_doc_role(request: Request, subject_id: str, doc_id: str, body: RoleBody):
    """Say what a document is for: notes to study from, a syllabus, or past papers (used to see what is asked most). Changing it does not re-read the file."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        if body.role not in ingest.ROLES:
            return err(400, "invalid", "Choose notes, syllabus or past papers.")
        doc = ctx.repo.get_document(ctx.uid, ctx.subject["id"], _int(doc_id) or -1)
        if doc is None:
            return err(404, "not_found", "Not found.")
        if body.role == "pyq" and doc["role"] != "pyq":
            return err(400, "invalid", "Choose past papers when you add the file, so its headings are not turned into topics.")
        db.execute("UPDATE documents SET role=? WHERE id=? AND subject_id=?", (body.role, doc["id"], ctx.subject["id"]))
        return _doc_json({**doc, "role": body.role})


@router.get("/subjects/{subject_id}/twin")
def learner_twin(request: Request, subject_id: str):
    """One picture of the learner for this subject, and the planner's next steps."""
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        profile, info, plan = _gaps(ctx)
        u = db.execute("SELECT department, semester FROM users WHERE id=?", (ctx.uid,)).fetchone()
        return twinmod.build(db, ctx.uid, ctx.subject, profile, dict(u), plan, info)


class ExampleBody(BaseModel):
    topic_id: int


def _example_json(row: dict) -> dict:
    payload = json.loads(row["payload_json"] or "{}")
    status = row["status"]
    if status == "pending" and row["updated_at"] < time.time() - 1800:
        status = "failed"
    return {"id": row["id"], "topic_id": row["topic_id"], "topic": row["topic"], "status": status, "model": row["model"], "level": row["level"], "example": payload or None,
            "created_at": iso(row["created_at"])}


@router.post("/subjects/{subject_id}/examples", status_code=202)
def make_example(request: Request, subject_id: str, body: ExampleBody):
    """Write a worked example for one topic, from that topic's own passages (in the background)."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        sid = ctx.subject["id"]
        if not tutor.passages(db, sid, body.topic_id, 1):
            return err(404, "not_found", "Not found.")
        now = time.time()
        recent = otp._events(db, "example_user", str(ctx.uid), 3600, now)
        if len(recent) >= 10:
            return _limited(otp.RateLimited(recent[-10] + 3600 - now))
        otp._note(db, "example_user", str(ctx.uid), now)
        e = insights.topic_confidence(db, ctx.uid, sid)["topics"].get(body.topic_id)
        iid = tutor.start(db, ctx.uid, sid, body.topic_id, "worked_example", e["confidence"] if e else None, e["answered"] if e else 0,
                          status="pending", level=ctx.subject.get("level"), dedupe=False)
    _app()._submit_task(_app()._process_example, ctx.uid, sid, iid)
    return JSONResponse({"id": iid, "status": "pending"}, status_code=202)


@router.get("/subjects/{subject_id}/examples")
def list_examples(request: Request, subject_id: str, topic_id: int | None = None):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        sql = ("SELECT i.*, t.name AS topic FROM interventions i JOIN topics t ON t.id=i.topic_id WHERE i.user_id=? AND i.subject_id=? AND i.kind='worked_example'"
               + (" AND i.topic_id=?" if topic_id is not None else "") + " ORDER BY i.created_at DESC, i.id DESC LIMIT 20")
        args = [ctx.uid, ctx.subject["id"]] + ([topic_id] if topic_id is not None else [])
        return {"examples": [_example_json(dict(r)) for r in db.execute(sql, args)]}


# ------------------------------------------------------------------------------------------------ profile and running jobs

class ProfileBody(BaseModel):
    username: str


@router.put("/account/profile")
def set_profile(request: Request, body: ProfileBody):
    """Change the name shown in the top bar."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        name = auth.normalise_username(body.username)
        try:
            auth.check_username(name)
        except auth.AuthError as e:
            return err(400, "invalid", str(e))
        try:
            db.execute("UPDATE users SET username=? WHERE id=?", (name, ctx.uid))
        except Exception:
            return err(409, "username_taken", "That name is already taken.")
        return {"username": name}


@router.get("/jobs/active")
def active_jobs(request: Request):
    """Question-writing jobs still running, across all subjects, so the app can tell the student when one finishes wherever they are."""
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        ctx.repo.expire_pending_mcq_jobs(3600)
        rows = db.execute("SELECT j.id, j.subject_id, s.name AS subject, j.requested AS count, j.created_at FROM mcq_jobs j JOIN subjects s ON s.id=j.subject_id "
                          "WHERE j.user_id=? AND s.user_id=? AND j.status='pending' ORDER BY j.id", (ctx.uid, ctx.uid)).fetchall()
        return {"jobs": [{"id": r["id"], "subject_id": r["subject_id"], "subject": r["subject"], "count": r["count"], "created_at": iso(r["created_at"])} for r in rows]}
