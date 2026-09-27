"""Slide-deck PDFs (bookmarks that are only "Slide 1, Slide 2...") get topics named after the slide titles; big textbooks are accepted."""
from __future__ import annotations

import io

import pytest

from studyhub import extract, ingest, settings
from studyhub.db import open_db
from studyhub.repo import Repo


def slide_pdf(titles: list[str | None], bookmarks: str | None = "Slide {n}", body_len: int = 420) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for n, title in enumerate(titles, start=1):
        if bookmarks:
            key = f"s{n}"
            c.bookmarkPage(key)
            c.addOutlineEntry(bookmarks.format(n=n), key, level=0)
        y = 800
        if title:
            c.setFont("Helvetica-Bold", 20)
            c.drawString(60, y, title)
            y -= 40
        c.setFont("Helvetica", 11)
        words = ("The signal travels through the channel and the receiver recovers it. " * 8).split()
        line = ""
        for w in words:
            if len(line) + len(w) > 90:
                c.drawString(60, y, line)
                y -= 16
                line = ""
            line += w + " "
        c.drawString(60, y, line)
        c.showPage()
    c.save()
    return buf.getvalue()


def topics_of(db, uid, sid):
    return [t["name"] for t in Repo(db).list_topics(uid, sid) if t["chunks"]]


@pytest.fixture
def account(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_DB", str(tmp_path / "s.db"))
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "u"))
    monkeypatch.setenv("STUDYHUB_SCRYPT_N", "1024")
    from studyhub import auth
    store = open_db()
    uid = auth.register(store.db, "sliding", "correct horse battery")
    sid = Repo(store.db).create_subject(uid, "Comms")
    yield store.db, uid, sid
    store.close()


def test_number_only_bookmarks_are_recognised():
    assert extract.generic_outline({1: [(1, "Slide 1")], 2: [(1, "Slide 2")], 3: [(1, "Slide 3")]}) is True
    assert extract.generic_outline({1: [(1, "Page 1")], 2: [(1, "Introduction")], 3: [(1, "Slide 3")]}) is True     # 2 of 3 are numbers
    assert extract.generic_outline({1: [(1, "Chapter One")], 2: [(1, "Signals and systems")]}) is False
    assert extract.generic_outline({}) is False


def test_a_slide_title_is_a_short_first_line_with_letters():
    assert extract.slide_title("Analog Modulation\nAmplitude varies with the message.") == "Analog Modulation"
    assert extract.slide_title("4\nAnalog Modulation") is None                         # a page number first: not a title
    assert extract.slide_title("Slide 4") is None
    assert extract.slide_title("x" * 200 + "\nbody") is None                           # a paragraph, not a title
    assert extract.slide_title("") is None


def test_a_slide_deck_gets_topics_named_after_its_titles_not_slide_numbers(account):
    db, uid, sid = account
    titles = ["Analog Modulation"] * 1 + ["Amplitude Modulation"] * 1 + ["Frequency Modulation"] * 1 + ["Noise in Channels"] * 1
    pdf = slide_pdf([t for t in titles for _ in range(3)])                              # 12 slides, 4 titles, 3 slides each
    r = ingest.ingest(db, uid, sid, "deck.pdf", pdf)
    names = topics_of(db, uid, sid)
    assert r.status == "parsed" and names and not any(n.lower().startswith("slide") for n in names)
    assert "Analog Modulation" in names and "Noise in Channels" in names and len(names) >= 2
    assert any("slide" in w.lower() for w in r.warnings)                                # the student is told how the topics were made


def test_slides_are_grouped_so_a_long_deck_does_not_make_a_topic_per_slide(account):
    db, uid, sid = account
    titles = [f"Topic {c}" for c in "ABCDEFGHIJKLMNOPQRST"]                             # 20 slides, each with its own short title
    ingest.ingest(db, uid, sid, "deck.pdf", slide_pdf(titles, body_len=300))
    names = topics_of(db, uid, sid)
    assert 2 <= len(names) < 20                                                         # small slides are gathered into fewer topics


def test_a_deck_without_any_bookmarks_still_reads_and_a_real_outline_is_left_alone(account):
    db, uid, sid = account
    ingest.ingest(db, uid, sid, "plain.pdf", slide_pdf(["Intro"] * 3, bookmarks=None))
    assert topics_of(db, uid, sid)                                                      # unchanged behaviour: one topic
    ingest.ingest(db, uid, sid, "book.pdf", slide_pdf(["Whatever"] * 3, bookmarks="Chapter {n}: Signals"))
    assert any(n.startswith("Chapter 1") for n in topics_of(db, uid, sid))              # real bookmark titles are kept


def test_large_textbooks_are_accepted_and_the_limits_can_still_be_lowered(account, monkeypatch):
    db, uid, sid = account
    assert settings.max_pages() >= 1000 and settings.max_subject_chars() >= 5_000_000
    monkeypatch.setenv("STUDYHUB_MAX_PAGES", "5")
    r = ingest.ingest(db, uid, sid, "big.pdf", slide_pdf(["T"] * 6, bookmarks=None))
    assert r.status == "failed" and any("limit is 5" in w for w in r.warnings)          # kept as a visible failed document, with the reason
