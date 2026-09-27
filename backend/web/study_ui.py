"""
Study-pack frontend. FastAPI + server-rendered HTML + a little vanilla JS. No build
step, no React, no framework beyond what the kit already uses.

    Screen 1  GET  /                    Study Input
    Screen 2  GET  /run/{id}            Generated Content (+ the human-review form)
    Screen 3  GET  /run/{id}/trace      Validation Trace
    Screen 4  GET  /run/{id}/revision   Revision history

The JSON API is the same machinery the CLI uses; the pages only display what is in
the run database. Nothing here computes a validation result.

    POST /api/generate         {source, title?, scenario?} -> {run_id, state, background}
    GET  /api/run/{id}         state, draft, verdict, failure, summary, active
    POST /api/run/{id}/review  {decision: APPROVE|REJECT, notes?, who?} -> {run_id, state}
    POST /api/run/{id}/resume  continue a run that stopped mid-way -> {run_id, state}
    POST /api/run/{id}/feedback {useful, rating?, comment?, confusing?, tester?} -> 201
    GET  /api/run/{id}/feedback  one run's feedback     GET /api/feedback  all of it

Live providers run in a background thread and the run page polls, so a slow local model
never holds an HTTP request open (a tunnel drops those at ~100 s). The fixture provider
is instant and runs inline.

Run:  uvicorn web.study_ui:app --host 127.0.0.1 --port 8080
      (LLM_PROVIDER=fixture|ollama|openrouter; SLICE_DB=path to the run database)

The backend stays usable without this file: scripts/study.py does everything it does.
There is NO authentication. Do not expose a live provider on a public URL: anyone who
can reach it can spend your tokens.
"""
from __future__ import annotations

import html
import json
import os
import threading
import time
from contextlib import contextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from demo.study import checks, feedback
from demo.study import flow as study_flow
from demo.study import trace as study_trace
from demo.study.flow import MAX_REVISIONS
from demo.study.samples import SAMPLE
from demo.study.stub import SCENARIOS, Scripted
from slice import callback, runner
from slice.config import settings as load_settings
from slice.providers import get_provider
from slice.records import RunState
from slice.store import Store

app = FastAPI(title="Study Pack Generator")

_ACTIVE: set[str] = set()          # runs being advanced by this process right now
_LOCK = threading.Lock()


# ---------------------------------------------------------------- database

def _db() -> str:
    """Read per request, not at import: a path frozen at first import made every later
    change to SLICE_DB silently ineffective."""
    return os.environ.get("SLICE_DB", "run.db")


@contextmanager
def _open():
    s = Store(_db())
    try:
        yield s
    finally:
        s.close()


# ------------------------------------------------------------------ running

def _mode_label(cfg) -> str:
    if cfg.llm_provider == "fixture":
        return "fixture (scripted replies - no model is called)"
    if cfg.llm_provider == "ollama":
        other = cfg.ollama_fallback_model or "same model, different prompt"
        return f"ollama: {cfg.ollama_model} (validator: {other})"
    return f"openrouter: {cfg.model} (validator: {cfg.fallback_model})"


def _make_call(cfg, scenario: str | None = None):
    if cfg.llm_provider == "fixture":
        return SCENARIOS[scenario or "revise"][1]()
    return get_provider(cfg)


def _resume_call(cfg):
    """After a human's answer nothing calls a model. If something does, a fixture run
    must fail loudly rather than quietly invent a reply."""
    return Scripted([], []) if cfg.llm_provider == "fixture" else get_provider(cfg)


def _work(run_id: str, cfg, call) -> None:
    """Advance one run on its own connection. Never raises: a crash becomes a
    recorded failure, because a thread that dies silently leaves a page spinning."""
    try:
        with _open() as s:
            try:
                runner.advance(s, run_id, study_flow.build_flow(call=call), cfg)
            except Exception as exc:                     # noqa: BLE001 - recorded, not swallowed
                s.append(run_id, "failure",
                         {"kind": "unexpected_error", "detail": f"{type(exc).__name__}: {exc}"},
                         produced_by="orchestrator")
                s.set_state(run_id, RunState.FAILED)
    finally:
        with _LOCK:
            _ACTIVE.discard(run_id)


