"""The API's HTTP conventions, on Django.

  * Success: JSON. Failure: {"error": {"code", "message"}} with the right status. Unknown/foreign resources are 404, never 403.
  * Signed-in requests are identified by the HttpOnly `sh_session` cookie. Every mutating request sends the session's CSRF token in
    the `X-CSRF-Token` header (GET /session returns it). Login and register use the pre-session (double-submit) token instead.
  * Views are plain Django functions: `api_view` turns a returned dict into JSON and runs background tasks; `methods` routes one URL
    to one view per HTTP method; `body`/`query` parse and validate input (bad input is a 422, like everywhere else).
"""
from __future__ import annotations

import json
import secrets
import threading
import time
import types
import typing
from contextlib import contextmanager
from functools import wraps

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pydantic import BaseModel, ValidationError

from studyhub import auth, settings
from studyhub import db as studydb
from studyhub.repo import Repo

SESSION_COOKIE, PRE_COOKIE = "sh_session", "sh_pre"


def err(status: int, code: str, message: str, headers: dict | None = None) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status, headers=headers)


def iso(ts) -> str | None:
    return None if ts is None else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _int(text) -> int | None:
    text = str(text)
    return int(text) if text.isdigit() and len(text) < 12 else None


@contextmanager
def _db():
    """One engine connection per request, in the thread that uses it (sqlite3 connections are thread-bound)."""
    store = studydb.open_db()
    try:
        yield store.db
    finally:
        store.close()


# ------------------------------------------------------------------------------------------------ sessions

def signed_in(request: HttpRequest, db):
    """(user, session) or None."""
    session = auth.get_session(db, request.COOKIES.get(SESSION_COOKIE))
    if session is None:
        return None
    user = Repo(db).get_user(session.user_id)
    if user:
        request.nexus_user_id = user["id"]          # read by the audit log
    return (user, session) if user else None


def set_session_cookie(response: HttpResponse, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, max_age=settings.session_days() * 86400, httponly=True,
                        samesite="Lax", secure=settings.cookie_secure(), path="/")


def pre_token(request: HttpRequest) -> tuple[str, bool]:
    existing = request.COOKIES.get(PRE_COOKIE)
    if existing and 20 <= len(existing) <= 100:
        return existing, False
    return secrets.token_urlsafe(24), True


def with_pre_cookie(response: HttpResponse, token: str, is_new: bool) -> HttpResponse:
    if is_new:
        response.set_cookie(PRE_COOKIE, token, httponly=True, samesite="Lax", secure=settings.cookie_secure(), path="/")
    return response


def pre_ok(request: HttpRequest) -> bool:
    return auth.same_token(request.headers.get("x-csrf-token"), request.COOKIES.get(PRE_COOKIE))


def client_ip(request: HttpRequest) -> str:
    """The caller's address. Behind our own Next.js proxy (loopback) it is the LAST X-Forwarded-For entry, the one the proxy itself
    added (earlier entries can be forged by the caller); anything else uses the connection's address."""
    host = request.META.get("REMOTE_ADDR", "") or ""
    if host in ("127.0.0.1", "::1"):
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[-1].strip()[:64]
    return host


class Ctx:
    def __init__(self, db, user, session, subject=None):
        self.db, self.user, self.session, self.subject, self.repo = db, user, session, subject, Repo(db)

    @property
    def uid(self) -> int:
        return self.user["id"]


def guard(request: HttpRequest, db, *, mutate: bool = False, subject_id: str | None = None):
    """(Ctx, None) or (None, error response). Checks sign-in, CSRF (for mutations) and subject ownership."""
    si = signed_in(request, db)
    if si is None:
        return None, err(401, "unauthenticated", "Please sign in.")
    user, session = si
    if mutate and not auth.same_token(request.headers.get("x-csrf-token"), session.csrf):
        return None, err(403, "csrf", "The request was refused. Reload the page and try again.")
    subject = None
    if subject_id is not None:
        subject = Repo(db).get_subject(user["id"], _int(subject_id) or -1)
        if subject is None:
            return None, err(404, "not_found", "Not found.")
    return Ctx(db, user, session, subject), None


# ------------------------------------------------------------------------------------------------ input

class Invalid(Exception):
    """Unparseable or invalid input: answered with a 422 by api_view."""


def body(request: HttpRequest, model: type[BaseModel]) -> BaseModel:
    """The JSON body validated against a pydantic model. An empty body is {} (every field then takes its default)."""
    raw = request.body or b"{}"
    try:
        data = json.loads(raw)
        return model.model_validate(data)
    except (ValueError, ValidationError) as e:
        raise Invalid(str(e)) from e


def _coerce(value: str, annotation):
    """Convert a query/path string to the annotated type (str, int, float, bool, or Optional of one of those)."""
    args = typing.get_args(annotation)
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        inner = [a for a in args if a is not type(None)]
        annotation = inner[0] if inner else str
    if annotation is bool:
        if value.lower() in ("1", "true", "yes", "on"):
            return True
        if value.lower() in ("0", "false", "no", "off"):
            return False
        raise Invalid(f"{value!r} is not a boolean")
    if annotation in (int, float):
        try:
            return annotation(value)
        except ValueError as e:
            raise Invalid(f"{value!r} is not a number") from e
    return value


def query(request: HttpRequest, name: str, default=None, annotation=str):
    """A query-string parameter converted to `annotation`; `default` when absent."""
    if name not in request.GET:
        return default
    return _coerce(request.GET[name], annotation)


def path_param(value: str, annotation=str):
    return _coerce(value, annotation)


# ------------------------------------------------------------------------------------------------ background work

class Background:
    """Work to do once the response is ready (e-mails). Inline under tests/scripts, otherwise on a short-lived thread."""

    def __init__(self):
        self.tasks: list[tuple] = []

    def add_task(self, fn, *args, **kwargs) -> None:
        self.tasks.append((fn, args, kwargs))

    def run(self) -> None:
        for fn, args, kwargs in self.tasks:
            if settings.qa_inline():
                fn(*args, **kwargs)
            else:
                threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()


# ------------------------------------------------------------------------------------------------ views

def api_view(status: int = 200, background: bool = False):
    """Decorate an API view: a returned dict/list becomes JSON with `status`; bad input becomes a 422.

    With background=True the view receives a Background as the keyword argument `background`, run after the view returns."""
    def deco(fn):
        @wraps(fn)
        def view(request, *args, **kwargs):
            tasks = Background() if background else None
            if tasks is not None:
                kwargs["background"] = tasks
            try:
                out = fn(request, *args, **kwargs)
            except Invalid:
                return err(422, "validation", "The request was not understood.")
            if tasks is not None:
                tasks.run()
            if isinstance(out, HttpResponse):
                return out
            return JsonResponse(out, status=status, safe=False)
        return view
    return deco


def methods(**handlers):
    """One URL, one view per HTTP method (GET=..., POST=...). Anything else is a 405 in the API's error format."""
    @csrf_exempt                                  # the API checks X-CSRF-Token itself (see guard / pre_ok)
    def dispatch(request, *args, **kwargs):
        handler = handlers.get(request.method)
        if handler is None:
            return err(405, "method_not_allowed", "Method not allowed.", headers={"Allow": ", ".join(handlers)})
        return handler(request, *args, **kwargs)
    return dispatch
