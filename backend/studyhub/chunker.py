"""Cut extracted blocks into searchable chunks that know where they came from.

A chunk never crosses a heading, is about TARGET characters (paragraph boundaries first, sentence boundaries when a
paragraph is long) and carries `heading_path` and `page_start/page_end`, so any citation can say WHERE in the material
the words are. Chunk text is a verbatim slice of the extracted text (only whitespace between paragraphs is added).

Topics come from structure: headings in the top two levels of the document. Text before the first heading, or in a
document with no headings at all, belongs to a topic named after the document.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .extract import Block

TARGET = 900
MAX = 1200
SEP = " › "                                             # "Chapter 3 > Trees"
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")


@dataclass
class ChunkSpec:
    text: str
    page_start: int | None
    page_end: int | None
    heading_path: str
    topic_path: str
    topic_origin: str                                        # 'heading' | 'document'
    flags: list[str] = field(default_factory=list)           # instruction-like snippets found by studyhub.screen

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def split_long(text: str, limit: int = MAX) -> list[str]:
    """Pieces of at most `limit` characters: on sentence ends, else on spaces, else hard."""
    if len(text) <= limit:
        return [text]
    pieces, cur = [], ""
    for sent in _SENTENCE.split(text):
        while len(sent) > limit:                             # one enormous sentence
            cut = sent.rfind(" ", 0, limit)
            cut = cut if cut > limit // 2 else limit
            head, sent = sent[:cut].strip(), sent[cut:].strip()
            if cur:
                pieces.append(cur)
                cur = ""
            if head:
                pieces.append(head)
        if cur and len(cur) + 1 + len(sent) > TARGET:
            pieces.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        pieces.append(cur)
    return pieces


def _has_words(text: str) -> bool:
    return sum(c.isalpha() for c in text) >= 3               # drops stray page numbers and rule lines


def chunk_blocks(blocks: list[Block], doc_title: str) -> list[ChunkSpec]:
    levels = [b.level for b in blocks if b.level]
    top = min(levels) if levels else 0
    stack: list[tuple[int, str]] = []                        # (level, title) of the headings we are inside
    out: list[ChunkSpec] = []
    cur: list[Block] = []

    def topic_path() -> tuple[str, str]:
        shown = [t for lv, t in stack if lv <= top + 1]
        return (SEP.join(shown), "heading") if shown else (doc_title, "document")

    def flush() -> None:
        nonlocal cur
        if not cur:
            return
        tpath, origin = topic_path()
        pages = [b.page for b in cur if b.page is not None]
        out.append(ChunkSpec("\n\n".join(b.text for b in cur), min(pages) if pages else None,
                             max(pages) if pages else None, SEP.join(t for _, t in stack), tpath, origin))
        cur = []

    for block in blocks:
        if block.level:
            flush()
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            continue
        if not _has_words(block.text):
            continue
        for piece in split_long(block.text):
            piece_block = Block(piece, block.page)
            size = sum(len(b.text) for b in cur) + 2 * len(cur)
            if cur and size + len(piece) > MAX:
                flush()
            cur.append(piece_block)
            if sum(len(b.text) for b in cur) + 2 * (len(cur) - 1) >= TARGET:
                flush()
    flush()
    return out
