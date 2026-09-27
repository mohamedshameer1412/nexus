"""StudyHub multiple-choice generation through the real HTTP routes. (FRONTEND HTTP test with SCRIPTED models.)"""
from __future__ import annotations

import re
import time

import pytest
from fastapi.testclient import TestClient

import studyhub.web.app as appmod
from studyhub.db import open_db
from studyhub.repo import Repo
from test_studyhub_materials_web import upload, visible  # noqa: F401
from test_studyhub_mcq import QUEUE_Q, STACK_Q, TRUTH, TREE_Q, McqModel, draft
from test_studyhub_qa import tier
from test_studyhub_qa_web import alice_ready, use_models
from test_studyhub_web import add_subject, env, new_client, session_csrf, sign_up, subject_id  # noqa: F401


@pytest.fixture(autouse=True)
def quiet(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "1")
    for k in ("OPENROUTER_API_KEY", "STUDYHUB_LOCAL_MODEL"):
        monkeypatch.delenv(k, raising=False)


# one question in each of the three topics of SAMPLE_TXT (Stacks, Queues, Trees)
TREE_IN_TREES = draft(TREE_Q["question"], TREE_Q["correct_answer"], TREE_Q["distractors"], TREE_Q["quote"], 1)


def three_topic_model():
    return McqModel([STACK_Q], [QUEUE_Q], [TREE_IN_TREES], truth=TRUTH)


def generate(c, sid, topic="", count="3", csrf=None):
    return c.post(f"/subjects/{sid}/mcq/generate",
                  data={"topic": topic, "count": count, "csrf": session_csrf(c) if csrf is None else csrf})


# ---------------------------------------------------------------------------------------------- happy path

def test_the_form_appears_only_after_material_is_uploaded(env):
    c = new_client()
    sign_up(c)
    sid = subject_id(add_subject(c))
    assert "Upload some material first" in visible(c.get(f"/subjects/{sid}").text) and "Generate questions" not in c.get(f"/subjects/{sid}").text
    upload(c, sid)
    html = c.get(f"/subjects/{sid}").text
    assert "Generate questions" in html and "<option value=''>Whole subject</option>" in html
    assert "Data Structures › Stacks (1 passages)" in visible(html)


def test_generating_shows_four_options_hides_the_answer_and_reveals_it_with_its_source(env, monkeypatch):
    use_models(monkeypatch, tier("local", three_topic_model()))
    c, sid = alice_ready()
    r = generate(c, sid)
    assert r.status_code == 303 and re.fullmatch(rf"/subjects/{sid}/mcq/jobs/\d+", r.headers["location"])
    html = c.get(r.headers["location"]).text
    page = visible(html)
    assert "Finished: 3 of 3 questions kept" in page
    assert html.count("<ol type='A' class='opts'>") == 3 and html.count("<details>") >= 3
    for card in re.findall(r"<div class='card' id='q\d+'>.*?</details>", html, re.S):
        before, _, after = card.partition("<details>")
        assert "Correct answer" not in before, "the answer must not be visible until it is opened"
        assert "Correct answer" in after and "<blockquote>" in after and "checked by the app" in after and "independent reader" in after
        options = re.findall(r"<li>(.*?)</li>", before)
        answer = re.search(r"Correct answer: ([A-D])\) (.*?)</b>", after)
        assert len(options) == 4 and options["ABCD".index(answer.group(1))] == answer.group(2), "the revealed answer is the option at that letter"
    assert "How these were produced" in page and "An independent reader answered each question" in page


