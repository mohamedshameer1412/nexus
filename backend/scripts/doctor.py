#!/usr/bin/env python3
"""
doctor.py - Is this environment actually going to work?

Runs automatically when you attach to the Codespace. Run it yourself any time
something feels wrong, and BEFORE you start debugging your own code - most of
what looks like a broken agent is often a broken environment.

Checks, in the order that things actually fail:
  1. .env exists and has a key
  2. the key works and has credit left
  3. the pinned models are reachable RIGHT NOW  (a provider 429 looks exactly
     like a bug in your prompt if you do not check)
  4. sqlite-vec loads
  5. the embedding model is baked into the image
"""
import json, os, sqlite3, sys, urllib.error, urllib.request

API = "https://openrouter.ai/api/v1"
OK, BAD, WARN, SKIP = "  ok  ", " FAIL ", " warn ", " skip "
fails = skips = 0


def line(state, what, detail=""):
    """Report and keep going. A diagnostic that stops at the first problem
    hides the rest of them - which is the opposite of its job."""
    global fails, skips
    if state is BAD:
        fails += 1
    elif state is SKIP:
        skips += 1
    print(f"[{state}] {what}" + (f"\n         {detail}" if detail else ""))


def load_env(path=".env"):
    try:
        for ln in open(path):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
        return True
    except FileNotFoundError:
        return False


