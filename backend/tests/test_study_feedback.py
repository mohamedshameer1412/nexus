"""Real-tester feedback: recording, persistence, validation, API, display, CLI.

Nothing here fabricates feedback - every item is submitted by the test through the same
function, endpoint or command a tester would use, and every "nobody has said anything"
case checks that the answer is empty.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
import time

import pytest
from fastapi.testclient import TestClient

from demo.study import feedback, trace
from demo.study.flow import build_flow
from demo.study.samples import SAMPLE
from demo.study.stub import SCENARIOS, V1, V2, Scripted, audit_v1, ok_audit
from scripts import study
from slice import callback, runner
from slice.config import Settings
from slice.records import RunState
from slice.store import Store
from web import study_ui

S = Settings(api_key="x", model="m", fallback_model="f", escalation_model="e", max_tokens=100,
             max_tokens_per_run=250_000, max_attempts_per_step=3, expert_timeout_minutes=45,
             langfuse_public="", langfuse_secret="", langfuse_host="")


def make_run(tmp_path, scenario="revise", text=SAMPLE, name="fb.db"):
    store = Store(tmp_path / name)
    run = store.create_run("study", {"mode": f"stub:{scenario}"})
    store.append(run, "input", {"text": text}, produced_by="user")
    runner.advance(store, run, build_flow(SCENARIOS[scenario][1]()), S)
    return store, run


GOOD = {"useful": True, "comment": "Q2 was too easy", "confusing": "Q3 wording", "tester": "sam"}


# ============================================================ creation and persistence

def test_feedback_is_a_durable_attributed_row_tied_to_what_the_tester_saw(tmp_path):
    store, run = make_run(tmp_path, "revise")                        # 2 drafts, approved
    before = time.time()
    rec = feedback.submit(store, run, {**GOOD, "rating": 4})
    assert (rec["useful"], rec["rating"], rec["tester"]) == (True, 4, "sam")
    assert (rec["draft"], rec["run_state"]) == (2, "complete"), "the SERVER records what they saw"

    (row,) = store.history(run, "feedback")
    assert row.produced_by == "tester:sam" and row.kind == "feedback"
    assert before - 1 <= row.created_at <= time.time() + 1, "timestamped by the store"
    (item,) = feedback.for_run(store, run)
    assert item["run_id"] == run and item["submitted_at"] == row.created_at
    assert (item["comment"], item["confusing"]) == ("Q2 was too easy", "Q3 wording")


def test_feedback_survives_the_process_dying(tmp_path):
    store, run = make_run(tmp_path)
    feedback.submit(store, run, GOOD)
    store.close()
    reopened = Store(tmp_path / "fb.db")
    (item,) = feedback.for_run(reopened, run)
    assert item["comment"] == "Q2 was too easy" and item["tester"] == "sam"


def test_several_testers_can_each_answer_and_history_stays_append_only(tmp_path):
    store, run = make_run(tmp_path)
    feedback.submit(store, run, {"useful": True, "tester": "asha"})
    feedback.submit(store, run, {"useful": False, "comment": "notes too vague", "tester": "ravi"})
    assert [f["tester"] for f in feedback.for_run(store, run)] == ["asha", "ravi"]
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store.db.execute("UPDATE versions SET payload_json='{}' WHERE kind='feedback'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store.db.execute("DELETE FROM versions WHERE kind='feedback'")


def test_a_run_that_failed_at_intake_can_still_be_given_feedback(tmp_path):
    store, run = make_run(tmp_path, "clean", text="too short to study")
    assert store.get_state(run) is RunState.FAILED
    rec = feedback.submit(store, run, {"useful": False, "confusing": "the error was unclear"})
    assert (rec["draft"], rec["run_state"]) == (0, "failed")


def test_feedback_never_moves_a_run(tmp_path):
    """It is not a review decision: it cannot approve, reject or resume anything."""
    store, run = make_run(tmp_path, "stuck")                          # waiting on a human
    assert store.get_state(run) is RunState.AWAITING_EXPERT
    feedback.submit(store, run, {"useful": True, "comment": "looks fine to me"})
    assert store.get_state(run) is RunState.AWAITING_EXPERT
    assert store.latest(run, "result") is None
    assert len(callback.pending(store, run)) == 1, "the review question is still open"
    assert runner.advance(store, run, build_flow(Scripted([], [])), S) is RunState.AWAITING_EXPERT


def test_when_nobody_has_said_anything_nothing_is_invented(tmp_path):
    store, run = make_run(tmp_path)
    assert feedback.for_run(store, run) == [] and feedback.everything(store) == []


def test_everything_gathers_across_runs_with_their_context(tmp_path):
    a, run_a = make_run(tmp_path, "clean")
    run_b = a.create_run("study", {"mode": "stub:other"})
    a.append(run_b, "input", {"text": SAMPLE}, produced_by="user")
    feedback.submit(a, run_a, {"useful": True, "tester": "first"})
    feedback.submit(a, run_b, {"useful": False, "tester": "second"})
    got = feedback.everything(a)
    assert [(f["tester"], f["run_mode"]) for f in got] == [("first", "stub:clean"), ("second", "stub:other")]
    assert got[0]["run_state_now"] == "complete"


# ==================================================================== bad input

def test_feedback_on_a_run_that_does_not_exist_is_refused_and_writes_nothing(tmp_path):
    store, run = make_run(tmp_path)
    with pytest.raises(KeyError):
        feedback.submit(store, "run_doesnotexist", GOOD)
    assert store.db.execute("SELECT COUNT(*) FROM versions WHERE kind='feedback'").fetchone()[0] == 0


@pytest.mark.parametrize("raw,fragment", [
    ({}, "useful"),                                                   # empty
    ({"comment": "great"}, "useful"),                                 # no verdict
    ({"useful": "yes"}, "useful"),                                    # strict: no guessing
    ({"useful": 1}, "useful"),
    ({"useful": None}, "useful"),
    ({"useful": True, "rating": 0}, "rating"),
    ({"useful": True, "rating": 6}, "rating"),
    ({"useful": True, "rating": "4"}, "rating"),
    ({"useful": True, "comment": "x" * 1001}, "comment"),
    ({"useful": True, "confusing": "y" * 1001}, "confusing"),
    ({"useful": True, "tester": "n" * 61}, "tester"),
    ({"useful": True, "comment": 42}, "comment"),
    ({"useful": True, "coment": "typo must not silently lose the text"}, "coment"),
    (["useful"], "feedback"),                                         # not an object
    ("useful", "feedback"),
    (None, "feedback"),
])
def test_invalid_feedback_is_refused_with_a_reason_and_writes_nothing(tmp_path, raw, fragment):
    store, run = make_run(tmp_path)
    with pytest.raises(feedback.FeedbackError, match=fragment):
        feedback.submit(store, run, raw)
    assert feedback.for_run(store, run) == []


def test_text_is_tidied_and_a_missing_name_becomes_anonymous(tmp_path):
    store, run = make_run(tmp_path)
    rec = feedback.submit(store, run, {"useful": False, "comment": "  too \n  vague  ",
                                       "confusing": "   ", "tester": "   "})
    assert (rec["comment"], rec["confusing"], rec["tester"], rec["rating"]) == \
        ("too vague", "", "anonymous", None)


# ===================================================================== the API

@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SLICE_DB", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture()
def client(env):
    with TestClient(study_ui.app) as c:
        yield c


def generate(client, scenario="revise"):
    r = client.post("/api/generate", json={"source": SAMPLE, "scenario": scenario})
    assert r.status_code == 200, r.text
    return r.json()["run_id"]


def test_the_api_records_and_returns_feedback(client):
    rid = generate(client)
    r = client.post(f"/api/run/{rid}/feedback", json={**GOOD, "rating": 5})
    assert r.status_code == 201
    body = r.json()
    assert body["run_id"] == rid and body["feedback"]["useful"] is True
    assert body["feedback"]["draft"] == 2 and body["feedback"]["run_state"] == "complete"

    listed = client.get(f"/api/run/{rid}/feedback").json()
    assert [f["tester"] for f in listed["feedback"]] == ["sam"] and listed["run_id"] == rid
    assert [f["comment"] for f in client.get("/api/feedback").json()["feedback"]] == ["Q2 was too easy"]
    assert client.get(f"/api/run/{rid}").json()["summary"]["feedback"] == 1


def test_the_api_says_nothing_when_nobody_has(client):
    rid = generate(client)
    assert client.get(f"/api/run/{rid}/feedback").json()["feedback"] == []
    assert client.get("/api/feedback").json() == {"feedback": []}
    assert client.get(f"/api/run/{rid}").json()["summary"]["feedback"] == 0


def test_the_api_refuses_an_unknown_run(client):
    assert client.post("/api/run/run_nope/feedback", json=GOOD).status_code == 404
    assert client.get("/api/run/run_nope/feedback").status_code == 404


@pytest.mark.parametrize("payload", [
    {}, {"useful": "yes"}, {"useful": True, "rating": 9}, {"useful": True, "comment": "z" * 1001},
    {"useful": True, "surprise": "field"},
])
def test_the_api_refuses_invalid_feedback_with_a_reason(client, payload):
    rid = generate(client)
    r = client.post(f"/api/run/{rid}/feedback", json=payload)
    assert r.status_code == 422 and r.json()["error"]
    assert client.get(f"/api/run/{rid}/feedback").json()["feedback"] == [], "nothing was stored"


def test_the_api_refuses_a_body_that_is_not_an_object(client):
    rid = generate(client)
    assert client.post(f"/api/run/{rid}/feedback", json=["useful"]).status_code == 400
    assert client.post(f"/api/run/{rid}/feedback", content="{",
                       headers={"content-type": "application/json"}).status_code == 400


def test_feedback_does_not_resume_or_approve_through_the_api(client):
    rid = generate(client, "stuck")
    assert client.post(f"/api/run/{rid}/feedback", json={"useful": True}).status_code == 201
    data = client.get(f"/api/run/{rid}").json()
    assert data["state"] == "awaiting_expert" and data["result"] is None and data["awaiting_review"]


# ==================================================== display: run page and trace

def test_a_finished_run_offers_the_feedback_form(client):
    rid = generate(client)
    page = client.get(f"/run/{rid}").text
    assert "Was this study material useful?" in page
    assert "data-useful='yes'" in page and "data-useful='no'" in page
    assert "What should be improved?" in page and "Submit feedback" in page
    assert f"'/api/run/'+{json.dumps(rid)}+'/feedback'" in page, "the form must post to THIS run"
    assert "Feedback so far" not in page, "nothing to list yet"


def test_submitted_feedback_is_shown_on_the_page_and_in_the_trace(client):
    rid = generate(client)
    client.post(f"/api/run/{rid}/feedback", json={"useful": False, "rating": 2, "tester": "meena",
                                                  "comment": "notes are thin", "confusing": "Q1"})
    page = client.get(f"/run/{rid}").text
    assert "Feedback so far (1)" in page and "meena" in page and "not useful" in page
    assert "2/5" in page and "notes are thin" in page and "about draft 2" in page

    trace_page = client.get(f"/run/{rid}/trace").text
    assert "TESTER FEEDBACK  (meena): NOT useful" in trace_page
    assert "what to improve: notes are thin" in trace_page and "confusing or wrong: Q1" in trace_page


def test_feedback_text_is_escaped_everywhere(client):
    rid = generate(client)
    evil = "<script>alert('x')</script>"
    client.post(f"/api/run/{rid}/feedback", json={"useful": True, "comment": evil,
                                                  "confusing": evil, "tester": "<b>bob</b>"})
    for path in ("", "/trace"):
        page = client.get(f"/run/{rid}{path}").text
        assert evil not in page and "<b>bob</b>" not in page, path
    assert "&lt;script&gt;" in client.get(f"/run/{rid}").text


class Gate(Scripted):
    """Scripted, but the generator waits for permission - a slow live model."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.release = threading.Event()

    def __call__(self, **kw):
        if kw.get("step") == "generate":
            assert self.release.wait(10)
        return super().__call__(**kw)


