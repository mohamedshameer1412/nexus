"""Adding a web page as material: the SSRF rules, redirects, text extraction, and the API around it."""
from __future__ import annotations

import socket

import pytest

from studyhub import webfetch
from test_studyhub_api import Api, is_error, quiet, signed_in  # noqa: F401
from test_studyhub_web import env  # noqa: F401

PAGE = ("<html><head><title>Queues &amp; stacks</title><style>p{color:red}</style><script>alert('x')</script></head><body>"
        "<nav>Home | About</nav><h1>Queues</h1><p>A queue is first in, first out. " + "The enqueue operation adds an element at the rear. " * 6 + "</p>"
        "<h2>Stacks</h2><p>A stack is last in, first out. The pop operation removes the top element. " * 3 + "</p><footer>copyright</footer></body></html>").encode()


def fake_resolver(mapping):
    def resolve(host, port, type=None):
        ips = mapping.get(host)
        if ips is None:
            raise socket.gaierror("no such host")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]
    return resolve


PUBLIC = fake_resolver({"example.com": ["93.184.216.34"], "evil.test": ["93.184.216.34", "10.0.0.5"], "lan.test": ["192.168.1.10"], "local.test": ["127.0.0.1"], "other.com": ["8.8.8.8"]})


@pytest.mark.parametrize("ip,ok", [("93.184.216.34", True), ("8.8.8.8", True), ("127.0.0.1", False), ("10.1.2.3", False), ("172.16.0.1", False), ("192.168.0.1", False),
                                   ("169.254.169.254", False), ("100.64.0.1", False), ("0.0.0.0", False), ("224.0.0.1", False), ("::1", False), ("fe80::1", False),
                                   ("fc00::1", False), ("::ffff:127.0.0.1", False), ("::ffff:10.0.0.1", False), ("not an ip", False), ("2606:4700:4700::1111", True)])
def test_only_public_addresses_are_allowed(ip, ok):
    assert webfetch.is_public(ip) is ok


@pytest.mark.parametrize("url", ["ftp://example.com/x", "file:///etc/passwd", "javascript:alert(1)", "http://user:pass@example.com/", "http://example.com:8080/", "http://example.com:22/",
                                 "http://", "example.com", "", "http://exa mple.com/", "https://example.com/\nHost: evil", "http://example.com:99999/"])
def test_addresses_that_are_not_plain_public_web_pages_are_refused(url):
    with pytest.raises(webfetch.FetchError):
        webfetch.check_url(url)


def test_a_name_that_resolves_to_a_private_address_is_refused_even_if_one_address_is_public():
    for host in ("lan.test", "local.test", "evil.test"):
        with pytest.raises(webfetch.FetchError):
            webfetch.resolve_public(host, 80, PUBLIC)
    assert webfetch.resolve_public("example.com", 443, PUBLIC) == "93.184.216.34"
    with pytest.raises(webfetch.FetchError):
        webfetch.resolve_public("missing.test", 80, PUBLIC)


def test_a_redirect_to_an_internal_address_is_refused_and_public_redirects_are_followed():
    calls = []

    def opener(scheme, host, ip, port, target):
        calls.append((host, ip, target))
        if host == "example.com" and target == "/go":
            return 302, {"location": "http://local.test/admin"}, b""
        if host == "example.com" and target == "/ok":
            return 301, {"location": "https://other.com/page?x=1"}, b""
        return 200, {"content-type": "text/html; charset=utf-8"}, PAGE
    with pytest.raises(webfetch.FetchError):
        webfetch.fetch("http://example.com/go", resolver=PUBLIC, opener=opener)
    assert all(h != "local.test" for h, _, _ in calls)                       # the internal host was never contacted
    url, ctype, body, cs = webfetch.fetch("http://example.com/ok", resolver=PUBLIC, opener=opener)
    assert url == "https://other.com/page?x=1" and ctype == "text/html" and calls[-1] == ("other.com", "8.8.8.8", "/page?x=1")   # connected to the checked address
    loop = lambda *a: (302, {"location": "http://example.com/again"}, b"")                                                      # noqa: E731
    with pytest.raises(webfetch.FetchError, match="too many times"):
        webfetch.fetch("http://example.com/again", resolver=PUBLIC, opener=loop)


def test_only_small_html_or_text_pages_are_accepted():
    def with_(status=200, ctype="text/html", body=b"x"):
        return lambda *a: (status, {"content-type": ctype}, body)
    for opener, why in [(with_(404), "error"), (with_(ctype="application/pdf"), "PDF"), (with_(ctype="image/png"), "web pages"),
                        (with_(body=b"x" * (webfetch.MAX_BYTES + 1)), "5 MB")]:
        with pytest.raises(webfetch.FetchError, match=why):
            webfetch.fetch("http://example.com/", resolver=PUBLIC, opener=opener)


def test_the_page_becomes_text_with_headings_and_no_markup():
    title, text = webfetch.html_to_text(PAGE)
    assert title == "Queues & stacks" and text.startswith("# Queues")
    assert "## Stacks" in text and "first in, first out" in text
    for gone in ("<", "alert(", "color:red", "Home | About", "copyright"):
        assert gone not in text
    assert webfetch.html_to_text("Plain words".encode(), "utf-8", "text/plain") == ("", "Plain words")


def test_a_web_page_is_added_like_an_upload_and_the_api_is_guarded(env, monkeypatch):  # noqa: F811
    seen = []

    def fake_fetch(url, **kw):
        seen.append(url)
        if "bad" in url:
            raise webfetch.FetchError("That address is not a public web page.")
        return url, "text/html", PAGE, "utf-8"
    monkeypatch.setattr(webfetch, "fetch", fake_fetch)
    a = signed_in("alice")
    sid = a.subject("Web")
    r = a.req("POST", f"/subjects/{sid}/materials/url", json={"url": "https://example.com/queues"})
    assert r.status_code == 201, r.text
    doc = r.json()["document"]
    assert doc["kind"] == "url" and doc["source"] == "https://example.com/queues" and doc["chunks"] >= 1 and doc["title"]
    assert a.req("POST", f"/subjects/{sid}/materials/url", json={"url": "https://example.com/queues"}).json()["duplicate"] is True
    assert is_error(a.req("POST", f"/subjects/{sid}/materials/url", json={"url": "http://bad.example/x"}), 400, "upload_refused")
    assert is_error(a.req("POST", f"/subjects/{sid}/materials/url", csrf=False, json={"url": "https://example.com/z"}), 403, "csrf")
    assert is_error(a.req("GET", f"/subjects/{sid}/materials/{doc['id']}/file"), 404, "not_found")             # no stored original to show
    b = signed_in("bob")
    assert is_error(b.req("POST", f"/subjects/{sid}/materials/url", json={"url": "https://example.com/other"}), 404, "not_found")
    assert is_error(Api().req("POST", f"/subjects/{sid}/materials/url", json={"url": "https://example.com/x"}), 401, "unauthenticated")
    assert len(seen) == 3                                                                                        # bob's and the signed-out call never fetched
