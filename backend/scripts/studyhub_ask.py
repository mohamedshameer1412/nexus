"""Ask a question about one subject from the terminal and see the explainable answer.

    # your real data (the same database the web app uses)
    python scripts/studyhub_ask.py "What does the pop operation do on a stack?" --user alice --subject "Data Structures"

    # self-contained demo: a throw-away database with sample material (and any files you add), no account needed
    python scripts/studyhub_ask.py --demo "What does the pop operation do on a stack?"
    python scripts/studyhub_ask.py --demo --file notes.pdf --file slides.docx "What is a foreign key?"

Prints the answer, its sources (file, section, PDF page), the exact evidence quotes, the model's step-by-step explanation
and what the app verified, then the recorded steps. Nothing is fabricated: the same checks as the web page decide what
is shown. This command does not write to the question history of the web app.

Options:  --db PATH  --revisions N  --no-trace  --json  --cloud   (--cloud uses your saved Account consent and the key in .env)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("STUDYHUB_SCRYPT_N", "1024")

from slice import config as slice_config                    # noqa: E402
from studyhub import auth, explain, ingest, models, qa       # noqa: E402
from studyhub.db import open_db                              # noqa: E402
from studyhub.repo import Repo                               # noqa: E402

WIDTH = 100
STATUS = {"answered": "ANSWERED FROM YOUR MATERIALS", "abstained": "NOT ANSWERED - NOTHING WAS GUESSED",
          "extractive": "NO MODEL AVAILABLE - MATCHING PASSAGES ONLY", "failed": "FAILED"}


def wrap(text: str, indent: str = "  ") -> str:
    return textwrap.fill(" ".join(str(text).split()), WIDTH, initial_indent=indent, subsequent_indent=indent)


def where(x: dict) -> str:
    bits = [x.get("doc_title") or ""]
    if x.get("heading_path"):
        bits.append("section: " + x["heading_path"])
    if x.get("page_start") is not None:
        end = x.get("page_end")
        bits.append(f"PDF p. {x['page_start']}" if end in (None, x["page_start"]) else f"PDF pp. {x['page_start']}-{end}")
    return " | ".join(b for b in bits if b)


def heading(title: str) -> None:
    print("\n" + "=" * 8, title, "=" * max(3, WIDTH - len(title) - 10))


def render(out: qa.Outcome, trace: list[dict], show_trace: bool) -> None:
    print(f"\nSTATUS: {STATUS.get(out.status, out.status)}"
          + (f"   (model: {out.model}, {out.tier})" if out.model else ""))
    if out.reason:
        print(wrap(out.reason, "  "))
    if out.status == "answered":
        uniq, index = [], {}
        for c in out.claims:
            for x in c["citations"]:
                key = (x["chunk_id"], x["quote"])
                if key not in index:
                    uniq.append(x)
                    index[key] = len(uniq)
        heading("YOUR MATERIALS DISAGREE (each side shown with its own quote)" if out.kind == "conflict" else "ANSWER")
        for i, c in enumerate(out.claims, start=1):
            refs = "".join(f"[{index[(x['chunk_id'], x['quote'])]}]" for x in c["citations"])
            print(wrap(f"{i}. {c['text']} {refs}", ""))
        if out.dropped:
            print(wrap(f"({out.dropped} other statement(s) the model wrote failed verification and were left out.)", ""))
        heading("SOURCE")
        for n, x in enumerate(uniq, start=1):
            print(f"  [{n}] {where(x)}")
        heading("EVIDENCE (exact words, found in your material by the app)")
        for n, x in enumerate(uniq, start=1):
            print(wrap(f'[{n}] "{x["quote"]}"', ""))
        if out.explanation:
            heading("EXPLANATION (the model's step-by-step reasoning; checked for invented numbers, not word for word)")
            print(wrap(out.explanation, ""))
        heading("VERIFICATION / GROUNDING")
        for row in explain.verification_rows(out.claims, out.dropped, trace):
            print(wrap("[ok] " + row, ""))
    elif out.sources:
        heading("CLOSEST PASSAGES (your own words, exactly as stored)")
        for i, s in enumerate(out.sources, start=1):
            print(f"  [{i}] {where(s)}" + (f"   matched: {', '.join(s['matched'])}" if s.get("matched") else "")
                  + ("   [NOT USED: reads like instructions to an AI]" if s.get("quarantined") else ""))
            print(wrap(s["text"][:420] + ("..." if len(s["text"]) > 420 else ""), "      "))
    if show_trace:
        heading("HOW THIS WAS PRODUCED (append-only log)")
        for i, step in enumerate(trace, start=1):
            print(wrap(f"{i:>2}. [{step['by']}] {explain.step_text(step)}", ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="?", help="the question to ask")
    ap.add_argument("--user")
    ap.add_argument("--subject")
    ap.add_argument("--db", help="database file (default: data/studyhub.db, or STUDYHUB_DB)")
    ap.add_argument("--demo", action="store_true", help="use a throw-away database with sample material")
    ap.add_argument("--file", action="append", default=[], help="(demo) add a PDF, DOCX or text file; repeatable")
    ap.add_argument("--revisions", type=int, help="times the model may correct itself (default 2)")
    ap.add_argument("--cloud", action="store_true", help="allow the cloud fallback (needs key in .env and consent on the Account page)")
    ap.add_argument("--no-trace", action="store_true")
    ap.add_argument("--json", action="store_true", help="print the raw result as JSON")
    args = ap.parse_args()
    if not args.question:
        ap.print_help()
        return 2

    if args.demo:
        tmp = tempfile.mkdtemp(prefix="studyhub-demo-")
        os.environ["STUDYHUB_DB"] = os.path.join(tmp, "demo.db")
        os.environ["STUDYHUB_UPLOADS"] = os.path.join(tmp, "uploads")
    elif args.db:
        os.environ["STUDYHUB_DB"] = args.db
    store = open_db()
    db, repo = store.db, Repo(store.db)

    if args.demo:
        from studyhub_files import SAMPLE_TXT
        uid = auth.register(db, "demo", "correct horse battery")
        sid = repo.create_subject(uid, "Demo subject")
        docs = [("data-structures.txt", SAMPLE_TXT.encode())] + [(Path(f).name, Path(f).read_bytes()) for f in args.file]
        for name, data in docs:
            r = ingest.ingest(db, uid, sid, name, data)
            print(f"loaded {name}: {r.chunks} passages ({r.status})" + "".join(f"\n  ! {w}" for w in r.warnings))
    else:
        if not (args.user and args.subject):
            print("Give --user and --subject (or use --demo).")
            return 2
        row = db.execute("SELECT id FROM users WHERE username=?", (args.user.lower(),)).fetchone()
        if row is None:
            print(f"No user named {args.user!r} in {os.environ.get('STUDYHUB_DB', 'data/studyhub.db')}.")
            return 2
        uid = row["id"]
        subj = next((s for s in repo.list_subjects(uid) if s["name"].lower() == args.subject.lower()), None)
        if subj is None:
            print(f"{args.user} has no subject {args.subject!r}. Subjects: {', '.join(s['name'] for s in repo.list_subjects(uid)) or 'none'}")
            return 2
        sid = subj["id"]

    tiers, notes = models.build_tiers(db, repo.get_user(uid), base=slice_config.settings())
    if not args.cloud:
        tiers = [t for t in tiers if t.name == "local"]
    print(f"\nQuestion: {args.question}\nModels in order: {', '.join(t.label for t in tiers) or 'none'}")
    for n in notes:
        print(f"  note: {n}")
    print("Working (a local model can take a minute or two)...", flush=True)

    out = qa.answer_question(store, uid, sid, args.question, tiers, notes=notes,
                             revisions=args.revisions if args.revisions is not None else None)
    trace = [{"kind": v.kind, "by": v.produced_by, "payload": v.payload} for v in store.replay(out.run_id)]
    if args.json:
        print(json.dumps({"status": out.status, "kind": out.kind, "reason": out.reason, "model": out.model, "tier": out.tier,
                          "claims": out.claims, "explanation": out.explanation, "dropped": out.dropped,
                          "sources": [{k: s[k] for k in ("doc_title", "heading_path", "page_start", "matched", "text")} for s in out.sources],
                          "trace": trace}, indent=1, default=str))
    else:
        render(out, trace, not args.no_trace)
    store.close()
    return 0 if out.status in ("answered", "abstained", "extractive") else 1


if __name__ == "__main__":
    raise SystemExit(main())
