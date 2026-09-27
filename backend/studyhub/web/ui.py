"""HTML for StudyHub: plain server-rendered forms, no JavaScript (so the CSP can forbid scripts outright)."""
from __future__ import annotations

import html
import re
import time

from ..explain import mcq_step_text, step_text, verification_rows

CSS = (
    ":root{color-scheme:light dark;--accent:#0d5c5f;--link:#0d5c5f;--bad:#b91c1c;--ok:#15803d;--border:#d4d4d8;--muted:#6b7280}"
    "*{box-sizing:border-box}"
    "body{font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;max-width:44rem;margin:0 auto;padding:1.2rem 1.2rem 4rem}"
    "header{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;"
    "border-bottom:1px solid var(--border);padding-bottom:.7rem;margin-bottom:1.6rem}"
    "header .brand{font-weight:700;text-decoration:none;color:inherit}"
    "header form{display:inline;margin:0}"
    "h1{font-size:1.4rem;margin:0 0 .3rem}h2{font-size:1.05rem;margin:1.6rem 0 .5rem}"
    ".sub{color:var(--muted);font-size:.9rem;margin:0 0 1.2rem}"
    ".card{border:1px solid var(--border);border-radius:8px;padding:.9rem 1.1rem;margin:0 0 .8rem}"
    "label{display:block;font-weight:600;font-size:.9rem;margin:.8rem 0 .25rem}"
    "input[type=text],input[type=password],textarea{width:100%;font:inherit;padding:.5rem .7rem;"
    "border:1px solid #a1a1aa;border-radius:6px;background:transparent;color:inherit}"
    "textarea{min-height:5rem;resize:vertical}"
    ".btn{font:inherit;font-weight:600;padding:.5rem 1.2rem;margin-top:.9rem;border:0;border-radius:6px;"
    "background:var(--accent);color:#fff;cursor:pointer}"
    ".btn-sec{background:transparent;border:1px solid var(--border);color:inherit}"
    ".btn-bad{background:#b91c1c}"
    "a{color:var(--link)}"
    ".error{background:#fee2e2;border:1px solid #fca5a5;color:var(--bad);border-radius:6px;padding:.6rem .9rem;margin:0 0 1rem}"
    ".note{font-size:.85rem;color:var(--muted)}"
    ".row{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}"
    ".row input[type=text]{flex:1;min-width:12rem;width:auto}"
    "h3{font-size:.95rem;margin:1.2rem 0 .4rem}"
    ".warn{background:#fef3c7;border:1px solid #fcd34d;color:#78350f;border-radius:6px;padding:.4rem .7rem;margin:.5rem 0 0;font-size:.88rem}"
    ".passage{white-space:pre-wrap;font-size:.93rem;margin-top:.3rem;overflow-wrap:anywhere}"
    ".topics{margin:.2rem 0;padding-left:1.2rem}"
    "mark{background:#fde68a;color:#111;border-radius:2px;padding:0 1px}"
    "blockquote{margin:.4rem 0;padding:.4rem .8rem;border-left:3px solid var(--accent);font-size:.92rem;overflow-wrap:anywhere}"
    ".badge{display:inline-block;font-size:.8rem;font-weight:600;border-radius:999px;padding:.1rem .7rem;border:1px solid var(--border)}"
    ".ok{color:var(--ok)}.claims li{margin:.6rem 0}.cite{font-size:.8rem;vertical-align:super}"
    "details{margin:1rem 0}summary{cursor:pointer;font-weight:600}"
    ".step{font-size:.88rem;margin:.35rem 0;padding-left:.6rem;border-left:2px solid var(--border)}.step.ok{border-left-color:var(--ok)}"
    "select,input[type=number]{font:inherit;padding:.45rem .6rem;border:1px solid #a1a1aa;border-radius:6px;background:transparent;color:inherit;max-width:100%}"
    "select option{color:#111}.opts{margin:.5rem 0;padding-left:1.6rem}.opts li{margin:.2rem 0}"
    "textarea.ask{min-height:4rem}.card:target{outline:2px solid var(--accent)}"
    "@media (prefers-color-scheme:dark){:root{--link:#5eead4;--muted:#a1a1aa;--bad:#f87171;--ok:#4ade80}"
    ".error{background:#450a0a;border-color:#7f1d1d}.warn{background:#3b2a05;border-color:#92400e;color:#fde68a}}"
)


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def csrf_field(token: str) -> str:
    return f"<input type='hidden' name='csrf' value='{esc(token)}'>"


def page(title: str, body: str, *, username: str | None = None, csrf: str | None = None) -> str:
    who = ""
    if username is not None and csrf:
        who = (f"<a class='note' href='/account'>Account</a><span class='note'>Signed in as <b>{esc(username)}</b></span>"
               f"<form method='post' action='/logout'>{csrf_field(csrf)}"
               "<button class='btn btn-sec' style='margin:0'>Log out</button></form>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title)} - StudyHub</title><style>{CSS}</style></head><body>"
            f"<header><a class='brand' href='/subjects'>StudyHub</a><div class='row'>{who}</div></header>"
            f"{body}</body></html>")


def error_box(message: str | None) -> str:
    return f"<div class='error' role='alert'>{esc(message)}</div>" if message else ""


def auth_form(kind: str, token: str, *, error: str | None = None, username: str = "") -> str:
    register = kind == "register"
    return (
        f"<h1>{'Create your account' if register else 'Log in'}</h1>"
        f"<p class='sub'>{'Your subjects and progress are private to your account.' if register else 'Welcome back.'}</p>"
        f"{error_box(error)}"
        f"<form method='post' action='/{kind}'>{csrf_field(token)}"
        f"<label for='username'>Username</label>"
        f"<input type='text' id='username' name='username' value='{esc(username)}' maxlength='32' "
        f"autocomplete='username' required autofocus>"
        f"<label for='password'>Password</label>"
        f"<input type='password' id='password' name='password' maxlength='128' "
        f"autocomplete='{'new-password' if register else 'current-password'}' required>"
        + ("<label for='password2'>Repeat password</label>"
           "<input type='password' id='password2' name='password2' maxlength='128' autocomplete='new-password' required>"
           if register else "")
        + f"<button class='btn'>{'Register' if register else 'Log in'}</button></form>"
        + (f"<p class='note'>Already registered? <a href='/login'>Log in</a></p>" if register
           else "<p class='note'>New here? <a href='/register'>Create an account</a></p>")
    )


