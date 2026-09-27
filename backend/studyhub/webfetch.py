"""Fetching a web page for a student's materials, without letting a URL reach anything inside our own network (SSRF).

Rules, all checked in code:
  * http or https only, no user:password in the address, ports 80 and 443 only;
  * the host name is resolved HERE and EVERY address must be public (no loopback, private, link-local, carrier-grade NAT, multicast,
    reserved or unspecified ranges, including IPv4-mapped IPv6); the connection then goes to that exact address, so the name cannot
    resolve differently a moment later (DNS rebinding);
  * redirects are followed by us, at most 3, and every hop is checked again from the start;
  * the answer is read up to 5 MB, no compression (so no decompression bombs), 10 seconds per request;
  * only HTML and plain text are accepted. The result is text with headings, never markup: scripts, styles and page furniture are dropped.
"""
from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
import urllib.parse
from html.parser import HTMLParser

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 10.0
MAX_REDIRECTS = 3
USER_AGENT = "NexusStudy/1.0 (+fetching a page a student added as study material)"


class FetchError(ValueError):
    """A reason the student can read."""


def is_public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return bool(addr.is_global) and not (addr.is_multicast or addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved or addr.is_unspecified)


def resolve_public(host: str, port: int, resolver=socket.getaddrinfo) -> str:
    """One public address for the host, or FetchError. Refuses when ANY address it resolves to is not public."""
    try:
        infos = resolver(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError):
        raise FetchError("That web address could not be found.") from None
    ips = [i[4][0] for i in infos]
    if not ips or not all(is_public(ip) for ip in ips):
        raise FetchError("That address is not a public web page.")
    return ips[0]


def check_url(url: str) -> urllib.parse.SplitResult:
    url = (url or "").strip()
    if not url or len(url) > 2000 or any(c in url for c in "\r\n\t "):
        raise FetchError("Enter a full web address, like https://example.com/page.")
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https"):
        raise FetchError("Only http:// and https:// addresses can be added.")
    if not p.hostname or p.username or p.password:
        raise FetchError("That web address is not valid.")
    try:
        port = p.port or (443 if p.scheme == "https" else 80)
    except ValueError:
        raise FetchError("That web address is not valid.") from None
    if port not in (80, 443):
        raise FetchError("Only the standard web ports (80 and 443) are allowed.")
    return p


class _Pinned(http.client.HTTPConnection):
    """Connects to a chosen address (not a name), but still speaks to the named host (Host header and TLS name)."""

    def __init__(self, host, port, ip, tls, timeout):
        super().__init__(host, port, timeout=timeout)
        self._ip, self._tls = ip, tls

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), timeout=self.timeout)
        self.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host) if self._tls else sock


def open_pinned(scheme: str, host: str, ip: str, port: int, target: str) -> tuple[int, dict, bytes]:
    conn = _Pinned(host, port, ip, scheme == "https", TIMEOUT)
    try:
        conn.request("GET", target, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9", "Accept-Encoding": "identity", "Connection": "close"})
        resp = conn.getresponse()
        headers = {k.lower(): v for k, v in resp.getheaders()}
        body = resp.read(MAX_BYTES + 1) if resp.status == 200 else b""
        return resp.status, headers, body
    except (OSError, http.client.HTTPException):
        raise FetchError("That page could not be reached.") from None
    finally:
        conn.close()


def fetch(url: str, *, resolver=socket.getaddrinfo, opener=open_pinned) -> tuple[str, str, bytes, str]:
    """(final url, content type, body bytes, charset). Raises FetchError with a message for the student."""
    for _ in range(MAX_REDIRECTS + 1):
        p = check_url(url)
        port = p.port or (443 if p.scheme == "https" else 80)
        ip = resolve_public(p.hostname, port, resolver)
        target = (p.path or "/") + (f"?{p.query}" if p.query else "")
        status, headers, body = opener(p.scheme, p.hostname, ip, port, target)
        if status in (301, 302, 303, 307, 308) and headers.get("location"):
            url = urllib.parse.urljoin(url, headers["location"])
            continue
        if status != 200:
            raise FetchError(f"The page answered with an error ({status}).")
        if len(body) > MAX_BYTES:
            raise FetchError("That page is larger than 5 MB.")
        ctype = headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype not in ("text/html", "application/xhtml+xml", "text/plain"):
            raise FetchError("Only web pages and plain text can be added. For a PDF or Word file, download it and upload it instead.")
        m = re.search(r"charset=([\w-]+)", headers.get("content-type", ""), re.I)
        return url, ctype, body, (m.group(1) if m else "utf-8")
    raise FetchError("That page redirects too many times.")


# ---------------------------------------------------------------------------------------------- HTML to text

_SKIP = {"script", "style", "noscript", "template", "svg", "iframe", "object", "embed", "canvas", "form", "nav", "footer", "header", "aside", "button", "select", "textarea"}
_BLOCK = {"p", "div", "section", "article", "main", "ul", "ol", "table", "tr", "br", "blockquote", "pre", "figure", "dl"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False
        self._heading = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif re.fullmatch(r"h[1-6]", tag):
            self._heading = int(tag[1])
            self.parts.append("\n\n" + "#" * self._heading + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in _BLOCK:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag == "title":
            self._in_title = False
        elif re.fullmatch(r"h[1-6]", tag):
            self._heading = 0
            self.parts.append("\n\n")
        elif tag in _BLOCK or tag == "li":
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.parts.append(data)


def html_to_text(body: bytes, charset: str = "utf-8", ctype: str = "text/html") -> tuple[str, str]:
    """(title, readable text with # headings). No markup survives."""
    try:
        text = body.decode(charset, errors="replace")
    except LookupError:
        text = body.decode("utf-8", errors="replace")
    if ctype == "text/plain":
        return "", text.strip()
    parser = _Text()
    parser.feed(text)
    out = "".join(parser.parts)
    out = re.sub(r"[ \t\f\v ]+", " ", out)
    out = re.sub(r" *\n *", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    title = " ".join(parser.title.split())[:200]
    if title and not out.lstrip().startswith("#"):
        out = f"# {title}\n\n{out}"
    return title, out
