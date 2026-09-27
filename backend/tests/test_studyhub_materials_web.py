"""StudyHub materials through the real HTTP routes: upload, view, search, delete, and other users. (FRONTEND HTTP test.)"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from studyhub_files import SAMPLE_TXT, encrypt_pdf, make_blank_pdf, make_docx, make_pdf
from test_studyhub_web import (add_subject, csrf_of, env, new_client, session_csrf, sign_in, sign_up,  # noqa: F401
                               subject_id)


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "uploads"))
    return tmp_path / "uploads"


def upload(client, sid, name="ds.txt", data=SAMPLE_TXT.encode(), csrf=None, ctype="application/octet-stream"):
    token = session_csrf(client) if csrf is None else csrf
    return client.post(f"/subjects/{sid}/materials", data={"csrf": token}, files={"file": (name, data, ctype)})


def alice_with_subject():
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    return c, sid


def visible(html: str) -> str:
    """The text a person sees: tags removed (search now wraps matched words in <mark>)."""
    return __import__("html").unescape(re.sub(r"<[^>]+>", "", html))


def doc_path(response) -> str:
    assert response.status_code == 303, response.text
    return response.headers["location"]


def stored_files(uploads: Path):
    return [p for p in uploads.rglob("*") if p.is_file()] if uploads.exists() else []


# --------------------------------------------------------------------------------------------- happy path

def test_upload_a_text_file_then_see_passages_topics_and_search_it(env):
    c, sid = alice_with_subject()
    loc = doc_path(upload(c, sid))
    assert re.fullmatch(rf"/subjects/{sid}/materials/\d+", loc)
    page = c.get(loc).text
    assert "3 passages" in page and "Stacks" in page and "last-in first-out" in page

    subject = c.get(f"/subjects/{sid}").text
    assert "ds" in subject and "Data Structures › Stacks" in subject and "Search your materials" in subject

    found = visible(c.get(f"/subjects/{sid}/search", params={"q": "how does inorder traversal work"}).text)
    assert "Inorder traversal visits the left subtree" in found and "Data Structures › Trees" in found


def test_upload_pdf_and_docx_and_see_page_numbers(env):
    c, sid = alice_with_subject()
    pdf = make_pdf(["Chapter One\nStacks push and pop at the top only.", "Queues serve the oldest element first."],
                   outline=[("Chapter One", 0), ("Queues", 1)], title="Course notes")
    page = c.get(doc_path(upload(c, sid, "notes.pdf", pdf))).text
    assert "Course notes" in page and "2 pages" in page and "p. 1" in page and "p. 2" in page
    hit = visible(c.get(f"/subjects/{sid}/search", params={"q": "oldest element"}).text)
    assert "p. 2" in hit and "Queues serve the oldest" in hit

    docx = make_docx([("Heading 1", "Networks"), ("Normal", "A router forwards packets between networks.")])
    page = c.get(doc_path(upload(c, sid, "net.docx", docx))).text
    assert "1 passages" in page and "router forwards packets" in page


def test_a_scanned_pdf_shows_its_warning_on_the_document_and_the_subject_page(env):
    c, sid = alice_with_subject()
    loc = doc_path(upload(c, sid, "scan.pdf", make_blank_pdf(2)))
    for html in (c.get(loc).text, c.get(f"/subjects/{sid}").text):
        assert "scanned PDF" in html and "OCR is not supported" in html
    assert "No passage" in c.get(f"/subjects/{sid}/search", params={"q": "anything"}).text


def test_an_encrypted_pdf_says_why(env):
    c, sid = alice_with_subject()
    html = c.get(doc_path(upload(c, sid, "locked.pdf", encrypt_pdf(make_pdf(["readable text about graphs"]))))).text
    assert "password-protected" in html


def test_the_same_file_again_is_recognised(env):
    c, sid = alice_with_subject()
    first = doc_path(upload(c, sid))
    second = doc_path(upload(c, sid, "copy.txt"))
    assert second == first + "?dup=1"
    assert "already in this subject" in c.get(second).text
    assert c.get(f"/subjects/{sid}").text.count("class='card'><a href='/subjects/") == 1


def test_search_with_no_match_says_nothing_is_guessed(env):
    c, sid = alice_with_subject()
    upload(c, sid)
    html = c.get(f"/subjects/{sid}/search", params={"q": "photosynthesis"}).text
    assert "Nothing is guessed" in html and "Inorder" not in html
    assert c.get(f"/subjects/{sid}/search", params={"q": ""}).status_code == 200


def test_removing_a_material_removes_it_from_search_and_disk(env, uploads):
    c, sid = alice_with_subject()
    loc = doc_path(upload(c, sid))
    assert len(stored_files(uploads)) == 1
    r = c.post(loc + "/delete", data={"csrf": session_csrf(c)})
    assert r.status_code == 303 and r.headers["location"] == f"/subjects/{sid}"
    assert c.get(loc).status_code == 404
    assert "No passage" in c.get(f"/subjects/{sid}/search", params={"q": "stack"}).text
    assert stored_files(uploads) == []


def test_deleting_the_subject_removes_its_files(env, uploads):
    c, sid = alice_with_subject()
    upload(c, sid)
    r = c.post(f"/subjects/{sid}/delete", data={"csrf": session_csrf(c), "confirm": "yes"})
    assert r.status_code == 303 and stored_files(uploads) == []


# ------------------------------------------------------------------------------------------- refusals

def test_unsupported_and_empty_files_get_a_clear_400(env):
    c, sid = alice_with_subject()
    r = upload(c, sid, "evil.exe", b"MZ" + b"\0" * 64)
    assert r.status_code == 400 and "Only PDF, Word (.docx) and plain-text files" in r.text
    r = upload(c, sid, "empty.txt", b"")
    assert r.status_code == 400 and "empty" in r.text
    r = c.post(f"/subjects/{sid}/materials", data={"csrf": session_csrf(c)})
    assert r.status_code == 422 or r.status_code == 400, "no file field at all"


def test_oversize_uploads_are_refused_both_early_and_late(env, monkeypatch):
    c, sid = alice_with_subject()
    monkeypatch.setenv("STUDYHUB_MAX_UPLOAD_BYTES", "1000")
    r = upload(c, sid, "big.txt", b"word " * 40_000)                      # over limit + slack: 413 before parsing
    assert r.status_code == 413 and "too large" in r.text.lower() and "Content-Security-Policy" in r.headers
    r = upload(c, sid, "mid.txt", b"word " * 300)                         # slightly over: refused by the handler
    assert r.status_code == 400 and "larger than" in r.text


def test_a_post_without_the_csrf_token_stores_nothing(env, uploads):
    c, sid = alice_with_subject()
    assert upload(c, sid, csrf="wrong-token").status_code == 403
    assert c.post(f"/subjects/{sid}/materials", files={"file": ("a.txt", b"some words here", "text/plain")}).status_code == 403
    assert stored_files(uploads) == []
    assert "No materials yet" in c.get(f"/subjects/{sid}").text


def test_signed_out_users_are_sent_to_login_and_nothing_is_stored(env, uploads):
    c, sid = alice_with_subject()
    anon = new_client()
    assert anon.post(f"/subjects/{sid}/materials", data={"csrf": "x"},
                     files={"file": ("a.txt", b"some words here", "text/plain")}).headers["location"] == "/login"
    assert anon.get(f"/subjects/{sid}/search", params={"q": "stack"}).headers["location"] == "/login"
    assert anon.get(f"/subjects/{sid}/materials/1").headers["location"] == "/login"
    assert stored_files(uploads) == []


# --------------------------------------------------------------------------------------- other users

def test_bob_cannot_reach_alices_materials_in_any_way(env, uploads):
    alice, sid = alice_with_subject()
    loc = doc_path(upload(alice, sid))
    bob = new_client()
    sign_up(bob, "bobby")
    token = session_csrf(bob)
    assert bob.get(loc).status_code == 404 and bob.get(f"/subjects/{sid}").status_code == 404
    r = bob.get(f"/subjects/{sid}/search", params={"q": "stack"})
    assert r.status_code == 404 and "last-in first-out" not in r.text
    assert bob.post(loc + "/delete", data={"csrf": token}).status_code == 404
    assert upload(bob, sid, "mine.txt", b"Bob writes words about biology cells here.", csrf=token).status_code == 404
    assert len(stored_files(uploads)) == 1, "bob's upload was not stored, alice's still is"
    assert alice.get(loc).status_code == 200 and "3 passages" in alice.get(loc).text


def test_bobs_own_subject_with_the_same_number_shows_none_of_alices_text(env):
    alice, sid = alice_with_subject()
    upload(alice, sid)
    bob = new_client()
    sign_up(bob, "bobby")
    bsid = subject_id(add_subject(bob, "Mine"))
    upload(bob, bsid, "bio.txt", b"# Cells\n\nThe nucleus stores genetic information in a cell.\n")
    html = bob.get(f"/subjects/{bsid}/search", params={"q": "stack queue tree nucleus"}).text
    assert "nucleus" in html and "last-in first-out" not in html and "Inorder" not in html
    assert bob.get(f"/subjects/{bsid}/materials/1").status_code == 404, "document 1 is alice's: not reachable via bob's subject"
    assert bob.get(f"/subjects/{bsid}/materials/2").status_code == 200, "document 2 is bob's own"


# ------------------------------------------------------------------------------------------- hostile input

def test_hostile_file_names_and_text_are_shown_as_text_and_never_used_as_paths(env, uploads):
    c, sid = alice_with_subject()
    evil = b"# <script>alert(1)</script>\n\nA paragraph with <img src=x onerror=alert(2)> and words about stacks.\n"
    loc = doc_path(upload(c, sid, "../../<script>alert(3)</script>.txt", evil))
    for html in (c.get(loc).text, c.get(f"/subjects/{sid}").text,
                 c.get(f"/subjects/{sid}/search", params={"q": "paragraph stacks"}).text):
        assert "<script>alert" not in html and "<img src=x" not in html
    assert "&lt;img src=x onerror=alert(2)&gt;" in c.get(loc).text
    (only,) = stored_files(uploads)
    assert re.fullmatch(r"[0-9a-f]{64}", only.name) and uploads in only.parents
    assert not list(uploads.parent.glob("*.txt")), "nothing escaped the uploads folder"


def test_search_text_is_escaped_and_cannot_break_the_query(env):
    c, sid = alice_with_subject()
    upload(c, sid)
    for q in ['<script>alert(1)</script>', 'a" OR "b', "stack AND (", "x' OR 1=1 --"]:
        r = c.get(f"/subjects/{sid}/search", params={"q": q})
        assert r.status_code == 200 and "<script>alert" not in r.text


def test_ids_that_are_not_numbers_are_a_404_not_a_crash(env):
    c, sid = alice_with_subject()
    for path in ("/subjects/abc/materials/1", f"/subjects/{sid}/materials/abc", f"/subjects/{sid}/materials/99999999999999",
                 f"/subjects/{sid}/materials/-1", "/subjects/1/materials/1"):
        assert c.get(path).status_code == 404


def test_security_headers_are_on_the_upload_and_view_pages(env):
    c, sid = alice_with_subject()
    r = upload(c, sid)
    page = c.get(r.headers["location"])
    assert "script-src 'none'" in page.headers["content-security-policy"] and page.headers["x-frame-options"] == "DENY"
