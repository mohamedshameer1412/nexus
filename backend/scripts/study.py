#!/usr/bin/env python3
"""The study agent. Spec and design: demo/study/README.md

    python scripts/study.py run --stub                     # scripted replies, no key
    python scripts/study.py run --stub --scenario stuck    # ends waiting for a human
    python scripts/study.py run --file notes.txt           # live: LLM_PROVIDER, default openrouter
    python scripts/study.py run --provider ollama          # live, local: no key, no internet
    python scripts/study.py review <run_id> --approve --notes "checked the quotes"
    python scripts/study.py resume <run_id>                # pick a run up where it stopped
    python scripts/study.py trace  <run_id>                # the execution trace, any time
    python scripts/study.py feedback <run_id> --useful --comment "..." --who sam
    python scripts/study.py feedbacks [run_id]             # what testers said
    python scripts/study.py runs

Exit codes from `run`, `review` and `resume`:
    0 approved   1 failed (the trace says why)   3 waiting for a human   2 could not start
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dataclasses
import time

import httpx

from demo.study import feedback, trace
from demo.study.flow import DOMAIN, build_flow
from demo.study.samples import CASES
from demo.study.stub import SCENARIOS
from slice import callback, runner
from slice.config import settings as load_settings
from slice.llm import ModelError
from slice.providers import get_provider
from slice.records import RunState
from slice.store import Store

EXIT = {RunState.COMPLETE: 0, RunState.FAILED: 1, RunState.AWAITING_EXPERT: 3}


def _ollama_problem(st) -> str | None:
    """Fail in one second, with the fix, instead of after a run has been created.
    Never downloads anything: pulling a 5 GB model is the user's decision."""
    try:
        r = httpx.get(f"{st.ollama_base_url}/api/tags", timeout=3.0)
        pulled = [m["name"] for m in r.json().get("models", [])]
    except (httpx.HTTPError, ValueError):
        return (f"Cannot reach Ollama at {st.ollama_base_url}.\n"
                "Start it with `ollama serve`, or use --provider openrouter, or --stub.")
    if st.ollama_model not in pulled:
        return (f"Ollama is running but {st.ollama_model!r} is not pulled "
                f"(pulled: {', '.join(pulled) or 'none'}).\n"
                f"Pull it yourself (this app never downloads models): ollama pull {st.ollama_model}")
    return None


def _no_model(**_kw):
    raise ModelError("No live provider is configured for this command. Set LLM_PROVIDER "
                     "(openrouter or ollama) - the fixture provider only runs with --stub.")


def _resume_call(st):
    """The client for a run that already exists. After a human's answer nothing calls a
    model, so a missing provider only matters for a run that crashed mid-generation."""
    try:
        return get_provider(st)
    except ValueError:
        return _no_model


