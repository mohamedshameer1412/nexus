"""StudyHub Q&A through the real HTTP routes. (FRONTEND HTTP test with SCRIPTED models: no network, no real model.)"""
from __future__ import annotations

import re
import time

import pytest
from fastapi.testclient import TestClient

import studyhub.web.app as appmod
from slice.providers import ProviderTimeout
from studyhub.citations import Answer, Citation, Claim
from studyhub.db import open_db
from studyhub.repo import Repo
from studyhub_files import SAMPLE_TXT, make_pdf
from test_studyhub_materials_web import doc_path, stored_files, upload, visible  # noqa: F401
from test_studyhub_qa import GOOD, Q_ENQ, Scripted, tier
from test_studyhub_web import add_subject, env, new_client, session_csrf, sign_up, subject_id  # noqa: F401

QUESTION = "how does the enqueue operation work in a queue"


@pytest.fixture(autouse=True)
def quiet(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    for k in ("OPENROUTER_API_KEY", "STUDYHUB_LOCAL_MODEL"):
        monkeypatch.delenv(k, raising=False)


def use_models(monkeypatch, *tiers, notes=()):
    """Make the app answer with these scripted tiers."""
    monkeypatch.setattr(appmod, "tier_factory", lambda db, user: (list(tiers), list(notes)))


def alice_ready(text=SAMPLE_TXT.encode(), name="ds.txt"):
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    upload(c, sid, name, text)
    return c, sid


def ask(c, sid, q=QUESTION, csrf=None):
    return c.post(f"/subjects/{sid}/ask", data={"question": q, "csrf": session_csrf(c) if csrf is None else csrf})


# ------------------------------------------------------------------------------------------ answered

def test_an_answer_shows_the_statement_its_exact_quote_and_how_it_was_produced(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted(GOOD)))
    c, sid = alice_ready()
    r = ask(c, sid)
    assert r.status_code == 303 and re.fullmatch(rf"/subjects/{sid}/questions/\d+", r.headers["location"])
    html = c.get(r.headers["location"]).text
    page = visible(html)
    assert "Answered from your materials" in page and "Enqueue adds an element at the rear of a queue." in page
    assert "<blockquote>The enqueue operation adds an element at the rear</blockquote>" in html
    assert "found in your material (checked by the app)" in page and "[1]" in page
    assert "Data Structures › Queues" in page and "local model" in page
    assert "How this was produced" in page and "Searched only this subject's materials" in page
    assert "Checked every quote against the passages (by the app, not by a model). Verified: 1." in page


def test_a_pdf_source_shows_its_pdf_page(env, monkeypatch):
    pdf = make_pdf(["Intro\nStacks push and pop at the top only.", "The enqueue operation adds an element at the rear of the queue."],
                   outline=[("Intro", 0), ("Queues", 1)], title="Notes")
    c, sid = alice_ready(pdf, "n.pdf")
    use_models(monkeypatch, tier("local", Scripted(Answer(claims=[Claim(text="Enqueue adds at the rear.", citations=[Citation(passage=1, quote=Q_ENQ)])]))))
    page = visible(c.get(ask(c, sid).headers["location"]).text)
    assert "PDF p. 2" in page and "Notes" in page


def test_the_question_appears_in_the_history_on_the_subject_page(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted(GOOD)))
    c, sid = alice_ready()
    ask(c, sid)
    page = visible(c.get(f"/subjects/{sid}").text)
    assert "Your recent questions" in page and QUESTION in page and "Answered from your materials" in page


# ------------------------------------------------------------------------------- not answered, honestly

def test_an_unrelated_question_is_not_answered_and_no_model_is_called(env, monkeypatch):
    model = Scripted()
    use_models(monkeypatch, tier("local", model))
    c, sid = alice_ready()
    html = c.get(ask(c, sid, "what is photosynthesis in plants").headers["location"]).text
    page = visible(html)
    assert "Not answered: nothing was guessed" in page and "Nothing was guessed." in page
    assert "Answer" not in re.findall(r"<h2>(.*?)</h2>", html) and model.calls == 0