def test_the_bank_lists_every_question_and_filters_by_topic(env, monkeypatch):
    use_models(monkeypatch, tier("local", three_topic_model()))
    c, sid = alice_ready()
    c.get(generate(c, sid).headers["location"])
    bank = c.get(f"/subjects/{sid}/mcq")
    assert bank.status_code == 200 and "3 multiple-choice questions" in visible(bank.text) and bank.text.count("<ol type='A'") == 3
    store = open_db()
    topic = Repo(store.db).list_topics(1, sid)[0]["id"]
    store.close()
    one = c.get(f"/subjects/{sid}/mcq", params={"topic": str(topic)})
    assert one.text.count("<ol type='A'") == 1
    assert c.get(f"/subjects/{sid}/mcq", params={"topic": "abc"}).status_code == 200
    assert "Question bank" in visible(c.get(f"/subjects/{sid}").text) or "question bank" in visible(c.get(f"/subjects/{sid}").text).lower()


def test_one_topic_can_be_chosen(env, monkeypatch):
    model = McqModel([STACK_Q, draft("Which operation adds an element at the top of a stack?", "The push operation",
                                     ("The pop operation", "The enqueue operation", "The dequeue operation"),
                                     "The push operation adds an element to the top of the stack")],
                     truth={**TRUTH, "Which operation adds an element at the top of a stack?": "The push operation"})
    use_models(monkeypatch, tier("local", model))
    c, sid = alice_ready()
    store = open_db()
    topic = Repo(store.db).list_topics(1, sid)[0]["id"]
    store.close()
    html = c.get(generate(c, sid, topic=str(topic), count="2").headers["location"]).text
    assert "Finished: 2 of 2" in visible(html) and 'from the topic "Data Structures › Stacks"' in visible(html)


def test_a_question_can_be_deleted(env, monkeypatch):
    use_models(monkeypatch, tier("local", three_topic_model()))
    c, sid = alice_ready()
    c.get(generate(c, sid).headers["location"])
    store = open_db()
    qid = store.db.execute("SELECT id FROM mcq_items ORDER BY id").fetchone()[0]
    store.close()
    r = c.post(f"/subjects/{sid}/mcq/{qid}/delete", data={"csrf": session_csrf(c)})
    assert r.status_code == 303 and r.headers["location"] == f"/subjects/{sid}/mcq"
    assert c.get(f"/subjects/{sid}/mcq").text.count("<ol type='A'") == 2
    assert c.post(f"/subjects/{sid}/mcq/{qid}/delete", data={"csrf": session_csrf(c)}).status_code == 404


# ------------------------------------------------------------------------------------------ honest failures

def test_with_no_model_available_nothing_is_written_and_it_says_so(env, monkeypatch):
    use_models(monkeypatch, notes=["the local model is switched off"])
    c, sid = alice_ready()
    page = visible(c.get(generate(c, sid).headers["location"]).text)
    assert "Could not finish: 0 of 3 questions kept" in page and "No language model is available" in page and "never made up" in page
    assert c.get(f"/subjects/{sid}/mcq").text.count("<ol type='A'") == 0


def test_a_model_that_writes_only_bad_questions_produces_none_and_shows_why(env, monkeypatch):
    bad = draft(quote="the pop operation deletes everything from the top")
    use_models(monkeypatch, tier("local", McqModel([bad], [bad], [bad], [bad], [bad], [bad], [bad], [bad], [bad], truth=TRUTH)))
    c, sid = alice_ready()
    html = c.get(generate(c, sid, count="1").headers["location"]).text
    page = visible(html)
    assert "0 of 1 questions kept" in page and "No question passed every check" in page and "does not appear word for word" in page
    assert "candidate question" in page


def test_an_unexpected_crash_shows_a_friendly_failure_not_a_traceback(env, monkeypatch):
    def boom(db, user):
        raise RuntimeError("secret internal detail /etc/passwd")
    monkeypatch.setattr(appmod, "tier_factory", boom)
    c, sid = alice_ready()
    html = c.get(generate(c, sid).headers["location"]).text
    assert "Something went wrong" in html and "secret internal detail" not in html and "Traceback" not in html


# --------------------------------------------------------------------------------------------- validation

