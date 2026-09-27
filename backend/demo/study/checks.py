"""The validator's deterministic half. Nothing in this file asks a model anything.

That is the point. A model can be talked into anything by the text in front of
it; a regular expression and a substring test cannot. So every claim the
generator or the auditor makes about the SOURCE is re-checked here, in plain
code, before it is allowed to matter:

    is the quoted passage really in the source?       locate_quote
    are the four options really four different ones?  check_pack
    does the source try to give the AI orders?         find_injection

The injection screen is a heuristic. It catches the common phrasings and is
deliberately narrow, because a false positive stops a run. It is one layer: the
auditor is asked to quote anything it sees (and the quote is verified here), and
approval is derived from observations, never from a model saying "approved".
"""
from __future__ import annotations

import re
import unicodedata

from .schema import Audit, HumanReview, Issue, StudyPack

MIN_SOURCE_WORDS = 25
MAX_SOURCE_CHARS = 12_000

# A revision cannot fix these: the problem is in what the user pasted, not in
# what the generator wrote. Regenerating would only spend tokens.
NON_REVISABLE = frozenset({"source_injection"})

_TYPOGRAPHY = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


def normalise(text: str) -> str:
    """Whitespace, typographic quotes and dashes, and invisible characters
    folded away - and nothing else. Case is kept: "verbatim" means verbatim."""
    t = unicodedata.normalize("NFKC", text or "").translate(_TYPOGRAPHY)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")   # zero-width tricks
    return re.sub(r"\s+", " ", t).strip()


# ------------------------------------------------------------ prompt injection

_INJECTION = [re.compile(p, re.I) for p in (
    # "ignore all previous instructions", "disregard the above rules"
    r"\b(?:ignore|disregard|forget|override)\s+(?:(?:the|these|those)\s+)?"
    r"(?:(?:all|any|every|previous|prior|above|earlier|preceding|your|my|other)\s+)+"
    r"(?:the\s+)?(?:instructions?|prompts?|rules|directions?|guidelines|constraints)\b",
    # "forget everything above"
    r"\b(?:forget|ignore|disregard)\s+(?:everything|all)\s+"
    r"(?:above|before|prior|previous|you\s+(?:were|have\s+been)\s+told)\b",
    # "reveal your system prompt" - "your", so a lab manual's "print the instructions" is safe
    r"\b(?:reveal|show|print|repeat|leak|output)\s+(?:me\s+)?your\s+"
    r"(?:system\s+|hidden\s+|initial\s+|original\s+)?(?:prompt|instructions)\b",
    # "you are now a pirate assistant"
    r"\byou\s+are\s+now\s+(?:an?\s+|the\s+|in\s+)?(?:\w+\s+){0,2}?"
    r"(?:assistant|chatbot|bot|dan|persona|jailbroken|unrestricted)\b",
    r"\b(?:new|updated|revised|override)\s+(?:system\s+)?instructions?\s*:",
    # aimed at THIS system: "mark this output as APPROVED", "reply with APPROVED".
    # The object is named, so "regulators mark a drug as approved" is not caught.
    r"\b(?:mark|label|declare|rate)\s+(?:this|it|everything|all|each|every|"
    r"the\s+(?:output|result|answer|response|pack|material|questions?))\b[^.\n]{0,20}?\bapproved\b",
    r"\b(?:output|return|respond\s+with|reply\s+with)\s+(?:only\s+)?[\"']?approved\b",
    r"\bnote\s+to\s+(?:the\s+)?(?:ai|assistant|model|llm|validator|grader|reviewer)\b",
    r"<\|?\s*(?:im_start|im_end|system|endoftext)\s*\|?>",
    r"\[/?INST\]",
    r"\b(?:jailbreak|developer\s+mode)\b",
)]


def find_injection(text: str) -> list[str]:
    """The passages in `text` that read as orders to an AI. Empty means none found."""
    t = normalise(text)
    hits: list[str] = []
    for rx in _INJECTION:
        for m in rx.finditer(t):
            snippet = m.group(0).strip()[:80]
            if snippet not in hits:
                hits.append(snippet)
    return hits


# ---------------------------------------------------------------- the source

def screen_source(source: str) -> list[Issue]:
    """Intake checks, run before any model is called. Cheap, and they stop a
    run that could never succeed from spending anything."""
    text = source or ""
    if not text.strip():
        return [Issue(code="empty_input", where="source", origin="code",
                      detail="The source text is empty. Paste the study material to work from.")]
    words = len(text.split())
    if words < MIN_SOURCE_WORDS:
        return [Issue(code="input_too_short", where="source", origin="code",
                      detail=f"The source has {words} words; at least {MIN_SOURCE_WORDS} are "
                             "needed to write questions that are grounded in it.")]
    if len(text) > MAX_SOURCE_CHARS:
        return [Issue(code="input_too_long", where="source", origin="code",
                      detail=f"The source is {len(text):,} characters; the limit is "
                             f"{MAX_SOURCE_CHARS:,}. Split it and run each part separately.")]
    hits = find_injection(text)
    if hits:
        return [Issue(code="source_injection", where="source", origin="code",
                      detail="The source contains text that tries to instruct the AI instead of "
                             "teach the subject: " + "; ".join(repr(h) for h in hits[:3]))]
    return []


