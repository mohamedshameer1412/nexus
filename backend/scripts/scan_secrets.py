"""Stops a commit that would contain a secret. Used by .githooks/pre-commit (turn it on once with:  git config core.hooksPath .githooks).

Looks only at what is being committed (the staged additions), never prints the secret itself, and exits 1 when it finds one.
    python scripts/scan_secrets.py            # scan the staged changes
    python scripts/scan_secrets.py --history  # scan every commit already made (prints counts and commit ids only)
"""
from __future__ import annotations

import re
import subprocess
import sys

PATTERNS = {
    "OpenRouter key": re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),
    "API key (sk-...)": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "mail/app password assignment": re.compile(r"(?im)^\+?[ 	]*(EMAIL_HOST_PASSWORD|SMTP_PASSWORD|OPENROUTER_API_KEY|SECRET_KEY)[ 	]*=[ 	]*(?!sk-or-v1-\.\.\.)(?!your|changeme|<|xxx|\.\.\.)[^\s#\"'(]{8,}[ 	]*$"),
}
FORBIDDEN_PATHS = re.compile(r"(^|/)\.env($|\.local$|\.production$)|\.db$|\.sqlite3?$|(^|/)otp\.key$")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def scan_text(text: str) -> list[str]:
    return sorted({name for name, rx in PATTERNS.items() if rx.search(text)})


def staged() -> int:
    bad = []
    for path in git("diff", "--cached", "--name-only", "--diff-filter=ACM").splitlines():
        if FORBIDDEN_PATHS.search(path) and not path.endswith(".env.example"):
            bad.append((path, "a file that must never be committed (.env, database, key file)"))
    diff = git("diff", "--cached", "-U0", "--no-color")
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for name in scan_text(line):
                bad.append((current, name))
    if bad:
        print("\nCOMMIT BLOCKED: a secret would be committed.\n", file=sys.stderr)
        for path, why in sorted(set(bad)):
            print(f"  - {path}: {why}", file=sys.stderr)
        print("\nMove it to the git-ignored .env file, leave a placeholder in the tracked file, then commit again.\n", file=sys.stderr)
        return 1
    return 0


def history() -> int:
    found = []
    for commit in git("rev-list", "--all").split():
        names = scan_text("\n".join(l for l in git("show", "--no-color", "-U0", "--format=", commit).splitlines() if l.startswith("+") and not l.startswith("+++")))
        if names:
            found.append((commit[:8], names))
    print("commits with a secret-looking value:", found or "none")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(history() if "--history" in sys.argv else staged())