def test_a_weakly_related_question_shows_the_closest_passages_verbatim(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted()))
    c, sid = alice_ready()
    page = visible(c.get(ask(c, sid, "what is the enqueue speed of hash tables in databases").headers["location"]).text)
    assert "Closest passages" in page and "The enqueue operation adds an element at the rear" in page.replace("\n", " ")


def test_when_no_model_is_available_the_matching_passages_are_shown(env, monkeypatch):
    use_models(monkeypatch, notes=["the local model is switched off"])
    c, sid = alice_ready()
    page = visible(c.get(ask(c, sid).headers["location"]).text)
    assert "No model: matching passages only" in page and "No language model is available" in page and "Passages that match" in page


def test_a_model_that_times_out_and_no_cloud_falls_back_to_passages(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted(ProviderTimeout("no answer in 600s"))))
    c, sid = alice_ready()
    page = visible(c.get(ask(c, sid).headers["location"]).text)
    assert "could not be reached" in page and "ProviderTimeout" in page and "Passages that match" in page


def test_an_unexpected_crash_shows_a_friendly_failure_not_a_traceback(env, monkeypatch):
    def boom(db, user):
        raise RuntimeError("secret internal detail /etc/passwd")
    monkeypatch.setattr(appmod, "tier_factory", boom)
    c, sid = alice_ready()
    html = c.get(ask(c, sid).headers["location"]).text
    assert "Something went wrong" in html and "secret internal detail" not in html and "Traceback" not in html


def test_statements_that_failed_verification_are_left_out_and_counted(env, monkeypatch):
    mixed = Answer(claims=[Claim(text="Enqueue adds an element at the rear of a queue.", citations=[Citation(passage=1, quote=Q_ENQ)]),
                           Claim(text="A queue can hold 64 elements at most.", citations=[Citation(passage=1, quote=Q_ENQ)])])
    monkeypatch.setenv("STUDYHUB_QA_MAX_REVISIONS", "0")
    use_models(monkeypatch, tier("local", Scripted(mixed)))
    c, sid = alice_ready()
    page = visible(c.get(ask(c, sid).headers["location"]).text)
    assert "1 other statement the model wrote could not be verified" in page and "64 elements" not in page


# -------------------------------------------------------------------------------------- background worker

def test_the_real_background_worker_answers_while_the_page_polls(env, monkeypatch):
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "0")
    monkeypatch.setattr(appmod, "_worker", None)

    class Slow(Scripted):
        def __call__(self, **kw):
            time.sleep(0.6)
            return super().__call__(**kw)
    use_models(monkeypatch, tier("local", Slow(GOOD)))
    c, sid = alice_ready()
    loc = ask(c, sid).headers["location"]
    first = c.get(loc).text
    assert "http-equiv='refresh'" in first and "Working on it" in first and "Answered" not in visible(first)
    for _ in range(50):
        html = c.get(loc).text
        if "http-equiv='refresh'" not in html:
            break
        time.sleep(0.2)
    assert "Answered from your materials" in html and "Enqueue adds an element" in visible(html)


def test_a_question_left_pending_by_a_restart_is_failed_at_startup(env):
    c, sid = alice_ready()
    store = open_db()
    repo = Repo(store.db)
    did = repo.create_doubt(1, sid, "interrupted question here")
    store.close()
    with TestClient(appmod.app):                                             # runs the startup hook
        pass
    store = open_db()
    d = Repo(store.db).get_doubt(1, sid, did)
    store.close()
    assert d["status"] == "failed" and "interrupted" in d["reason"]


