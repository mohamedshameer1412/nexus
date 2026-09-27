"""StudyHub materials: extraction, chunking, ingestion, retrieval and LEAKAGE across users. (UNIT - no network, no model.)"""
from __future__ import annotations

import inspect
import io
import re
import zipfile
from pathlib import Path

import pytest

from studyhub import auth, ingest, retrieval, settings
from studyhub.chunker import MAX, chunk_blocks, split_long
from studyhub.db import open_db
from studyhub.extract import Block, ExtractError, extract, sniff
from studyhub.repo import Repo
from studyhub_files import (SAMPLE_TXT, encrypt_pdf, make_blank_pdf, make_docx, make_pdf)

PW = "correct horse battery"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYHUB_SCRYPT_N", "1024")
    monkeypatch.setenv("STUDYHUB_DB", str(tmp_path / "m.db"))
    monkeypatch.setenv("STUDYHUB_UPLOADS", str(tmp_path / "uploads"))


@pytest.fixture()
def world():
    store = open_db()
    db = store.db
    alice, bob = auth.register(db, "alice", PW), auth.register(db, "bob", PW)
    repo = Repo(db)
    a_subj, b_subj = repo.create_subject(alice, "Data structures"), repo.create_subject(bob, "Data structures")
    yield db, repo, alice, bob, a_subj, b_subj
    store.close()


def count(db, table):
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ------------------------------------------------------------------------------------------------ TXT

def test_txt_headings_are_found_and_body_text_is_kept():
    ex = extract("ds.txt", SAMPLE_TXT.encode())
    heads = [(b.level, b.text) for b in ex.blocks if b.level]
    assert heads == [(1, "Data Structures"), (2, "Stacks"), (2, "Queues"), (2, "Trees")]
    assert ex.status == "parsed" and ex.kind == "txt" and ex.title == "ds"
    assert "last-in first-out" in " ".join(b.text for b in ex.blocks)


def test_txt_numbered_and_uppercase_headings_but_not_sentences():
    text = ("1 Introduction\n\nSome words about the topic here.\n\n1.2 Details\n\nMore words about details here.\n\n"
            "SUMMARY\n\nThis line is a normal sentence that ends with a period.\n\n"
            "The quick brown fox jumps over the lazy dog and keeps running far away from here again\n\nend text")
    ex = extract("n.txt", text.encode())
    assert [(b.level, b.text) for b in ex.blocks if b.level] == [(1, "1 Introduction"), (2, "1.2 Details"), (1, "SUMMARY")]


def test_txt_heading_glued_to_its_paragraph_in_markdown():
    ex = extract("g.txt", b"## Stacks\nA stack pushes and pops elements at one end only.\n")
    assert [(b.level, b.text) for b in ex.blocks] == [(2, "Stacks"), (0, "A stack pushes and pops elements at one end only.")]


def test_txt_line_wraps_are_joined_within_a_paragraph():
    ex = extract("w.txt", b"first line of a\nparagraph that wraps\n\nsecond paragraph here")
    assert [b.text for b in ex.blocks] == ["first line of a paragraph that wraps", "second paragraph here"]


def test_txt_bom_is_dropped_and_cp1252_is_read_with_a_warning():
    assert extract("b.txt", b"\xef\xbb\xbfhello world of notes").blocks[0].text == "hello world of notes"
    ex = extract("c.txt", "café society notes about naive things".encode("cp1252"))
    assert "café" in ex.blocks[0].text and any("Windows-1252" in w for w in ex.warnings)


def test_txt_with_binary_content_is_refused():
    with pytest.raises(ExtractError, match="Only PDF"):
        extract("x.txt", b"abc\x00def" * 10)


# ------------------------------------------------------------------------------------------------ PDF

def test_pdf_pages_outline_and_metadata_title():
    pdf = make_pdf(["Chapter One\nThe first page talks about stacks and queues.",
                    "The second page talks about binary trees."], outline=[("Chapter One", 0), ("Trees", 1)],
                   title="My Course Notes")
    ex = extract("notes.pdf", pdf)
    assert (ex.kind, ex.pages, ex.title, ex.status) == ("pdf", 2, "My Course Notes", "parsed")
    assert [(b.level, b.text, b.page) for b in ex.blocks if b.level] == [(1, "Chapter One", 1), (1, "Trees", 2)]
    body = [b for b in ex.blocks if not b.level]
    assert {b.page for b in body} == {1, 2} and "binary trees" in body[-1].text