def get(path, token, body=None, timeout=45):
    req = urllib.request.Request(
        API + path, data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:    return e.code, json.loads(raw)
        except Exception: return e.code, {"raw": raw.decode(errors="replace")[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


print("\nagentic-slice-kit doctor\n" + "-" * 60)

# 1 --------------------------------------------------------------------------
have_env = load_env()
provider = os.environ.get("LLM_PROVIDER", "openrouter").strip().lower()
key = os.environ.get("OPENROUTER_API_KEY", "").strip()
if have_env:
    line(OK, ".env loaded")
elif provider == "openrouter":
    line(BAD, ".env not found",
         "Run:  cp .env.example .env   then paste your key.\n"
         "         No key? LLM_PROVIDER=ollama runs a local model; LLM_PROVIDER=fixture needs nothing.")
else:
    line(WARN, ".env not found - using environment variables and defaults")
if provider == "openrouter" and have_env and not key:
    line(BAD, "OPENROUTER_API_KEY is empty",
         "Paste the key from the registration desk into .env, then rerun.")
elif provider != "openrouter" and not key:
    line(SKIP, f"OPENROUTER_API_KEY - not needed for LLM_PROVIDER={provider}")

# 2 --------------------------------------------------------------------------
if not key:
    line(SKIP, "credit check - needs a key")
else:
  st, me = get("/key", key)
  if st != 200:
    line(BAD, f"key rejected (HTTP {st})", json.dumps(me)[:160])
  else:
    d = me.get("data", {})
    used, lim = d.get("usage"), d.get("limit")
    if lim:
        left = float(lim) - float(used or 0)
        pct = 100 * left / float(lim)
        line(OK if pct > 25 else WARN,
             f"key works - ${left:.3f} of ${float(lim):.2f} left ({pct:.0f}%)",
             "" if pct > 25 else "Running low. Lower SLICE_MAX_TOKENS or see the desk.")
    else:
        line(OK, f"key works - ${float(used or 0):.3f} used, no cap set")

# 3 --------------------------------------------------------------------------
models_to_check = (("SLICE_MODEL", "SLICE_FALLBACK_MODEL", "SLICE_ESCALATION_MODEL")
                   if (provider == "openrouter" or key) else ())
if not models_to_check:
    line(SKIP, f"cloud model reachability - not needed for LLM_PROVIDER={provider}")
for var in models_to_check:
    mid = os.environ.get(var, "").strip()
    if not mid:
        line(WARN, f"{var} not set"); continue
    if not key:
        line(SKIP, f"{var}={mid} - reachability needs a key"); continue
    if ":batch" in mid or mid.startswith("~"):
        line(BAD, f"{var}={mid}",
             "batch variants are not callable here, and ~latest aliases drift. Pin a version.")
        continue
    st, body = get("/chat/completions", key,
                   {"model": mid, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]})
    if st == 200:
        line(OK, f"{var}={mid} reachable")
    elif st == 429:
        line(WARN, f"{var}={mid} rate-limited right now (429)",
             "Not your code. Retry, or switch to the fallback for a while.")
    elif st == 402:
        line(BAD, f"{var}={mid} refused for credit (402)",
             "Your cap cannot cover this request. Lower SLICE_MAX_TOKENS or top up.")
    else:
        line(BAD, f"{var}={mid} unreachable (HTTP {st})", json.dumps(body)[:160])

# 3b -------------------------------------------------------------------------
# Ollama is REQUIRED when LLM_PROVIDER=ollama and merely reported otherwise, so a
# machine with no key and no local model still gets a clean "fixture only" verdict.
line(OK, f"LLM_PROVIDER={provider}")
if provider not in ("openrouter", "ollama", "fixture"):
    line(BAD, f"LLM_PROVIDER={provider!r} is not recognised",
         "Valid values: openrouter, ollama, fixture.")
ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").strip()
ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.1:latest").strip()
ollama_fallback = os.environ.get("OLLAMA_FALLBACK_MODEL", "").strip()
need_ollama = provider == "ollama"
try:
    req = urllib.request.Request(f"{ollama_url}/api/tags", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        models = [m["name"] for m in json.load(r).get("models", [])]
except (urllib.error.URLError, OSError, ValueError) as e:
    import shutil
    installed = "installed" if shutil.which("ollama") else "not installed"
    if need_ollama:
        line(BAD, f"Cannot reach Ollama at {ollama_url} (binary {installed})",
             "Start it:  ollama serve   (or install from https://ollama.com)")
    else:
        line(SKIP, f"Ollama not running (binary {installed}) - only needed for LLM_PROVIDER=ollama")
else:
    pulled = ", ".join(models[:6]) or "none"
    if not need_ollama:
        line(OK, f"Ollama is running; pulled: {pulled}  (use it with LLM_PROVIDER=ollama)")
    elif ollama_model in models:
        line(OK, f"Ollama running, model {ollama_model!r} available")
    else:
        line(BAD, f"Ollama running but {ollama_model!r} is not pulled",
             f"Pull it yourself (this app never downloads models):  ollama pull {ollama_model}\n"
             f"         Pulled: {pulled}")
    if need_ollama and ollama_fallback:
        if ollama_fallback in models:
            line(OK, f"fallback model {ollama_fallback!r} available")
        else:
            line(WARN, f"OLLAMA_FALLBACK_MODEL={ollama_fallback!r} is not pulled",
                 f"Without it there is no fallback.  ollama pull {ollama_fallback}")

# 4 --------------------------------------------------------------------------
try:
    import sqlite_vec
    db = sqlite3.connect(":memory:")
    db.enable_load_extension(True); sqlite_vec.load(db); db.enable_load_extension(False)
    line(OK, f"sqlite-vec {db.execute('select vec_version()').fetchone()[0]} loads")
except Exception as e:
    line(BAD, "sqlite-vec will not load", str(e)[:160])

# 5 --------------------------------------------------------------------------
try:
    import shutil, subprocess
    exe = shutil.which("cloudflared")
    if not exe:
        line(WARN, "cloudflared not installed",
             "You will not be able to share a public demo URL from this codespace.")
    else:
        v = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
        line(OK, f"cloudflared present ({v.stdout.strip()[:48] or 'version unknown'})")
except Exception as e:
    line(WARN, "cloudflared check failed", str(e)[:120])

# 6 --------------------------------------------------------------------------
cache = os.environ.get("FASTEMBED_CACHE_PATH", "/opt/fastembed")
if os.path.isdir(cache) and any(os.scandir(cache)):
    line(OK, f"embedding model present in the image ({cache})")
else:
    line(WARN, "embedding model not baked in",
         "First ingest will download ~80MB. Fine on good wifi, painful otherwise.")

print("-" * 60)
if fails:
    print(f"{fails} problem(s) above" + (f", {skips} check(s) skipped" if skips else ""))
    print("Fix these BEFORE you start debugging your agent - most of what looks")
    print("like a broken agent is often a broken environment.\n")
elif skips:
    print(f"no failures, {skips} check(s) skipped for want of a key\n")
else:
    print("all clear\n")
sys.exit(1 if fails else 0)
