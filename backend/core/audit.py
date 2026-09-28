"""Audit log: every state-changing API request (who, what, when, from where, result) is recorded in core_auditlog.

Reads are not logged (they change nothing); request bodies are never stored (they can hold passwords and study material).
"""
from __future__ import annotations

import logging

log = logging.getLogger("nexus")
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


def record(*, user_id: int | None, action: str, method: str = "", path: str = "", status: int = 0, ip: str = "", detail: str = "") -> None:
    """Write one audit row. An audit failure is logged but never breaks the request it describes."""
    from core.models import AuditLog
    try:
        AuditLog.objects.create(user_id=user_id, action=action[:80], method=method, path=path[:300], status=status,
                                ip=ip[:64], detail=detail[:500])
    except Exception:                                     # e.g. a database without the audit table yet (run `migrate`)
        log.warning("audit log write failed for %s %s", method, path, exc_info=True)


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method in MUTATING and request.path.startswith("/api/"):
            from core.http import client_ip
            action = request.path.removeprefix("/api/v1/").split("?")[0]
            record(user_id=getattr(request, "nexus_user_id", None), action=f"{request.method} {action}", method=request.method,
                   path=request.path, status=response.status_code, ip=client_ip(request))
        return response
