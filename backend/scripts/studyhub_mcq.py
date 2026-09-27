"""Generate multiple-choice questions from a subject's uploaded material, from the terminal.

    # your real data (the same database the web app uses); add --save to keep the questions in the subject's question bank
    python scripts/studyhub_mcq.py --user alice --subject "Data Structures" --count 5 [--topic Stacks] [--save]

    # self-contained demo: a throw-away database with sample material (and any files you add), no account needed
    python scripts/studyhub_mcq.py --demo --count 3
    python scripts/studyhub_mcq.py --demo --file notes.pdf --file slides.docx --count 5

For each question it prints the four options, then the answer, the explanation, the exact source words and which checks passed.
Every question was checked by the app (its quote is word for word in the material, the question does not give the answer away, the
wrong answers are not restatements of the source, no invented numbers) and, unless --no-solver, answered by an independent second
pass that never saw the key. Nothing is made up if no model is available.

Options: --db PATH  --topic TEXT  --revisions N  --no-solver  --cloud  --no-trace  --json  --save
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

from slice import config as slice_config                     # noqa: E402
from studyhub import auth, explain, ingest, mcq, models       # noqa: E402
from studyhub.db import open_db                               # noqa: E402
from studyhub.repo import Repo                                # noqa: E402

WIDTH = 100
LETTERS = "ABCD"


def wrap(text: str, indent: str = "") -> str:
    return textwrap.fill(" ".join(str(text).split()), WIDTH, initial_indent=indent, subsequent_indent=indent + "   " if indent else "   ")


def where(it: dict) -> str:
    bits = [it["doc_title"]]
    if it.get("heading_path"):
        bits.append("section: " + it["heading_path"])
    if it.get("page_start") is not None:
        end = it.get("page_end")
        bits.append(f"PDF p. {it['page_start']}" if end in (None, it["page_start"]) else f"PDF pp. {it['page_start']}-{end}")
    return " | ".join(b for b in bits if b)


def render(res: mcq.Result, trace: list[dict], show_trace: bool) -> None:
    print(f"\nRESULT: {res.status.upper()} - {len(res.items)} of {res.requested} questions kept"
          + (f"   (model: {res.model}, {res.tier})" if res.model else "") + f"   candidates rejected by a check: {res.rejected}")
    if res.reason:
        print(wrap(res.reason, "  "))
    for n, it in enumerate(res.items, start=1):
        print("\n" + "-" * WIDTH)
        print(wrap(f"Q{n}. {it['question']}", ""))
        for j, opt in enumerate(it["options"]):
            print(wrap(f"{LETTERS[j]}) {opt}", "     "))
        print(wrap(f"ANSWER: {LETTERS[it['answer_index']]}) {it['options'][it['answer_index']]}", "  "))
        if it["explanation"]:
            print(wrap(f"Why: {it['explanation']}", "  "))
        print(wrap(f"Source: {where(it)}", "  "))
        print(wrap(f'Exact words: "{it["quote"]}"', "  "))
        print("  Checks: quote found word for word [ok]; question does not give the answer away [ok]; wrong answers are not restatements [ok]; "
              + ("answered correctly by an independent reader [ok]" if it["solver"] == "agreed" else "independent reader: NOT run"))
    if show_trace:
        print("\n" + "=" * 8, "HOW THIS WAS PRODUCED (append-only log)", "=" * 40)
        for i, step in enumerate(trace, start=1):
            print(wrap(f"{i:>2}. [{step['by']}] {explain.mcq_step_text(step)}", ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user")
    ap.add_argument("--subject")
    ap.add_argument("--db")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--file", action="append", default=[], help="(demo) add a PDF, DOCX or text file; repeatable")
    ap.add_argument("--count", type=int, default=mcq.DEFAULT_COUNT)
    ap.add_argument("--topic", help="only topics whose name contains this text")
    ap.add_argument("--revisions", type=int)
    ap.add_argument("--no-solver", action="store_true")
    ap.add_argument("--cloud", action="store_true")
    ap.add_argument("--save", action="store_true", help="store the approved questions in the subject's question bank")
    ap.add_argument("--no-trace", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.demo:
        tmp = tempfile.mkdtemp(prefix="studyhub-mcq-")
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
        for name, data in [("data-structures.txt", SAMPLE_TXT.encode())] + [(Path(f).name, Path(f).read_bytes()) for f in args.file]:
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

    topic_id = None
    if args.topic:
        hits = [t for t in repo.list_topics(uid, sid) if t["chunks"] and args.topic.lower() in t["path"].lower()]
        if len(hits) != 1:
            print(f"--topic {args.topic!r} matches {len(hits)} topics: " + (", ".join(t["path"] for t in hits) or "none")
                  + "\nAll topics: " + ", ".join(t["path"] for t in repo.list_topics(uid, sid)))
            return 2
        topic_id = hits[0]["id"]

    tiers, notes = models.build_tiers(db, repo.get_user(uid), base=slice_config.settings())
    if not args.cloud:
        tiers = [t for t in tiers if t.name == "local"]
    solver = None if not args.no_solver else False
    print(f"\nModels in order: {', '.join(t.label for t in tiers) or 'none'}   count: {args.count}   independent reader: {'off' if args.no_solver else 'on'}")
    for n in notes:
        print(f"  note: {n}")
    print("Working (a local model can take a few minutes for a batch)...", flush=True)

    if args.save:
        job = repo.create_mcq_job(uid, sid, topic_id, f"{args.count} questions (terminal)", args.count)
        mcq.run_job(store, uid, job, tiers, notes)
        j = repo.get_mcq_job(uid, sid, job)
        items = repo.list_mcq(uid, sid, job_id=job)
        res = mcq.Result(j["status"], j["reason"], items, j["rejected"], j["tier"], j["model"], j["run_id"], args.count)
        print(f"saved {len(items)} question(s) to the question bank of {args.subject or 'the demo subject'}")
    else:
        res = mcq.generate(store, uid, sid, topic_id, args.count, tiers, notes=notes, revisions=args.revisions, solver=solver)
    trace = [{"kind": v.kind, "by": v.produced_by, "payload": v.payload} for v in store.replay(res.run_id)]
    if args.json:
        print(json.dumps({"status": res.status, "reason": res.reason, "rejected": res.rejected, "model": res.model, "questions": [
            {k: it[k] for k in ("question", "options", "answer_index", "explanation", "quote", "doc_title", "heading_path",
                                "page_start", "solver")} for it in res.items], "trace": trace}, indent=1, default=str))
    else:
        render(res, trace, not args.no_trace)
    store.close()
    return 0 if res.status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