def subjects_page(subjects: list[dict], csrf: str, *, error: str | None = None, name: str = "",
                  description: str = "") -> str:
    cards = "".join(
        f"<div class='card'><a href='/subjects/{int(s['id'])}'><b>{esc(s['name'])}</b></a>"
        + (f"<div class='note'>{esc(s['description'])}</div>" if s["description"] else "") + "</div>"
        for s in subjects) or "<p class='note'>No subjects yet. Create your first one below.</p>"
    return (
        "<h1>Your subjects</h1><p class='sub'>Each subject keeps its own materials, questions, quizzes and progress.</p>"
        f"{cards}<h2>New subject</h2>{error_box(error)}"
        f"<form method='post' action='/subjects'>{csrf_field(csrf)}"
        f"<label for='name'>Name</label><input type='text' id='name' name='name' maxlength='80' value='{esc(name)}' required>"
        f"<label for='description'>Description (optional)</label>"
        f"<textarea id='description' name='description' maxlength='500'>{esc(description)}</textarea>"
        "<button class='btn'>Create subject</button></form>"
    )


def _where(page_start, page_end) -> str:
    if page_start is None:
        return ""
    return f"PDF p. {int(page_start)}" if page_end in (None, page_start) else f"PDF pp. {int(page_start)}–{int(page_end)}"


def _warnings(items: list[str]) -> str:
    return "".join(f"<div class='warn'>{esc(w)}</div>" for w in items)


def materials_section(subject_id: int, documents: list[dict], topics: list[dict], csrf: str, *,
                      upload_error: str | None = None) -> str:
    sid = int(subject_id)
    rows = ""
    for d in documents:
        rows += (f"<div class='card'><a href='/subjects/{sid}/materials/{int(d['id'])}'><b>{esc(d['title'])}</b></a>"
                 f"<div class='note'>{esc(d['kind']).upper()} &middot; {esc(d['source'])} &middot; "
                 + (f"{int(d['pages'])} pages &middot; " if d["pages"] else "")
                 + f"{int(d['chunks'])} passages"
                 + ("" if d["status"] == "parsed" else f" &middot; <b>{esc(d['status'])}</b>")
                 + f"</div>{_warnings(d['warnings'])}</div>")
    rows = rows or "<p class='note'>No materials yet. Upload a PDF, a Word document or a text file.</p>"
    topic_items = "".join(f"<li>{esc(t['path'])} <span class='note'>({int(t['chunks'])} passages)</span></li>" for t in topics)
    return (
        "<h2>Materials</h2>" + rows
        + "<h3>Add material</h3>" + error_box(upload_error)
        + f"<form method='post' action='/subjects/{sid}/materials' enctype='multipart/form-data'>{csrf_field(csrf)}"
        "<label for='file'>PDF, Word (.docx) or text file (up to 20 MB)</label>"
        "<input type='file' id='file' name='file' accept='.pdf,.docx,.txt,.md,text/plain,application/pdf' required>"
        "<button class='btn'>Upload</button></form>"
        + (f"<h3>Topics found</h3><ul class='topics'>{topic_items}</ul>" if topics else "")
        + (f"<h3>Search your materials</h3><form method='get' action='/subjects/{sid}/search' class='row'>"
           "<input type='text' name='q' maxlength='200' aria-label='Search' placeholder='e.g. binary tree traversal' required>"
           "<button class='btn' style='margin:0'>Search</button></form>" if documents else "")
    )


def mcq_section(subject_id: int, csrf: str, topics: list[dict], bank_size: int, *, has_material: bool,
                error: str | None = None) -> str:
    sid = int(subject_id)
    if not has_material:
        return ("<h2>Multiple-choice questions</h2><p class='note'>Upload some material first. Questions are written only from what you "
                "upload to this subject.</p>")
    options = "<option value=''>Whole subject</option>" + "".join(
        f"<option value='{int(t['id'])}'>{esc(t['path'])} ({int(t['chunks'])} passages)</option>" for t in topics if t["chunks"])
    return (
        "<h2>Multiple-choice questions</h2>"
        "<p class='note'>Four-option questions written from this subject's materials only. Every question keeps the exact words it is "
        "based on, is checked by the app, and is answered independently before it is kept. Nothing is made up if no model is available.</p>"
        + error_box(error)
        + f"<form method='post' action='/subjects/{sid}/mcq/generate'>{csrf_field(csrf)}"
        "<label for='topic'>Topic</label>"
        f"<select id='topic' name='topic'>{options}</select>"
        "<label for='count'>How many (1 to 10)</label>"
        "<input type='number' id='count' name='count' min='1' max='10' value='5' required style='width:6rem'>"
        "<button class='btn'>Generate questions</button></form>"
        f"<p class='note'><a href='/subjects/{sid}/mcq'>Open the question bank</a> ({int(bank_size)} question{'s' if bank_size != 1 else ''})</p>"
    )