def _start(run_id: str, cfg, call, *, background: bool) -> bool:
    """False if the run is already being advanced: two advances would race."""
    with _LOCK:
        if run_id in _ACTIVE:
            return False
        _ACTIVE.add(run_id)
    if background:
        threading.Thread(target=_work, args=(run_id, cfg, call), daemon=True).start()
    else:
        _work(run_id, cfg, call)
    return True


# --------------------------------------------------------------------- html

_CSS = (
    ":root{color-scheme:light dark;--accent:#0d5c5f;--bad:#b91c1c;"
    "--warn:#b45309;--ok:#15803d;--border:#d4d4d8;--muted:#6b7280}"
    "*{box-sizing:border-box}"
    "body{font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;"
    "max-width:48rem;margin:0 auto;padding:2rem 1.2rem 4rem}"
    "h1{font-size:1.4rem;margin:0 0 .25rem}h2{font-size:1.1rem;margin:1.6rem 0 .5rem}"
    "h3{font-size:1rem;margin:0 0 .4rem}"
    ".sub{color:var(--muted);font-size:.9rem;margin:0 0 1.2rem}"
    ".card{border:1px solid var(--border);border-radius:8px;padding:1rem 1.2rem;margin:0 0 .9rem}"
    "textarea{width:100%;min-height:10rem;font:inherit;padding:.7rem;"
    "border:1px solid #a1a1aa;border-radius:6px;background:transparent;color:inherit;resize:vertical}"
    "input[type=text],select{width:100%;font:inherit;padding:.5rem .7rem;"
    "border:1px solid #a1a1aa;border-radius:6px;background:transparent;color:inherit}"
    "label{display:block;margin-bottom:.25rem;font-weight:600;font-size:.9rem}"
    ".btn{display:inline-block;font:inherit;font-weight:600;padding:.6rem 1.4rem;"
    "margin-top:.9rem;border:0;border-radius:6px;background:var(--accent);color:#fff;"
    "cursor:pointer;text-decoration:none}.btn:disabled{opacity:.5;cursor:wait}"
    ".btn-sec{background:transparent;border:1px solid var(--border);color:inherit}"
    ".btn-bad{background:var(--bad)}"
    "a{color:var(--accent)}"
    ".tag{display:inline-block;padding:.15rem .5rem;border-radius:4px;font-size:.8rem;font-weight:600}"
    ".ok{background:#dcfce7;color:var(--ok)}.warn{background:#fef3c7;color:var(--warn)}"
    ".bad{background:#fee2e2;color:var(--bad)}"
    ".dim{color:var(--muted);font-size:.85rem}"
    ".banner{background:rgba(127,127,127,.1);border-radius:6px;padding:.5rem .8rem;"
    "font-size:.85rem;margin:0 0 1.2rem}"
    ".trace-line{padding:.25rem 0;border-bottom:1px solid var(--border)}"
    ".trace-title{font-weight:600}"
    ".trace-detail{font-size:.85rem;padding-left:1rem;white-space:pre-wrap;"
    "font-family:ui-monospace,monospace}"
    ".spinner{display:none;width:20px;height:20px;border:3px solid var(--border);"
    "border-top-color:var(--accent);border-radius:50%;"
    "animation:spin .8s linear infinite;margin-left:.6rem;vertical-align:middle}"
    ".spinner.on{display:inline-block}@keyframes spin{to{transform:rotate(360deg)}}"
    ".row{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}"
    ".error-box{background:#fee2e2;border:1px solid #fca5a5;border-radius:6px;"
    "padding:.8rem 1rem;color:var(--bad);margin:1rem 0}"
    ".answer-key{font-weight:700;color:var(--ok)}"
    ".note{font-size:.85rem;color:var(--muted)}"
    ".strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));gap:.5rem;margin:0 0 1rem}"
    ".strip div{border:1px solid var(--border);border-radius:6px;padding:.4rem .7rem;font-size:.85rem}"
    ".strip b{display:block;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}"
)


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _page(title: str, body: str, head: str = "") -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html>\n<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{_esc(title)}</title><style>{_CSS}</style>{head}</head><body>{body}</body></html>")


def _tag(text: str, tone: str) -> str:
    return f"<span class='tag {tone}'>{_esc(text)}</span>"


