"""Request/response rules for the whole backend.

  * Only /api/, /admin/, /static/ and /healthz are served. Other GETs are sent to the web app (NEXUS_PUBLIC_URL); anything else is a 404.
  * An upload larger than STUDYHUB_MAX_UPLOAD_BYTES is refused before the body is read (413).
  * Security headers on every response; unexpected errors are logged to data/server-errors.log and answered with a reference
    (never a bare "Internal Server Error").
"""
from __future__ import annotations

import logging
import secrets
import time
import traceback
from pathlib import Path

from django.http import HttpResponseRedirect, JsonResponse

from core.http import err
from studyhub import settings

SERVED = ("/api/", "/admin", "/static/", "/healthz")
log = logging.getLogger("nexus")


class ApiMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith(SERVED):
            from studyhub import mailer
            response = (HttpResponseRedirect(mailer.public_url() + "/") if request.method == "GET"
                        else JsonResponse({"error": {"code": "not_found", "message": "Not found."}}, status=404))
            response["Cache-Control"] = "no-store"
            return response
        declared = request.META.get("CONTENT_LENGTH", "")
        if declared.isdigit() and int(declared) > settings.max_upload_bytes() + 64 * 1024:
            limit = settings.max_upload_bytes() / 1048576
            response = err(413, "too_large", f"That upload is too large. The limit is {limit:.3g} MB per file.")
        else:
            response = self.get_response(request)
        return self._harden(path, response)

    @staticmethod
    def _harden(path: str, response):
        if path.startswith("/api/"):
            if response.get("X-Nexus-Frameable") == "1":       # the officer's own uploaded file, shown by our own viewer
                del response["X-Nexus-Frameable"]
                response["Content-Security-Policy"] = "frame-ancestors 'self'"
                response["X-Frame-Options"] = "SAMEORIGIN"
            else:
                response["Content-Security-Policy"] = ("default-src 'self'; style-src 'unsafe-inline'; script-src 'none'; form-action 'self'; "
                                                   "frame-ancestors 'none'; base-uri 'none'")
                response["X-Frame-Options"] = "DENY"
            response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "same-origin"
        return response

    def process_exception(self, request, exc):
        ref = secrets.token_hex(3)
        try:
            out = Path(settings.db_path()).parent / "server-errors.log"
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ref {ref} {request.method} {request.path}\n"
                        f"{''.join(traceback.format_exception(exc))}\n")
        except Exception:
            log.exception("unexpected error %s", ref)
        if request.path.startswith("/api/"):
            return err(500, "server_error", f"Something went wrong on our side. Please try again in a moment. (reference {ref})")
        return None
