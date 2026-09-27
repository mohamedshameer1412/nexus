#!/usr/bin/env python
"""One live run, end to end, against the RUNNING app, with the "sent back" steps made visible.

    python scripts/live_run.py                 # local Ollama model (free, slow)
    python scripts/live_run.py --cloud         # OpenRouter first (needs the key in .env; costs a few cents)
    python scripts/live_run.py --out docs/studyhub-evidence/live-run

What it does, with a throw-away account, real models and nothing faked:
  1. uploads a study document                                   (materials)
  2. asks cited questions: a model drafts, CODE checks every quote, failed drafts are SENT BACK   (loop 1: verifier -> model)
  3. writes practice questions: rejected drafts are SENT BACK to be replaced                     (loop 1 again, in question generation)
  4. takes a quiz and misses questions: the quiz SENDS THE STUDENT BACK to the topic it builds on (loop 2: backtracking)
  5. takes a revision quiz, and the twin checks whether the action helped; the planner reacts     (loop 3: improvement loop)
It prints every step and writes a transcript. If a loop did not fire in this run it says so; it never invents one.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8100/api/v1"
LOG: list[str] = []
FOUND = {"qa_sent_back": 0, "qa_rejected": 0, "mcq_sent_back": 0, "mcq_rejected": 0, "step_backs": [], "loop_outcomes": []}


def say(text: str = "") -> None:
    print(text, flush=True)
    LOG.append(text)


class Api:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = json.load(self.op.open(BASE + "/session"))["csrf"]

    def call(self, method, path, body=None, raw=None, ctype="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(BASE + path, data=data, method=method, headers={"X-CSRF-Token": self.csrf, "Content-Type": ctype})
        try:
            with self.op.open(req, timeout=120) as r:
                t = r.read()
                return json.loads(t) if t else {}
        except urllib.error.HTTPError as e:
            return {"_http": e.code, **json.loads(e.read() or b"{}")}

    def wait(self, path, limit, every=4):
        t0 = time.time()
        while time.time() - t0 < limit:
            v = self.call("GET", path)
            if v.get("status") != "pending":
                return v, round(time.time() - t0)
            time.sleep(every)
        return v, round(time.time() - t0)


def show_steps(steps: list[dict], sent_back_key: str) -> None:
    for s in steps:
        mark = "  <<< SENT BACK" if s.get("kind") == "revision" else ""
        say(f"    [{s['by']:<12}] {s['text']}{mark}")
        if s.get("kind") == "revision":
            FOUND[sent_back_key] += 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloud", action="store_true", help="allow OpenRouter models first (uses the key in .env)")
    ap.add_argument("--doc", default=str(ROOT / "frontend" / "e2e" / "fixtures" / "ds.txt"))
    ap.add_argument("--questions", type=int, default=3)
    ap.add_argument("--practice", type=int, default=6)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    a = Api()
    name = "live" + "".join(c for c in uuid.uuid4().hex if c.isdigit())[:7]
    a.csrf = a.call("POST", "/register", {"username": name, "password": "correct horse battery"})["csrf"]
    say(f"# Live run  ({time.strftime('%Y-%m-%d %H:%M:%S')})  account {name}  models: {'OpenRouter first, Ollama backup' if args.cloud else 'local Ollama'}")
    if args.cloud:
        say(f"cloud consent: {a.call('PUT', '/account/cloud', {'consent': True})}")
    sid = a.call("POST", "/subjects", {"name": "Live run"})["id"]
    b = "----x"
    raw = (f"--{b}\r\nContent-Disposition: form-data; name=\"role\"\r\n\r\nnotes\r\n--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"notes.txt\"\r\nContent-Type: text/plain\r\n\r\n").encode() \
        + Path(args.doc).read_bytes() + f"\r\n--{b}--\r\n".encode()
    doc = a.call("POST", f"/subjects/{sid}/materials", raw=raw, ctype=f"multipart/form-data; boundary={b}")["document"]
    topics = a.call("GET", f"/subjects/{sid}/topics")["topics"]
    say(f"\n## 1. Material\nUploaded “{doc['title']}”: {doc['chunks']} passages, topics: {', '.join(t['name'] for t in topics)}")

    say("\n## 2. Cited answers: model drafts, code verifies, failed drafts are sent back")
    asks = ["What does the pop operation do on a stack, and where is it used?", "How do enqueue and dequeue differ, and what is a queue used for?",
            "What is the difference between a stack and a queue, and how does a tree relate to them?"][: args.questions]
    for q in asks:
        qid = a.call("POST", f"/subjects/{sid}/questions", {"question": q})["id"]
        d, secs = a.wait(f"/subjects/{sid}/questions/{qid}", 400)
        say(f"\nQ: {q}\n  -> {d.get('status')} in {secs}s by {d.get('model')} ({d.get('tier')}); statements kept {len(d.get('claims') or [])}, dropped {d.get('dropped')}")
        show_steps(d.get("steps") or [], "qa_sent_back")
        FOUND["qa_rejected"] += (d.get("loop") or {}).get("rejected", 0)
        for c in (d.get("claims") or [])[:2]:
            say(f"     answer: {c['text'][:160]}  |  quote: “{c['citations'][0]['quote'][:100]}”")

    say("\n## 3. Practice questions: rejected drafts are sent back and replaced")
    job = a.call("POST", f"/subjects/{sid}/mcq/jobs", {"count": args.practice})
    j, secs = a.wait(f"/subjects/{sid}/mcq/jobs/{job['id']}", 900)
    say(f"asked for {args.practice}: {j.get('status')} in {secs}s by {j.get('model')}; kept {j.get('produced')}, rejected {j.get('rejected')}")
    show_steps(j.get("steps") or [], "mcq_sent_back")
    FOUND["mcq_rejected"] += (j.get("loop") or {}).get("rejected", 0)
    if not j.get("produced"):
        say("No practice question was produced, so the quiz and improvement parts cannot run.")
        return finish(args, sid)

    say("\n## 4. Quiz: a miss sends the student back to the topic it builds on")
    aid = a.call("POST", f"/subjects/{sid}/quiz/attempts", {"kind": "standard", "mode": "practice", "adaptive": True})["id"]
    for n in range(60):
        st = a.call("GET", f"/subjects/{sid}/quiz/attempts/{aid}")
        if st.get("state") != "mcq":
            break
        it = st["item"]
        tag = f"  (STEP BACK question: asked because “{it['backtrack']['from']}” went wrong)" if it.get("backtrack") else ""
        r = a.call("POST", f"/subjects/{sid}/quiz/attempts/{aid}/answer", {"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": 0, "response_time": 6.0})
        say(f"  Q{n + 1} [{it['topic']}] answered option A{tag}")
        if r.get("backtrack"):
            FOUND["step_backs"].append(r["backtrack"])
            say(f"    >>> SENT BACK: missed “{r['backtrack']['from']}”, so {r['backtrack']['questions']} question(s) from {', '.join(r['backtrack']['to'])} come next")
    res = a.call("GET", f"/subjects/{sid}/quiz/attempts/{aid}/result")
    right = {x["question"]: x["answer_index"] for x in res.get("answers", [])}
    say(f"quiz finished: {res['attempt']['correct']} right, {res['attempt']['incorrect']} wrong; step-backs asked: {sum(1 for x in res.get('answers', []) if x['backtrack'])}")

    say("\n## 5. Improvement loop: revise, retest, check whether it helped, let the planner react")
    tw = a.call("GET", f"/subjects/{sid}/twin")
    say("planner before: " + "; ".join(f"{n['title']} ({'; '.join(n['why'][:2])})" for n in tw["next"][:2]))
    rv = a.call("POST", f"/subjects/{sid}/quiz/attempts", {"kind": "revision", "mode": "practice"})
    if "id" in rv:
        for n in range(40):
            st = a.call("GET", f"/subjects/{sid}/quiz/attempts/{rv['id']}")
            if st.get("state") != "mcq":
                break
            it = st["item"]
            a.call("POST", f"/subjects/{sid}/quiz/attempts/{rv['id']}/answer",
                   {"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": right.get(it["question"], 1), "response_time": 8.0})
        say("revision quiz done (answered from the feedback shown after the first quiz)")
    for _ in range(3):                                                        # enough new answers on each topic for the loop to judge the action
        q2 = a.call("POST", f"/subjects/{sid}/quiz/attempts", {"kind": "standard", "mode": "practice"})
        for n in range(40):
            st = a.call("GET", f"/subjects/{sid}/quiz/attempts/{q2['id']}")
            if st.get("state") != "mcq":
                break
            it = st["item"]
            a.call("POST", f"/subjects/{sid}/quiz/attempts/{q2['id']}/answer",
                   {"answer_row_id": it["answer_row_id"], "item_id": it["item_id"], "chosen": right.get(it["question"], 1), "response_time": 8.0})
    tw = a.call("GET", f"/subjects/{sid}/twin")
    for h in tw["history"]:
        outcome = h["outcome"] or "waiting for 3 new answers"
        if h["outcome"]:
            FOUND["loop_outcomes"].append(f"{h['kind']} on {h['topic']}: {outcome} ({round((h['conf_before'] or 0) * 100)}% -> {round((h['conf_after'] or 0) * 100)}%)")
        say(f"  action: {h['kind']:<15} topic: {h['topic']:<14} result: {outcome}")
    say("what has worked: " + ("; ".join(f"{m['label']} {m['improved']}/{m['tried']}" for m in tw["memory"]) or "nothing judged yet"))
    say("planner after:  " + "; ".join(f"{n['title']} ({'; '.join(n['why'][:2])})" for n in tw["next"][:2]) if tw["next"] else "planner after:  nothing is below target")
    return finish(args, sid)


def finish(args, sid) -> int:
    say("\n## What the loop did in this run")
    say(f"- Verifier -> model, cited answers: sent back {FOUND['qa_sent_back']} time(s); {FOUND['qa_rejected']} statement(s) rejected by the checker")
    say(f"- Verifier -> model, practice questions: sent back {FOUND['mcq_sent_back']} time(s); {FOUND['mcq_rejected']} question(s) rejected")
    say(f"- Quiz backtracking: {len(FOUND['step_backs'])} step-back(s)" + "".join(f"\n    missed “{s['from']}” -> asked from {', '.join(s['to'])}" for s in FOUND["step_backs"]))
    say(f"- Improvement loop: {len(FOUND['loop_outcomes'])} action(s) judged" + "".join(f"\n    {o}" for o in FOUND["loop_outcomes"]))
    if not (FOUND["qa_sent_back"] or FOUND["mcq_sent_back"] or FOUND["step_backs"]):
        say("NOTE: no send-back happened in this run (every draft passed first time and no question was missed). Run again, or use a harder question.")
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"live-run-{time.strftime('%Y%m%d-%H%M%S')}{'-cloud' if args.cloud else '-local'}.md"
        path.write_text("\n".join(LOG) + "\n", encoding="utf-8")
        print(f"\ntranscript: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