def _nav(run_id: str | None = None) -> str:
    links = ["<a href='/'>&larr; New pack</a>"]
    if run_id:
        rid = html.escape(run_id, quote=True)
        links += [f"<a href='/run/{rid}'>Content</a>", f"<a href='/run/{rid}/trace'>Trace</a>",
                  f"<a href='/run/{rid}/revision'>Revision</a>"]
    return "<nav style='margin-bottom:1.5rem;display:flex;gap:1.2rem;flex-wrap:wrap'>" \
        + " ".join(links) + "</nav>"


def _not_found() -> HTMLResponse:
    return _page("Not found", _nav() + "<h1>Run not found</h1>")


_STATE_LABEL = {
    RunState.COMPLETE: ("APPROVED", "ok"), RunState.FAILED: ("FAILED", "bad"),
    RunState.AWAITING_EXPERT: ("HUMAN REVIEW REQUIRED", "warn"),
    RunState.GATING: ("VALIDATING", "warn"), RunState.DRAFTING: ("GENERATING", "warn"),
    RunState.PROBING: ("APPLYING REVIEW", "warn"),
}


def _status(s: Store, run_id: str) -> dict:
    """The run at a glance, read from the records - never computed by the page."""
    state = s.get_state(run_id)
    drafts, verdicts = s.history(run_id, "draft"), s.history(run_id, "verdict")
    result, failure = s.latest(run_id, "result"), s.latest(run_id, "failure")
    last = verdicts[-1].payload if verdicts else None
    if result:
        outcome = f"approved by {result['approved_by']}"
    elif failure:
        outcome = f"stopped: {failure['kind']}"
    elif state is RunState.AWAITING_EXPERT:
        outcome = "waiting for a human reviewer"
    else:
        outcome = "in progress"
    return {
        "state": state,
        "generator": f"{len(drafts)} draft(s) written" if drafts else "no draft yet",
        "validator": (f"{last['status']} ({len(last['issues'])} issue(s))" if last else "not run yet"),
        "revisions": max(0, len(drafts) - 1),
        "outcome": outcome,
        "active": run_id in _ACTIVE,
    }


def _strip(st: dict) -> str:
    label, cls = _STATE_LABEL.get(st["state"], (st["state"].value.upper(), "dim"))
    cells = [("Generator", st["generator"]), ("Validator", st["validator"]),
             ("Revision", f"{st['revisions']} of {MAX_REVISIONS}"),
             ("Workflow state", _tag(label, cls)), ("Outcome", _esc(st["outcome"]))]
    return "<div class='strip'>" + "".join(
        f"<div><b>{k}</b>{v if k == 'Workflow state' else _esc(v)}</div>" for k, v in cells) + "</div>"


def _issues(items: list[dict]) -> str:
    return "<ul>" + "".join(
        f"<li><code>{_esc(x['code'])}</code> <span class='dim'>[{_esc(x['origin'])}]</span> "
        f"@ {_esc(x['where'])}: {_esc(x['detail'])}</li>" for x in items) + "</ul>"


# ------------------------------------------------------------------ Screen 1

@app.get("/", response_class=HTMLResponse)
def index():
    cfg = load_settings()
    scenario = ""
    if cfg.llm_provider == "fixture":
        opts = "".join(f"<option value='{k}'>{_esc(k)} - {_esc(v[0])}</option>"
                       for k, v in SCENARIOS.items())
        scenario = ("<label for='scenario' style='margin-top:.9rem'>Scripted scenario "
                    "<span class='dim'>(fixture mode only)</span></label>"
                    f"<select id='scenario'>{opts}</select>")
    sample = json.dumps(SAMPLE).replace("</", "<\\/")
    body = (
        _nav() + "<h1>Study Pack Generator</h1>"
        "<p class='sub'>Paste your study material. The system writes notes and quiz "
        "questions, then a separate validator tries to reject them.</p>"
        f"<div class='banner'>Mode: <b>{_esc(_mode_label(cfg))}</b></div>"
        "<form id='gen-form'>"
        "<label for='title'>Subject / title (optional)</label>"
        "<input type='text' id='title' placeholder='e.g. Chapter 3 - Photosynthesis' maxlength='100'>"
        "<label for='source' style='margin-top:.9rem'>Source material "
        f"<span class='dim'>(at least {checks.MIN_SOURCE_WORDS} words, at most "
        f"{checks.MAX_SOURCE_CHARS:,} characters)</span></label>"
        "<textarea id='source' placeholder='Paste the text you want to study from...' required>"
        "</textarea>" + scenario +
        "<div class='row'><button type='submit' class='btn' id='gen-btn'>Generate study pack</button>"
        "<button type='button' class='btn btn-sec' id='sample-btn'>Use sample text</button>"
        "<span class='spinner' id='spinner'></span></div>"
        "<div id='error-area'></div></form>"
        "<script>const SAMPLE=" + sample + ";"
        "const $=id=>document.getElementById(id);"
        "$('sample-btn').onclick=()=>{$('source').value=SAMPLE;};"
        "$('gen-form').addEventListener('submit',async e=>{e.preventDefault();"
        "const err=$('error-area');err.textContent='';err.className='';"
        "$('gen-btn').disabled=true;$('spinner').classList.add('on');"
        "const fail=m=>{err.className='error-box';err.textContent=m;"
        "$('gen-btn').disabled=false;$('spinner').classList.remove('on');};"
        "try{const body={source:$('source').value,title:$('title').value};"
        "if($('scenario'))body.scenario=$('scenario').value;"
        "const r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify(body)});const d=await r.json();"
        "if(d.error)fail(d.error);else window.location.href='/run/'+d.run_id;"
        "}catch(x){fail('Network error: '+x.message);}});</script>"
    )
    return _page("Study Pack Generator", body)


