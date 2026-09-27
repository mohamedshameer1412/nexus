"""Scripted replies, so the whole state machine can be run with no key, no network
and no tokens.

THIS IS NOT A MODEL. Every reply below was written by hand, and a run made with
it says so in its header (`mode: stub:...`). What it proves is the wiring - the
orchestrator, the deterministic checks, the loop, the suspension - not that any
model can do the job. Only a live run says that.

What is real even here: every reply is parsed through the real schema, and the
checks in checks.py run for real against the real source. In the default
scenario the auditor's first reply says nothing about the fabricated quote in
question 2 - the CODE catches it, because the auditor was never shown the quote.
"""
from __future__ import annotations

import json
from typing import Any

NOTES = [
    "Photosynthesis converts light energy into chemical energy stored in glucose.",
    "In plants it happens mainly in the leaves, inside chloroplasts that contain chlorophyll.",
    "Light-dependent reactions split water, release oxygen and make ATP and NADPH.",
    "The Calvin cycle uses ATP and NADPH to turn carbon dioxide into glucose.",
    "Carbon dioxide enters the leaf through tiny pores called stomata.",
]


def _q(question, options, answer, why, quote) -> dict:
    return {"question": question, "options": options, "answer": answer,
            "explanation": why, "source_quote": quote}


Q_CHLOROPLAST = _q(
    "Where in a plant cell does photosynthesis mainly take place?",
    ["Mitochondria", "Chloroplasts", "Nucleus", "Ribosomes"], "B",
    "Photosynthesis happens in chloroplasts, which hold the green pigment chlorophyll.",
    "inside organelles called chloroplasts")

# Flaw 1: the cited passage is not in the source. Plausible, and invented.
Q_OXYGEN_INVENTED = _q(
    "Which substance is released as a by-product of the light-dependent reactions?",
    ["Carbon dioxide", "Oxygen", "Nitrogen", "Glucose"], "B",
    "Splitting water in the light-dependent reactions releases oxygen.",
    "Oxygen is released through the roots of the plant.")

Q_OXYGEN = _q(
    "Which substance is released as a by-product of the light-dependent reactions?",
    ["Carbon dioxide", "Oxygen", "Nitrogen", "Glucose"], "B",
    "Splitting water in the light-dependent reactions releases oxygen.",
    "releasing oxygen as a by-product")

# Flaw 2: two options are defensible (ATP and NADPH, and carbon dioxide).
Q_CALVIN_AMBIGUOUS = _q(
    "Which of these does the Calvin cycle use?",
    ["ATP and NADPH", "Carbon dioxide", "Direct sunlight", "Chlorophyll"], "A",
    "The Calvin cycle uses ATP and NADPH made in the light-dependent reactions.",
    "the plant uses ATP and NADPH to turn carbon dioxide from the air into glucose")

Q_STOMATA = _q(
    "Through which structures does carbon dioxide enter the leaf?",
    ["Stomata", "Chloroplasts", "Roots", "Thylakoids"], "A",
    "The source says carbon dioxide enters the leaf through tiny pores called stomata.",
    "Carbon dioxide enters the leaf through tiny pores called stomata")


def pack(questions: list[dict], title: str = "Photosynthesis") -> dict:
    return {"title": title, "notes": list(NOTES), "questions": questions}


V1 = pack([Q_CHLOROPLAST, Q_OXYGEN_INVENTED, Q_CALVIN_AMBIGUOUS])   # two flaws
V2 = pack([Q_CHLOROPLAST, Q_OXYGEN, Q_STOMATA])                     # both fixed


def ok_audit(p: dict) -> dict:
    """An auditor that finds nothing wrong: exactly the marked option is supported."""
    return {"notes_faithful": True, "notes_problem": "",
            "questions": [{"number": i, "clear": True, "supported": [q["answer"]],
                           "explanation_valid": True, "problem": ""}
                          for i, q in enumerate(p["questions"], 1)],
            "injection_quote": None}


def audit_v1() -> dict:
    a = ok_audit(V1)
    a["questions"][2]["supported"] = ["A", "B"]
    a["questions"][2]["problem"] = (
        "The source says the Calvin cycle uses ATP and NADPH and also carbon dioxide, "
        "so options A and B are both correct.")
    return a


def never_right(n: int) -> dict:
    """Draft n of a generator that keeps inventing its evidence. Each draft is
    different - otherwise the repeated-output guard would fire first, which is a
    different stop with a different remedy."""
    return pack([Q_CHLOROPLAST, Q_STOMATA, _q(
        "Which substance is released as a by-product of the light-dependent reactions?",
        ["Carbon dioxide", "Oxygen", "Nitrogen", "Glucose"], "B",
        "Splitting water in the light-dependent reactions releases oxygen.",
        f"Oxygen is released through the roots of the plant (claim {n}).")])


class Scripted:
    """A drop-in for slice.llm.complete. Same keyword signature, no network.

    Each step ("generate", "audit") replays its own list in order. An item that
    is an exception INSTANCE is raised instead - that is how a test simulates an
    API failure or a malformed reply the real client could not repair."""

    def __init__(self, generate: list[Any], audit: list[Any]) -> None:
        self._script = {"generate": list(generate), "audit": list(audit)}
        self._n: dict[str, int] = {}
        self.calls: list[dict] = []          # what each call was given, for assertions

    def __call__(self, *, settings, budget, messages, schema=None, model=None,
                 step: str = "call", timeout: float = 120.0) -> Any:
        i = self._n.get(step, 0)
        self._n[step] = i + 1
        self.calls.append({"step": step, "messages": messages, "model": model or settings.model,
                           "fallback": settings.fallback_model, "max_tokens": settings.max_tokens})
        try:
            item = self._script[step][i]
        except (KeyError, IndexError):
            raise AssertionError(
                f"the script has no reply {i} for step {step!r}: the flow made a call it was "
                "not expecting, which is usually the finding rather than a problem with the script")
        if isinstance(item, BaseException):
            raise item
        raw = item if isinstance(item, str) else json.dumps(item)
        budget.record_tokens(len(raw) // 4 + 1)          # a plausible count, so the fences move
        return schema.model_validate_json(raw) if schema else raw

    def count(self, step: str) -> int:
        return self._n.get(step, 0)


SCENARIOS = {
    "revise": ("rejected once, revised, approved",
               lambda: Scripted([V1, V2], [audit_v1(), ok_audit(V2)])),
    "clean":  ("approved on the first draft",
               lambda: Scripted([V2], [ok_audit(V2)])),
    "stuck":  ("never converges: three revisions, then a human decides",
               lambda: Scripted([never_right(n) for n in range(1, 5)],
                                [ok_audit(never_right(n)) for n in range(1, 5)])),
    "repeat": ("the generator repeats itself, so a human decides",
               lambda: Scripted([V1, V1], [audit_v1(), audit_v1()])),
}