def test_pdf_without_an_outline_is_one_topic_and_says_so():
    ex = extract("plain.pdf", make_pdf(["Just some text about relational databases and keys."]))
    assert not any(b.level for b in ex.blocks) and ex.title == "plain"
    assert any("no outline" in w for w in ex.warnings)


def test_pdf_words_hyphenated_across_lines_are_rejoined():
    ex = extract("h.pdf", make_pdf(["The first algo-\nrithm sorts the data."]))
    assert "first algorithm sorts" in ex.blocks[0].text


def test_a_pdf_that_puts_a_space_line_between_every_word_is_not_split_into_word_paragraphs():
    """Found by looking at a screenshot of a real PDF: 'word\\n \\nword' made ~200 one-word paragraphs per page."""
    from studyhub.extract import pdf_paragraphs
    page = "AI  software  falls  into  four  categories  \nthe\n \nanalogy\n \nof\n \nrunning\n \na\n \nrestaurant\n \nkitchen.\n"
    assert pdf_paragraphs(page) == ["AI software falls into four categories the analogy of running a restaurant kitchen."]
    assert pdf_paragraphs("first paragraph.\n\nsecond paragraph.") == ["first paragraph.", "second paragraph."]


def test_ligatures_from_pdf_fonts_are_folded_but_other_text_is_untouched():
    from studyhub.extract import clean
    assert clean("the ﬁrst eﬃcient ﬂow", compat=True) == "the first efficient flow"
    assert clean("café “quoted”", compat=False) == "café “quoted”"


def test_a_scanned_pdf_is_reported_not_silently_empty():
    ex = extract("scan.pdf", make_blank_pdf(3))
    assert ex.status == "empty" and ex.pages == 3
    assert any("scanned" in w and "OCR" in w for w in ex.warnings)


def test_pages_without_text_are_counted():
    ex = extract("mixed.pdf", make_pdf(["Real text about hashing and collisions in tables.", "", ""]))
    assert any("2 of 3 pages" in w for w in ex.warnings)