# ------------------------------------------------------------------ Screen 2

def _review_card(s: Store, run_id: str) -> str:
    esc = s.latest(run_id, "escalation") or {}
    why = {"max_revisions": f"the validator still rejected the draft after {MAX_REVISIONS} revisions",
           "repeated_output": "the generator produced the same draft twice"}.get(esc.get("reason"), "")
    rid = json.dumps(run_id)
    return (
        "<div class='card' style='border-color:var(--warn)'><h3>Human review required</h3>"
        f"<p class='note'>Why: {_esc(why or 'the validator could not be satisfied')}. Review the "
        "draft and the validator's objections above, then decide. Approving overrides the "
        "validator, and the override is recorded.</p>"
        "<label for='notes'>Notes (optional)</label><input type='text' id='notes' maxlength='300'>"
        "<label for='who' style='margin-top:.6rem'>Your name</label>"
        "<input type='text' id='who' value='reviewer' maxlength='60'>"
        "<div class='row'><button class='btn' data-decision='APPROVE'>Approve this draft</button>"
        "<button class='btn btn-bad' data-decision='REJECT'>Reject</button></div>"
        "<div id='review-error'></div></div>"
        "<script>document.querySelectorAll('[data-decision]').forEach(b=>b.addEventListener('click',async()=>{"
        "const e=document.getElementById('review-error');e.className='';e.textContent='';b.disabled=true;"
        "try{const r=await fetch('/api/run/'+" + rid + "+'/review',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify({decision:b.dataset.decision,"
        "notes:document.getElementById('notes').value,who:document.getElementById('who').value})});"
        "const d=await r.json();if(d.error){e.className='error-box';e.textContent=d.error;b.disabled=false;}"
        "else location.reload();}catch(x){e.className='error-box';e.textContent='Network error: '+x.message;"
        "b.disabled=false;}}));</script>")


def _stalled_card(run_id: str) -> str:
    return (
        "<div class='card' style='border-color:var(--warn)'><h3>This run stopped part-way</h3>"
        "<p class='note'>Nothing is working on it: the server may have restarted, or a review "
        "deadline passed with no answer. Its state is saved; resume to carry on from the last "
        "completed step (an unanswered review is closed as unreviewed - never approved).</p>"
        "<button class='btn' id='resume-btn'>Resume</button><div id='resume-error'></div></div>"
        "<script>document.getElementById('resume-btn').onclick=async()=>{"
        "const e=document.getElementById('resume-error');e.className='';e.textContent='';"
        f"const r=await fetch('/api/run/'+{json.dumps(run_id)}+'/resume',{{method:'POST'}});"
        "const d=await r.json();if(d.error){e.className='error-box';e.textContent=d.error;}"
        "else location.reload();};</script>")


