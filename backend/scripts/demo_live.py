#!/usr/bin/env python
"""
Live LLM demo: run a study pack with a real model.

Usage:
    # With Ollama (llama3.1:latest must be pulled)
    python scripts/demo_live.py --provider ollama

    # With OpenRouter (OPENROUTER_API_KEY must be set)
    python scripts/demo_live.py --provider openrouter

    # With a custom source file
    python scripts/demo_live.py --provider ollama --source path/to/text.txt

    # Check what providers are available without running
    python scripts/demo_live.py --check

Environment:
    OPENROUTER_API_KEY   required for --provider openrouter
    OLLAMA_BASE_URL      optional, default http://localhost:11434
    OLLAMA_MODEL         optional, default llama3.1:latest
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from demo.study import trace as study_trace
from demo.study.flow import build_flow
from demo.study.samples import SAMPLE
from slice import runner
from slice.config import settings as load_settings
from slice.providers import OllamaProvider, get_provider
from slice.store import Store

SEP = "-" * 80


def check_providers() -> None:
    """Print a quick health check for each provider."""
    cfg = load_settings()
    print("\nProvider health check")
    print(SEP)

    # OpenRouter
    if cfg.api_key:
        print(f"  OpenRouter    CONFIGURED   (key starts: {cfg.api_key[:8]}...)")
    else:
        print("  OpenRouter    NO KEY        (set OPENROUTER_API_KEY)")

    # Ollama
    import httpx
    try:
        r = httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=3.0)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            if cfg.ollama_model in models:
                print(f"  Ollama        READY        ({cfg.ollama_model} available)")
            else:
                print(f"  Ollama        RUNNING      ({cfg.ollama_model} NOT pulled)")
                if models:
                    print(f"                             available: {', '.join(models[:5])}")
        else:
            print(f"  Ollama        ERROR        (HTTP {r.status_code})")
    except httpx.ConnectError:
        print(f"  Ollama        OFFLINE      (start with: ollama serve)")
    except Exception as e:
        print(f"  Ollama        ERROR        ({e})")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a live study-pack generation.")
    ap.add_argument("--provider", choices=["openrouter", "ollama"],
                    default="ollama", help="LLM provider (default: ollama)")
    ap.add_argument("--source", default=None,
                    help="Path to a text file to use as study material")
    ap.add_argument("--check", action="store_true",
                    help="Check provider availability and exit")
    args = ap.parse_args()

    if args.check:
        check_providers()
        return

    cfg = load_settings()
    # Override provider from CLI
    from dataclasses import replace
    cfg = replace(cfg, llm_provider=args.provider)

    # Source material
    if args.source:
        source = Path(args.source).read_text(encoding="utf-8").strip()
    else:
        source = SAMPLE

    print(f"\nStudy Pack Generator — Live Demo ({args.provider})")
    print(SEP)
    print(f"Provider:  {args.provider}")
    if args.provider == "ollama":
        print(f"Model:     {cfg.ollama_model} @ {cfg.ollama_base_url}")
    else:
        print(f"Model:     {cfg.model}")
    print(f"Source:    {len(source.split())} words")
    print(SEP + "\n")

    # Fail early if Ollama is not running
    if args.provider == "ollama":
        import httpx
        try:
            r = httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=3.0)
            models = [m["name"] for m in r.json().get("models", [])]
            if cfg.ollama_model not in models:
                print(f"ERROR: model {cfg.ollama_model!r} is not available in Ollama.")
                print(f"Pull it first:  ollama pull {cfg.ollama_model}")
                print(f"Available:      {', '.join(models) or 'none'}")
                sys.exit(1)
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to Ollama at {cfg.ollama_base_url}")
            print("Start Ollama:   ollama serve")
            sys.exit(1)

    call = get_provider(cfg)
    label = (f"live {args.provider}: {cfg.ollama_model}" if args.provider == "ollama"
             else f"live {args.provider}: {cfg.model}")
    with tempfile.TemporaryDirectory() as d:
        store = Store(str(Path(d) / "live.db"))
        try:
            run_id = store.create_run("study", meta={"mode": label})
            store.append(run_id, "input", {"text": source}, produced_by="demo")
            final = runner.advance(store, run_id, build_flow(call=call), cfg)
            print(study_trace.render_text(store, run_id, color=sys.stdout.isatty()))
        finally:
            store.close()       # Windows cannot delete a SQLite file that is still open

    print(f"\n{SEP}")
    print(f"  Result: {final.value.upper()}")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