@pytest.mark.parametrize("count,topic,fragment", [("0", "", "from 1 to 10"), ("11", "", "from 1 to 10"), ("abc", "", "from 1 to 10"),
                                                  ("-3", "", "from 1 to 10"), ("3", "99999", "not part of this subject"),
                                                  ("3", "abc", "not part of this subject")])
def test_bad_requests_are_refused_and_create_nothing(env, monkeypatch, count, topic, fragment):
    model = McqModel()
    use_models(monkeypatch, tier("local", model))
    c, sid = alice_ready()
    r = generate(c, sid, topic=topic, count=count)
    assert r.status_code == 400 and fragment in visible(r.text) and model.n == {"write": 0, "solve": 0}
    store = open_db()
    assert store.db.execute("SELECT COUNT(*) FROM mcq_jobs").fetchone()[0] == 0
    store.close()


def test_a_topic_of_another_subject_of_the_same_user_is_refused(env, monkeypatch):
    use_models(monkeypatch, tier("local", McqModel()))
    c, sid = alice_ready()
    other = subject_id(add_subject(c, "Networks"))
    upload(c, other, "n.txt", b"# Networks\n\nThe transport layer provides delivery of data between processes running on different hosts, in order.\n")
    store = open_db()
    foreign = Repo(store.db).list_topics(1, other)[0]["id"]
    store.close()
    assert "not part of this subject" in visible(generate(c, sid, topic=str(foreign)).text)


def test_only_one_job_at_a_time_per_user(env, monkeypatch):
    use_models(monkeypatch, tier("local", McqModel()))
    c, sid = alice_ready()
    store = open_db()
    Repo(store.db).create_mcq_job(1, sid, None, "waiting", 3)
    store.close()
    r = generate(c, sid)
    assert r.status_code == 400 and "already being written" in visible(r.text)


def test_a_pending_job_page_polls(env):
    c, sid = alice_ready()
    store = open_db()
    jid = Repo(store.db).create_mcq_job(1, sid, None, "3 questions from the whole subject", 3)
    store.close()
    page = c.get(f"/subjects/{sid}/mcq/jobs/{jid}").text
    assert "http-equiv='refresh'" in page and "Reading your materials and writing questions" in page


def test_a_job_left_pending_by_a_restart_is_failed_at_startup(env):
    c, sid = alice_ready()
    store = open_db()
    jid = Repo(store.db).create_mcq_job(1, sid, None, "x", 3)
    store.close()
    with TestClient(appmod.app):
        pass
    store = open_db()
    j = Repo(store.db).get_mcq_job(1, sid, jid)
    store.close()
    assert j["status"] == "failed" and "interrupted" in j["reason"]


def test_the_real_background_worker_writes_questions_while_the_page_polls(env, monkeypatch):
    monkeypatch.setenv("STUDYHUB_QA_INLINE", "0")
    monkeypatch.setattr(appmod, "_worker", None)

    class Slow(McqModel):
        def __call__(self, **kw):
            time.sleep(0.4)
            return super().__call__(**kw)
    use_models(monkeypatch, tier("local", Slow([STACK_Q], [QUEUE_Q], [TREE_IN_TREES], truth=TRUTH)))
    c, sid = alice_ready()
    loc = generate(c, sid).headers["location"]
    assert "http-equiv='refresh'" in c.get(loc).text
    html = ""
    for _ in range(80):
        html = c.get(loc).text
        if "http-equiv='refresh'" not in html:
            break
        time.sleep(0.25)
    assert "Finished: 3 of 3 questions kept" in visible(html)


# ------------------------------------------------------------------------------ CSRF, sign-in, ownership

def test_a_post_without_the_csrf_token_creates_nothing(env, monkeypatch):
    model = McqModel()
    use_models(monkeypatch, tier("local", model))
    c, sid = alice_ready()
    assert generate(c, sid, csrf="nope").status_code == 403
    assert c.post(f"/subjects/{sid}/mcq/generate", data={"count": "3"}).status_code == 403
    assert model.n["write"] == 0