def mcq_card(sid: int, item: dict, n: int, csrf: str | None = None) -> str:
    letters = "ABCD"
    opts = "".join(f"<li>{esc(o)}</li>" for o in item["options"])
    answer = f"{letters[item['answer_index']]}) {item['options'][item['answer_index']]}"
    source = (esc(item["doc_title"]) + (f" &middot; section: {esc(item['heading_path'])}" if item["heading_path"] else "")
              + (f" &middot; {esc(_where(item['page_start'], item['page_end']))}" if item["page_start"] is not None else ""))
    checked = ("&#10003; Answered correctly by an independent reader who saw only the passages, not the key."
               if item["solver"] == "agreed" else "Not independently checked (the reader step was unavailable).")
    delete = (f"<form method='post' action='/subjects/{sid}/mcq/{int(item['id'])}/delete' style='margin-top:.5rem'>{csrf_field(csrf)}"
              "<button class='btn btn-sec' style='margin:0'>Delete this question</button></form>") if csrf else ""
    return (f"<div class='card' id='q{int(item['id'])}'><b>{n}. {esc(item['question'])}</b>"
            f"<ol type='A' class='opts'>{opts}</ol>"
            f"<details><summary>Show answer and source</summary>"
            f"<div class='note ok'><b>Correct answer: {esc(answer)}</b></div>"
            + (f"<div>{esc(item['explanation'])}</div>" if item["explanation"] else "")
            + f"<div class='note'>Source: {source}</div><blockquote>{esc(item['quote'])}</blockquote>"
            f"<div class='note ok'>&#10003; These exact words were found in your material (checked by the app).</div>"
            f"<div class='note ok'>{checked}</div></details>{delete}</div>")


def mcq_bank_page(subject: dict, items: list[dict], topics: list[dict], current_topic: int | None, csrf: str) -> str:
    sid = int(subject["id"])
    tabs = "".join(
        f"<a href='/subjects/{sid}/mcq?topic={int(t['id'])}'>{'<b>' if t['id'] == current_topic else ''}{esc(t['path'])}{'</b>' if t['id'] == current_topic else ''}</a> &middot; "
        for t in topics if t["chunks"])
    body = "".join(mcq_card(sid, it, i, csrf) for i, it in enumerate(items, start=1)) or (
        "<p class='note'>No questions yet. Use <b>Generate questions</b> on the subject page.</p>")
    return (f"<p class='note'><a href='/subjects/{sid}'>&larr; {esc(subject['name'])}</a></p><h1>Question bank</h1>"
            f"<p class='sub'>{len(items)} multiple-choice question{'s' if len(items) != 1 else ''}. Answers are hidden until you open them.</p>"
            f"<p class='note'><a href='/subjects/{sid}/mcq'>All topics</a> &middot; {tabs}</p>{body}")


def mcq_job_page(subject: dict, job: dict, items: list[dict], trace: list[dict], csrf: str) -> str:
    sid, jid = int(subject["id"]), int(job["id"])
    head = f"<p class='note'><a href='/subjects/{sid}'>&larr; {esc(subject['name'])}</a></p><h1>Writing questions</h1><p class='sub'>{esc(job['scope'])}</p>"
    if job["status"] == "pending":
        return ("<meta http-equiv='refresh' content='4'>" + head +
                "<div class='card'><b>Reading your materials and writing questions…</b><div class='note'>A model running on this computer "
                "writes each batch and then a second pass answers every question without seeing the key. This can take a few minutes. "
                "This page refreshes by itself.</div></div>")
    label = {"done": "Finished", "failed": "Could not finish"}[job["status"]]
    body = (f"<p><span class='badge {'ok' if job['produced'] else ''}'>{label}: {int(job['produced'])} of {int(job['requested'])} questions kept</span></p>")
    if job["reason"]:
        body += f"<div class='warn'>{esc(job['reason'])}</div>"
    if job["rejected"]:
        body += (f"<p class='note'>{int(job['rejected'])} candidate question{'s' if job['rejected'] != 1 else ''} failed a check and "
                 f"{'were' if job['rejected'] != 1 else 'was'} not kept.</p>")
    cards = "".join(mcq_card(sid, it, i, csrf) for i, it in enumerate(items, start=1))
    steps = "".join(f"<div class='step'>{esc(mcq_step_text(s))}</div>" for s in trace)
    return (head + body + cards + f"<p><a href='/subjects/{sid}/mcq'>Open the question bank</a></p>"
            + (f"<details><summary>How these were produced</summary><p class='note'>Every step is recorded in an append-only log. "
               f"Models propose; the app checks and decides.</p>{steps}</details>" if steps else ""))


def subject_page(subject: dict, csrf: str, *, error: str | None = None, documents: list[dict] | None = None,
                 topics: list[dict] | None = None, upload_error: str | None = None, doubts: list[dict] | None = None,
                 ask_error: str | None = None, question: str = "", bank_size: int = 0, mcq_error: str | None = None) -> str:
    sid = int(subject["id"])
    made = time.strftime("%Y-%m-%d", time.localtime(subject["created_at"]))
    return (
        f"<p class='note'><a href='/subjects'>&larr; All subjects</a></p>"
        f"<h1>{esc(subject['name'])}</h1>"
        f"<p class='sub'>{esc(subject['description']) or 'No description.'} &middot; created {made}</p>"
        + ask_section(sid, csrf, doubts or [], has_material=any(d["chunks"] for d in (documents or [])),
                      error=ask_error, question=question)
        + mcq_section(sid, csrf, topics or [], bank_size, has_material=any(d["chunks"] for d in (documents or [])), error=mcq_error)
        + materials_section(sid, documents or [], topics or [], csrf, upload_error=upload_error)
        + "<div class='card'><b>Quizzes and progress</b><div class='note'>Arrive in the next phases.</div></div>"
        f"<h2>Rename or describe</h2>{error_box(error)}"
        f"<form method='post' action='/subjects/{sid}/edit'>{csrf_field(csrf)}"
        f"<label for='name'>Name</label><input type='text' id='name' name='name' maxlength='80' value='{esc(subject['name'])}' required>"
        f"<label for='description'>Description</label>"
        f"<textarea id='description' name='description' maxlength='500'>{esc(subject['description'])}</textarea>"
        "<button class='btn'>Save</button></form>"
        "<h2>Delete this subject</h2>"
        "<p class='note'>This permanently deletes the subject and everything inside it.</p>"
        f"<form method='post' action='/subjects/{sid}/delete'>{csrf_field(csrf)}"
        "<label><input type='checkbox' name='confirm' value='yes'> I understand this cannot be undone</label>"
        "<button class='btn btn-bad'>Delete subject</button></form>"
    )