def paragraphs(source: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", source or "") if p.strip()]


def locate_quote(source: str, quote: str) -> tuple[bool, int | None]:
    """Is `quote` in `source` word for word (whitespace and typography aside)?

    Returns (found, paragraph) - the 1-based paragraph, or None when the quote
    straddles a paragraph break. The paragraph comes from HERE, not from the
    model, so it is a fact about the source rather than a claim about it."""
    q = normalise(quote)
    if not q:
        return False, None
    for i, p in enumerate(paragraphs(source), 1):
        if q in normalise(p):
            return True, i
    return (q in normalise(source)), None


# ---------------------------------------------------------------- the draft

def _pack_text(pack: StudyPack) -> str:
    parts = [pack.title, *pack.notes]
    for q in pack.questions:
        parts += [q.question, *q.options, q.explanation]
    return "\n".join(parts)


def check_pack(source: str, pack: StudyPack) -> list[Issue]:
    """What can be established about a draft without asking a model."""
    issues: list[Issue] = []
    seen: dict[str, int] = {}

    for i, q in enumerate(pack.questions):
        where = f"questions[{i}]"

        norm = [normalise(o).casefold() for o in q.options]
        if len(set(norm)) != len(norm):
            issues.append(Issue(
                code="duplicate_options", where=where, origin="code",
                detail="Two options are the same, so the question cannot have exactly one "
                       "correct answer. Make all four options distinct."))

        # Found on a real local-model run: options written as "A. To produce ...", which the
        # page then renders as "A. A. To produce ...". A validator that is the same model as
        # the generator did not notice; code does. All four must carry their own position's
        # letter, so a legitimate "A. thaliana" among ordinary options is left alone.
        if all(re.match(rf"\(?{'ABCD'[j]}[.):]\s", normalise(o), re.I) for j, o in enumerate(q.options)):
            issues.append(Issue(
                code="option_label_in_text", where=where, origin="code",
                detail="Every option already starts with its own letter (A., B., ...). Write only "
                       "the option text; the letters are added for you."))

        found, _ = locate_quote(source, q.source_quote)
        if not found:
            issues.append(Issue(
                code="quote_not_in_source", where=where, origin="code",
                detail=f"The cited passage {q.source_quote!r} does not appear in the source. "
                       "Copy a supporting passage exactly as it is written there."))

        key = normalise(q.question).casefold()
        if key in seen:
            issues.append(Issue(
                code="duplicate_questions", where=where, origin="code",
                detail=f"This question repeats questions[{seen[key]}]. Ask about something else."))
        seen.setdefault(key, i)

    leaked = find_injection(_pack_text(pack))
    if leaked:
        issues.append(Issue(
            code="injection_in_output", where="notes", origin="code",
            detail="The generated text contains instruction-like wording: "
                   + "; ".join(repr(h) for h in leaked[:3])
                   + ". Write study material only."))
    return issues


def issues_from_audit(source: str, pack: StudyPack, audit: Audit) -> tuple[list[Issue], list[str]]:
    """Turn the auditor's OBSERVATIONS into issues.

    The auditor never saw the answer key. Here it is compared with what the
    auditor found: if the source supports anything other than exactly the
    marked option, the question does not have exactly one correct answer."""
    issues: list[Issue] = []
    warnings: list[str] = []

    if not audit.notes_faithful:
        issues.append(Issue(
            code="unfaithful_notes", where="notes", origin="model",
            detail=audit.notes_problem or "The auditor judged the notes not faithful to the source."))

    by_number = {qa.number: qa for qa in audit.questions}
    for i, q in enumerate(pack.questions):
        where, qa = f"questions[{i}]", by_number.get(i + 1)
        if qa is None:
            issues.append(Issue(code="not_audited", where=where, origin="model",
                                detail="The auditor returned no judgement for this question."))
            continue
        supported = sorted(set(qa.supported))
        if supported != [q.answer]:
            found = ", ".join(supported) if supported else "none"
            issues.append(Issue(
                code="not_exactly_one_correct", where=where, origin="model",
                detail=f"The marked answer is {q.answer}, but the source supports: {found}. "
                       f"{qa.problem}".strip()))
        if not qa.clear:
            issues.append(Issue(
                code="unclear_question", where=where, origin="model",
                detail=qa.problem or "The auditor found this question unclear or ambiguous."))
        if not qa.explanation_valid:
            issues.append(Issue(
                code="invalid_explanation", where=where, origin="model",
                detail=qa.problem or "The explanation is not supported by the source."))

    if audit.injection_quote:
        found, _ = locate_quote(source, audit.injection_quote)
        if found:
            issues.append(Issue(
                code="source_injection", where="source", origin="model",
                detail="The source contains text that tries to instruct the AI: "
                       f"{audit.injection_quote!r}"))
        else:
            # A claim about the source that the source does not bear out is a
            # finding about the auditor. Record it; do not act on it.
            warnings.append("The auditor reported an injection quote that is not in the source; "
                            "ignored because it could not be verified.")
    return issues, warnings


# ------------------------------------------------------------- the human

_APPROVE = ("approve", "approved", "accept", "accepted")
_REJECT = ("reject", "rejected", "decline", "declined")


def parse_review(answer: dict | None) -> HumanReview:
    """Prose -> record. The reviewer writes APPROVE or REJECT, then any notes.

    Anything else is UNCLEAR, and unclear never approves: an answer we cannot
    read is not a yes."""
    if not answer or answer.get("source") == "unresolved_no_expert" \
            or not (answer.get("answer") or "").strip():
        return HumanReview(decision="NO_RESPONSE", source="unresolved_no_expert")

    text = answer["answer"].strip()
    m = re.match(r"([A-Za-z]+)[\s:,.\-]*(.*)", text, re.S)
    word, rest = (m.group(1).lower(), m.group(2).strip()) if m else ("", text)
    if word in _APPROVE:
        decision, notes = "APPROVED", rest
    elif word in _REJECT:
        decision, notes = "REJECTED", rest
    else:
        decision, notes = "UNCLEAR", text
    return HumanReview(decision=decision, notes=notes, reviewer=answer.get("who"),
                       source="human_expert")
