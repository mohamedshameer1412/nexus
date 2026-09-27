"""Nexus API additions (/api/v1): analytics, data tables with export, PDF/XLSX reports, the agent console and system status.

Same conventions as api.py: signed-in only, everything scoped to the user in SQL, someone else's subject is a 404.
"""
from __future__ import annotations

import re
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from studyhub import agents, analytics, ocr, reports, semantic, smartnotes
from studyhub.web import api as base

router = APIRouter(prefix="/api/v1")
_db, guard, err, iso = base._db, base.guard, base.err, base.iso


def _file(data: bytes | str, media: str, name: str) -> Response:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")[:90] or "nexus-export"
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{safe}"'})


MEDIA = {"csv": "text/csv; charset=utf-8", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "pdf": "application/pdf"}


def _sid(ctx, subject_id) -> tuple[int | None, Response | None]:
    """An optional subject filter that must be the user's own."""
    if subject_id in (None, "", "all"):
        return None, None
    sid = base._int(str(subject_id))
    if sid is None or ctx.repo.get_subject(ctx.uid, sid) is None:
        return None, err(404, "not_found", "Not found.")
    return sid, None


# ------------------------------------------------------------------------------------------------ analytics

@router.get("/analytics")
def analytics_overview(request: Request, days: int = 30, subject_id: str | None = None):
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        sid, bad = _sid(ctx, subject_id)
        return bad or analytics.overview(db, ctx.uid, days, sid)


@router.get("/analytics/tables/{name}")
def analytics_table(request: Request, name: str, subject_id: str | None = None):
    fmt = None
    m = re.fullmatch(r"(\w+)\.(csv|xlsx|pdf)", name)
    if m:
        name, fmt = m.group(1), m.group(2)
    if name not in analytics.TABLES:
        return err(404, "not_found", "Not found.")
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        sid, bad = _sid(ctx, subject_id)
        if bad:
            return bad
        rows = analytics.TABLES[name](db, ctx.uid, sid)
        cols = analytics.COLUMNS[name]
        if fmt is None:
            return {"name": name, "columns": [{"key": k, "label": lbl} for k, lbl in cols], "rows": rows}
        stamp = time.strftime("%Y%m%d")
        title = f"Nexus {name}"
        if fmt == "csv":
            return _file(reports.table_csv(cols, rows), MEDIA["csv"], f"nexus-{name}-{stamp}.csv")
        if fmt == "xlsx":
            return _file(reports.workbook([(name.title(), cols, rows)]), MEDIA["xlsx"], f"nexus-{name}-{stamp}.xlsx")
        return _file(reports.table_pdf(title, cols, rows), MEDIA["pdf"], f"nexus-{name}-{stamp}.pdf")


@router.get("/analytics/report.pdf")
def analytics_report(request: Request, days: int = 30, subject_id: str | None = None):
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        sid, bad = _sid(ctx, subject_id)
        if bad:
            return bad
        ov = analytics.overview(db, ctx.uid, days, sid)
        pdf = reports.analytics_report(ov, analytics.attempts_table(db, ctx.uid, sid, 60), analytics.topics_table(db, ctx.uid, sid))
        return _file(pdf, MEDIA["pdf"], f"nexus-analytics-{time.strftime('%Y%m%d')}.pdf")


@router.get("/analytics/workbook.xlsx")
def analytics_workbook(request: Request, days: int = 30, subject_id: str | None = None):
    """Everything in one spreadsheet: a summary sheet plus one sheet per table."""
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        sid, bad = _sid(ctx, subject_id)
        if bad:
            return bad
        ov = analytics.overview(db, ctx.uid, days, sid)
        subj_cols = [("name", "Subject"), ("materials", "Materials"), ("topics", "Topics"), ("quizzes", "Quizzes"), ("answered", "Answered"), ("accuracy", "Accuracy %"),
                     ("theta", "Ability θ"), ("se", "± SE"), ("confidence", "Confidence %"), ("readiness", "Readiness %"), ("risk", "Risk"), ("debt_hours", "Debt h")]
        day_cols = [("date", "Date"), ("answered", "Answered"), ("correct", "Correct"), ("accuracy", "Accuracy %"), ("avg_seconds", "Avg s"), ("asked", "Questions asked"),
                    ("flashcards", "Flashcards")]
        sheets = [("Subjects", subj_cols, ov["subjects"]), ("Daily activity", day_cols, ov["timeline"])]
        sheets += [(n.title(), analytics.COLUMNS[n], analytics.TABLES[n](db, ctx.uid, sid)) for n in ("topics", "attempts", "questions", "materials")]
        return _file(reports.workbook(sheets), MEDIA["xlsx"], f"nexus-analytics-{time.strftime('%Y%m%d')}.xlsx")


# ------------------------------------------------------------------------------------------------ subject reports