def document_page(subject: dict, doc: dict, chunks: list[dict], csrf: str, *, notice: str | None = None) -> str:
    sid = int(subject["id"])
    items = "".join(
        f"<div class='card' id='c{int(c['id'])}'><div class='note'>#{int(c['ordinal']) + 1}"
        + (f" &middot; {esc(c['heading_path'])}" if c["heading_path"] else "")
        + (f" &middot; {esc(_where(c['page_start'], c['page_end']))}" if c["page_start"] is not None else "")
        + (f"</div><div class='warn'>Not used for answers: reads like instructions to an AI ({esc(c['flag_reason'])}).</div>"
           "<div class='passage'>" if c.get("quarantined") else "</div><div class='passage'>")
        + f"{esc(c['text'])}</div></div>" for c in chunks)
    return (
        f"<p class='note'><a href='/subjects/{sid}'>&larr; {esc(subject['name'])}</a></p>"
        f"<h1>{esc(doc['title'])}</h1>"
        f"<p class='sub'>{esc(doc['kind']).upper()} &middot; {esc(doc['source'])} &middot; "
        + (f"{int(doc['pages'])} pages &middot; " if doc["pages"] else "")
        + f"{int(doc['chunks'])} passages &middot; {esc(doc['status'])}</p>"
        + (f"<div class='warn'>{esc(notice)}</div>" if notice else "") + _warnings(doc["warnings"])
        + (items or "<p class='note'>Nothing could be extracted from this file.</p>")
        + "<h2>Remove this material</h2><p class='note'>Its passages disappear from search, questions and quizzes.</p>"
        f"<form method='post' action='/subjects/{sid}/materials/{int(doc['id'])}/delete'>{csrf_field(csrf)}"
        "<button class='btn btn-bad'>Remove material</button></form>"
    )


def highlight(text: str, matched: list[str]) -> str:
    """Escaped text with the matched search words wrapped in <mark>. Escaping happens per piece, before any tag is added."""
    keys = [m.lower() for m in matched if m]
    if not keys:
        return esc(text)

    def hit(word: str) -> bool:
        w = word.lower()
        return any(w == k or (len(k) >= 4 and w.startswith(k[: max(4, len(k) - 2)])) for k in keys)

    out = []
    for m in _TOKEN.finditer(text):
        piece = m.group()
        out.append(f"<mark>{esc(piece)}</mark>" if piece[0].isalnum() and hit(piece) else esc(piece))
    return "".join(out)


_TOKEN = re.compile(r"[^\W_]+|[\W_]+", re.UNICODE)


def _passage_card(sid: int, r, *, link: bool = True, note: str = "") -> str:
    get = (lambda k: r[k])
    title = (f"<a href='/subjects/{sid}/materials/{int(get('document_id'))}#c{int(get('id'))}'>{esc(get('doc_title'))}</a>"
             if link and get("document_id") else esc(get("doc_title")))
    return ("<div class='card'><div class='note'>" + title
            + (f" &middot; {esc(get('heading_path'))}" if get("heading_path") else "")
            + (f" &middot; {esc(_where(get('page_start'), get('page_end')))}" if get("page_start") is not None else "")
            + (f" &middot; matched: {esc(', '.join(get('matched')))}" if get("matched") else "") + note
            + f"</div><div class='passage'>{highlight(get('text'), list(get('matched') or []))}</div></div>")


def search_page(subject: dict, query: str, results: list) -> str:
    """`results` are retrieval.Hit objects: the ones that match enough of the words first, weak ones labelled."""
    sid = int(subject["id"])
    strong = [r for r in results if r.relevant]
    weak = [r for r in results if not r.relevant]
    body = "".join(_passage_card(sid, r) for r in strong)
    if not strong and weak:
        body += ("<p class='note'>No passage matches most of your words. These contain only some of them, so they may not "
                 "be about your topic:</p>")
    elif weak:
        body += "<h3>Weaker matches</h3>"
    body += "".join(_passage_card(sid, r) for r in weak[: 3])
    return (
        f"<p class='note'><a href='/subjects/{sid}'>&larr; {esc(subject['name'])}</a></p><h1>Search</h1>"
        f"<form method='get' action='/subjects/{sid}/search' class='row'>"
        f"<input type='text' name='q' maxlength='200' value='{esc(query)}' aria-label='Search' required>"
        "<button class='btn' style='margin:0'>Search</button></form>"
        + (body or "<p class='note'>No passage in this subject matches. Nothing is guessed: try other words, "
                   "or upload material that covers it.</p>")
    )


# ---------------------------------------------------------------------------------------------- questions

_STATUS = {
    "pending": ("Working on it", ""),
    "answered": ("Answered from your materials", "ok"),
    "abstained": ("Not answered: nothing was guessed", ""),
    "extractive": ("No model: matching passages only", ""),
    "failed": ("Something went wrong", ""),
}


def ask_section(subject_id: int, csrf: str, doubts: list[dict], *, has_material: bool, error: str | None = None,
                question: str = "") -> str:
    sid = int(subject_id)
    if not has_material:
        return ("<h2>Ask a question</h2><p class='note'>Upload some material first. Answers are written only from what you "
                "upload to this subject.</p>")
    history = "".join(
        f"<div class='card'><a href='/subjects/{sid}/questions/{int(d['id'])}'>{esc(d['question'])}</a>"
        f"<div class='note'>{esc(_STATUS.get(d['status'], (d['status'], ''))[0])}"
        + (f" &middot; marked \"{esc(d['feedback'])}\"" if d.get("feedback") else "") + "</div></div>" for d in doubts)
    return (
        "<h2>Ask a question</h2>"
        "<p class='note'>The answer is written only from this subject's materials, and every statement shows the exact words "
        "it rests on. If your materials do not cover it, it says so instead of guessing.</p>"
        + error_box(error)
        + f"<form method='post' action='/subjects/{sid}/ask'>{csrf_field(csrf)}"
        "<label for='question'>Your question</label>"
        f"<textarea class='ask' id='question' name='question' maxlength='500' required>{esc(question)}</textarea>"
        "<button class='btn'>Ask</button></form>"
        + (f"<h3>Your recent questions</h3>{history}" if history else "")
    )


