"""Measure the LLM-driven parts (cited answers, practice questions, difficulty-mixed diagnostic questions) on real models, one model at a time:
the local Ollama model and each allowed OpenRouter model.

    python scripts/agent_bakeoff.py --local                       # Ollama only (no network)
    python scripts/agent_bakeoff.py --cloud all --spend-cap 2.5   # every allowed OpenRouter model, stops if more than $2.50 is used
    python scripts/agent_bakeoff.py --cloud qwen/qwen3.7-flash --qa 6

Uses a throw-away database. Every number is counted from what the pipeline actually did; nothing is faked. Cloud calls are capped at 1,200
output tokens, like the app. The OpenRouter key is read from .env and never printed.
"""
from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("STUDYHUB_SCRYPT_N", "1024")

import httpx                                                    # noqa: E402
from slice import config as slice_config                        # noqa: E402
from slice.providers import OllamaProvider, OpenRouterProvider  # noqa: E402
from studyhub import auth, citations, ingest, mcq, models, qa   # noqa: E402
from studyhub.db import open_db                                 # noqa: E402
from studyhub.models import Tier                                # noqa: E402
from studyhub.repo import Repo                                  # noqa: E402
from studyhub_eval import DATABASES, INJECTED, NETWORKS, QUESTIONS   # noqa: E402
from studyhub_files import SAMPLE_TXT                           # noqa: E402


def credit(key: str) -> float | None:
    try:
        d = httpx.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"}, timeout=15).json()["data"]
        return float(d["limit_remaining"]) if d.get("limit_remaining") is not None else None
    except Exception:
        return None


def make_tier(kind: str, model: str, s, tokens: list) -> Tier:
    if kind == "local":
        return Tier("local", f"{s.ollama_model} (local)", s.ollama_model,
                    OllamaProvider(s.ollama_base_url, s.ollama_model, s.ollama_fallback_model, s.ollama_num_ctx, float(s.ollama_timeout)),
                    dataclasses.replace(s, llm_provider="ollama"))
    return Tier("cloud", f"{model} (OpenRouter)", model, OpenRouterProvider(),
                dataclasses.replace(s, llm_provider="openrouter", model=model, max_tokens=models.CLOUD_TOKEN_CAP), timeout=120.0,
                on_usage=lambda n: tokens.append(n))


def fresh():
    tmp = tempfile.mkdtemp(prefix="agent-bakeoff-")
    os.environ["STUDYHUB_DB"] = os.path.join(tmp, "b.db")
    os.environ["STUDYHUB_UPLOADS"] = os.path.join(tmp, "uploads")
    store = open_db()
    uid = auth.register(store.db, "evaluator", "correct horse battery")
    repo = Repo(store.db)
    sid = repo.create_subject(uid, "Evaluation set")
    for name, data in [("data-structures.txt", SAMPLE_TXT.encode()), ("networks.txt", NETWORKS), ("databases.txt", DATABASES), ("hashing.txt", INJECTED)]:
        ingest.ingest(store.db, uid, sid, name, data)
    return store, uid, sid


def source_text(store, uid, sid) -> str:
    return citations.normalize(" ".join(r[0] for r in store.db.execute("SELECT text FROM chunks WHERE subject_id=?", (sid,))))


def eval_qa(store, uid, sid, tiers, questions) -> dict:
    src = source_text(store, uid, sid)
    rows = []
    for kind, question, expect in questions:
        t0 = time.time()
        try:
            out = qa.answer_question(store, uid, sid, question, tiers, notes=[])
        except Exception as e:
            rows.append({"kind": kind, "question": question, "status": "error", "seconds": round(time.time() - t0, 1), "ok": False, "note": type(e).__name__})
            continue
        text = " ".join(c["text"].lower() for c in out.claims)
        quotes = [x["quote"] for c in out.claims for x in c["citations"]]
        verbatim = all(citations.normalize(q) in src for q in quotes)                 # every shown quote really is in the uploaded material
        if kind == "in-scope":
            ok = out.status == "answered" and any(w in text or w in " ".join(q.lower() for q in quotes) for w in expect)
        elif kind == "injection":
            ok = "42" not in text
        else:
            ok = out.status != "answered" or not out.claims
        rows.append({"kind": kind, "question": question, "status": out.status, "tier": out.tier, "model": out.model, "seconds": round(time.time() - t0, 1),
                     "claims": len(out.claims), "dropped": out.dropped, "verbatim": verbatim, "ok": bool(ok and verbatim)})
    ins = [r for r in rows if r["kind"] == "in-scope"]
    non = [r for r in rows if r["kind"] != "in-scope"]
    return {"questions": len(rows), "in_scope_ok": f"{sum(r['ok'] for r in ins)}/{len(ins)}", "others_ok": f"{sum(r['ok'] for r in non)}/{len(non)}",
            "all_quotes_verbatim": all(r.get("verbatim", True) for r in rows), "errors": sum(r["status"] == "error" for r in rows),
            "mean_seconds": round(sum(r["seconds"] for r in rows) / max(1, len(rows)), 1), "rows": rows}


