"""
End-to-end scenarios for the study domain.
All 12 scenarios from the requirements - no network, Scripted fixtures only.
"""
from __future__ import annotations

import pytest

from demo.study import checks
from demo.study.flow import MAX_REVISIONS, build_flow
from demo.study.samples import INJECTED, SAMPLE
from demo.study.stub import (
    SCENARIOS,
    Scripted,
    V1,
    V2,
    audit_v1,
    never_right,
    ok_audit,
    pack,
)
from slice import runner
from slice.config import settings as load_settings
from slice.llm import ModelError, SchemaFailure
from slice.records import RunState
from slice.store import Store


def _run(tmp_path, call, source=SAMPLE):
    store = Store(str(tmp_path / "t.db"))
    run_id = store.create_run("study")
    store.append(run_id, "input", {"text": source}, produced_by="test")
    final = runner.advance(store, run_id, build_flow(call=call), load_settings())
    return store, run_id, final


# Scenario 1: Valid input produces approved content
def test_e2e_1_valid_input_approved(tmp_path):
    _, factory = SCENARIOS["clean"]
    _, _, final = _run(tmp_path, factory())
    assert final is RunState.COMPLETE


# Scenario 2: Invalid content (fabricated quote) is rejected
def test_e2e_2_invalid_content_rejected(tmp_path):
    # V1 has a fabricated source quote; with a clean-pass audit the code check catches it
    call = Scripted(generate=[V1], audit=[ok_audit(V1)])
    store, run_id, final = _run(tmp_path, call)
    # The quote check is deterministic - either rejects or escalates
    verdicts = store.history(run_id, "verdict")
    assert any(v.payload["status"] == "REJECTED" for v in verdicts)


# Scenario 3: Rejected content is revised and then approved
def test_e2e_3_rejected_then_revised_then_approved(tmp_path):
    _, factory = SCENARIOS["revise"]
    store, run_id, final = _run(tmp_path, factory())
    assert final is RunState.COMPLETE
    assert len(store.history(run_id, "draft")) == 2


# Scenario 4: Three failed revisions lead to human review
def test_e2e_4_three_failures_lead_to_human_review(tmp_path):
    _, factory = SCENARIOS["stuck"]
    store, run_id, final = _run(tmp_path, factory())
    assert final is RunState.AWAITING_EXPERT
    rejections = sum(1 for v in store.history(run_id, "verdict")
                     if v.payload["status"] == "REJECTED")
    assert rejections > MAX_REVISIONS


# Scenario 5: Malformed LLM output is handled safely
def test_e2e_5_malformed_llm_output_handled(tmp_path):
    call = Scripted(generate=[SchemaFailure("model returned garbage")], audit=[])
    store, run_id, final = _run(tmp_path, call)
    assert final is RunState.FAILED
    # The run must leave a failure record - not a bare exception
    assert store.latest(run_id, "failure") is not None


# Scenario 6: Empty input is rejected before any model call
def test_e2e_6_empty_input_rejected(tmp_path):
    call = Scripted(generate=[], audit=[])
    store, run_id, final = _run(tmp_path, call, source="")
    assert final is RunState.FAILED
    assert call.count("generate") == 0, "model should not be called on empty input"


# Scenario 7: Invalid source references are detected by code check
def test_e2e_7_invalid_source_references_detected(tmp_path):
    from demo.study.stub import Q_OXYGEN_INVENTED, NOTES
    bad_pack = pack([Q_OXYGEN_INVENTED, Q_OXYGEN_INVENTED, Q_OXYGEN_INVENTED])
    # Use a different question to avoid duplicate_questions error
    from demo.study.stub import Q_CHLOROPLAST, Q_STOMATA
    bad_pack2 = pack([Q_OXYGEN_INVENTED, Q_CHLOROPLAST, Q_STOMATA])
    call = Scripted(generate=[bad_pack2], audit=[ok_audit(bad_pack2)])
    store, run_id, final = _run(tmp_path, call)
    verdicts = store.history(run_id, "verdict")
    assert verdicts, "should have at least one verdict"
    # The fabricated quote should be caught
    first_verdict = verdicts[0].payload
    assert first_verdict["status"] == "REJECTED"
    assert any(i["code"] == "quote_not_in_source"
               for i in first_verdict.get("issues", []))


# Scenario 8: Prompt injection in source material is rejected, not followed
def test_e2e_8_prompt_injection_rejected(tmp_path):
    call = Scripted(generate=[], audit=[])
    store, run_id, final = _run(tmp_path, call, source=INJECTED)
    assert final is RunState.FAILED
    failure = store.latest(run_id, "failure")
    assert failure and failure["kind"] == "source_injection"
    assert call.count("generate") == 0


# Scenario 9: Duplicate output escalates (not an infinite loop)
def test_e2e_9_duplicate_output_escalates(tmp_path):
    _, factory = SCENARIOS["repeat"]
    store, run_id, final = _run(tmp_path, factory())
    assert final is RunState.AWAITING_EXPERT
    escalation = store.latest(run_id, "escalation")
    assert escalation and escalation["reason"] == "repeated_output"
    # Should stop after 2 drafts, not spin indefinitely
    assert len(store.history(run_id, "draft")) == 2


# Scenario 10: LLM timeout / unavailable provider is handled
def test_e2e_10_llm_timeout_handled(tmp_path):
    call = Scripted(generate=[ModelError("connection timeout")], audit=[])
    store, run_id, final = _run(tmp_path, call)
    assert final is RunState.FAILED
    failure = store.latest(run_id, "failure")
    assert failure is not None


# Scenario 11: Application can resume from persisted state
def test_e2e_11_resume_from_persisted_state(tmp_path):
    _, factory = SCENARIOS["stuck"]
    call = factory()
    db = str(tmp_path / "t.db")

    # First advance: run to AWAITING_EXPERT (a real suspended state)
    s1 = Store(db)
    run_id = s1.create_run("study")
    s1.append(run_id, "input", {"text": SAMPLE}, produced_by="test")
    final1 = runner.advance(s1, run_id, build_flow(call=call), load_settings())
    assert final1 is RunState.AWAITING_EXPERT
    draft_count = len(s1.history(run_id, "draft"))
    s1.close()

    # Reopen - state and records must be identical
    s2 = Store(db)
    assert s2.get_state(run_id) is RunState.AWAITING_EXPERT
    assert len(s2.history(run_id, "draft")) == draft_count


# Scenario 12: Fixture mode works without any API key or local model
def test_e2e_12_fixture_mode_no_key_no_model(tmp_path):
    """Verify that the Scripted fixture runs the full flow without any external dependencies."""
    _, factory = SCENARIOS["clean"]
    call = factory()
    # Explicitly check no API key is needed
    from slice.config import Settings
    cfg = Settings(
        api_key="", model="", fallback_model="", escalation_model="",
        max_tokens=1200, max_tokens_per_run=250000, max_attempts_per_step=3,
        expert_timeout_minutes=45, langfuse_public="", langfuse_secret="",
        langfuse_host="", llm_provider="fixture",
        ollama_base_url="", ollama_model="",
    )
    store = Store(str(tmp_path / "t.db"))
    run_id = store.create_run("study")
    store.append(run_id, "input", {"text": SAMPLE}, produced_by="test")
    final = runner.advance(store, run_id, build_flow(call=call), cfg)
    assert final is RunState.COMPLETE
