"""Quiz agents — question generator and answer evaluator for the backward-pass loop.

Ported from tracer/agents.py (agentic-slice-kit) and adapted to use the
existing OllamaProvider instead of raw urllib calls, so timeouts, JSON-schema
constraints, and fallback model handling are inherited for free.

spot_agent  → generates one diagnostic open-ended question for a topic
gate_agent  → binary PASS / BLOCK evaluation of a student's answer

Both are thin wrappers that build a prompt, call the provider, and return a
plain Python value.  The state machine (quiz_flow.py) decides what to do next.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Prompt templates (mirroring tracer/prompts/spot.md and gate.md) ──────────

_SPOT_PROMPT = """\
You are a tutoring assistant generating a diagnostic question.

Topic: {topic_name}
Difficulty level: {difficulty}/3  (1=basic recall, 2=application, 3=analysis)
Prior objections from this student (what they got wrong before):
{prior_objections}

Write exactly ONE short, clear question that tests understanding of this topic \
at the given difficulty level. If there are prior objections, target those gaps.

Reply with JSON only:
{{"content": "Your question here?"}}"""

_GATE_PROMPT = """\
You are a strict evaluator. Decide whether the student's answer shows \
sufficient understanding of the topic.

Topic: {topic_name}
Question: {question}
Student answer: {student_answer}
Prior evaluations on this topic:
{prior_verdicts}

Rules:
- PASS if the answer is substantially correct and complete for the difficulty level.
- BLOCK if there is a clear gap or misconception.
- List specific objections only on BLOCK (max 3 bullet points).
- prerequisite_id: if you BLOCK, suggest the most likely prerequisite gap topic \
  from this list: {prereq_id} (use null if none applies or you are unsure).

Reply with JSON only:
{{"status": "PASS" or "BLOCK", "objections": ["..."], "prerequisite_id": null_or_id}}"""


# ── Core call (uses the existing OllamaProvider machinery) ───────────────────

def _call_provider(provider_fn, prompt: str, schema_class, timeout: int = 90) -> dict | None:
    """Call the given provider callable and return parsed dict, or None on error."""
    from pydantic import BaseModel

    class _QuestionOut(BaseModel):
        content: str = ""

    class _VerdictOut(BaseModel):
        status: str = "BLOCK"
        objections: list[str] = []
        prerequisite_id: str | None = None

    try:
        messages = [{"role": "user", "content": prompt}]
        # schema_class is passed so the provider enforces JSON output
        result = provider_fn(messages=messages, schema=schema_class, timeout=timeout)
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)
    except Exception as exc:
        logger.error("[quiz_agents] provider call failed: %s", exc)
        return None


# ── spot_agent ────────────────────────────────────────────────────────────────

def spot_agent(
    topic_id: int,
    topic_name: str,
    difficulty: int,
    prior_objections: list[str],
    provider_fn,  # callable(messages, schema, timeout) -> Pydantic model
) -> str:
    """Generate one diagnostic question. Returns question string.

    Falls back to a generic question if the model fails — the state machine
    must never crash because the question generator errored.
    """
    from pydantic import BaseModel

    class _Out(BaseModel):
        content: str = ""

    objections_text = (
        "\n".join(f"- {o}" for o in prior_objections)
        if prior_objections else "(none)"
    )
    prompt = _SPOT_PROMPT.format(
        topic_name=topic_name,
        difficulty=difficulty,
        prior_objections=objections_text,
    )
    result = _call_provider(provider_fn, prompt, _Out)
    if result and result.get("content"):
        return result["content"].strip()
    # Graceful fallback (same pattern as tracer/agents.py)
    logger.warning("[spot_agent] fallback for topic '%s'", topic_name)
    return f"Explain the core idea of '{topic_name}' in your own words."


# ── gate_agent ────────────────────────────────────────────────────────────────

def gate_agent(
    topic_id: int,
    topic_name: str,
    question: str,
    student_answer: str,
    prior_verdicts: list[dict[str, Any]],
    prereq_id: int | None,
    graph: dict[int, dict],
    provider_fn,
) -> dict[str, Any]:
    """Evaluate the student's answer. Returns verdict dict.

    Safety (from tracer/agents.py):
      - prerequisite_id is ALWAYS resolved from the graph in code.
        The LLM decides PASS/BLOCK and the objections only.
      - If the model returns an unknown prerequisite_id it is overridden.
    """
    from pydantic import BaseModel

    class _Out(BaseModel):
        status: str = "BLOCK"
        objections: list[str] = []
        prerequisite_id: str | None = None

    verdicts_text = "\n".join(
        f"- [{v.get('status')}] {', '.join(v.get('objections', []))}"
        for v in prior_verdicts
        if v.get("topic_id") == topic_id
    ) or "(none)"

    prompt = _GATE_PROMPT.format(
        topic_name=topic_name,
        question=question,
        student_answer=student_answer,
        prior_verdicts=verdicts_text,
        prereq_id=str(prereq_id) if prereq_id is not None else "null",
    )
    result = _call_provider(provider_fn, prompt, _Out)

    if result is None:
        # Conservative fallback: BLOCK with graph prereq (same as tracer/agents.py)
        return {
            "topic_id": topic_id,
            "status": "BLOCK",
            "objections": ["The evaluator could not be reached. Try again."],
            "prerequisite_id": prereq_id,
        }

    raw_status = str(result.get("status", "BLOCK")).upper()
    verdict_status = "PASS" if raw_status == "PASS" else "BLOCK"

    # Safety: lock prerequisite_id to graph-known values only
    returned_prereq = result.get("prerequisite_id")
    if returned_prereq is not None:
        try:
            returned_prereq_int = int(returned_prereq)
            if returned_prereq_int not in graph:
                logger.warning(
                    "[gate_agent] model returned unknown prereq %s for topic %s; overriding",
                    returned_prereq, topic_id,
                )
                returned_prereq_int = prereq_id
        except (TypeError, ValueError):
            returned_prereq_int = prereq_id
    else:
        returned_prereq_int = prereq_id if verdict_status == "BLOCK" else None

    return {
        "topic_id": topic_id,
        "status": verdict_status,
        "objections": result.get("objections", []) if verdict_status == "BLOCK" else [],
        "prerequisite_id": returned_prereq_int if verdict_status == "BLOCK" else None,
    }


# ── Stub implementations (for tests / offline mode) ──────────────────────────

def stub_spot(topic_id: int, topic_name: str, difficulty: int,
              prior_objections: list[str], **_) -> str:
    return f"[STUB] Explain the core concept of '{topic_name}' at level {difficulty}."


def stub_gate(topic_id: int, topic_name: str, question: str,
              student_answer: str, prior_verdicts: list, prereq_id: int | None,
              graph: dict, **_) -> dict:
    """Always passes in stub mode so tests run deterministically."""
    return {"topic_id": topic_id, "status": "PASS", "objections": [], "prerequisite_id": None}


def stub_gate_block(topic_id: int, topic_name: str, question: str,
                    student_answer: str, prior_verdicts: list, prereq_id: int | None,
                    graph: dict, **_) -> dict:
    """Always blocks — for testing the backward-pass branch."""
    return {
        "topic_id": topic_id,
        "status": "BLOCK",
        "objections": ["[STUB] Insufficient answer."],
        "prerequisite_id": prereq_id,
    }