def _draft_html(draft: dict, source: str, n: int) -> str:
    notes = "".join(f"<li>{_esc(x)}</li>" for x in draft["notes"])
    qs = ""
    for i, q in enumerate(draft["questions"], 1):
        opts = "".join(
            f"<li class='{'answer-key' if chr(65 + j) == q['answer'] else ''}'>{chr(65 + j)}. {_esc(o)}"
            f"{'  &larr; marked correct' if chr(65 + j) == q['answer'] else ''}</li>"
            for j, o in enumerate(q["options"]))
        found, para = checks.locate_quote(source, q["source_quote"])
        proof = (_tag(f"quote found in source{f', paragraph {para}' if para else ''}", "ok")
                 if found else _tag("QUOTE NOT FOUND IN SOURCE", "bad"))
        qs += (f"<div class='card'><h3>Q{i}. {_esc(q['question'])}</h3><ul>{opts}</ul>"
               f"<p class='note'><strong>Why:</strong> {_esc(q['explanation'])}</p>"
               f"<p class='dim'>Source: &ldquo;{_esc(q['source_quote'])}&rdquo; {proof}</p></div>")
    return (f"<h2>Notes &mdash; {_esc(draft['title'])} <span class='dim'>(draft {n})</span></h2>"
            f"<ul>{notes}</ul><h2>Quiz</h2>{qs}")


def _feedback_card(run_id: str) -> str:
    """The tester's form. It only ever POSTs to the API; nothing here is stored client-side."""
    stars = "".join(f"<option value='{n}'>{n}</option>" for n in range(1, 6))
    return (
        "<div class='card' id='feedback'><h3>Was this study material useful?</h3>"
        "<p class='note'>Your answer is saved with this run. Use a nickname - please do not "
        "enter personal details.</p>"
        "<div class='row'><button type='button' class='btn btn-sec' data-useful='yes'>Yes</button>"
        "<button type='button' class='btn btn-sec' data-useful='no'>No</button></div>"
        "<label for='fb-improve' style='margin-top:.9rem'>What should be improved?</label>"
        "<textarea id='fb-improve' maxlength='1000' style='min-height:4rem'></textarea>"
        "<label for='fb-confusing' style='margin-top:.6rem'>Was anything confusing or wrong?</label>"
        "<textarea id='fb-confusing' maxlength='1000' style='min-height:4rem'></textarea>"
        "<label for='fb-rating' style='margin-top:.6rem'>Rating (optional)</label>"
        f"<select id='fb-rating'><option value=''>-</option>{stars}</select>"
        "<label for='fb-who' style='margin-top:.6rem'>Your name or nickname (optional)</label>"
        "<input type='text' id='fb-who' maxlength='60'>"
        "<button type='button' class='btn' id='fb-submit' disabled>Submit feedback</button>"
        "<div id='fb-msg'></div></div>"
        "<script>(function(){let useful=null;const $=id=>document.getElementById(id);"
        "const pick=document.querySelectorAll('[data-useful]');"
        "pick.forEach(b=>b.addEventListener('click',()=>{useful=b.dataset.useful==='yes';"
        "pick.forEach(x=>{x.className='btn'+(x===b?'':' btn-sec');});$('fb-submit').disabled=false;}));"
        "$('fb-submit').addEventListener('click',async()=>{const m=$('fb-msg');m.className='';m.textContent='';"
        "$('fb-submit').disabled=true;"
        "const body={useful:useful,comment:$('fb-improve').value,confusing:$('fb-confusing').value,"
        "tester:$('fb-who').value};if($('fb-rating').value)body.rating=Number($('fb-rating').value);"
        "try{const r=await fetch('/api/run/'+" + json.dumps(run_id) + "+'/feedback',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();"
        "if(d.error){m.className='error-box';m.textContent=d.error;$('fb-submit').disabled=false;}"
        "else location.reload();}catch(x){m.className='error-box';m.textContent='Network error: '+x.message;"
        "$('fb-submit').disabled=false;}});})();</script>")


def _feedback_list(items: list[dict]) -> str:
    if not items:
        return ""
    rows = ""
    for f in items:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(f["submitted_at"]))
        rating = f" &middot; {f['rating']}/5" if f.get("rating") else ""
        detail = "".join(f"<p class='note'><b>{label}:</b> {_esc(f[key])}</p>"
                         for label, key in (("Improve", "comment"), ("Confusing or wrong", "confusing"))
                         if f.get(key))
        rows += (f"<div class='card'><b>{_esc(f['tester'])}</b> "
                 f"{_tag('useful' if f['useful'] else 'not useful', 'ok' if f['useful'] else 'warn')}"
                 f"{rating} <span class='dim'>&middot; {when} &middot; about draft {f['draft']}</span>"
                 f"{detail}</div>")
    return f"<h2>Feedback so far ({len(items)})</h2>{rows}"