@router.get("/subjects/{subject_id}/report.pdf")
def subject_report_pdf(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        data = base._report_data(ctx)
        run = agents.latest(db, ctx.uid, ctx.subject["id"])
        info = base.roadmapmod.skill_gaps(db, ctx.uid, ctx.subject["id"], ctx.subject.get("level"))
        pdf = reports.subject_report(data, agents=run, twin={"target": info["target"]})
        return _file(pdf, MEDIA["pdf"], f"nexus-{ctx.subject['name']}-report.pdf")


@router.get("/subjects/{subject_id}/report.xlsx")
def subject_report_xlsx(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        sid = ctx.subject["id"]
        sheets = [(n.title(), analytics.COLUMNS[n], analytics.TABLES[n](db, ctx.uid, sid)) for n in ("topics", "attempts", "questions", "materials")]
        return _file(reports.workbook(sheets), MEDIA["xlsx"], f"nexus-{ctx.subject['name']}-report.xlsx")


@router.get("/subjects/{subject_id}/quiz/attempts/{attempt_id}/report.pdf")
def attempt_report_pdf(request: Request, subject_id: str, attempt_id: str):
    result = base.quiz_result(request, subject_id, attempt_id)
    if not isinstance(result, dict):
        return result                                          # the same 401/404/409 as the result page
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        return _file(reports.attempt_report(ctx.subject["name"], result), MEDIA["pdf"], f"nexus-quiz-{result['attempt']['id']}.pdf")


# ------------------------------------------------------------------------------------------------ agent console

def _run_json(r: dict | None) -> dict | None:
    if r is None:
        return None
    return {**r, "created_at": iso(r["created_at"])}


@router.get("/subjects/{subject_id}/agents")
def agent_console(request: Request, subject_id: str, attempt_id: int | None = None):
    """The latest run of the six agents (runs them for a finished quiz that has not been analysed yet), the history and the catalogue."""
    with _db() as db:
        ctx, bad = guard(request, db, subject_id=subject_id)
        if bad:
            return bad
        sid = ctx.subject["id"]
        run = None
        if attempt_id is not None:
            att = ctx.repo.get_attempt(ctx.uid, sid, attempt_id)
            if att is None:
                return err(404, "not_found", "Not found.")
            if not att["is_active"]:
                run = agents.after_quiz(db, ctx.uid, sid, attempt_id)
        if run is None:
            run = agents.latest(db, ctx.uid, sid)
            last = db.execute("SELECT id FROM quiz_attempts WHERE user_id=? AND subject_id=? AND is_active=0 AND correct_answers+incorrect_answers>0 "
                              "ORDER BY finished_at DESC, id DESC LIMIT 1", (ctx.uid, sid)).fetchone()
            if last and (run is None or run.get("attempt_id") != last[0]):
                run = agents.after_quiz(db, ctx.uid, sid, last[0]) or run
            if run is None:
                run = agents.run(db, ctx.uid, sid, trigger="first_look")
        return {"agents": agents.AGENTS, "run": _run_json(run),
                "history": [{**h, "created_at": iso(h["created_at"])} for h in agents.history(db, ctx.uid, sid)]}


@router.post("/subjects/{subject_id}/agents/run")
def agent_run(request: Request, subject_id: str):
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        run = agents.run(db, ctx.uid, ctx.subject["id"], trigger="manual")
        return {"agents": agents.AGENTS, "run": _run_json(run),
                "history": [{**h, "created_at": iso(h["created_at"])} for h in agents.history(db, ctx.uid, ctx.subject["id"])]}


# ------------------------------------------------------------------------------------------------ smart notes

class SmartBody(BaseModel):
    topic_ids: list[int] | None = Field(default=None, max_length=200)


@router.post("/subjects/{subject_id}/notes/smart", status_code=201)
def smart_notes(request: Request, subject_id: str, body: SmartBody):
    """Build (or refresh) a smart note per topic from that topic's own passages. Extractive: nothing is invented."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True, subject_id=subject_id)
        if bad:
            return bad
        ids = smartnotes.generate(db, ctx.uid, ctx.subject["id"], body.topic_ids)
        if not ids:
            return err(400, "nothing_to_summarise", "There is no readable material in these topics yet.")
        notes = [ctx.repo.get_note(ctx.uid, ctx.subject["id"], i) for i in ids]
        return JSONResponse({"notes": [base._note_json(n, full=False) for n in notes if n]}, status_code=201)


# ------------------------------------------------------------------------------------------------ system status

@router.get("/system/status")
def system_status(request: Request):
    """What this server can do right now: semantic search, OCR, and how much of the student's material is embedded."""
    with _db() as db:
        ctx, bad = guard(request, db)
        if bad:
            return bad
        return {"semantic": {**semantic.status(), **semantic.coverage(db, ctx.uid)}, "ocr": ocr.status()}


@router.post("/system/reindex")
def system_reindex(request: Request):
    """Embed any of the student's passages that are not embedded yet (in the background)."""
    with _db() as db:
        ctx, bad = guard(request, db, mutate=True)
        if bad:
            return bad
        fut = semantic.schedule_for(db)
        return {"scheduled": fut is not None, **semantic.status()}
