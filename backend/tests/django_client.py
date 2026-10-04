"""An HTTP client for tests, talking to the Django app in-process (no server): httpx over WSGI, the same interface the tests used before."""
from __future__ import annotations

import httpx
from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()


def TestClient(application=None, follow_redirects: bool = False, base_url: str = "http://testserver",  # noqa: N802
               raise_server_exceptions: bool = True) -> httpx.Client:
    """raise_server_exceptions is accepted for compatibility: the API always answers an unexpected error with a JSON 500
    (see core.middleware), and the error is also written to data/server-errors.log."""
    return httpx.Client(transport=httpx.WSGITransport(app=application or app), base_url=base_url, follow_redirects=follow_redirects)