@app.get("/run/{run_id}", response_class=HTMLResponse)
def run_page(run_id: str):
    with _open() as s:
        try:
            st = _status(s, run_id)
        except KeyError:
            return _not_found()
        meta, failure = s.meta(run_id), s.latest(run_id, "failure")
        drafts, verdicts = s.history(run_id, "draft"), s.history(run_id, "verdict")
        source = (s.latest(run_id, "input") or {}).get("text", "")
        state, active = st["state"], st["active"]
        awaiting = state is RunState.AWAITING_EXPERT and bool(callback.pending(s, run_id))
        review = _review_card(s, run_id) if awaiting else ""

        working = ""
        if active:
            label = _STATE_LABEL.get(state, ("WORKING", "warn"))[0].lower()
            working = ("<div class='card'><span class='spinner on'></span> "
                       f"Working - currently <b>{_esc(label)}</b>. This page refreshes itself; "
                       "a local model can take minutes per step.</div>")
        # Nothing is working on it, it is not finished, and there is no live question to
        # answer: either the process died part-way, or a review deadline passed unanswered.
        stalled = _stalled_card(run_id) if (
            not active and not state.is_terminal
            and (not state.is_suspended or not awaiting)) else ""

        fail_html = (f"<div class='error-box'><strong>{_esc(failure['kind'])}</strong>: "
                     f"{_esc(failure['detail'])}</div>") if failure else ""
        last = verdicts[-1].payload if verdicts else None
        issues_html = (f"<div class='card'><h3>Validator objections "
                       f"({'draft ' + str(last['draft']) if last['draft'] else 'intake check'})</h3>"
                       f"{_issues(last['issues'])}</div>") if last and last["issues"] else ""
        draft_html = _draft_html(drafts[-1].payload, source, len(drafts)) if drafts else ""
        # Only once nobody is still working on it: feedback on half a result is about
        # something the tester has not seen.
        feedback_html = ("" if active else
                         _feedback_list(feedback.for_run(s, run_id)) + _feedback_card(run_id))

        body = (_nav(run_id) + f"<h1>{_esc(meta.get('title', 'Study Pack'))}</h1>"
                f"<p class='sub'>Mode: {_esc(meta.get('mode', 'unknown'))} &nbsp; "
                f"<a href='/run/{html.escape(run_id, quote=True)}/trace'>View trace &rarr;</a></p>"
                + _strip(st) + working + stalled + fail_html + issues_html + review + draft_html
                + feedback_html)
    head = "<meta http-equiv='refresh' content='3'>" if active else ""
    return _page("Study Pack", body, head)


# ------------------------------------------------------------------ Screen 3

@app.get("/run/{run_id}/trace", response_class=HTMLResponse)
def trace_page(run_id: str):
    with _open() as s:
        try:
            st = _status(s, run_id)
        except KeyError:
            return _not_found()
        events, summary = study_trace.build(s, run_id), study_trace.summary(s, run_id)

    tone = {"ok": "ok", "warn": "warn", "bad": "bad", "info": "", "dim": "dim"}
    rows = ""
    for e in events:
        if e.kind == "step":
            rows += f"<div class='dim trace-line'>&nbsp;&nbsp;. {_esc(e.title)}</div>"
            continue
        detail = "".join(f"<div class='trace-detail'>{_esc(x)}</div>" for x in e.lines)
        rows += (f"<div class='trace-line'><span class='trace-title'>"
                 f"{_tag(f'#{e.seq}', tone.get(e.tone, '') or 'dim')} {_esc(e.title)}</span>{detail}</div>")
    head = "<meta http-equiv='refresh' content='3'>" if st["active"] else ""
    body = (_nav(run_id) + "<h1>Execution Trace</h1>"
            f"<p class='sub'>Run {_esc(run_id)} &mdash; {summary['drafts']} draft(s), "
            f"{summary['revisions']} revision(s), {summary['tokens']:,} tokens</p>"
            + _strip(st) + f"<p class='dim'>Path: {_esc(summary['path'])}</p>"
            f"<div style='margin-top:1rem'>{rows}</div>")
    return _page("Execution Trace", body, head)