def test_feedback_waits_until_the_run_has_finished(env, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    gate = Gate([V1, V2], [audit_v1(), ok_audit(V2)])
    monkeypatch.setattr(study_ui, "_make_call", lambda cfg, scenario=None: gate)
    with TestClient(study_ui.app) as c:
        rid = c.post("/api/generate", json={"source": SAMPLE}).json()["run_id"]
        assert c.get(f"/api/run/{rid}").json()["active"] is True
        assert "Was this study material useful?" not in c.get(f"/run/{rid}").text
        r = c.post(f"/api/run/{rid}/feedback", json={"useful": True})
        assert r.status_code == 409 and "finished" in r.json()["error"]

        gate.release.set()
        end = time.time() + 10
        while c.get(f"/api/run/{rid}").json()["active"] and time.time() < end:
            time.sleep(0.05)
        assert "Was this study material useful?" in c.get(f"/run/{rid}").text
        assert c.post(f"/api/run/{rid}/feedback", json={"useful": True}).status_code == 201


# ====================================================================== the CLI

def cli(tmp_path, capsys, *argv):
    code = study.main(["--db", str(tmp_path / "cli.db"), *argv])
    return code, capsys.readouterr().out


@pytest.fixture()
def cli_env(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.chdir("/")


def new_run(tmp_path, capsys, *extra):
    _, out = cli(tmp_path, capsys, "run", "--stub", *extra)
    return re.search(r"run (run_\w+)", out).group(1)


def test_the_cli_records_and_lists_feedback(tmp_path, capsys, cli_env):
    rid = new_run(tmp_path, capsys)
    code, out = cli(tmp_path, capsys, "feedback", rid, "--useful", "--rating", "4",
                    "--comment", "good notes", "--confusing", "Q2", "--who", "kavya")
    assert code == 0 and "Recorded feedback" in out and "'kavya'" in out and "useful" in out

    code, out = cli(tmp_path, capsys, "feedbacks", rid)
    assert code == 0 and "kavya" in out and "4/5" in out
    assert "improve: good notes" in out and "confusing/wrong: Q2" in out and "1 feedback item" in out
    assert "kavya" in cli(tmp_path, capsys, "feedbacks")[1], "with no run id: everything"


def test_the_cli_records_not_useful(tmp_path, capsys, cli_env):
    rid = new_run(tmp_path, capsys)
    assert cli(tmp_path, capsys, "feedback", rid, "--not-useful")[0] == 0
    assert "NOT useful" in cli(tmp_path, capsys, "feedbacks", rid)[1]


def test_the_cli_refuses_bad_feedback(tmp_path, capsys, cli_env):
    rid = new_run(tmp_path, capsys)
    code, out = cli(tmp_path, capsys, "feedback", "run_nope", "--useful")
    assert code == 2 and "No such run" in out
    code, out = cli(tmp_path, capsys, "feedback", rid, "--useful", "--rating", "9")
    assert code == 2 and "not recorded" in out and "rating" in out
    assert "No feedback has been submitted yet." in cli(tmp_path, capsys, "feedbacks", rid)[1]
    with pytest.raises(SystemExit) as e:                             # a verdict is required
        study.main(["--db", str(tmp_path / "cli.db"), "feedback", rid])
    assert e.value.code == 2


def test_the_cli_reports_on_a_run_or_a_database_with_no_feedback(tmp_path, capsys, cli_env):
    rid = new_run(tmp_path, capsys)
    assert "No feedback has been submitted yet." in cli(tmp_path, capsys, "feedbacks")[1]
    assert cli(tmp_path, capsys, "feedbacks", "run_nope")[0] == 2


def test_feedback_appears_in_the_cli_trace(tmp_path, capsys, cli_env):
    rid = new_run(tmp_path, capsys)
    cli(tmp_path, capsys, "feedback", rid, "--useful", "--comment", "clear", "--who", "dev")
    _, out = cli(tmp_path, capsys, "trace", rid)
    assert "TESTER FEEDBACK  (dev): useful" in out and "what to improve: clear" in out
    assert "(about draft 2; run was complete)" in out


def test_the_cli_run_output_tells_a_tester_how_to_give_feedback(tmp_path, capsys, cli_env):
    _, out = cli(tmp_path, capsys, "run", "--stub", "--scenario", "clean")
    assert "study.py feedback" in out and "--useful" in out


def test_the_trace_module_reports_a_feedback_count(tmp_path):
    store, run = make_run(tmp_path)
    assert trace.summary(store, run)["feedback"] == 0
    feedback.submit(store, run, GOOD)
    assert trace.summary(store, run)["feedback"] == 1