def _read_source(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    return CASES[args.case]


def _show(store: Store, run_id: str, final: RunState) -> int:
    print(trace.render_text(store, run_id, color=sys.stdout.isatty()))
    print()
    if final is RunState.AWAITING_EXPERT:
        print("A person has to decide. Either:")
        print(f"  python scripts/study.py review {run_id} --approve   (or --reject)")
        print("  or answer it on the expert page, then: "
              f"python scripts/study.py resume {run_id}")
    elif final is RunState.COMPLETE:
        print(f"trace again:  python scripts/study.py trace {run_id}")
        print(f"a tester?     python scripts/study.py feedback {run_id} --useful "
              "--comment \"...\" --who <nickname>")
    return EXIT.get(final, 1)


def cmd_run(args: argparse.Namespace) -> int:
    st = load_settings()
    if args.stub:
        call = SCENARIOS[args.scenario][1]()
        mode = f"stub:{args.scenario} (scripted replies - no model is called)"
    else:
        provider = args.provider or st.llm_provider
        st = dataclasses.replace(st, llm_provider=provider)
        if provider == "fixture":
            print("LLM_PROVIDER=fixture has no model to call. Use --stub for the scripted demo.")
            return 2
        if provider == "openrouter":
            if not st.api_key:
                print("No OPENROUTER_API_KEY in .env or the environment.\n"
                      "Run with --stub for a scripted demo, or --provider ollama for a local model.")
                return 2
            mode = f"live (openrouter: {st.model}; validator on {st.fallback_model})"
        elif provider == "ollama":
            problem = _ollama_problem(st)
            if problem:
                print(problem)
                return 2
            other = st.ollama_fallback_model or f"{st.ollama_model} (same model, different prompt)"
            mode = f"live (ollama: {st.ollama_model} at {st.ollama_base_url}; validator on {other})"
        else:
            print(f"Unknown provider {provider!r}. Choose openrouter or ollama.")
            return 2
        call = get_provider(st)

    store = Store(args.db)
    run_id = store.create_run(DOMAIN, {"mode": mode})
    store.append(run_id, "input", {"text": _read_source(args)}, produced_by="user")
    final = runner.advance(store, run_id, build_flow(call), st)
    return _show(store, run_id, final)


def cmd_review(args: argparse.Namespace) -> int:
    store, st = Store(args.db), load_settings()
    if store.get_state(args.run_id) is RunState.AWAITING_EXPERT:
        callback.sweep(store, args.run_id)               # a deadline may have passed
    open_qs = callback.pending(store, args.run_id)
    if not open_qs:
        print(f"Run {args.run_id} is {store.get_state(args.run_id).value}; "
              "nothing is waiting for a reviewer.")
        return 2
    verdict = "APPROVE" if args.approve else "REJECT"
    callback.answer(store, open_qs[0].id, f"{verdict} {args.notes}".strip(), who=args.who)
    final = runner.advance(store, args.run_id, build_flow(_resume_call(st)), st)
    return _show(store, args.run_id, final)


def cmd_resume(args: argparse.Namespace) -> int:
    store, st = Store(args.db), load_settings()
    final = runner.advance(store, args.run_id, build_flow(_resume_call(st)), st)
    return _show(store, args.run_id, final)


def cmd_trace(args: argparse.Namespace) -> int:
    print(trace.render_text(Store(args.db), args.run_id, color=sys.stdout.isatty()))
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    raw = {"useful": bool(args.useful), "comment": args.comment,
           "confusing": args.confusing, "tester": args.who}
    if args.rating is not None:
        raw["rating"] = args.rating
    store = Store(args.db)
    try:
        rec = feedback.submit(store, args.run_id, raw)
    except KeyError:
        print(f"No such run: {args.run_id}")
        return 2
    except feedback.FeedbackError as e:
        print(f"Feedback not recorded: {e}")
        return 2
    print(f"Recorded feedback #{rec['seq']} on {args.run_id} from {rec['tester']!r}: "
          f"{'useful' if rec['useful'] else 'NOT useful'} (about draft {rec['draft']}, "
          f"run was {rec['run_state']}).")
    return 0


def cmd_feedbacks(args: argparse.Namespace) -> int:
    store = Store(args.db)
    if args.run_id:
        try:
            store.get_state(args.run_id)
        except KeyError:
            print(f"No such run: {args.run_id}")
            return 2
        items = feedback.for_run(store, args.run_id)
    else:
        items = feedback.everything(store)
    if not items:
        print("No feedback has been submitted yet.")
        return 0
    for f in items:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(f["submitted_at"]))
        rating = f" {f['rating']}/5" if f.get("rating") else ""
        print(f"{f['run_id']}  #{f['seq']}  {when}  {f['tester']:<14} "
              f"{'useful' if f['useful'] else 'NOT useful'}{rating}  (draft {f['draft']}, {f['run_state']})")
        for label, key in (("improve", "comment"), ("confusing/wrong", "confusing")):
            if f.get(key):
                print(f"      {label}: {f[key]}")
    print(f"\n{len(items)} feedback item(s).")
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    for r in Store(args.db).list_runs():
        print(f"{r['id']}  {r['domain']:<6} {r['state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):              # a Windows console must not crash on
        try:                                             # a curly quote in somebody's notes
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default="run.db", help="the run database (default: run.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="generate, validate, revise, and approve or escalate")
    r.add_argument("--stub", action="store_true", help="scripted replies; no key, no network")
    r.add_argument("--provider", choices=["openrouter", "ollama"],
                   help="live model to use (default: LLM_PROVIDER, else openrouter)")
    r.add_argument("--scenario", choices=sorted(SCENARIOS), default="revise",
                   help="with --stub: " + "; ".join(f"{k} = {v[0]}" for k, v in SCENARIOS.items()))
    src = r.add_mutually_exclusive_group()
    src.add_argument("--case", choices=sorted(CASES), default="sample",
                     help="a built-in source (default: sample)")
    src.add_argument("--file", help="a text file to study")
    src.add_argument("--text", help="the source text itself")
    r.set_defaults(fn=cmd_run)

    v = sub.add_parser("review", help="answer a run that is waiting for a human")
    v.add_argument("run_id")
    d = v.add_mutually_exclusive_group(required=True)
    d.add_argument("--approve", action="store_true")
    d.add_argument("--reject", action="store_true")
    v.add_argument("--notes", default="")
    v.add_argument("--who", default="reviewer")
    v.set_defaults(fn=cmd_review)

    for name, fn, helptext in (("resume", cmd_resume, "continue a run from its saved state"),
                               ("trace", cmd_trace, "print a run's execution trace")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("run_id")
        s.set_defaults(fn=fn)
    f = sub.add_parser("feedback", help="record a real tester's verdict on a run")
    f.add_argument("run_id")
    fu = f.add_mutually_exclusive_group(required=True)
    fu.add_argument("--useful", action="store_true")
    fu.add_argument("--not-useful", dest="useful", action="store_false")
    f.add_argument("--rating", type=int, help="1 (poor) to 5 (excellent)")
    f.add_argument("--comment", default="", help="what should be improved?")
    f.add_argument("--confusing", default="", help="what was confusing or wrong?")
    f.add_argument("--who", default="anonymous", help="a nickname; no personal details needed")
    f.set_defaults(fn=cmd_feedback)

    fs = sub.add_parser("feedbacks", help="show feedback (one run, or everything)")
    fs.add_argument("run_id", nargs="?")
    fs.set_defaults(fn=cmd_feedbacks)

    sub.add_parser("runs", help="list recent runs").set_defaults(fn=cmd_runs)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