# ------------------------------------------------------------------ Screen 4

def _changed(prev: dict, cur: dict) -> list[str]:
    out = ["notes"] if prev["notes"] != cur["notes"] else []
    out += [f"questions[{i}]" for i, (a, b) in enumerate(zip(prev["questions"], cur["questions"]))
            if a != b]
    return out


@app.get("/run/{run_id}/revision", response_class=HTMLResponse)
def revision_page(run_id: str):
    with _open() as s:
        try:
            st = _status(s, run_id)
        except KeyError:
            return _not_found()
        drafts = [v.payload for v in s.history(run_id, "draft")]
        verdicts = {v.payload["draft"]: v.payload for v in s.history(run_id, "verdict")}
        esc = s.latest(run_id, "escalation")

    used = st["revisions"]
    pct = min(100, int(used / MAX_REVISIONS * 100))
    bar = ("<div style='background:var(--border);border-radius:4px;height:8px;margin:.5rem 0'>"
           f"<div style='background:{'var(--ok)' if used < MAX_REVISIONS else 'var(--bad)'};"
           f"border-radius:4px;height:8px;width:{pct}%'></div></div>"
           f"<p class='dim'>{used} of {MAX_REVISIONS} revisions used. The limit is enforced by the "
           "orchestrator, not by this page.</p>")
    esc_html = (f"<div class='error-box'><strong>Escalated to a human:</strong> "
                f"{_esc(esc['reason'])}</div>" if esc else "")

    rounds = ""
    for n, d in enumerate(drafts, 1):
        v = verdicts.get(n)
        head = f"<h3>Draft {n}{' (revision ' + str(n - 1) + ')' if n > 1 else ''}"
        if v:
            head += f" &mdash; {_tag(v['status'], 'ok' if v['status'] == 'APPROVED' else 'warn')}"
        head += "</h3>"
        changed = ""
        if n > 1:
            what = _changed(drafts[n - 2], d)
            changed = (f"<p class='note'>Changed from draft {n - 1}: "
                       f"{_esc(', '.join(what)) if what else 'nothing (identical draft)'}</p>")
        rounds += (f"<div class='card'>{head}{changed}"
                   f"{_issues(v['issues']) if v and v['issues'] else ''}</div>")
    head = "<meta http-equiv='refresh' content='3'>" if st["active"] else ""
    body = (_nav(run_id) + "<h1>Revision History</h1>"
            "<p class='sub'>Each draft, what the validator objected to, and what changed.</p>"
            + _strip(st) + bar + esc_html + (rounds or "<p class='dim'>No draft yet.</p>")
            + f"<p><a href='/run/{html.escape(run_id, quote=True)}' class='btn btn-sec'>View latest draft</a></p>")
    return _page("Revision History", body, head)


# ------------------------------------------------------------------ JSON API