def _cite_labels(claims: list[dict]) -> tuple[list[dict], dict]:
    """Unique (chunk, quote) pairs in order of first use, and a lookup so each statement can show [1][2]."""
    uniq: list[dict] = []
    index: dict = {}
    for c in claims:
        for cit in c["citations"]:
            key = (cit["chunk_id"], cit["quote"])
            if key not in index:
                uniq.append(cit)
                index[key] = len(uniq)
    return uniq, index


def trace_section(trace: list[dict]) -> str:
    if not trace:
        return ""
    items = "".join(f"<div class='step'>{esc(step_text(s))}</div>" for s in trace)
    return ("<details><summary>How this was produced</summary>"
            "<p class='note'>Every step is recorded in an append-only log. Models propose; the app checks and decides.</p>"
            f"{items}</details>")


def _verification(d: dict, trace: list[dict]) -> str:
    rows = verification_rows(d["claims"], d["dropped"], trace)
    return "<h2>Verification</h2>" + "".join(f"<div class='step ok'>&#10003; {esc(r)}</div>" for r in rows)


def doubt_page(subject: dict, d: dict, trace: list[dict], csrf: str) -> str:
    sid, did = int(subject["id"]), int(d["id"])
    label, cls = _STATUS.get(d["status"], (d["status"], ""))
    head = (f"<p class='note'><a href='/subjects/{sid}'>&larr; {esc(subject['name'])}</a></p>"
            f"<h1>{esc(d['question'])}</h1><p><span class='badge {cls}'>{esc(label)}</span></p>")
    if d["status"] == "pending":
        return ("<meta http-equiv='refresh' content='4'>" + head +
                "<div class='card'><b>Reading your materials and writing an answer…</b><div class='note'>"
                "A model that runs on this computer can take a minute or two. This page refreshes by itself; you can also "
                "leave and come back from the subject page.</div></div>")
    body = ""
    if d["status"] == "answered":
        uniq, index = _cite_labels(d["claims"])
        conflict = d.get("kind") == "conflict"
        items = "".join(
            f"<li>{esc(c['text'])}" + "".join(f"<a class='cite' href='#s{index[(x['chunk_id'], x['quote'])]}'>[{index[(x['chunk_id'], x['quote'])]}]</a>"
                                             for x in c["citations"]) + "</li>" for c in d["claims"])
        cards = ""
        for n, x in enumerate(uniq, start=1):
            cards += (f"<div class='card' id='s{n}'><div class='note'><b>[{n}]</b> {esc(x['doc_title'])}"
                      + (f" &middot; section: {esc(x['heading_path'])}" if x["heading_path"] else "")
                      + (f" &middot; {esc(_where(x['page_start'], x['page_end']))}" if x["page_start"] is not None else "")
                      + f"</div><blockquote>{esc(x['quote'])}</blockquote>"
                      "<div class='note ok'>&#10003; These exact words were found in your material (checked by the app).</div></div>")
        body += ("<h2>Your materials disagree</h2><p class='note'>Two passages say different things. Each side is shown with its own "
                 "quote; the app does not pick a winner.</p>" if conflict else "<h2>Answer</h2>")
        body += f"<ol class='claims'>{items}</ol>"
        if d["dropped"]:
            body += (f"<div class='warn'>{int(d['dropped'])} other statement{'s' if d['dropped'] != 1 else ''} the model wrote "
                     "could not be verified against your materials and "
                     f"{'were' if d['dropped'] != 1 else 'was'} left out.</div>")
        body += ("<h2>Sources and evidence</h2><p class='note'>Each source shows the file, the section and the PDF page, and the "
                 "exact words the answer rests on. The app checks that the words exist in your material; it cannot check that a "
                 "statement reads them correctly, so read the quote.</p>" + cards)
        if d.get("explanation"):
            body += ("<h2>Explanation, step by step</h2><div class='card'>" f"<div>{esc(d['explanation'])}</div>"
                     "<div class='note'>The model's own reasoning. It passed simple checks (no invented numbers, follows the "
                     "quotes) but is not verified word for word.</div></div>")
        body += _verification(d, trace) + f"<p class='note'>Written by {esc(d['model'] or d['tier'])} ({esc(d['tier'])}).</p>"
    else:
        if d["reason"]:
            body += f"<div class='warn'>{esc(d['reason'])}</div>"
        if d["sources"]:
            body += ("<h2>" + ("Passages that match" if d["status"] == "extractive" else "Closest passages") + "</h2>"
                     "<p class='note'>These are your own words from your materials, shown exactly as stored.</p>"
                     + "".join(_passage_card(sid, {**s, "document_id": None}, link=False) for s in d["sources"]))
        if d["status"] == "abstained":
            body += "<p class='note'>Try different words, or upload material that covers this.</p>"
    fb = ""
    if d["status"] == "answered":
        fb = (f"<form method='post' action='/subjects/{sid}/questions/{did}/feedback' class='row'>{csrf_field(csrf)}"
              "<button class='btn btn-sec' name='value' value='helpful'>This helped</button>"
              "<button class='btn btn-sec' name='value' value='wrong'>This looks wrong</button>"
              + (f"<span class='note'>You marked this &quot;{esc(d['feedback'])}&quot;.</span>" if d.get("feedback") else "")
              + "</form>")
    return (head + body + fb + trace_section(trace)
            + f"<form method='post' action='/subjects/{sid}/questions/{did}/delete'>{csrf_field(csrf)}"
              "<button class='btn btn-sec'>Delete this question</button></form>")


