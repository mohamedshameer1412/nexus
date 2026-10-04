"""Faculty and contest endpoints (/api/v1/faculty/..., /api/v1/contests, .../answers/<id>/contest).

Faculty review AI-drafted questions before officers see them, resolve contested scores and read the NSSTA insights. Officers
contest a marked answer and follow their contests. The rules live in studyhub.faculty; this file only checks roles and input.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.http import _db, _int, api_view, body as parse_body, err, guard, iso, query
from studyhub import faculty


def _iso_times(d: dict, *keys: str) -> dict:
    return {**d, **{k: iso(d.get(k)) for k in keys}}


# ------------------------------------------------------------------------------------------------ review queue

class DecisionBody(BaseModel):
    note: str = Field(default="", max_length=500)


class EditBody(BaseModel):
    question: str = Field(max_length=300)
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    explanation: str = Field(default="", max_length=1000)
    note: str = Field(default="", max_length=500)


@api_view(status=200)
def review_queue(request):
    status = query(request, "status", "pending")
    if status not in faculty.REVIEW_STATES:
        return err(400, "invalid", "The status must be pending, approved or rejected.")
    with _db() as db:
        ctx, bad = guard(request, db, role="faculty")
        if bad:
            return bad
        out = faculty.review_queue(db, status)
        out["items"] = [_iso_times(i, "created_at", "reviewed_at") for i in out["items"]]
        return out


def _decide(decision: str):
    @api_view(status=200)
    def view(request, item_id):
        b = parse_body(request, DecisionBody)
        if decision == "rejected" and len(b.note.strip()) < 5:
            return err(400, "invalid", "Say why the question is rejected (at least 5 characters).")
        with _db() as db:
            ctx, bad = guard(request, db, mutate=True, role="faculty")
            if bad:
                return bad
            item = faculty.decide(db, ctx.uid, _int(item_id) or -1, decision, b.note)
            return _iso_times(item, "created_at", "reviewed_at") if item else err(404, "not_found", "Not found.")
    return view


approve = _decide("approved")
reject = _decide("rejected")


@api_view(status=200)
def edit_item(request, item_id):
    b = parse_body(request, EditBody)
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, role="faculty")
        if bad:
            return bad
        out = faculty.edit(db, ctx.uid, _int(item_id) or -1, question=b.question, options=b.options, answer_index=b.answer_index,
                           explanation=b.explanation, note=b.note)
        if out is None:
            return err(404, "not_found", "Not found.")
        if isinstance(out, str):
            return err(400, "invalid", out)
        return _iso_times(out, "created_at", "reviewed_at")


# ------------------------------------------------------------------------------------------------ contests

class ContestBody(BaseModel):
    reason: str = Field(max_length=1000)


class ResolveBody(BaseModel):
    decision: str
    resolution: str = Field(max_length=1000)


def _contest(c: dict) -> dict:
    return _iso_times(c, "created_at", "resolved_at")


@api_view(status=201)
def contest_answer(request, subject_id, attempt_id, answer_id):
    """An officer contests one answer of their finished quiz that was marked wrong."""
    b = parse_body(request, ContestBody)
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        out = faculty.open_contest(db, ctx.uid, ctx.subject["id"], _int(attempt_id) or -1, _int(answer_id) or -1, b.reason)
        if out is None:
            return err(404, "not_found", "Not found.")
        if isinstance(out, str):
            return err(409 if "already" in out else 400, "invalid", out)
        return _contest(out)


@api_view(status=200)
def my_contests(request):
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        return {"contests": [_contest(c) for c in faculty.list_contests(db, user_id=ctx.uid)]}


@api_view(status=200)
def contest_queue(request):
    status = query(request, "status", "open")
    if status not in ("open", "upheld", "rejected"):
        return err(400, "invalid", "The status must be open, upheld or rejected.")
    with _db() as db:
        ctx, bad = guard(request, db, role="faculty")
        if bad:
            return bad
        return {"contests": [_contest(c) for c in faculty.list_contests(db, status=status)]}


@api_view(status=200)
def resolve_contest(request, contest_id):
    b = parse_body(request, ResolveBody)
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, role="faculty")
        if bad:
            return bad
        out = faculty.resolve(db, ctx.uid, _int(contest_id) or -1, b.decision, b.resolution)
        if out is None:
            return err(404, "not_found", "Not found.")
        if isinstance(out, str):
            return err(409 if "already" in out else 400, "invalid", out)
        return _contest(out)


# ------------------------------------------------------------------------------------------------ insights

@api_view(status=200)
def insights(request):
    with _db() as db:
        ctx, bad = guard(request, db, role="faculty")
        return bad or faculty.insights(db)