def test_a_pending_page_polls_and_a_user_cannot_pile_up_questions(env, monkeypatch):
    c, sid = alice_ready()
    store = open_db()
    repo = Repo(store.db)
    ids = [repo.create_doubt(1, sid, f"waiting question number {i}") for i in range(2)]
    store.close()
    page = c.get(f"/subjects/{sid}/questions/{ids[0]}").text
    assert "http-equiv='refresh'" in page and "Reading your materials" in page
    r = ask(c, sid)
    assert r.status_code == 400 and "already have questions being answered" in visible(r.text)


# ------------------------------------------------------------------------------------------- validation

@pytest.mark.parametrize("q,msg", [("", "Type your question"), ("  ", "Type your question"), ("hi", "Type your question"),
                                   ("x " * 400, "under 500")])
def test_bad_questions_are_refused_and_nothing_is_stored(env, monkeypatch, q, msg):
    use_models(monkeypatch, tier("local", Scripted()))
    c, sid = alice_ready()
    r = ask(c, sid, q)
    assert r.status_code == 400 and msg in visible(r.text)
    assert "Your recent questions" not in r.text


def test_the_ask_form_needs_material_first(env):
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    assert "Upload some material first" in visible(c.get(f"/subjects/{sid}").text)


def test_a_post_without_the_csrf_token_creates_nothing(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted()))
    c, sid = alice_ready()
    assert ask(c, sid, csrf="nope").status_code == 403
    assert c.post(f"/subjects/{sid}/ask", data={"question": QUESTION}).status_code == 403
    assert "Your recent questions" not in c.get(f"/subjects/{sid}").text


# ---------------------------------------------------------------------------------------------- hostile

def test_question_text_and_model_output_are_escaped(env, monkeypatch):
    evil = Answer(claims=[Claim(text="Enqueue adds an element <img src=x onerror=alert(document.cookie)> at the rear.",
                                citations=[Citation(passage=1, quote=Q_ENQ)])])
    use_models(monkeypatch, tier("local", Scripted(evil)))
    c, sid = alice_ready()
    loc = ask(c, sid, "how does <script>alert(2)</script> the enqueue operation work in a queue").headers["location"]
    for html in (c.get(loc).text, c.get(f"/subjects/{sid}").text):
        assert "<script>alert" not in html and "<img src=x" not in html
    assert "&lt;img src=x onerror=alert(document.cookie)&gt;" in c.get(loc).text


def test_material_text_shown_in_passages_and_search_is_escaped_and_highlighted_safely(env):
    c, sid = alice_ready(b"# Notes\n\nThe queue holds <b>bold</b> <script>alert(1)</script> enqueue words in order.\n", "x.txt")
    html = c.get(f"/subjects/{sid}/search", params={"q": "queue enqueue words"}).text
    assert "<script>alert" not in html and "<b>bold</b>" not in html and "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "<mark>queue</mark>" in html and "<mark>enqueue</mark>" in html


# ---------------------------------------------------------------------------------------------- ownership

def test_bob_cannot_read_ask_rate_or_delete_alices_questions(env, monkeypatch):
    model = Scripted(GOOD)
    use_models(monkeypatch, tier("local", model))
    alice, sid = alice_ready()
    loc = ask(alice, sid).headers["location"]
    did = loc.rsplit("/", 1)[1]
    bob = new_client()
    sign_up(bob, "bobby")
    tok = session_csrf(bob)
    assert bob.get(loc).status_code == 404
    assert bob.post(f"/subjects/{sid}/ask", data={"question": QUESTION, "csrf": tok}).status_code == 404
    assert bob.post(loc + "/feedback", data={"value": "wrong", "csrf": tok}).status_code == 404
    assert bob.post(loc + "/delete", data={"csrf": tok}).status_code == 404
    assert model.calls == 1, "bob's attempts never reached a model"
    page = alice.get(loc)
    assert page.status_code == 200 and "marked" not in visible(alice.get(f"/subjects/{sid}").text)
    store = open_db()
    assert store.db.execute("SELECT COUNT(*) FROM doubts").fetchone()[0] == 1
    store.close()
    assert did.isdigit()


