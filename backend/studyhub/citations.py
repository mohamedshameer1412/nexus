"""Verification of a model's cited answer. Pure code: no model, no network.

The model proposes statements and, for each, quotes from numbered passages. This module decides what may be shown.
A statement survives only if EVERY citation passes:

  1. the passage number is one the model was actually given;
  2. the quote appears word for word, in one piece, in that passage (whitespace and typographic quotes/dashes are
     normalised; letter case and wording are not);
  3. the quote is long enough to mean something (not "the" or "stack");
  4. every number in the statement also appears in its quotes (a made-up figure has nothing to stand on);
  5. the statement shares enough of its content words with its quotes (a real quote pinned to an unrelated claim fails).

What this guarantees: every displayed statement rests on text that really exists in the student's material.
What it does NOT guarantee: that the statement is a faithful reading of that text (the entailment gap). The page
therefore always shows the quote beside the statement.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field

from typing import Literal

from pydantic import BaseModel

from . import screen
from .retrieval import stem, terms

MIN_QUOTE_WORDS = 4
MIN_QUOTE_CHARS = 20
MAX_QUOTE_WORDS = 80
MAX_CITATIONS_PER_CLAIM = 3
MAX_CLAIMS = 5
MIN_OVERLAP = 0.25


class Citation(BaseModel):
    passage: int
    quote: str


class Claim(BaseModel):
    text: str
    citations: list[Citation]


class Answer(BaseModel):
    """What a model returns. The shape follows the knowledge agent's grounded answer: a status, the statements with their
    evidence, and a step-by-step explanation.

    NOT_SUPPORTED (or no claims) = the passages do not answer the question. CONFLICT = the passages disagree with each
    other; the claims then state each side with its own quote."""
    status: Literal["SUPPORTED", "NOT_SUPPORTED", "CONFLICT"] = "SUPPORTED"
    claims: list[Claim] = []
    explanation: str = ""

    @property
    def not_covered(self) -> bool:
        return self.status == "NOT_SUPPORTED" or not self.claims


# ------------------------------------------------------------------------------------------------ normalising

_QUOTES = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"',
                         "„": '"', "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
                         "−": "-", "­": "", "…": "..."})


def normalize(text: str) -> str:
    """Whitespace and typography only. Case, wording and punctuation stay, so a changed word never matches."""
    text = unicodedata.normalize("NFKC", text or "").translate(_QUOTES)
    return " ".join(text.split())


def clean_quote(quote: str) -> str:
    """Drop the decoration models add around a quote: outer quotation marks, leading/trailing ellipses."""
    q = normalize(quote)
    for _ in range(3):
        q = q.strip()
        if q.startswith("..."):
            q = q[3:]
        if q.endswith("..."):
            q = q[:-3]
        q = q.strip()
        if len(q) >= 2 and q[0] == q[-1] and q[0] in "\"'":
            q = q[1:-1]
    return q.strip()


def find_span(quote: str, passage_text: str) -> str | None:
    """The exact words of the passage that the quote matches, or None.

    The match is word for word, with ONE allowance: the first letter may differ in case (a model that starts a quote at
    a mid-sentence word will capitalise it). What is returned - and what the page shows - is the passage's own text."""
    q, hay = clean_quote(quote), normalize(passage_text)
    if not q:
        return None
    for candidate in (q, q[0].swapcase() + q[1:]):
        at = hay.find(candidate)
        if at >= 0:
            return hay[at:at + len(candidate)]
    return None


def quote_in_passage(quote: str, passage_text: str) -> bool:
    return find_span(quote, passage_text) is not None


# --------------------------------------------------------------------------------------------- word matching

_stem = stem


_NUMBER = re.compile(r"\d[\d,.]*\d|\d")


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in _NUMBER.findall(normalize(text))}


def overlap(claim: str, quotes: list[str]) -> tuple[int, int]:
    """(content words of the claim found in the quotes, content words in the claim), after light stemming."""
    claim_words = {_stem(w) for w in terms(claim)}
    quote_words = {_stem(w) for q in quotes for w in re.findall(r"[^\W_]+", q.lower())}
    return len(claim_words & quote_words), len(claim_words)


# ------------------------------------------------------------------------------------------------- verifying

@dataclass
class ClaimCheck:
    index: int                                   # 1-based, as the model numbered it
    text: str
    ok: bool
    problems: list[str] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)      # verified snapshots, only when ok
    duplicate: bool = False                      # says the same as an earlier statement: left out quietly, not a failure


@dataclass
class Verification:
    checks: list[ClaimCheck]
    truncated: int = 0                           # claims beyond MAX_CLAIMS that were never looked at

    @property
    def verified(self) -> list[ClaimCheck]:
        return [c for c in self.checks if c.ok]

    @property
    def dropped(self) -> int:
        return len([c for c in self.checks if not c.ok and not c.duplicate])

    @property
    def all_ok(self) -> bool:
        return bool(self.verified) and all(c.ok or c.duplicate for c in self.checks)

    def feedback(self) -> str:
        """What to tell the model so its next draft can fix the failures (only the failures)."""
        lines = [f"- Statement {c.index} (\"{_short(c.text, 70)}\"): " + " ".join(c.problems) for c in self.checks if not c.ok and not c.duplicate]
        return "\n".join(lines)


