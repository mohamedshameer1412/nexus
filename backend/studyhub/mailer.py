"""Sending e-mail (one place). Settings come from .env: EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
DEFAULT_FROM_EMAIL, and EMAIL_DEBUG (with no SMTP settings, messages are written to data/outbox/ instead of being sent).

The password is read from the environment and never logged, stored, or put in a message. Recipients and subjects are checked for
line breaks so a crafted value cannot add headers.
"""
from __future__ import annotations

import logging
import os
import re
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from slice import config as slice_config

log = logging.getLogger("nexus.mail")
_ADDRESS = re.compile(r"^[A-Za-z0-9._%+'-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}$")
_loaded = False


def _env(name: str, default: str = "") -> str:
    global _loaded
    if not _loaded:
        try:
            if not os.environ.get("PYTEST_CURRENT_TEST"):          # a test must never pick up (and use) the real mail account from .env
                slice_config.load_env()
        except Exception:
            pass
        _loaded = True
    return os.environ.get(name, default).strip()


def valid_address(address: str) -> bool:
    return bool(address) and len(address) <= 254 and bool(_ADDRESS.match(address))


def configured() -> bool:
    return bool(_env("EMAIL_HOST") and _env("EMAIL_HOST_USER") and _env("EMAIL_HOST_PASSWORD"))


def debug_outbox() -> bool:
    return _env("EMAIL_DEBUG").lower() in ("1", "true", "yes")


def public_url() -> str:
    return (_env("NEXUS_PUBLIC_URL") or "http://localhost:3000").rstrip("/")


def send(to: str, subject: str, text: str, html: str) -> str:
    """Returns "sent", "outbox" (written to a file, debug only), "unconfigured" or "failed". Never raises."""
    if not valid_address(to) or "\n" in subject or "\r" in subject:
        return "failed"
    sender = _env("DEFAULT_FROM_EMAIL") or _env("EMAIL_HOST_USER")
    msg = EmailMessage()
    msg["Subject"], msg["To"], msg["Date"], msg["Message-ID"] = subject, to, formatdate(localtime=True), make_msgid(domain="nexus.local")
    msg["From"] = formataddr(("Nexus", sender)) if valid_address(sender) else "Nexus <noreply@nexus.local>"
    msg["Auto-Submitted"], msg["X-Auto-Response-Suppress"] = "auto-generated", "All"
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    if not configured():
        if debug_outbox():
            folder = Path(os.environ.get("STUDYHUB_DB", "data/studyhub.db")).parent / "outbox"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{int(time.time() * 1000)}.eml").write_bytes(bytes(msg))
            return "outbox"
        return "unconfigured"
    try:
        port = int(_env("EMAIL_PORT", "587") or 587)
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(_env("EMAIL_HOST"), port, timeout=15, context=context) as smtp:
                smtp.login(_env("EMAIL_HOST_USER"), _env("EMAIL_HOST_PASSWORD"))
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(_env("EMAIL_HOST"), port, timeout=15) as smtp:
                smtp.ehlo()
                if _env("EMAIL_USE_TLS", "True").lower() in ("1", "true", "yes"):
                    smtp.starttls(context=context)
                    smtp.ehlo()
                smtp.login(_env("EMAIL_HOST_USER"), _env("EMAIL_HOST_PASSWORD"))
                smtp.send_message(msg)
        return "sent"
    except Exception as e:                        # the reason is logged without the message body or any secret
        log.warning("e-mail to a user failed: %s", type(e).__name__)
        return "failed"
