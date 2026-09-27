"""The original-file viewer endpoint and the notes API: ownership, safe headers, notes built from stored answers."""
from __future__ import annotations

import studyhub.web.app as appmod
from studyhub_files import SAMPLE_TXT, make_pdf
from test_studyhub_api import Api, is_error, quiet, signed_in, use_models  # noqa: F401
from test_studyhub_web import env  # noqa: F401


def doc_id(a, sid, name="ds.txt", data=SAMPLE_TXT.encode()):
    return a.upload(sid, name=name, data=data).json()["document"]["id"]


def test_the_original_file_is_served_to_its_owner_only_and_can_be_framed_by_our_own_pages(env):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Mine")
    pdf = make_pdf(["Page one about stacks and queues in data structures.\n" * 4, "Page two about trees."])
    pid, tid = doc_id(a, sid, "book.pdf", pdf), doc_id(a, sid)
    r = a.req("GET", f"/subjects/{sid}/materials/{pid}/file")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content == pdf
    assert r.headers["content-disposition"].startswith("inline") and r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "SAMEORIGIN" and r.headers["content-security-policy"] == "frame-ancestors 'self'"
    assert "x-nexus-frameable" not in r.headers
    t = a.req("GET", f"/subjects/{sid}/materials/{tid}/file")
    assert t.headers["content-type"].startswith("text/plain") and b"stack" in t.content.lower()
    other = a.req("GET", f"/subjects/{sid}/materials")
    assert other.headers["x-frame-options"] == "DENY"                                # every other response still refuses framing
    b = signed_in("bob")
    assert is_error(b.req("GET", f"/subjects/{sid}/materials/{pid}/file"), 404, "not_found")
    assert is_error(b.req("GET", f"/subjects/{b.subject('Mine')}/materials/{pid}/file"), 404, "not_found")
    assert is_error(Api().req("GET", f"/subjects/{sid}/materials/{pid}/file"), 401, "unauthenticated")


def test_answers_carry_the_document_they_came_from_so_the_viewer_can_open_it(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    use_models(monkeypatch)
    a = signed_in("alice")
    sid = a.subject("Mine")
    did = doc_id(a, sid)
    qid = a.req("POST", f"/subjects/{sid}/questions", json={"question": "how does the enqueue operation work in a queue"}).json()["id"]
    q = a.req("GET", f"/subjects/{sid}/questions/{qid}").json()
    assert q["sources"] and all(s["document_id"] == did for s in q["sources"])


def test_notes_are_written_edited_deleted_and_private(env):  # noqa: F811
    a = signed_in("alice")
    sid = a.subject("Mine")
    assert a.req("GET", f"/subjects/{sid}/notes").json() == {"notes": []}
    assert is_error(a.req("POST", f"/subjects/{sid}/notes", json={"title": "  ", "body": ""}), 400, "invalid")
    n = a.req("POST", f"/subjects/{sid}/notes", json={"title": "Stacks", "body": "LIFO: **last in, first out**."})
    assert n.status_code == 201 and n.json()["source"] == "own" and n.json()["body"].startswith("LIFO")
    nid = n.json()["id"]
    assert a.req("POST", f"/subjects/{sid}/notes", json={"title": "", "body": "only text here"}).json()["title"] == "only text here"
    assert a.req("PUT", f"/subjects/{sid}/notes/{nid}", json={"title": "Stacks 2", "body": "changed"}).json()["title"] == "Stacks 2"
    assert [x["snippet"] for x in a.req("GET", f"/subjects/{sid}/notes").json()["notes"]][0] == "changed"     # newest edit first
    assert "body" not in a.req("GET", f"/subjects/{sid}/notes").json()["notes"][0]                            # the list is light
    assert is_error(a.req("POST", f"/subjects/{sid}/notes", csrf=False, json={"title": "x"}), 403, "csrf")
    b = signed_in("bob")
    bs = b.subject("Mine")
    assert is_error(b.req("GET", f"/subjects/{sid}/notes"), 404, "not_found")
    assert is_error(b.req("GET", f"/subjects/{bs}/notes/{nid}"), 404, "not_found")            # right subject, someone else's note
    assert is_error(b.req("PUT", f"/subjects/{bs}/notes/{nid}", json={"title": "x", "body": "y"}), 404, "not_found")
    assert is_error(b.req("DELETE", f"/subjects/{bs}/notes/{nid}"), 404, "not_found")
    assert a.req("DELETE", f"/subjects/{sid}/notes/{nid}").status_code == 204
    assert is_error(a.req("GET", f"/subjects/{sid}/notes/{nid}"), 404, "not_found")


def test_chat_answers_become_a_note_built_on_the_server_from_the_stored_answer(env, monkeypatch):  # noqa: F811
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    use_models(monkeypatch)
    a = signed_in("alice")
    sid = a.subject("Mine")
    doc_id(a, sid)
    q1 = a.req("POST", f"/subjects/{sid}/questions", json={"question": "how does the enqueue operation work in a queue"}).json()["id"]
    q2 = a.req("POST", f"/subjects/{sid}/questions", json={"question": "what is photosynthesis in plants"}).json()["id"]   # not answered
    assert is_error(a.req("POST", f"/subjects/{sid}/notes/from-answers", json={"doubt_ids": [q2]}), 400, "invalid")
    assert is_error(a.req("POST", f"/subjects/{sid}/notes/from-answers", json={"doubt_ids": []}), 404, "not_found")
    assert is_error(a.req("POST", f"/subjects/{sid}/notes/from-answers", json={"doubt_ids": [q1, 99999]}), 404, "not_found")
    r = a.req("POST", f"/subjects/{sid}/notes/from-answers", json={"doubt_ids": [q1, q2]}).json()
    assert r["source"] == "chat" and "enqueue" in r["body"].lower() and "photosynthesis" not in r["body"]
    b = signed_in("bob")
    bs = b.subject("Mine")
    assert is_error(b.req("POST", f"/subjects/{bs}/notes/from-answers", json={"doubt_ids": [q1]}), 404, "not_found")   # someone else's answer
    assert "notes" in a.req("GET", "/account/export").json()["subjects"][0]