def account_page(user: dict, csrf: str, *, key_configured: bool, allowed: list[str], notice: str | None = None) -> str:
    on = bool(user["cloud_consent"])
    return (
        f"<h1>Account</h1><p class='sub'>Signed in as <b>{esc(user['username'])}</b></p>"
        + (f"<div class='warn'>{esc(notice)}</div>" if notice else "")
        + "<h2>Cloud models</h2>"
        "<p>Questions are answered by a model running on this computer first. If that fails, the app can ask a cloud model "
        "(OpenRouter) instead.</p>"
        "<p><b>If you allow this, the passages found for your question (a few paragraphs, never your whole files) are sent to "
        "OpenRouter and the model provider.</b> If you do not, nothing ever leaves this computer.</p>"
        f"<p class='note'>Cloud key configured on the server: <b>{'yes' if key_configured else 'no'}</b>"
        + (" &middot; allowed models: " + esc(", ".join(allowed)) if allowed else "") + "</p>"
        f"<form method='post' action='/account/cloud'>{csrf_field(csrf)}"
        f"<label><input type='checkbox' name='consent' value='yes'{' checked' if on else ''}> "
        "Allow cloud models as a fallback for my questions</label>"
        "<button class='btn'>Save</button></form>"
        "<p><a href='/subjects'>&larr; Your subjects</a></p>"
    )


def not_found() -> str:
    return "<h1>Not found</h1><p class='sub'>That page does not exist, or it is not yours.</p><p><a href='/subjects'>Your subjects</a></p>"


# ============================================================= Phase C — Quiz UI

def _state_bar(answered: int, total: int, correct: int) -> str:
    pct = int(100 * answered / total) if total else 0
    return (
        f"<div style='margin:.5rem 0 1rem'>"
        f"<div style='height:8px;background:var(--border);border-radius:4px'>"
        f"<div style='height:8px;width:{pct}%;background:var(--accent);border-radius:4px;transition:width .3s'></div>"
        f"</div>"
        f"<p class='note'>{answered}/{total} answered &middot; {correct} correct</p>"
        f"</div>"
    )


def _proctor_js(subject_id: int, attempt_id: int, nonce: str, csrf: str) -> str:
    """The quiz page's only script. It runs because the response's CSP carries this nonce; it sends the session token."""
    token = __import__("json").dumps(csrf)
    return (
        f"<script nonce='{esc(nonce)}'>"
        f"(function(){{"
        f"var sid={subject_id},aid={attempt_id};"
        f"function log(type,sev,detail){{"
        f"fetch('/subjects/'+sid+'/quiz/attempt/'+aid+'/proctor',{{"
        f"method:'POST',headers:{{'Content-Type':'application/json','X-CSRF-Token':{token}}},"
        f"body:JSON.stringify({{event_type:type,details:detail||{{}}}})}})}}"
        f"document.addEventListener('visibilitychange',function(){{if(document.hidden)log('tab_switch',60,{{}});}});"
        f"document.addEventListener('fullscreenchange',function(){{if(!document.fullscreenElement)log('full_screen_exit',30,{{}});}});"
        f"document.addEventListener('copy',function(e){{e.preventDefault();log('copy_attempt',20,{{}});}});"
        f"document.addEventListener('paste',function(e){{e.preventDefault();log('paste_attempt',20,{{}});}});"
        f"var _t0=Date.now(),_hes=0,_chosen=null;"
        f"document.querySelectorAll('input[name=chosen]').forEach(function(r){{"
        f"r.addEventListener('change',function(){{if(_chosen!==null)_hes++;_chosen=this.value;}});}});"
        f"var _form=document.querySelector('form.qform');"
        f"if(_form)_form.addEventListener('submit',function(){{"
        f"var rt=((Date.now()-_t0)/1000).toFixed(1);"
        f"document.getElementById('rt').value=rt;"
        f"document.getElementById('hes').value=_hes;}});"
        f"}})();"
        f"</script>"
    )


def quiz_home_page(subject: dict, topics: list, items_count: int,
                   attempts: list, weaks: list, active_attempt, csrf: str) -> str:
    import time as _t
    sid = subject["id"]
    parts = [
        f"<h1>Quiz &mdash; {esc(subject['name'])}</h1>",
        f"<p class='sub'>{items_count} questions in the bank &middot; "
        f"<a href='/subjects/{sid}/progress'>View progress</a> &middot; "
        f"<a href='/subjects/{sid}'>&larr; Subject</a></p>",
    ]
    if active_attempt:
        parts.append(
            f"<div class='warn'>You have an active quiz in progress. "
            f"<a href='/subjects/{sid}/quiz/attempt/{active_attempt['id']}'>Continue</a> "
            f"or start a new one below (will abandon current).</div>"
        )
    if items_count == 0:
        parts.append("<div class='error'>No questions yet. Generate some on the subject page first.</div>")
    else:
        parts.append(
            f"<form method='post' action='/subjects/{sid}/quiz/start'>{csrf_field(csrf)}"
            f"<label>Topic (optional — leave blank for whole subject)</label>"
            f"<select name='topic_id'><option value=''>Whole subject</option>"
            + "".join(f"<option value='{t['id']}'>{esc(t['path'])}</option>" for t in topics)
            + "</select>"
            f"<button class='btn' style='margin-left:.5rem'>Start quiz</button>"
            f"</form>"
        )
    if weaks:
        parts.append("<h2>Weak topics (review these)</h2><ul class='topics'>")
        for w in weaks:
            pct = round(w["mastery"] * 100)
            parts.append(f"<li>{esc(w['name'])} &mdash; {pct}% mastery ({w['answered']} answered)</li>")
        parts.append("</ul>")
    if attempts:
        parts.append("<h2>Recent attempts</h2>")
        for a in attempts:
            started = _t.strftime("%d %b %H:%M", _t.localtime(a["started_at"])) if a.get("started_at") else ""
            c, mx = int(a.get("correct_answers", 0)), int(a.get("max_score", 0) or 0)
            status = "active" if a["is_active"] else "done"
            link = (f"<a href='/subjects/{sid}/quiz/attempt/{a['id']}'>Continue</a>"
                    if a["is_active"] else f"<a href='/subjects/{sid}/quiz/result/{a['id']}'>Details</a>")
            parts.append(
                f"<div class='card'><b>{started}</b> &middot; {c}/{mx if mx else '?'} correct &middot; "
                f"<span class='badge'>{status}</span> {link}</div>"
            )
    return "".join(parts)