def test_signed_out_visitors_are_sent_to_login(env, monkeypatch):
    use_models(monkeypatch, tier("local", three_topic_model()))
    alice, sid = alice_ready()
    loc = generate(alice, sid).headers["location"]
    anon = new_client()
    assert anon.get(loc).headers["location"] == "/login" and anon.get(f"/subjects/{sid}/mcq").headers["location"] == "/login"
    assert anon.post(f"/subjects/{sid}/mcq/generate", data={"count": "3", "csrf": "x"}).headers["location"] == "/login"


def test_bob_cannot_read_generate_or_delete_alices_questions(env, monkeypatch):
    model = three_topic_model()
    use_models(monkeypatch, tier("local", model))
    alice, sid = alice_ready()
    loc = generate(alice, sid).headers["location"]
    store = open_db()
    qid = store.db.execute("SELECT id FROM mcq_items ORDER BY id").fetchone()[0]
    store.close()
    bob = new_client()
    sign_up(bob, "bobby")
    tok = session_csrf(bob)
    calls = dict(model.n)
    assert bob.get(loc).status_code == 404 and bob.get(f"/subjects/{sid}/mcq").status_code == 404
    assert bob.post(f"/subjects/{sid}/mcq/generate", data={"count": "3", "topic": "", "csrf": tok}).status_code == 404
    assert bob.post(f"/subjects/{sid}/mcq/{qid}/delete", data={"csrf": tok}).status_code == 404
    assert model.n == calls, "bob's attempts never reached a model"
    assert alice.get(f"/subjects/{sid}/mcq").text.count("<ol type='A'") == 3


def test_bobs_own_subject_shows_none_of_alices_questions(env, monkeypatch):
    use_models(monkeypatch, tier("local", three_topic_model()))
    alice, sid = alice_ready()
    alice.get(generate(alice, sid).headers["location"])
    bob = new_client()
    sign_up(bob, "bobby")
    bsid = subject_id(add_subject(bob, "Mine"))
    assert "0 multiple-choice questions" in visible(bob.get(f"/subjects/{bsid}/mcq").text)
    assert bob.get(f"/subjects/{bsid}/mcq/jobs/1").status_code == 404, "job 1 is alice's, whatever subject it is asked through"


# --------------------------------------------------------------------------------------------- hostile

def test_model_text_and_material_text_are_escaped_everywhere(env, monkeypatch):
    material = (b"# Stacks\n\nStacks are used in many programs. The <b>pop</b> operation removes the element from the top of the stack, "
                b"and the <script>alert(document.cookie)</script> push operation adds an element to the top of the stack in constant time.\n")
    evil = draft("Which operation removes the element from the top of the stack?", "The pop operation",
                 ("<img src=x onerror=alert(document.cookie)>", "The enqueue operation", "The dequeue operation"),
                 "The <b>pop</b> operation removes the element from the top of the stack", 1,
                 "The <b>pop</b> operation removes the element from the top.")
    use_models(monkeypatch, tier("local", McqModel([evil], solve=None, truth={evil["question"]: "The pop operation"})))
    c, sid = alice_ready(material, "<script>x</script>.txt")
    html = c.get(generate(c, sid, count="1").headers["location"]).text
    assert "<script>alert" not in html and "<img src=x" not in html and "<b>pop</b>" not in html
    assert "&lt;img src=x onerror=alert(document.cookie)&gt;" in html and "&lt;b&gt;pop&lt;/b&gt;" in html
    bank = c.get(f"/subjects/{sid}/mcq").text
    assert "<script>alert" not in bank and "<img src=x" not in bank


def test_security_headers_are_on_the_question_pages(env, monkeypatch):
    use_models(monkeypatch, tier("local", three_topic_model()))
    c, sid = alice_ready()
    page = c.get(generate(c, sid).headers["location"])
    assert "script-src 'none'" in page.headers["content-security-policy"] and page.headers["x-frame-options"] == "DENY"
