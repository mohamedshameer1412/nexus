"""A run's history, made readable.

The execution trace is not a log written for the demo. It is the run's own
record - the same rows the state machine reads to decide what to do next - so
what you see is what the system actually did, and it can be rebuilt at any time
from the database, including for a run whose process died last week.
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass, field

from slice.store import Store

from . import checks
from .schema import LETTERS

_ANSI = {"ok": "\033[32m", "warn": "\033[33m", "bad": "\033[31m", "dim": "\033[2m",
         "info": "\033[1m"}
_RESET = "\033[0m"

_REASONS = {
    "max_revisions": "The validator still rejected the draft after {revisions} revisions, "
                     "which is the limit.",
    "repeated_output": "The generator produced the same draft twice, so another revision "
                       "would change nothing.",
}


@dataclass
class Event:
    seq: int
    kind: str
    title: str
    lines: list[str] = field(default_factory=list)
    tone: str = "info"          # ok | warn | bad | info | dim


# ------------------------------------------------------------------ pieces

def render_pack(pack: dict, source: str | None = None) -> list[str]:
    """A study pack as text. With the source, each quote is re-verified HERE -
    the marker is a fact recomputed from the source, not something stored."""
    out = [f"Title: {pack['title']}", "Notes:"]
    out += [f"  - {n}" for n in pack["notes"]]
    out.append("Questions:")
    for i, q in enumerate(pack["questions"], 1):
        out.append(f"  Q{i}. {q['question']}")
        for letter, opt in zip(LETTERS, q["options"]):
            out.append(f"      {letter}. {opt}" + ("   <-- answer" if letter == q["answer"] else ""))
        out.append(f"      why: {q['explanation']}")
        cite = f"      source: \"{q['source_quote']}\""
        if source is not None:
            found, para = checks.locate_quote(source, q["source_quote"])
            cite += ("   [verified in source" + (f", paragraph {para}" if para else "") + "]"
                     if found else "   [NOT FOUND IN SOURCE]")
        out.append(cite)
    return out


def render_issues(issues: list[dict]) -> list[str]:
    return [f"  x [{i['origin']}] {i['where']}: {i['code']} - {i['detail']}" for i in issues]


def _preview(text: str, limit: int = 320) -> list[str]:
    flat = " ".join(text.split())
    return [flat if len(flat) <= limit else flat[:limit].rstrip() + " ..."]


# ------------------------------------------------------------------ the trace

def build(store: Store, run_id: str) -> list[Event]:
    versions = store.replay(run_id)
    source = next((v.payload["text"] for v in versions if v.kind == "input"), None)
    events: list[Event] = []
    drafts = 0

    for v in versions:
        p = v.payload
        if v.kind == "input":
            events.append(Event(v.seq, "input", f"SOURCE  ({len(p['text'].split())} words)",
                                _preview(p["text"]), "info"))

        elif v.kind == "draft":
            drafts += 1
            tag = f"  (revision {drafts - 1})" if drafts > 1 else ""
            events.append(Event(v.seq, "draft", f"DRAFT {drafts}{tag}   by {v.produced_by}",
                                render_pack(p, source), "info"))

        elif v.kind == "verdict":
            label = f"draft {p['draft']}" if p.get("draft") else "intake check"
            if p["status"] == "APPROVED":
                lines = [f"  ! {w}" for w in p.get("warnings", [])]
                events.append(Event(v.seq, "verdict", f"VALIDATOR  APPROVED  ({label})", lines, "ok"))
            else:
                n = len(p["issues"])
                lines = render_issues(p["issues"]) + [f"  ! {w}" for w in p.get("warnings", [])]
                events.append(Event(v.seq, "verdict",
                                    f"VALIDATOR  REJECTED  ({label}, {n} issue{'s' * (n != 1)})",
                                    lines, "warn"))

        elif v.kind == "escalation":
            reason = _REASONS.get(p["reason"], p["reason"]).format(**p)
            events.append(Event(v.seq, "escalation", f"HUMAN REVIEW REQUIRED  ({p['reason']})",
                                [reason], "warn"))

        elif v.kind == "question":
            events.append(Event(v.seq, "question", "REVIEW REQUESTED", [p["question"]], "info"))

        elif v.kind == "expert_answer":
            if p.get("source") == "unresolved_no_expert":
                events.append(Event(v.seq, "answer", "NO REVIEWER ANSWER",
                                    ["Nobody replied before the deadline."], "warn"))
            else:
                events.append(Event(v.seq, "answer", f"REVIEWER ANSWER  ({p.get('who')})",
                                    [p["answer"]], "info"))

        elif v.kind == "human_review":
            ok = p["decision"] == "APPROVED"
            events.append(Event(v.seq, "review", f"HUMAN DECISION  {p['decision']}",
                                [p["notes"]] if p.get("notes") else [], "ok" if ok else "bad"))

        elif v.kind == "result":
            lines = [f"approved by {p['approved_by']}, draft {p['draft']}, "
                     f"after {p['revisions']} revision{'s' * (p['revisions'] != 1)}"]
            if p.get("overrode"):
                lines.append("over validator issues: " + ", ".join(p["overrode"]))
            events.append(Event(v.seq, "result", "RESULT  APPROVED", lines, "ok"))

        elif v.kind == "failure":
            events.append(Event(v.seq, "failure", f"STOPPED  {p['kind']}", [p["detail"]], "bad"))

        elif v.kind == "feedback":
            who = v.produced_by.removeprefix("tester:")
            lines = ([f"rating: {p['rating']}/5"] if p.get("rating") else [])
            lines += [f"what to improve: {p['comment']}"] if p.get("comment") else []
            lines += [f"confusing or wrong: {p['confusing']}"] if p.get("confusing") else []
            lines.append(f"(about draft {p['draft']}; run was {p['run_state']})")
            events.append(Event(v.seq, "feedback",
                                f"TESTER FEEDBACK  ({who}): "
                                f"{'useful' if p['useful'] else 'NOT useful'}",
                                lines, "ok" if p["useful"] else "warn"))

        elif v.kind == "step":
            events.append(Event(v.seq, "step",
                                f"{p['state']} -> {p['next']}   {p['tokens']:,} tok   {p['seconds']}s",
                                [], "dim"))
    return events


def summary(store: Store, run_id: str) -> dict:
    """The run in one glance: where it is, how it got there, what it cost."""
    versions = store.replay(run_id)
    steps = [v.payload for v in versions if v.kind == "step"]
    path: list[str] = []
    for s in steps:
        if not path or path[-1] != s["state"]:
            path.append(s["state"])            # a hop made outside a handler: a human answered
        path.append(s["next"])
    drafts = sum(1 for v in versions if v.kind == "draft")
    return {
        "state": store.get_state(run_id).value,
        "drafts": drafts,
        "revisions": max(0, drafts - 1),
        "path": " -> ".join(path),
        "tokens": int(store.counter(run_id, "tokens")),
        "seconds": round(sum(s["seconds"] for s in steps), 1),
        "feedback": sum(1 for v in versions if v.kind == "feedback"),
    }


# ------------------------------------------------------------------ text

def _wrap(line: str, width: int) -> list[str]:
    if len(line) <= width:
        return [line]
    indent = len(line) - len(line.lstrip())
    return textwrap.wrap(line, width=width, subsequent_indent=" " * (indent + 4),
                         break_long_words=False, break_on_hyphens=False) or [line]


def render_text(store: Store, run_id: str, width: int = 100, color: bool = False) -> str:
    def paint(s: str, tone: str) -> str:
        return f"{_ANSI[tone]}{s}{_RESET}" if color else s

    meta = store.meta(run_id)
    out = [paint(f"run {run_id}   mode: {meta.get('mode', 'unknown')}", "dim"), ""]

    for e in build(store, run_id):
        if e.kind == "step":
            out.append(paint(f"   . {e.title}", "dim"))
            continue
        head = f"-- {e.seq:>2}  {e.title} "
        out.append(paint(head + "-" * max(4, min(width, 78) - len(head)), e.tone))
        for line in e.lines:
            out.extend("   " + w for w in _wrap(line, width - 3))
        out.append("")

    s = summary(store, run_id)
    out.append(paint(f"path    {s['path']}", "dim"))
    out.append(paint(f"state   {s['state'].upper()}   {s['drafts']} draft(s), "
                     f"{s['revisions']} revision(s), {s['tokens']:,} tok, {s['seconds']}s in steps",
                     "ok" if s["state"] == "complete" else
                     "warn" if s["state"] == "awaiting_expert" else "bad"))
    return "\n".join(out)
