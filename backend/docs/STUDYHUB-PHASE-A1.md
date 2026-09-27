# StudyHub — Phase A1 report: accounts, sessions, subjects

Scope (from [STUDYHUB-DESIGN.md](STUDYHUB-DESIGN.md) §11): register / login / logout, per-user subjects, ownership
enforced in SQL. **Not in this phase:** uploads, Q&A, quizzes, progress.

## What exists

| Piece | File |
|---|---|
| Settings from environment | `studyhub/settings.py` |
| Schema + migrations (one SQLite file, shared with the `slice/` spine) | `studyhub/db.py` |
| Password hashing (scrypt), throttling, sessions | `studyhub/auth.py` |
| Subject CRUD, every query filtered by `user_id` | `studyhub/repo.py` |
| Server-rendered pages (no JavaScript) and routes | `studyhub/web/ui.py`, `studyhub/web/app.py` |

Run it: `uvicorn studyhub.web.app:app --port 8100` (database: `data/studyhub.db`, or set `STUDYHUB_DB`).

## Evidence

**Automated:** 86 new tests (`test_studyhub_auth` 39, `test_studyhub_repo` 13, `test_studyhub_web` 34).
Full suite: **429 passed, 4 skipped, 0 failed** (the 4 skips are the earlier live-model tests that need a running model).

**Real browser:** Microsoft Edge 153 (headless, driven over the DevTools protocol) against a real `uvicorn` process,
at the production scrypt cost (n=32768), on a fresh database. **19/19 checks passed**; full log in
[studyhub-evidence/a1/studyhub_a1_browser.txt](studyhub-evidence/a1/studyhub_a1_browser.txt), screenshots and the harness
in the same folder. What it covered:

- signed-out visitors are redirected to the login page; register lands on the subjects page (about 0.6 s including scrypt)
- session cookie is `HttpOnly`, `SameSite=Lax`, path `/`; page JavaScript cannot read it
- create / rename subjects; a subject named `<img src=x onerror=alert(1)>` is displayed as text (0 `<img>` and 0 `<script>` elements)
- logout removes the cookie; **putting the old cookie back does not log in** (sessions are deleted server-side)
- wrong password and unknown user give the identical message
- a second user sees none of the first user's subjects, and opening the first user's subject URL returns **404** with no information
- a POST without the CSRF token returns 403
- CSP (`script-src 'none'`), `X-Frame-Options: DENY`, `nosniff` reach the browser
- 0 JavaScript errors

**Database inspected directly:** two users, 32-byte hashes with the scrypt parameters stored per row, the test password
does not appear anywhere in the file, the sessions table holds only hashes of tokens.

## Found while testing, and fixed

- The screenshot showed link text (dark teal) nearly unreadable on a dark background. Added dark-mode colours for links,
  muted text and error boxes, then re-ran the browser test (still 19/19) and re-checked the screenshot.

## Not verified / known limits

- The `Secure` cookie flag is covered by an HTTPS test client in the unit tests, not by a real HTTPS browser session
  (the local server is plain HTTP). Set `STUDYHUB_COOKIE_SECURE=1` behind HTTPS.
- Only Edge was used; no Firefox or Safari run.
- Login throttling is keyed on username and on IP as seen by the server; behind a reverse proxy the IP will be the proxy's
  until forwarded-header handling is added.
- No password reset and no e-mail verification (out of scope for A1).
- No load or concurrency testing beyond SQLite's default behaviour.