def test_an_encrypted_pdf_and_a_damaged_pdf_are_refused_with_a_clear_message():
    good = make_pdf(["Some readable text about graphs and their edges."])
    with pytest.raises(ExtractError, match="password"):
        extract("locked.pdf", encrypt_pdf(good))
    with pytest.raises(ExtractError, match="damaged"):
        extract("bad.pdf", good[: len(good) // 2])
    with pytest.raises(ExtractError, match="damaged"):
        extract("junk.pdf", b"%PDF-1.4\nthis is not really a pdf at all" * 5)


def test_a_pdf_over_the_page_limit_is_refused(monkeypatch):
    monkeypatch.setenv("STUDYHUB_MAX_PAGES", "2")
    with pytest.raises(ExtractError, match="limit is 2"):
        extract("long.pdf", make_pdf(["one page of words", "two pages of words", "three pages of words"]))


# ----------------------------------------------------------------------------------------------- DOCX

def test_docx_heading_styles_paragraphs_and_tables():
    data = make_docx([("Heading 1", "Networks"), ("Normal", "A network connects computers so they can share data."),
                      ("Heading 2", "Layers"), ("Normal", "The stack has several layers with different jobs.")],
                     table=[["Layer", "Job"], ["Transport", "Delivery"]], title="Networking basics")
    ex = extract("net.docx", data)
    assert ex.title == "Networking basics" and ex.kind == "docx" and ex.pages is None
    assert [(b.level, b.text) for b in ex.blocks if b.level] == [(1, "Networks"), (2, "Layers")]
    assert "Transport | Delivery" in [b.text for b in ex.blocks]


def test_a_zip_bomb_docx_is_refused():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", "<w:document/>")
        z.writestr("word/padding.bin", b"\0" * 8_000_000)
    with pytest.raises(ExtractError, match="unreasonable size"):
        extract("bomb.docx", buf.getvalue())


def test_a_corrupt_docx_is_refused():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "not xml at all")
    with pytest.raises(ExtractError, match="could not be read"):
        extract("broken.docx", buf.getvalue())


# ------------------------------------------------------------------------------------------ file types

def test_files_are_recognised_by_content_not_by_name():
    assert sniff("notes.txt", make_pdf(["some text for the sniffer to see"])) == "pdf"
    assert sniff("notes.pdf", b"just plain words") == "txt"
    assert sniff("x", make_docx([("Normal", "hello there")])) == "docx"


@pytest.mark.parametrize("name,data", [
    ("evil.exe", b"MZ\x90\x00" + b"\0" * 100), ("pic.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 20),
    ("old.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 50), ("data.zip", b"PK\x03\x04" + b"\0" * 40),
    ("bin.bin", b"\x01\x02\x00\x03" * 50), ("elf", b"\x7fELF" + b"\x01" * 30)])
def test_unsupported_files_are_refused(name, data):
    with pytest.raises(ExtractError, match="Only PDF"):
        sniff(name, data)


# --------------------------------------------------------------------------------------------- chunker

def test_chunks_carry_headings_pages_and_never_cross_a_heading():
    blocks = [Block("Ch 1", None, 1), Block("word " * 50, 1), Block("Trees", None, 2), Block("tree " * 60, 2),
              Block("more tree " * 40, 3), Block("Graphs", None, 2), Block("graph " * 30, 4)]
    chunks = chunk_blocks(blocks, "Doc")
    assert {c.topic_path for c in chunks} == {"Ch 1", "Ch 1 › Trees", "Ch 1 › Graphs"}
    trees = [c for c in chunks if c.topic_path.endswith("Trees")]
    assert trees[0].page_start == 2 and trees[-1].page_end == 3 and trees[0].heading_path == "Ch 1 › Trees"
    for c in chunks:
        assert "graph" not in c.text or c.topic_path.endswith("Graphs"), "text of one section must not leak into another"


def test_chunk_sizes_are_bounded_and_long_paragraphs_split_on_sentences():
    para = " ".join(f"Sentence number {i} says something useful about the topic." for i in range(80))
    chunks = chunk_blocks([Block(para, 1)], "Doc")
    assert len(chunks) > 3 and all(len(c.text) <= MAX for c in chunks)
    assert all(c.text.rstrip().endswith(".") for c in chunks), "cut at sentence ends"
    assert " ".join(c.text.replace("\n\n", " ") for c in chunks) == para, "nothing lost, nothing added"


def test_one_enormous_sentence_is_hard_split_without_losing_text():
    text = "x" * 3000
    pieces = split_long(text)
    assert all(len(p) <= MAX for p in pieces) and "".join(pieces) == text


def test_no_text_is_lost_between_blocks_and_chunks():
    ex = extract("ds.txt", SAMPLE_TXT.encode())
    chunks = chunk_blocks(ex.blocks, ex.title)
    body = " ".join(b.text for b in ex.blocks if not b.level)
    assert " ".join(c.text.replace("\n\n", " ") for c in chunks) == body


def test_documents_without_headings_become_one_topic_named_after_the_document():
    chunks = chunk_blocks([Block("plenty of words about arrays " * 5, 1)], "My Notes")
    assert {(c.topic_path, c.topic_origin) for c in chunks} == {("My Notes", "document")}


def test_text_before_the_first_heading_goes_to_the_document_topic():
    chunks = chunk_blocks([Block("preface words about this book here", 1), Block("Ch 1", None, 1), Block("body words for chapter one", 1)], "Book")
    assert [c.topic_path for c in chunks] == ["Book", "Ch 1"]


def test_headings_deeper_than_two_levels_stay_in_the_path_but_not_the_topic():
    blocks = [Block("A", None, 1), Block("B", None, 2), Block("C", None, 3), Block("deep text about the subtopic here", 1)]
    (chunk,) = chunk_blocks(blocks, "Doc")
    assert chunk.topic_path == "A › B" and chunk.heading_path == "A › B › C"


def test_stray_page_numbers_and_rules_are_not_chunks():
    assert chunk_blocks([Block("12", 1), Block("-----", 1), Block("A real sentence about sorting lives here.", 1)], "D")[0].text.startswith("A real")
    assert len(chunk_blocks([Block("12", 1), Block("- - -", 1)], "D")) == 0


# --------------------------------------------------------------------------------------------- ingest

def test_ingest_stores_document_topics_and_searchable_chunks(world):
    db, repo, alice, _, sid, _ = world
    r = ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    assert (r.status, r.duplicate) == ("parsed", False) and r.chunks == 3 and r.topics == 3
    assert [t["path"] for t in repo.list_topics(alice, sid)] == [
        "Data Structures › Stacks", "Data Structures › Queues", "Data Structures › Trees"]
    assert repo.list_documents(alice, sid)[0]["chunks"] == 3
    hit = retrieval.search(db, alice, sid, "inorder traversal of a binary tree")[0]
    assert "Inorder traversal" in hit["text"] and hit["heading_path"].endswith("Trees") and hit["doc_title"] == "ds"


def test_the_original_is_kept_on_disk_under_its_hash_only(world, tmp_path):
    db, repo, alice, _, sid, _ = world
    data = SAMPLE_TXT.encode()
    ingest.ingest(db, alice, sid, "../../evil name.txt", data)
    files = [p for p in (tmp_path / "uploads").rglob("*") if p.is_file()]
    assert len(files) == 1 and files[0].parent.name == str(alice) and re.fullmatch(r"[0-9a-f]{64}", files[0].name)
    assert files[0].read_bytes() == data
    assert repo.list_documents(alice, sid)[0]["source"] == "../../evil name.txt", "kept only as a label, never as a path"


def test_the_same_file_twice_in_one_subject_adds_nothing(world):
    db, _, alice, _, sid, _ = world
    first = ingest.ingest(db, alice, sid, "a.txt", SAMPLE_TXT.encode())
    before = (count(db, "documents"), count(db, "chunks"), count(db, "topics"))
    again = ingest.ingest(db, alice, sid, "renamed.txt", SAMPLE_TXT.encode())
    assert again.duplicate and again.document_id == first.document_id
    assert (count(db, "documents"), count(db, "chunks"), count(db, "topics")) == before


def test_the_same_file_may_live_in_two_subjects(world):
    db, repo, alice, _, sid, _ = world
    other = repo.create_subject(alice, "Second")
    ingest.ingest(db, alice, sid, "a.txt", SAMPLE_TXT.encode())
    assert ingest.ingest(db, alice, other, "a.txt", SAMPLE_TXT.encode()).duplicate is False
    assert count(db, "documents") == 2


def test_a_scanned_pdf_is_recorded_as_empty_with_its_warning(world):
    db, repo, alice, _, sid, _ = world
    r = ingest.ingest(db, alice, sid, "scan.pdf", make_blank_pdf(2))
    doc = repo.get_document(alice, sid, r.document_id)
    assert (doc["status"], doc["chunks"], doc["pages"]) == ("empty", 0, 2) and "OCR" in doc["warnings"][0]
    assert retrieval.search(db, alice, sid, "anything") == []


def test_an_encrypted_pdf_is_recorded_as_failed_and_can_be_removed(world):
    db, repo, alice, _, sid, _ = world
    r = ingest.ingest(db, alice, sid, "locked.pdf", encrypt_pdf(make_pdf(["Some readable text about graphs."])))
    doc = repo.get_document(alice, sid, r.document_id)
    assert doc["status"] == "failed" and "password" in doc["warnings"][0]
    assert ingest.delete_document(db, alice, sid, r.document_id) and repo.list_documents(alice, sid) == []


@pytest.mark.parametrize("name,data,fragment", [
    ("empty.txt", b"", "empty"), ("evil.exe", b"MZ" + b"\0" * 50, "Only PDF"), ("p.png", b"\x89PNG" + b"\0" * 9, "Only PDF")])
def test_refused_uploads_store_nothing(world, tmp_path, name, data, fragment):
    db, _, alice, _, sid, _ = world
    with pytest.raises(ingest.IngestError, match=fragment):
        ingest.ingest(db, alice, sid, name, data)
    assert count(db, "documents") == 0 and not list((tmp_path / "uploads").rglob("*"))


def test_size_limits(world, monkeypatch):
    db, _, alice, _, sid, _ = world
    monkeypatch.setenv("STUDYHUB_MAX_UPLOAD_BYTES", "500")
    with pytest.raises(ingest.IngestError, match="larger than"):
        ingest.ingest(db, alice, sid, "big.txt", b"word " * 200)
    monkeypatch.setenv("STUDYHUB_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))
    monkeypatch.setenv("STUDYHUB_MAX_SUBJECT_CHARS", "600")
    ingest.ingest(db, alice, sid, "one.txt", (b"alpha sentence about arrays. " * 15))
    with pytest.raises(ingest.IngestError, match="material limit"):
        ingest.ingest(db, alice, sid, "two.txt", (b"beta sentence about lists. " * 15))
    assert count(db, "documents") == 1


def test_a_failure_halfway_leaves_nothing_behind(world, monkeypatch):
    db, repo, alice, _, sid, _ = world
    real = db.execute
    calls = {"n": 0}

    class Boom(Exception):
        pass

    class Wrapper:
        def __getattr__(self, name):
            return getattr(db, name)

        def execute(self, sql, *args):
            if sql.lstrip().startswith("INSERT INTO chunks("):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise Boom()
            return real(sql, *args)

    with pytest.raises(Boom):
        Repo(Wrapper()).store_document(alice, sid, {"kind": "txt", "title": "t", "source": "s", "sha256": "0" * 64,
                                                    "bytes": 1, "pages": None, "status": "parsed", "warnings": []},
                                       chunk_blocks(extract("ds.txt", SAMPLE_TXT.encode()).blocks, "ds"))
    assert (count(db, "documents"), count(db, "chunks"), count(db, "topics")) == (0, 0, 0)
    assert retrieval.search(db, alice, sid, "stack") == []


def test_deleting_a_document_removes_chunks_topics_index_entries_and_the_file(world, tmp_path):
    db, repo, alice, _, sid, _ = world
    r = ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    assert ingest.delete_document(db, alice, sid, r.document_id)
    assert (count(db, "documents"), count(db, "chunks"), count(db, "topics")) == (0, 0, 0)
    assert retrieval.search(db, alice, sid, "stack") == []
    db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')")      # raises if the index disagrees
    assert not [p for p in (tmp_path / "uploads").rglob("*") if p.is_file()]


def test_a_shared_original_survives_until_its_last_document_is_gone(world, tmp_path):
    db, repo, alice, _, sid, _ = world
    other = repo.create_subject(alice, "Second")
    a = ingest.ingest(db, alice, sid, "a.txt", SAMPLE_TXT.encode())
    ingest.ingest(db, alice, other, "a.txt", SAMPLE_TXT.encode())
    ingest.delete_document(db, alice, sid, a.document_id)
    assert len([p for p in (tmp_path / "uploads").rglob("*") if p.is_file()]) == 1
    ingest.delete_subject(db, alice, other)
    assert not [p for p in (tmp_path / "uploads").rglob("*") if p.is_file()]


def test_deleting_a_subject_removes_its_whole_material_and_index(world):
    db, repo, alice, bob, sid, bsid = world
    ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    ingest.ingest(db, bob, bsid, "ds.txt", SAMPLE_TXT.encode())
    assert ingest.delete_subject(db, alice, sid)
    assert count(db, "documents") == 1 and count(db, "chunks") == 3
    db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')")
    assert retrieval.search(db, bob, bsid, "stack"), "bob's copy is untouched"


def test_topics_are_shared_by_documents_with_the_same_heading(world):
    db, repo, alice, _, sid, _ = world
    ingest.ingest(db, alice, sid, "a.txt", b"# Stacks\n\nA stack pushes and pops at one end only.\n")
    ingest.ingest(db, alice, sid, "b.txt", b"# Stacks\n\nStacks are used for function calls and undo.\n")
    topics = repo.list_topics(alice, sid)
    assert len(topics) == 1 and topics[0]["chunks"] == 2


# ------------------------------------------------------------------------------------------- retrieval

def test_build_match_keeps_content_words_and_quotes_them():
    assert retrieval.build_match("What is the inorder traversal of a binary tree?") == \
        '"inorder" OR "traversal" OR "binary" OR "tree"'
    assert retrieval.build_match("") == "" and retrieval.build_match("the a of is") == ""
    assert retrieval.build_match("tree tree TREE") == '"tree"'
    assert retrieval.build_match(" ".join(f"word{i}" for i in range(50))).count("OR") == retrieval.MAX_TERMS - 1


@pytest.mark.parametrize("q", ['a" OR "b', "stack AND NOT queue", "NEAR(a b)", "stack*", "col:stack", "-stack", "(((", '"', "\\",
                               "x'; DROP TABLE chunks;--", "\x00", "stack" * 500])
def test_hostile_search_text_never_raises_and_never_acts_as_syntax(world, q):
    db, _, alice, _, sid, _ = world
    ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    retrieval.search(db, alice, sid, q)
    assert count(db, "chunks") == 3


def test_search_ranks_the_relevant_passage_first_and_stems_words(world):
    db, _, alice, _, sid, _ = world
    ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    assert retrieval.search(db, alice, sid, "how does dequeue work")[0]["heading_path"].endswith("Queues")
    assert retrieval.search(db, alice, sid, "traversals of trees")[0]["heading_path"].endswith("Trees")
    assert retrieval.search(db, alice, sid, "push and pop")[0]["heading_path"].endswith("Stacks")


def test_no_match_returns_nothing_rather_than_something_vaguely_related(world):
    db, _, alice, _, sid, _ = world
    ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    assert retrieval.search(db, alice, sid, "photosynthesis chlorophyll") == []
    assert retrieval.search(db, alice, sid, "") == []


def test_k_is_bounded(world):
    db, _, alice, _, sid, _ = world
    ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    assert len(retrieval.search(db, alice, sid, "collection structure", k=1)) == 1
    assert len(retrieval.search(db, alice, sid, "collection structure", k=10_000)) <= 20


# ---------------------------------------------------------------------------------------------- LEAKAGE

def test_user_b_cannot_search_read_list_or_delete_user_as_materials(world):
    db, repo, alice, bob, sid, bsid = world
    r = ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    hit = retrieval.search(db, alice, sid, "stack")[0]
    assert retrieval.search(db, bob, sid, "stack") == [], "bob searching alice's subject"
    assert retrieval.search(db, bob, bsid, "stack") == [], "bob's own subject has none of alice's text"
    assert repo.list_documents(bob, sid) == [] and repo.list_topics(bob, sid) == []
    assert repo.get_document(bob, sid, r.document_id) is None
    assert repo.document_chunks(bob, sid, r.document_id) == []
    assert repo.get_chunk(bob, sid, hit["id"]) is None
    assert repo.find_document_by_hash(bob, sid, "0" * 64) is None and repo.subject_chars(bob, sid) == 0
    assert ingest.delete_document(db, bob, sid, r.document_id) is False
    assert ingest.delete_subject(db, bob, sid) is False
    assert count(db, "documents") == 1 and count(db, "chunks") == 3, "all still there"


def test_user_b_cannot_upload_into_user_as_subject(world):
    db, _, alice, bob, sid, _ = world
    with pytest.raises(ingest.IngestError, match="does not exist"):
        ingest.ingest(db, bob, sid, "ds.txt", SAMPLE_TXT.encode())
    assert count(db, "documents") == 0


def test_identical_text_in_two_accounts_never_crosses_over(world):
    db, _, alice, bob, sid, bsid = world
    ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    ingest.ingest(db, bob, bsid, "ds.txt", SAMPLE_TXT.encode())
    a = {h["id"] for h in retrieval.search(db, alice, sid, "stack queue tree", k=20)}
    b = {h["id"] for h in retrieval.search(db, bob, bsid, "stack queue tree", k=20)}
    assert a and b and not (a & b)


def test_a_subject_of_the_same_user_is_also_a_hard_boundary(world):
    db, repo, alice, _, sid, _ = world
    other = repo.create_subject(alice, "Biology")
    ingest.ingest(db, alice, sid, "ds.txt", SAMPLE_TXT.encode())
    assert retrieval.search(db, alice, other, "stack queue tree") == []


def test_every_repo_method_that_takes_a_material_id_takes_user_and_subject(world):
    for name, fn in inspect.getmembers(Repo, inspect.isfunction):
        params = inspect.signature(fn).parameters
        if {"document_id", "chunk_id"} & set(params):
            assert {"user_id", "subject_id"} <= set(params), f"Repo.{name}"


# --------------------------------------------------------------------------------- a real file (if present)

REAL_PDF = Path(__file__).resolve().parent.parent / "docs" / "One Dinner Four Kitchens.pdf"


@pytest.mark.skipif(not REAL_PDF.exists(), reason="sample PDF not in this checkout")
def test_a_real_world_pdf_is_ingested_and_searchable(world):
    db, repo, alice, _, sid, _ = world
    r = ingest.ingest(db, alice, sid, REAL_PDF.name, REAL_PDF.read_bytes())
    doc = repo.get_document(alice, sid, r.document_id)
    assert doc["status"] == "parsed" and doc["pages"] >= 1 and doc["chunks"] >= 1, doc
    first = repo.document_chunks(alice, sid, r.document_id)[0]
    word = max(re.findall(r"[A-Za-z]{6,}", first["text"]), key=len)
    lengths = [len(c["text"]) for c in repo.document_chunks(alice, sid, r.document_id)]
    assert sum(lengths) / len(lengths) > 300 and max(lengths) > 400, f"passages should be paragraphs, not fragments: {lengths}"
    hits = retrieval.search(db, alice, sid, word)
    assert hits and hits[0]["page_start"] is not None and any(word.lower() in h["text"].lower() for h in hits)