def quiz_question_page(subject: dict, attempt: dict, question_row, opts: list,
                       csrf: str, *, error: str = "", nonce: str = "") -> str:
    sid = subject["id"]
    aid = attempt["id"]
    answered = attempt.get("correct_answers", 0) + attempt.get("incorrect_answers", 0)
    total    = max(1, int(attempt.get("max_score", 0) or 1))
    correct  = attempt.get("correct_answers", 0)
    letters  = ["A", "B", "C", "D"]
    opts_html = "".join(
        f"<li style='margin:.4rem 0'>"
        f"<label style='font-weight:400;cursor:pointer'>"
        f"<input type='radio' name='chosen' value='{i}' style='margin-right:.5rem'>"
        f"<b>{letters[i]}.</b> {esc(o)}"
        f"</label></li>"
        for i, o in enumerate(opts[:4])
    )
    return (
        f"<h1>Quiz &mdash; {esc(subject['name'])}</h1>"
        + _state_bar(answered, total, int(correct))
        + error_box(error)
        + f"<div class='card'>"
        f"<p class='note'>{esc(question_row['topic_path'] or '')}</p>"
        f"<p><b>{esc(question_row['question'])}</b></p>"
        f"<form class='qform' method='post' action='/subjects/{sid}/quiz/attempt/{aid}/answer'>"
        f"{csrf_field(csrf)}"
        f"<input type='hidden' name='item_id' value='{question_row['item_id']}'>"
        f"<input type='hidden' name='answer_row_id' value='{question_row['answer_row_id']}'>"
        f"<input type='hidden' id='rt' name='response_time' value='0'>"
        f"<input type='hidden' id='hes' name='hesitations' value='0'>"
        f"<ul style='list-style:none;padding:0;margin:.5rem 0'>{opts_html}</ul>"
        f"<button class='btn'>Submit answer</button>"
        f"</form>"
        f"</div>"
        + (_proctor_js(sid, aid, nonce, csrf) if nonce else "")
    )


def quiz_diagnostic_page(subject: dict, attempt: dict, result, csrf: str, nonce: str = "") -> str:
    sid = subject["id"]
    aid = attempt["id"]
    return (
        f"<h1>Diagnostic &mdash; {esc(subject['name'])}</h1>"
        f"<p class='sub'>All multiple-choice questions done. "
        f"Answer this to confirm understanding of <b>{esc(result.topic_name)}</b>.</p>"
        + (f"<div class='warn'>&times; Your last answer was not sufficient. Try again.</div>" if result.verdict == "BLOCK" else "")
        + f"<div class='card'>"
        f"<p><b>{esc(result.question)}</b></p>"
        f"<form method='post' action='/subjects/{sid}/quiz/attempt/{aid}/diagnostic/answer'>"
        f"{csrf_field(csrf)}"
        f"<input type='hidden' name='topic_id' value='{result.topic_id or 0}'>"
        f"<input type='hidden' name='question' value='{esc(result.question)}'>"
        f"<label>Your answer</label>"
        f"<textarea name='answer' class='ask' required placeholder='Explain in your own words&hellip;'></textarea>"
        f"<button class='btn'>Submit</button>"
        f"</form>"
        f"</div>"
        + (_proctor_js(sid, aid, nonce, csrf) if nonce else "")
    )


def quiz_callback_page(subject: dict, attempt: dict, csrf: str) -> str:
    sid = subject["id"]
    aid = attempt["id"]
    depth    = attempt.get("depth", 0)
    stack    = attempt.get("topic_stack", [])
    topic_id = stack[-1] if stack else None
    verdicts = attempt.get("verdict_log", [])
    last     = next((v for v in reversed(verdicts) if v.get("topic_id") == topic_id), {})
    objs     = last.get("objections", [])
    prereq_id = last.get("prerequisite_id")
    obj_html = "".join(f"<li>{esc(o)}</li>" for o in objs) or "<li>No specific objections recorded.</li>"
    return (
        f"<h1>Prerequisite Check &mdash; {esc(subject['name'])}</h1>"
        f"<p class='sub'>Depth: {depth}/3</p>"
        f"<div class='card'>"
        f"<p>Your answer did not fully demonstrate understanding. The evaluator noted:</p>"
        f"<ul>{obj_html}</ul>"
        f"<p>What would you like to do?</p>"
        f"<form method='post' action='/subjects/{sid}/quiz/attempt/{aid}/callback'>"
        f"{csrf_field(csrf)}"
        f"<div class='row' style='margin-top:.8rem'>"
        + (f"<button class='btn' name='decision' value='step_back'>&larr; Go to prerequisite topic</button>" if prereq_id else "")
        + f"<button class='btn btn-sec' name='decision' value='retry'>Try this topic again</button>"
        f"</div></form></div>"
    )