def _err(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


@app.post("/api/generate")
async def api_generate(request: Request):
    try:
        body = await request.json()
    except Exception:                                    # noqa: BLE001
        return _err("Invalid JSON body", 400)
    if not isinstance(body, dict):
        return _err("Invalid JSON body", 400)
    source, title = str(body.get("source") or "").strip(), str(body.get("title") or "").strip()[:100]
    if not source:
        return _err("source is required", 422)

    cfg, scenario = load_settings(), str(body.get("scenario") or "revise")
    if cfg.llm_provider == "fixture" and scenario not in SCENARIOS:
        return _err(f"unknown scenario {scenario!r}; choose one of {', '.join(SCENARIOS)}", 422)
    if cfg.llm_provider == "openrouter" and not cfg.api_key:
        return _err("OPENROUTER_API_KEY is not set. Set it, or start the server with "
                    "LLM_PROVIDER=ollama (local) or LLM_PROVIDER=fixture (scripted).", 503)
    try:
        call = _make_call(cfg, scenario)
    except ValueError as exc:
        return _err(str(exc), 500)

    with _open() as s:
        run_id = s.create_run("study", meta={"title": title or "Study Pack",
                                             "mode": _mode_label(cfg)})
        s.append(run_id, "input", {"text": source}, produced_by="user")
    background = cfg.llm_provider != "fixture"
    _start(run_id, cfg, call, background=background)
    with _open() as s:
        state = s.get_state(run_id).value
    return JSONResponse({"run_id": run_id, "state": state, "background": background})


@app.get("/api/run/{run_id}")
def api_run(run_id: str):
    with _open() as s:
        try:
            st = _status(s, run_id)
        except KeyError:
            return _err("run not found", 404)
        return JSONResponse({
            "run_id": run_id, "state": st["state"].value, "active": st["active"],
            "mode": s.meta(run_id).get("mode"),
            "draft": s.latest(run_id, "draft"), "verdict": s.latest(run_id, "verdict"),
            "failure": s.latest(run_id, "failure"), "result": s.latest(run_id, "result"),
            "escalation": s.latest(run_id, "escalation"),
            "awaiting_review": bool(callback.pending(s, run_id)),
            "summary": study_trace.summary(s, run_id),
        })


@app.post("/api/run/{run_id}/review")
async def api_review(run_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:                                    # noqa: BLE001
        return _err("Invalid JSON body", 400)
    if not isinstance(body, dict):
        return _err("Invalid JSON body", 400)
    decision = str(body.get("decision") or "").upper()
    if decision not in ("APPROVE", "REJECT"):
        return _err("decision must be APPROVE or REJECT", 422)
    notes = str(body.get("notes") or "").strip()[:300]
    who = str(body.get("who") or "").strip()[:60] or "reviewer"

    cfg = load_settings()
    with _open() as s:
        try:
            s.get_state(run_id)
        except KeyError:
            return _err("run not found", 404)
        expired = callback.sweep(s, run_id)              # a deadline may already have passed
        waiting = callback.pending(s, run_id)
        if waiting:
            callback.answer(s, waiting[0].id, f"{decision} {notes}".strip(), who=who)
    if not waiting:
        if expired:
            # The sweep already recorded "nobody answered". Apply it now, so the run is not
            # left half-way - and never approved on the strength of a late click.
            _start(run_id, cfg, _resume_call(cfg), background=False)
            return _err("the review deadline had passed, so the run was closed without a "
                        "review", 409)
        return _err("nothing is waiting for a reviewer on this run", 409)

    if not _start(run_id, cfg, _resume_call(cfg), background=False):
        return _err("this run is busy; try again in a moment", 409)
    with _open() as s:
        return JSONResponse({"run_id": run_id, "state": s.get_state(run_id).value})


@app.post("/api/run/{run_id}/resume")
def api_resume(run_id: str):
    with _open() as s:
        try:
            s.get_state(run_id)
        except KeyError:
            return _err("run not found", 404)
    cfg = load_settings()
    try:
        call = _resume_call(cfg)
    except ValueError as exc:
        return _err(str(exc), 500)
    if not _start(run_id, cfg, call, background=cfg.llm_provider != "fixture"):
        return _err("this run is already being worked on", 409)
    with _open() as s:
        return JSONResponse({"run_id": run_id, "state": s.get_state(run_id).value})


# ---------------------------------------------------------------- feedback API

@app.post("/api/run/{run_id}/feedback")
async def api_feedback(run_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:                                    # noqa: BLE001
        return _err("Invalid JSON body", 400)
    if not isinstance(body, dict):
        return _err("Invalid JSON body", 400)
    with _open() as s:
        try:
            s.get_state(run_id)
        except KeyError:
            return _err("run not found", 404)
        if run_id in _ACTIVE:
            return _err("this run is still being worked on; give feedback once it has finished", 409)
        try:
            record = feedback.submit(s, run_id, body)
        except feedback.FeedbackError as exc:
            return _err(str(exc), 422)
    return JSONResponse({"run_id": run_id, "feedback": record}, status_code=201)


@app.get("/api/run/{run_id}/feedback")
def api_run_feedback(run_id: str):
    with _open() as s:
        try:
            s.get_state(run_id)
        except KeyError:
            return _err("run not found", 404)
        return JSONResponse({"run_id": run_id, "feedback": feedback.for_run(s, run_id)})


@app.get("/api/feedback")
def api_all_feedback():
    """Everything testers have said, across runs. Unauthenticated, like the rest of this app."""
    with _open() as s:
        return JSONResponse({"feedback": feedback.everything(s)})