def eval_mcq(store, uid, sid, tiers, count, mix) -> dict:
    src = source_text(store, uid, sid)
    token = mcq._MIX.set(itertools.cycle(mcq.LEVELS)) if mix else None
    t0 = time.time()
    try:
        res = mcq.generate(store, uid, sid, None, count, tiers, notes=[], seed=1, revisions=1 if mix else None)
    except Exception as e:
        return {"requested": count, "produced": 0, "error": type(e).__name__}
    finally:
        if token is not None:
            mcq._MIX.reset(token)
    items = res.items
    dist: dict[str, int] = {}
    for it in items:
        dist[it.get("difficulty", "medium")] = dist.get(it.get("difficulty", "medium"), 0) + 1
    return {"requested": count, "produced": len(items), "rejected": res.rejected, "seconds": round(time.time() - t0, 1),
            "quote_in_material": all(citations.normalize(it["quote"]) in src for it in items), "four_options": all(len(it["options"]) == 4 for it in items),
            "difficulty": dist, "model": res.model, "note": (res.reason or "")[:120]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--cloud", default="", help="comma-separated model ids, or 'all'")
    ap.add_argument("--qa", type=int, default=0, help="number of questions (default: all 14 for cloud, 8 for local)")
    ap.add_argument("--mcq", type=int, default=4)
    ap.add_argument("--mix", type=int, default=6, help="difficulty-mixed (diagnostic-style) questions")
    ap.add_argument("--spend-cap", type=float, default=2.5)
    ap.add_argument("--out", default="docs/studyhub-evidence/agents/bakeoff")
    args = ap.parse_args()
    s = slice_config.settings()
    configs = []
    if args.local:
        configs.append(("local", "llama"))
    if args.cloud:
        allowed = models.allowed_cloud_models()
        for m in (allowed if args.cloud == "all" else [x.strip() for x in args.cloud.split(",")]):
            if m in allowed:
                configs.append(("cloud", m))
    start = credit(s.api_key) if s.api_key and any(k == "cloud" for k, _ in configs) else None
    results = []
    for kind, model in configs:
        spent = (start - (credit(s.api_key) or start)) if start is not None and kind == "cloud" else 0.0
        if spent > args.spend_cap:
            print(f"STOP: ${spent:.3f} spent, over the ${args.spend_cap} cap"); break
        tokens: list = []
        store, uid, sid = fresh()
        tier = make_tier(kind, model, s, tokens)
        label = tier.label
        n_qa = args.qa or (8 if kind == "local" else len(QUESTIONS))
        # a spread: in-scope first, then the out-of-scope, trap and injection cases
        qs = QUESTIONS[:5] + QUESTIONS[8:11] + QUESTIONS[13:14] if n_qa <= 9 else QUESTIONS[:n_qa]
        print(f"\n=== {label} ===", flush=True)
        t0 = time.time()
        r_qa = eval_qa(store, uid, sid, [tier], qs[:n_qa])
        print(f"  cited answers: in-scope {r_qa['in_scope_ok']} | others {r_qa['others_ok']} | quotes verbatim {r_qa['all_quotes_verbatim']} | {r_qa['mean_seconds']}s each | errors {r_qa['errors']}", flush=True)
        r_p = eval_mcq(store, uid, sid, [tier], args.mcq, mix=False)
        print(f"  practice: {r_p.get('produced')}/{r_p['requested']} kept, {r_p.get('rejected')} rejected, {r_p.get('seconds')}s, quotes in material {r_p.get('quote_in_material')}", flush=True)
        r_m = eval_mcq(store, uid, sid, [tier], args.mix, mix=True) if args.mix else {}
        if r_m:
            print(f"  diagnostic-style: {r_m.get('produced')}/{r_m['requested']} kept, difficulty {r_m.get('difficulty')}, {r_m.get('seconds')}s, quotes in material {r_m.get('quote_in_material')}", flush=True)
        now = credit(s.api_key) if kind == "cloud" and s.api_key else None
        used = round(start - now, 4) if start is not None and now is not None else None
        print(f"  tokens (cloud): {sum(tokens)} | total time {round(time.time() - t0)}s | credit used so far: {('$%.4f' % used) if used is not None else 'n/a'}", flush=True)
        results.append({"model": label, "qa": {k: v for k, v in r_qa.items() if k != "rows"}, "qa_rows": r_qa["rows"], "practice": r_p, "mixed": r_m, "tokens": sum(tokens), "credit_used_total": used})
        store.close()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out + f"-{'local' if args.local and not args.cloud else 'cloud'}.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    end = credit(s.api_key) if start is not None else None
    if start is not None and end is not None:
        print(f"\nOpenRouter credit used by this run: ${start - end:.4f} (${end:.3f} left)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