def _short(text: str, n: int) -> str:
    text = normalize(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def verify(answer: Answer, passages: list[dict], focus: str | list[str] | None = None) -> Verification:
    """Check `answer` against the numbered `passages` the model was shown (passages[0] is P1).

    Each passage is a dict with at least: id, text, doc_title, page_start, page_end, heading_path.
    `focus` are the question's key words (see retrieval.focus_terms); a statement must mention at least one, in its own
    words or in its quotes, so a true-but-off-topic statement is not shown as the answer."""
    focus_words = [focus] if isinstance(focus, str) else list(focus or [])
    checks: list[ClaimCheck] = []
    seen: set[str] = set()
    accepted: list[tuple[set[str], frozenset[str]]] = []      # (content words, quotes) of statements already kept
    for i, claim in enumerate(answer.claims[:MAX_CLAIMS], start=1):
        problems: list[str] = []
        text = normalize(claim.text)
        if not 10 <= len(text) <= 500:
            problems.append("The statement must be one clear sentence of 10 to 500 characters.")
        identical = text.lower() in seen
        seen.add(text.lower())
        cites = claim.citations[:MAX_CITATIONS_PER_CLAIM]
        if not cites:
            problems.append("It has no citation. Every statement needs at least one quote from a passage.")
        verified: list[dict] = []
        quotes: list[str] = []
        for c in cites:
            if not 1 <= c.passage <= len(passages):
                problems.append(f"Passage {c.passage} does not exist; the passages are P1 to P{len(passages)}.")
                continue
            p = passages[c.passage - 1]
            q = clean_quote(c.quote)
            words = len(q.split())
            if len(q) < MIN_QUOTE_CHARS or words < MIN_QUOTE_WORDS:
                problems.append(f"The quote \"{_short(q, 50)}\" is too short; quote at least {MIN_QUOTE_WORDS} consecutive words.")
                continue
            if words > MAX_QUOTE_WORDS:
                problems.append(f"The quote starting \"{_short(q, 40)}\" is longer than {MAX_QUOTE_WORDS} words; quote less.")
                continue
            if screen.find(q):
                problems.append(f'The quote "{_short(q, 50)}" reads like an instruction to an AI, not like course material.')
                continue
            span = find_span(q, p["text"])
            if span is None:
                problems.append(f"The quote \"{_short(q, 60)}\" does not appear word for word in passage {c.passage}. "
                                "Copy the exact words from one place in one passage.")
                continue
            quotes.append(span)
            verified.append({"chunk_id": p["id"], "quote": span, "doc_title": p["doc_title"], "page_start": p["page_start"],
                             "page_end": p["page_end"], "heading_path": p["heading_path"], "passage": c.passage})
        if verified and not problems:
            unsupported = sorted(numbers_in(text) - numbers_in(" ".join(quotes)))
            if unsupported:
                problems.append("The number(s) " + ", ".join(unsupported) + " appear in the statement but not in its quotes.")
            shared, total = overlap(text, quotes)
            if total and shared < max(1, math.ceil(MIN_OVERLAP * total)):
                problems.append("The statement does not seem to be about what its quote says; make it follow the quote.")
            if focus_words and not problems:
                have = {_stem(w) for w in re.findall(r"[^\W_]+", " ".join([text] + quotes).lower())}
                if not any(_stem(f) in have for f in focus_words):
                    shown = " or ".join(f'"{f}"' for f in focus_words)
                    problems.append(f"The statement does not mention {shown}, the key word of the question. "
                                    "Only include statements that answer the question.")
        ok = not problems and bool(verified)
        duplicate = False
        if ok:
            stems = {_stem(w) for w in terms(text)}
            key = frozenset(v["quote"] for v in verified)
            duplicate = identical or any(
                key == prev_key and len(stems & prev) / max(1, len(stems | prev)) >= 0.6 for prev, prev_key in accepted)
            if duplicate:
                ok = False
            else:
                accepted.append((stems, key))
        checks.append(ClaimCheck(i, text, ok, problems, verified if ok else [], duplicate))
    return Verification(checks, max(0, len(answer.claims) - MAX_CLAIMS))


# ---------------------------------------------------------------------------------------------- explanation

MAX_EXPLANATION_CHARS = 900
# "statement 1", "quote 2", "passage P3", "[2]", "step 1": numbers that point at parts of the answer, not facts in it
_REFERENCE = re.compile(r"\b(?:statements?|claims?|quotes?|passages?|sources?|citations?|evidence|points?|steps?|parts?)"
                        r"\s*#?\s*\d+\b|\bP\d+\b|\[\d+\]", re.I)


def check_explanation(explanation: str, statements: list[str], quotes: list[str]) -> tuple[str, str]:
    """(text to show, note). The explanation is model prose, so it is only shown when cheap code checks pass:
    it must not read as an order to an AI, must not contain a number that is in neither the statements nor the quotes,
    and must share enough content words with them. Otherwise it is dropped and the note says why (the answer stands).
    It is never presented as verified word for word: the page labels it as the model's reasoning."""
    text = normalize(explanation)
    if not text:
        return "", "the model gave no explanation"
    if len(text) > MAX_EXPLANATION_CHARS:
        cut = text[:MAX_EXPLANATION_CHARS]
        text = cut[: cut.rfind(". ") + 1] if ". " in cut else cut
    if screen.find(text):
        return "", "the explanation read like an instruction to an AI"
    base = " ".join(statements + quotes)
    extra = sorted(numbers_in(_REFERENCE.sub(" ", text)) - numbers_in(base))
    if extra:
        return "", "the explanation contained number(s) " + ", ".join(extra) + " that are not in the statements or quotes"
    shared, total = overlap(text, [base])
    if total and shared < max(1, math.ceil(MIN_OVERLAP * total)):
        return "", "the explanation did not follow the evidence"
    return text, ""