def quiz_result_page(subject: dict, attempt: dict, answers: list,
                     proctor: dict, weaks: list, csrf: str) -> str:
    sid      = subject["id"]
    correct  = attempt.get("correct_answers", 0)
    incorrect = attempt.get("incorrect_answers", 0)
    total    = correct + incorrect
    pct      = round(100 * correct / total) if total else 0
    trust    = proctor.get("trust_score", 100)
    bscore   = round(attempt.get("behavior_score", 100))
    tc       = "var(--ok)" if trust >= 80 else ("var(--bad)" if trust < 50 else "#d97706")

    rows_html = ""
    for a in answers:
        if a.get("chosen_index") is None:
            continue
        ok     = bool(a.get("is_correct"))
        colour = "var(--ok)" if ok else "var(--bad)"
        mark   = "&check;" if ok else "&times;"
        opts_list = a.get("options", [])
        ci  = a.get("chosen_index", -1)
        ai  = a.get("answer_index", -1)
        chosen  = opts_list[ci] if 0 <= ci < len(opts_list) else "—"
        correct_opt = opts_list[ai] if 0 <= ai < len(opts_list) else "—"
        rows_html += (
            f"<div class='card' style='border-left:4px solid {colour}'>"
            f"<p style='margin:0'><b>{esc(a.get('question',''))}</b></p>"
            f"<p class='note' style='margin:.3rem 0'>Topic: {esc(a.get('topic_name',''))}</p>"
            f"<p style='margin:.3rem 0;color:{colour}'>{mark} You: {esc(chosen)}"
            + (f"</p><p class='note'>Correct: {esc(correct_opt)}</p>" if not ok else "</p>")
            + (f"<p class='note'>{esc(a.get('explanation',''))}</p>" if a.get("explanation") else "")
            + "</div>"
        )

    weaks_html = ""
    if weaks:
        weaks_html = "<h2>Topics to review</h2><ul class='topics'>"
        weaks_html += "".join(f"<li>{esc(w['name'])} &mdash; {round(w['mastery']*100)}% mastery</li>" for w in weaks)
        weaks_html += "</ul>"

    return (
        f"<h1>Result &mdash; {esc(subject['name'])}</h1>"
        f"<div class='card'>"
        f"<p><b>MCQ score:</b> {correct}/{total} ({pct}%)</p>"
        f"<p><b>Behavior score:</b> {bscore}/100</p>"
        f"<p><b>Trust score:</b> <span style='color:{tc}'>{trust}/100</span></p>"
        f"<p class='note'>Tab switches: {proctor.get('total_tab_switches',0)} &middot; "
        f"Fullscreen exits: {proctor.get('total_fullscreen_exits',0)} &middot; "
        f"Copy attempts: {proctor.get('total_copy_attempts',0)}</p>"
        f"</div>"
        + weaks_html
        + (f"<h2>Question breakdown</h2>{rows_html}" if rows_html else "")
        + f"<p style='margin-top:1.5rem'>"
        f"<a href='/subjects/{sid}/quiz'>Take another quiz</a> &middot; "
        f"<a href='/subjects/{sid}/progress'>View progress</a> &middot; "
        f"<a href='/subjects/{sid}'>&larr; Subject</a></p>"
    )


def progress_page(subject: dict, progress: list, prereqs: list, topics: list, csrf: str) -> str:
    sid = subject["id"]
    STATE_COLOUR = {"mastered": "var(--ok)", "weak": "var(--bad)",
                    "learning": "#d97706", "unknown": "var(--muted)"}
    muted = "var(--muted)"
    rows = "".join(
        f"<tr>"
        f"<td style='padding:.3rem .5rem'>{esc(p['name'])}</td>"
        f"<td style='padding:.3rem .5rem;text-align:center'>{p['answered']}</td>"
        f"<td style='padding:.3rem .5rem;text-align:center'>{p['correct']}</td>"
        f"<td style='padding:.3rem .5rem;color:{STATE_COLOUR.get(p['state'], muted)}'"
        f"><b>{round(p['mastery']*100)}%</b> ({p['state']})</td>"
        f"</tr>"
        for p in progress
    )
    table = (
        f"<table style='width:100%;border-collapse:collapse;font-size:.92rem'>"
        f"<thead><tr style='border-bottom:1px solid var(--border)'>"
        f"<th style='text-align:left;padding:.3rem .5rem'>Topic</th>"
        f"<th style='padding:.3rem .5rem'>Answered</th>"
        f"<th style='padding:.3rem .5rem'>Correct</th>"
        f"<th style='text-align:left;padding:.3rem .5rem'>Mastery</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    ) if rows else "<p class='sub'>No answers yet &mdash; take a quiz first.</p>"

    prereq_rows = "".join(
        f"<div class='card' style='display:flex;justify-content:space-between;align-items:center'>"
        f"<span>{esc(pr['topic_name'])} requires &rarr; {esc(pr['prereq_name'])}</span>"
        f"<form method='post' action='/subjects/{sid}/prereq/delete' style='margin:0'>"
        f"{csrf_field(csrf)}"
        f"<input type='hidden' name='topic_id' value='{pr['topic_id']}'>"
        f"<input type='hidden' name='prereq_id' value='{pr['prereq_id']}'>"
        f"<button class='btn btn-bad' style='margin:0;padding:.3rem .8rem;font-size:.85rem'>Remove</button>"
        f"</form></div>"
        for pr in prereqs
    )
    topic_opts = "".join(
        f"<option value='{t['id']}'>{esc(t['path'])}</option>" for t in topics if t.get("chunks")
    )
    add_form = (
        f"<form method='post' action='/subjects/{sid}/prereq/set' style='margin-top:.8rem'>"
        f"{csrf_field(csrf)}"
        f"<div class='row'>"
        f"<select name='topic_id'><option value=''>Topic</option>{topic_opts}</select>"
        f"<span style='padding:.4rem'>requires &rarr;</span>"
        f"<select name='prereq_id'><option value=''>Prerequisite</option>{topic_opts}</select>"
        f"<button class='btn'>Add</button>"
        f"</div></form>"
    ) if topic_opts else ""

    return (
        f"<h1>Progress &mdash; {esc(subject['name'])}</h1>"
        f"<p class='sub'><a href='/subjects/{sid}/quiz'>Take a quiz</a> &middot; "
        f"<a href='/subjects/{sid}'>&larr; Subject</a></p>"
        f"<h2>Topic mastery</h2>{table}"
        f"<h2>Prerequisite graph</h2>"
        + (prereq_rows or "<p class='sub'>No prerequisites set.</p>")
        + add_form
    )