def test_signed_out_visitors_are_sent_to_login(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted(GOOD)))
    alice, sid = alice_ready()
    loc = ask(alice, sid).headers["location"]
    anon = new_client()
    assert anon.get(loc).headers["location"] == "/login"
    assert anon.post(f"/subjects/{sid}/ask", data={"question": QUESTION, "csrf": "x"}).headers["location"] == "/login"
    assert anon.get("/account").headers["location"] == "/login"


# ------------------------------------------------------------------------------------ feedback / delete

def test_feedback_is_recorded_and_shown_and_bad_values_are_refused(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted(GOOD)))
    c, sid = alice_ready()
    loc = ask(c, sid).headers["location"]
    assert c.post(loc + "/feedback", data={"value": "wrong", "csrf": session_csrf(c)}).status_code == 303
    assert "You marked this &quot;wrong&quot;" in c.get(loc).text
    assert 'marked "wrong"' in visible(c.get(f"/subjects/{sid}").text)
    assert c.post(loc + "/feedback", data={"value": "<script>", "csrf": session_csrf(c)}).status_code == 404
    assert c.post(loc + "/feedback", data={"value": "helpful"}).status_code == 403


def test_a_question_can_be_deleted(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted(GOOD)))
    c, sid = alice_ready()
    loc = ask(c, sid).headers["location"]
    r = c.post(loc + "/delete", data={"csrf": session_csrf(c)})
    assert r.status_code == 303 and c.get(loc).status_code == 404


def test_deleting_a_subject_removes_its_questions_and_trace_rows_stay_unreadable(env, monkeypatch):
    use_models(monkeypatch, tier("local", Scripted(GOOD)))
    c, sid = alice_ready()
    ask(c, sid)
    c.post(f"/subjects/{sid}/delete", data={"csrf": session_csrf(c), "confirm": "yes"})
    store = open_db()
    assert store.db.execute("SELECT COUNT(*) FROM doubts").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM doubt_citations").fetchone()[0] == 0
    store.close()


# ------------------------------------------------------------------------------------------------ account

def test_the_account_page_explains_cloud_use_and_saves_consent(env):
    c = new_client()
    sign_up(c)
    page = visible(c.get("/account").text)
    assert "sent to OpenRouter" in page and "Cloud key configured on the server: no" in page
    assert "checked" not in c.get("/account").text
    assert c.post("/account/cloud", data={"consent": "yes", "csrf": session_csrf(c)}).status_code == 303
    assert "checked" in c.get("/account").text
    assert c.post("/account/cloud", data={"consent": "yes"}).status_code == 403
    c.post("/account/cloud", data={"csrf": session_csrf(c)})
    assert "checked" not in c.get("/account").text


def test_consent_is_per_user(env):
    a, b = new_client(), new_client()
    sign_up(a)
    sign_up(b, "bobby")
    a.post("/account/cloud", data={"consent": "yes", "csrf": session_csrf(a)})
    assert "checked" in a.get("/account").text and "checked" not in b.get("/account").text


# ------------------------------------------------------------------------------------------------ search

def test_search_puts_strong_matches_first_and_labels_weak_ones(env):
    c, sid = alice_ready()
    page = visible(c.get(f"/subjects/{sid}/search", params={"q": "how does inorder traversal of a binary tree work"}).text)
    assert "Inorder traversal visits the left subtree" in page and "matched: inorder, traversal, binary, tree" in page
    weak = visible(c.get(f"/subjects/{sid}/search", params={"q": "enqueue speed of hash tables"}).text)
    assert "No passage matches most of your words" in weak and "may not be about your topic" in weak
    none = visible(c.get(f"/subjects/{sid}/search", params={"q": "photosynthesis"}).text)
    assert "Nothing is guessed" in none
