"""The ONLY place that reads or writes user-owned rows.

Every method takes `user_id` and puts it in the WHERE clause. There is no method that fetches a subject by id alone,
so a route that forgets an ownership check cannot exist: it has nothing to call. tests/test_studyhub_repo.py tries
to break this from a second user's account.
"""
from __future__ import annotations

import json
import sqlite3
import time

from slice import pg

from . import settings


class SubjectError(ValueError):
    """A problem with a subject the user can be told about."""


def _clean(text: str, limit: int) -> str:
    return " ".join((text or "").split())[:limit]


class Repo:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self._pg = getattr(db, "pg", False)

    # ------------------------------------------------------------------ users
    def get_user(self, user_id: int) -> dict | None:
        row = self.db.execute("SELECT id, username, cloud_consent, created_at, email, email_verified, role FROM users WHERE id=?",
                              (user_id,)).fetchone()
        return dict(row) if row else None

    # --------------------------------------------------------------- subjects
    def create_subject(self, user_id: int, name: str, description: str = "") -> int:
        name = _clean(name, 200)
        if not name:
            raise SubjectError("Give the subject a name.")
        if len(name) > 80:
            raise SubjectError("A subject name can be at most 80 characters.")
        description = _clean(description, 501)
        if len(description) > 500:
            raise SubjectError("A description can be at most 500 characters.")
        try:
            cur = self.db.execute("INSERT INTO subjects(user_id, name, description, created_at) VALUES (?,?,?,?)",
                                  (user_id, name, description, time.time()))
        except sqlite3.IntegrityError:
            raise SubjectError("You already have a subject with that name.") from None
        return int(cur.lastrowid)

    def list_subjects(self, user_id: int) -> list[dict]:
        rows = self.db.execute("SELECT id, name, description, created_at, level, exam_date FROM subjects WHERE user_id=? "
                               "ORDER BY name COLLATE NOCASE", (user_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_subject(self, user_id: int, subject_id: int) -> dict | None:
        """None if it does not exist OR belongs to someone else - the caller cannot tell which."""
        row = self.db.execute("SELECT id, name, description, created_at, level, exam_date FROM subjects WHERE id=? AND user_id=?",
                              (subject_id, user_id)).fetchone()
        return dict(row) if row else None

    def update_subject(self, user_id: int, subject_id: int, name: str, description: str = "") -> bool:
        name, description = _clean(name, 200), _clean(description, 501)
        if not name:
            raise SubjectError("Give the subject a name.")
        if len(name) > 80:
            raise SubjectError("A subject name can be at most 80 characters.")
        if len(description) > 500:
            raise SubjectError("A description can be at most 500 characters.")
        try:
            cur = self.db.execute("UPDATE subjects SET name=?, description=? WHERE id=? AND user_id=?",
                                  (name, description, subject_id, user_id))
        except sqlite3.IntegrityError:
            raise SubjectError("You already have a subject with that name.") from None
        return cur.rowcount == 1

    def delete_subject(self, user_id: int, subject_id: int) -> bool:
        return self.db.execute("DELETE FROM subjects WHERE id=? AND user_id=?", (subject_id, user_id)).rowcount == 1

    # -------------------------------------------------------------- materials
    def subject_chars(self, user_id: int, subject_id: int) -> int:
        """Characters of material already stored in a subject (0 if it is not the user's)."""
        return int(self.db.execute(
            "SELECT COALESCE(SUM(LENGTH(c.text)), 0) FROM chunks c JOIN subjects s ON s.id=c.subject_id "
            "WHERE c.subject_id=? AND s.user_id=?", (subject_id, user_id)).fetchone()[0])

    def find_document_by_hash(self, user_id: int, subject_id: int, sha256: str) -> dict | None:
        row = self.db.execute(
            "SELECT d.id, d.title, d.status FROM documents d JOIN subjects s ON s.id=d.subject_id "
            "WHERE d.subject_id=? AND s.user_id=? AND d.sha256=?", (subject_id, user_id, sha256)).fetchone()
        return dict(row) if row else None

    def store_document(self, user_id: int, subject_id: int, doc: dict, chunks: list) -> int | None:
        """Insert a document with its topics and chunks in ONE transaction. None if the subject is not the user's."""
        if self.get_subject(user_id, subject_id) is None:
            return None
        self.db.execute("BEGIN")
        try:
            cur = self.db.execute(
                "INSERT INTO documents(subject_id, kind, title, source, sha256, bytes, pages, status, warnings, created_at, role, ocr_pages) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (subject_id, doc["kind"], doc["title"], doc["source"], doc["sha256"], doc["bytes"], doc["pages"],
                 doc["status"], json.dumps(doc["warnings"]), time.time(), doc.get("role", "notes"), int(doc.get("ocr_pages") or 0)))
            doc_id = int(cur.lastrowid)
            topic_ids: dict[str, int] = {}
            past_paper = doc.get("role") == "pyq"                       # past papers are evidence of what is asked, not topics to study
            for ordinal, ch in enumerate(chunks):
                if not past_paper and ch.topic_path not in topic_ids:
                    row = self.db.execute("SELECT id FROM topics WHERE subject_id=? AND path=?",
                                          (subject_id, ch.topic_path)).fetchone()
                    if row:
                        topic_ids[ch.topic_path] = int(row[0])
                    else:
                        nxt = self.db.execute("SELECT COALESCE(MAX(ordinal), -1) + 1 FROM topics WHERE subject_id=?",
                                              (subject_id,)).fetchone()[0]
                        name = ch.topic_path.rsplit(" › ", 1)[-1]
                        topic_ids[ch.topic_path] = int(self.db.execute(
                            "INSERT INTO topics(subject_id, name, path, ordinal, origin) VALUES (?,?,?,?,?)",
                            (subject_id, name, ch.topic_path, nxt, ch.topic_origin)).lastrowid)
                self.db.execute(
                    "INSERT INTO chunks(subject_id, document_id, topic_id, ordinal, page_start, page_end, heading_path, "
                    "text, sha256, quarantined, flag_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (subject_id, doc_id, None if past_paper else topic_ids[ch.topic_path], ordinal, ch.page_start, ch.page_end,
                     ch.heading_path, ch.text, ch.sha256, 1 if ch.flags else 0, "; ".join(ch.flags)[:300]))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return doc_id

    def list_documents(self, user_id: int, subject_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT d.id, d.kind, d.title, d.source, d.pages, d.status, d.warnings, d.bytes, d.created_at, d.role, d.ocr_pages, "
            "(SELECT COUNT(*) FROM chunks c WHERE c.document_id=d.id) AS chunks "
            "FROM documents d JOIN subjects s ON s.id=d.subject_id "
            "WHERE d.subject_id=? AND s.user_id=? ORDER BY d.created_at DESC, d.id DESC", (subject_id, user_id)).fetchall()
        return [self._doc(r) for r in rows]

    def get_document(self, user_id: int, subject_id: int, document_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT d.id, d.kind, d.title, d.source, d.pages, d.status, d.warnings, d.bytes, d.sha256, d.created_at, d.role, d.ocr_pages, "
            "(SELECT COUNT(*) FROM chunks c WHERE c.document_id=d.id) AS chunks "
            "FROM documents d JOIN subjects s ON s.id=d.subject_id "
            "WHERE d.id=? AND d.subject_id=? AND s.user_id=?", (document_id, subject_id, user_id)).fetchone()
        return self._doc(row) if row else None

    @staticmethod
    def _doc(row) -> dict:
        d = dict(row)
        d["warnings"] = json.loads(d["warnings"] or "[]")
        return d

    def delete_document(self, user_id: int, subject_id: int, document_id: int) -> dict | None:
        """Delete one document (its chunks go with it). Returns {sha256, still_used} so the caller can drop the file."""
        doc = self.get_document(user_id, subject_id, document_id)
        if doc is None:
            return None
        self.db.execute("DELETE FROM documents WHERE id=? AND subject_id=?", (document_id, subject_id))
        used = self.db.execute(
            "SELECT COUNT(*) FROM documents d JOIN subjects s ON s.id=d.subject_id WHERE s.user_id=? AND d.sha256=?",
            (user_id, doc["sha256"])).fetchone()[0]
        self.db.execute("DELETE FROM topics WHERE subject_id=? AND id NOT IN "
                        "(SELECT topic_id FROM chunks WHERE subject_id=? AND topic_id IS NOT NULL)", (subject_id, subject_id))
        return {"sha256": doc["sha256"], "still_used": used > 0}

    def document_hashes(self, user_id: int, subject_id: int) -> list[str]:
        return [r[0] for r in self.db.execute(
            "SELECT DISTINCT d.sha256 FROM documents d JOIN subjects s ON s.id=d.subject_id "
            "WHERE d.subject_id=? AND s.user_id=?", (subject_id, user_id))]

    def hash_in_use(self, user_id: int, sha256: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM documents d JOIN subjects s ON s.id=d.subject_id WHERE s.user_id=? AND d.sha256=? LIMIT 1",
            (user_id, sha256)).fetchone() is not None

    def list_topics(self, user_id: int, subject_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT t.id, t.name, t.path, t.ordinal, t.origin, COUNT(c.id) AS chunks "
            "FROM topics t JOIN subjects s ON s.id=t.subject_id LEFT JOIN chunks c ON c.topic_id=t.id "
            "WHERE t.subject_id=? AND s.user_id=? GROUP BY t.id ORDER BY t.ordinal", (subject_id, user_id)).fetchall()
        return [dict(r) for r in rows]

    def document_chunks(self, user_id: int, subject_id: int, document_id: int, limit: int = 500) -> list[dict]:
        rows = self.db.execute(
            "SELECT c.id, c.ordinal, c.page_start, c.page_end, c.heading_path, c.text, c.quarantined, c.flag_reason "
            "FROM chunks c JOIN subjects s ON s.id=c.subject_id "
            "WHERE c.document_id=? AND c.subject_id=? AND s.user_id=? ORDER BY c.ordinal LIMIT ?",
            (document_id, subject_id, user_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_chunk(self, user_id: int, subject_id: int, chunk_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT c.id, c.document_id, c.topic_id, c.page_start, c.page_end, c.heading_path, c.text, d.title AS doc_title "
            "FROM chunks c JOIN subjects s ON s.id=c.subject_id JOIN documents d ON d.id=c.document_id "
            "WHERE c.id=? AND c.subject_id=? AND s.user_id=?", (chunk_id, subject_id, user_id)).fetchone()
        return dict(row) if row else None

    def matching_chunk_ids(self, user_id: int, subject_id: int, match: str, chunk_ids: list[int]) -> list[int]:
        """Which of `chunk_ids` (in this user's subject) contain the term(s) in the safe FTS expression `match`."""
        if not match or not chunk_ids:
            return []
        marks = ",".join("?" * len(chunk_ids))
        if self._pg:
            rows = self.db.execute(
                "SELECT c.id FROM chunks c JOIN subjects s ON s.id = c.subject_id "
                f"WHERE c.tsv @@ to_tsquery('english', ?) AND c.subject_id = ? AND s.user_id = ? AND c.id IN ({marks})",
                (pg.tsquery(match), subject_id, user_id, *[int(i) for i in chunk_ids])).fetchall()
            return [int(r[0]) for r in rows]
        rows = self.db.execute(
            "SELECT c.id FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid JOIN subjects s ON s.id = c.subject_id "
            f"WHERE chunks_fts MATCH ? AND c.subject_id = ? AND s.user_id = ? AND c.id IN ({marks})",
            (match, subject_id, user_id, *[int(i) for i in chunk_ids])).fetchall()
        return [int(r[0]) for r in rows]

    def term_frequency(self, user_id: int, subject_id: int, match: str, answers: bool = False) -> int:
        """In how many passages of this user's subject the safe FTS expression `match` occurs."""
        if not match:
            return 0
        if self._pg:
            return int(self.db.execute(
                "SELECT COUNT(*) FROM chunks c JOIN subjects s ON s.id = c.subject_id "
                "WHERE c.tsv @@ to_tsquery('english', ?) AND c.subject_id = ? AND s.user_id = ? AND c.quarantined <= ?",
                (pg.tsquery(match), subject_id, user_id, 0 if answers else 1)).fetchone()[0])
        return int(self.db.execute(
            "SELECT COUNT(*) FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid JOIN subjects s ON s.id = c.subject_id "
            "WHERE chunks_fts MATCH ? AND c.subject_id = ? AND s.user_id = ? AND c.quarantined <= ?",
            (match, subject_id, user_id, 0 if answers else 1)).fetchone()[0])

    def search_chunks(self, user_id: int, subject_id: int, match: str, k: int = 5, answers: bool = False) -> list[dict]:
        """BM25 keyword search inside ONE subject of ONE user. `match` must already be a safe FTS5 expression.
        With answers=True, quarantined passages (instruction-like text) are left out."""
        if not match:
            return []
        if self._pg:                                  # PostgreSQL full-text: ts_rank_cd, negated so lower is better like BM25
            rows = self.db.execute(
                "SELECT c.id, c.document_id, d.title AS doc_title, c.topic_id, c.heading_path, c.page_start, c.page_end, "
                "c.text, c.quarantined, -ts_rank_cd(c.tsv, q) AS score "
                "FROM chunks c CROSS JOIN to_tsquery('english', ?) q "
                "JOIN documents d ON d.id = c.document_id JOIN subjects s ON s.id = c.subject_id "
                "WHERE c.tsv @@ q AND c.subject_id = ? AND s.user_id = ? AND c.quarantined <= ? ORDER BY score, c.id LIMIT ?",
                (pg.tsquery(match), subject_id, user_id, 0 if answers else 1, k)).fetchall()
            return [dict(r) for r in rows]
        rows = self.db.execute(
            "SELECT c.id, c.document_id, d.title AS doc_title, c.topic_id, c.heading_path, c.page_start, c.page_end, "
            "c.text, c.quarantined, bm25(chunks_fts) AS score "
            "FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid "
            "JOIN documents d ON d.id = c.document_id JOIN subjects s ON s.id = c.subject_id "
            "WHERE chunks_fts MATCH ? AND c.subject_id = ? AND s.user_id = ? AND c.quarantined <= ? ORDER BY score LIMIT ?",
            (match, subject_id, user_id, 0 if answers else 1, k)).fetchall()
        return [dict(r) for r in rows]

    # ---------------------------------------------------------------- doubts
    def create_doubt(self, user_id: int, subject_id: int, question: str) -> int | None:
        """Record a new question as 'pending'. None if the subject is not the user's."""
        if self.get_subject(user_id, subject_id) is None:
            return None
        return int(self.db.execute(
            "INSERT INTO doubts(user_id, subject_id, question, status, created_at) VALUES (?,?,?,'pending',?)",
            (user_id, subject_id, question, time.time())).lastrowid)

    def pending_doubts(self, user_id: int) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM doubts WHERE user_id=? AND status='pending'",
                                   (user_id,)).fetchone()[0])

    def set_doubt_run(self, user_id: int, doubt_id: int, run_id: str) -> None:
        self.db.execute("UPDATE doubts SET run_id=? WHERE id=? AND user_id=?", (run_id, doubt_id, user_id))

    def finish_doubt(self, user_id: int, doubt_id: int, *, status: str, tier: str | None, model: str | None,
                     reason: str, dropped: int, claims: list[dict], sources: list[dict], kind: str = "supported",
                     explanation: str = "") -> bool:
        """Close a pending question and store what will be shown, atomically. False if it was not pending/yours."""
        self.db.execute("BEGIN")
        try:
            cur = self.db.execute(
                "UPDATE doubts SET status=?, tier=?, model=?, reason=?, dropped=?, finished_at=?, kind=?, explanation=? "
                "WHERE id=? AND user_id=? AND status='pending'",
                (status, tier, model, reason, dropped, time.time(), kind, explanation, doubt_id, user_id))
            if cur.rowcount != 1:
                self.db.execute("ROLLBACK")
                return False
            for i, claim in enumerate(claims):
                self.db.execute("INSERT INTO doubt_claims(doubt_id, ordinal, text) VALUES (?,?,?)",
                                (doubt_id, i, claim["text"]))
                for n, c in enumerate(claim["citations"]):
                    self.db.execute(
                        "INSERT INTO doubt_citations(doubt_id, claim, n, chunk_id, quote, doc_title, page_start, page_end, "
                        "heading_path) VALUES (?,?,?,?,?,?,?,?,?)",
                        (doubt_id, i, n, c["chunk_id"], c["quote"], c["doc_title"], c["page_start"], c["page_end"],
                         c["heading_path"]))
            for rank, s in enumerate(sources):
                self.db.execute(
                    "INSERT INTO doubt_sources(doubt_id, rank, chunk_id, doc_title, page_start, page_end, heading_path, "
                    "text, matched) VALUES (?,?,?,?,?,?,?,?,?)",
                    (doubt_id, rank, s["id"], s["doc_title"], s["page_start"], s["page_end"], s["heading_path"],
                     s["text"], json.dumps(s["matched"])))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return True

    def get_doubt(self, user_id: int, subject_id: int, doubt_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT d.* FROM doubts d JOIN subjects s ON s.id=d.subject_id "
            "WHERE d.id=? AND d.subject_id=? AND d.user_id=? AND s.user_id=?",
            (doubt_id, subject_id, user_id, user_id)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["claims"] = []
        for c in self.db.execute("SELECT ordinal, text FROM doubt_claims WHERE doubt_id=? ORDER BY ordinal", (doubt_id,)):
            cites = [dict(x) for x in self.db.execute(
                "SELECT n, chunk_id, quote, doc_title, page_start, page_end, heading_path, "
                "(SELECT document_id FROM chunks WHERE chunks.id=doubt_citations.chunk_id) AS document_id FROM doubt_citations "
                "WHERE doubt_id=? AND claim=? ORDER BY n", (doubt_id, c["ordinal"]))]
            d["claims"].append({"text": c["text"], "citations": cites})
        d["sources"] = []
        for s in self.db.execute("SELECT chunk_id, doc_title, page_start, page_end, heading_path, text, matched, "
                                 "(SELECT document_id FROM chunks WHERE chunks.id=doubt_sources.chunk_id) AS document_id "
                                 "FROM doubt_sources WHERE doubt_id=? ORDER BY rank", (doubt_id,)):
            item = dict(s)
            item["matched"] = json.loads(item["matched"] or "[]")
            d["sources"].append(item)
        return d

    def list_doubts(self, user_id: int, subject_id: int, limit: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT d.id, d.question, d.status, d.tier, d.created_at, d.feedback, d.saved FROM doubts d "
            "JOIN subjects s ON s.id=d.subject_id WHERE d.subject_id=? AND d.user_id=? AND s.user_id=? "
            "ORDER BY d.created_at DESC, d.id DESC LIMIT ?", (subject_id, user_id, user_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def set_doubt_feedback(self, user_id: int, subject_id: int, doubt_id: int, value: str | None) -> bool:
        if value not in (None, "helpful", "wrong"):
            return False
        return self.db.execute("UPDATE doubts SET feedback=? WHERE id=? AND subject_id=? AND user_id=?",
                               (value, doubt_id, subject_id, user_id)).rowcount == 1

    def delete_doubt(self, user_id: int, subject_id: int, doubt_id: int) -> bool:
        return self.db.execute("DELETE FROM doubts WHERE id=? AND subject_id=? AND user_id=?",
                               (doubt_id, subject_id, user_id)).rowcount == 1

    def expire_pending_doubts(self, older_than_seconds: float) -> int:
        """Maintenance (not user-scoped): a question still pending long after it started was cut off by a restart."""
        return self.db.execute(
            "UPDATE doubts SET status='failed', reason='This question was interrupted (the app restarted). Ask it again.', "
            "finished_at=? WHERE status='pending' AND created_at < ?", (time.time(), time.time() - older_than_seconds)).rowcount

    # ------------------------------------------------------------- cloud use
    def set_cloud_consent(self, user_id: int, on: bool) -> None:
        self.db.execute("UPDATE users SET cloud_consent=? WHERE id=?", (1 if on else 0, user_id))

    def cloud_tokens_today(self, day: str, user_id: int | None = None) -> int:
        if user_id is None:
            return int(self.db.execute("SELECT COALESCE(SUM(tokens),0) FROM cloud_usage WHERE day=?", (day,)).fetchone()[0])
        return int(self.db.execute("SELECT COALESCE(SUM(tokens),0) FROM cloud_usage WHERE day=? AND user_id=?",
                                   (day, user_id)).fetchone()[0])

    def record_cloud_usage(self, user_id: int, day: str, model: str, tokens: int) -> None:
        self.db.execute("INSERT INTO cloud_usage(user_id, day, model, tokens, at) VALUES (?,?,?,?,?)",
                        (user_id, day, model, int(tokens), time.time()))

    def doubt_trace(self, user_id: int, subject_id: int, doubt_id: int) -> list[dict]:
        """The spine's append-only steps for one of this user's questions, oldest first."""
        rows = self.db.execute(
            "SELECT v.seq, v.kind, v.produced_by, v.payload_json, v.created_at FROM versions v "
            "JOIN doubts d ON d.run_id = v.run_id JOIN subjects s ON s.id = d.subject_id "
            "WHERE d.id=? AND d.subject_id=? AND d.user_id=? AND s.user_id=? ORDER BY v.seq",
            (doubt_id, subject_id, user_id, user_id)).fetchall()
        return [{"seq": r["seq"], "kind": r["kind"], "by": r["produced_by"], "at": r["created_at"],
                 "payload": json.loads(r["payload_json"])} for r in rows]

    # ------------------------------------------------------------------- multiple-choice questions
    def topic_chunks(self, user_id: int, subject_id: int, topic_id: int, answers: bool = True) -> list[dict]:
        """Passages of one topic of this user's subject, in reading order. With answers=True, quarantined ones are left out."""
        rows = self.db.execute(
            "SELECT c.id, c.ordinal, c.page_start, c.page_end, c.heading_path, c.text, d.title AS doc_title "
            "FROM chunks c JOIN subjects s ON s.id=c.subject_id JOIN documents d ON d.id=c.document_id "
            "WHERE c.topic_id=? AND c.subject_id=? AND s.user_id=? AND c.quarantined <= ? ORDER BY d.id, c.ordinal",
            (topic_id, subject_id, user_id, 0 if answers else 1)).fetchall()
        return [dict(r) for r in rows]

    def create_mcq_job(self, user_id: int, subject_id: int, topic_id: int | None, scope: str, requested: int, purpose: str = "practice") -> int | None:
        if self.get_subject(user_id, subject_id) is None:
            return None
        return int(self.db.execute(
            "INSERT INTO mcq_jobs(user_id, subject_id, topic_id, scope, requested, status, created_at, purpose) VALUES (?,?,?,?,?,'pending',?,?)",
            (user_id, subject_id, topic_id, scope, requested, time.time(), purpose)).lastrowid)

    def pending_mcq_jobs(self, user_id: int) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM mcq_jobs WHERE user_id=? AND status='pending'", (user_id,)).fetchone()[0])

    def get_mcq_job(self, user_id: int, subject_id: int, job_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT j.* FROM mcq_jobs j JOIN subjects s ON s.id=j.subject_id "
            "WHERE j.id=? AND j.subject_id=? AND j.user_id=? AND s.user_id=?", (job_id, subject_id, user_id, user_id)).fetchone()
        return dict(row) if row else None

    def set_mcq_job_run(self, user_id: int, job_id: int, run_id: str) -> None:
        self.db.execute("UPDATE mcq_jobs SET run_id=? WHERE id=? AND user_id=?", (run_id, job_id, user_id))

    def finish_mcq_job(self, user_id: int, job_id: int, *, status: str, reason: str, rejected: int, tier: str | None,
                       model: str | None, items: list[dict]) -> int:
        """Store the approved questions and close the job, atomically. Returns how many were stored (exact duplicates are skipped)."""
        job = self.db.execute("SELECT subject_id FROM mcq_jobs WHERE id=? AND user_id=? AND status='pending'", (job_id, user_id)).fetchone()
        if job is None:
            return 0
        subject_id, stored = int(job["subject_id"]), 0
        self.db.execute("BEGIN")
        try:
            for it in items:
                try:
                    self.db.execute(
                        "INSERT INTO mcq_items(subject_id, topic_id, job_id, topic_path, question, options, answer_index, explanation, "
                        "quote, chunk_id, doc_title, page_start, page_end, heading_path, solver, model, key, created_at, difficulty, review, key_check) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (subject_id, it["topic_id"], job_id, it["topic_path"], it["question"], json.dumps(it["options"]),
                         it["answer_index"], it["explanation"], it["quote"], it["chunk_id"], it["doc_title"], it["page_start"],
                         it["page_end"], it["heading_path"], it["solver"], model, it["key"], time.time(), it.get("difficulty", "medium"),
                         "pending" if settings.faculty_review() else "approved", it.get("key_check", "")))
                    stored += 1
                except sqlite3.IntegrityError:
                    pass
            self.db.execute(
                "UPDATE mcq_jobs SET status=?, reason=?, produced=?, rejected=?, tier=?, model=?, finished_at=? WHERE id=?",
                (status, reason, stored, rejected, tier, model, time.time(), job_id))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return stored

    def list_mcq(self, user_id: int, subject_id: int, topic_id: int | None = None, job_id: int | None = None) -> list[dict]:
        """The officer's question bank: only questions a faculty member approved (or every one, with faculty review off)."""
        sql = ("SELECT m.* FROM mcq_items m JOIN subjects s ON s.id=m.subject_id WHERE m.subject_id=? AND s.user_id=? AND m.review='approved'")
        args: list = [subject_id, user_id]
        if topic_id is not None:
            sql += " AND m.topic_id=?"
            args.append(topic_id)
        if job_id is not None:
            sql += " AND m.job_id=?"
            args.append(job_id)
        out = []
        for r in self.db.execute(sql + " ORDER BY m.id", args):
            d = dict(r)
            d["options"] = json.loads(d["options"])
            out.append(d)
        return out

    def mcq_questions(self, user_id: int, subject_id: int) -> list[str]:
        """Question texts already in this user's bank for the subject (to avoid generating the same one again)."""
        return [r[0] for r in self.db.execute(
            "SELECT m.question FROM mcq_items m JOIN subjects s ON s.id=m.subject_id WHERE m.subject_id=? AND s.user_id=?",
            (subject_id, user_id))]

    def delete_mcq(self, user_id: int, subject_id: int, item_id: int) -> bool:
        return self.db.execute(
            "DELETE FROM mcq_items WHERE id=? AND subject_id=? AND subject_id IN (SELECT id FROM subjects WHERE id=? AND user_id=?)",
            (item_id, subject_id, subject_id, user_id)).rowcount == 1

    def expire_pending_mcq_jobs(self, older_than_seconds: float) -> int:
        """Maintenance (not user-scoped): a job still pending long after it started was cut off by a restart."""
        return self.db.execute(
            "UPDATE mcq_jobs SET status='failed', reason='This job was interrupted (the app restarted). Generate again.', "
            "finished_at=? WHERE status='pending' AND created_at < ?", (time.time(), time.time() - older_than_seconds)).rowcount

    def mcq_trace(self, user_id: int, subject_id: int, job_id: int) -> list[dict]:
        """The spine's append-only steps for one of this user's generation jobs, oldest first."""
        rows = self.db.execute(
            "SELECT v.seq, v.kind, v.produced_by, v.payload_json, v.created_at FROM versions v "
            "JOIN mcq_jobs j ON j.run_id = v.run_id JOIN subjects s ON s.id = j.subject_id "
            "WHERE j.id=? AND j.subject_id=? AND j.user_id=? AND s.user_id=? ORDER BY v.seq",
            (job_id, subject_id, user_id, user_id)).fetchall()
        return [{"seq": r["seq"], "kind": r["kind"], "by": r["produced_by"], "at": r["created_at"],
                 "payload": json.loads(r["payload_json"])} for r in rows]

    # ---------------------------------------------------------------- notes

    def list_notes(self, user_id: int, subject_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT n.id, n.title, n.body, n.source, n.doubt_id, n.topic_id, n.created_at, n.updated_at FROM notes n JOIN subjects s ON s.id=n.subject_id "
            "WHERE n.subject_id=? AND n.user_id=? AND s.user_id=? ORDER BY n.updated_at DESC, n.id DESC", (subject_id, user_id, user_id)).fetchall()
        return [dict(r) for r in rows]

    def get_note(self, user_id: int, subject_id: int, note_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT n.id, n.title, n.body, n.source, n.doubt_id, n.topic_id, n.created_at, n.updated_at FROM notes n JOIN subjects s ON s.id=n.subject_id "
            "WHERE n.id=? AND n.subject_id=? AND n.user_id=? AND s.user_id=?", (note_id, subject_id, user_id, user_id)).fetchone()
        return dict(row) if row else None

    def add_note(self, user_id: int, subject_id: int, title: str, body: str, source: str = "own", doubt_id: int | None = None,
                 topic_id: int | None = None) -> int | None:
        if self.get_subject(user_id, subject_id) is None:
            return None
        now = time.time()
        return int(self.db.execute(
            "INSERT INTO notes(user_id, subject_id, title, body, source, doubt_id, topic_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, subject_id, title, body, source, doubt_id, topic_id, now, now)).lastrowid)

    def update_note(self, user_id: int, subject_id: int, note_id: int, title: str, body: str) -> bool:
        return self.db.execute(
            "UPDATE notes SET title=?, body=?, updated_at=? WHERE id=? AND subject_id=? AND user_id=? "
            "AND EXISTS(SELECT 1 FROM subjects s WHERE s.id=? AND s.user_id=?)",
            (title, body, time.time(), note_id, subject_id, user_id, subject_id, user_id)).rowcount == 1

    def delete_note(self, user_id: int, subject_id: int, note_id: int) -> bool:
        return self.db.execute(
            "DELETE FROM notes WHERE id=? AND subject_id=? AND user_id=? AND EXISTS(SELECT 1 FROM subjects s WHERE s.id=? AND s.user_id=?)",
            (note_id, subject_id, user_id, subject_id, user_id)).rowcount == 1

    # ---------------------------------------------------------------- quiz attempts (Phase C)

    def list_attempts(self, user_id: int, subject_id: int, limit: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT qa.* FROM quiz_attempts qa JOIN subjects s ON s.id=qa.subject_id "
            "WHERE qa.user_id=? AND qa.subject_id=? AND s.user_id=? "
            "ORDER BY qa.started_at DESC LIMIT ?",
            (user_id, subject_id, user_id, limit)).fetchall()
        return [self._attempt(r) for r in rows]

    def get_attempt(self, user_id: int, subject_id: int, attempt_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT qa.* FROM quiz_attempts qa JOIN subjects s ON s.id=qa.subject_id "
            "WHERE qa.id=? AND qa.user_id=? AND qa.subject_id=? AND s.user_id=?",
            (attempt_id, user_id, subject_id, user_id)).fetchone()
        return self._attempt(row) if row else None

    def get_active_attempt(self, user_id: int, subject_id: int) -> dict | None:
        """Return the most recent active attempt for this subject, or None."""
        row = self.db.execute(
            "SELECT qa.* FROM quiz_attempts qa JOIN subjects s ON s.id=qa.subject_id "
            "WHERE qa.user_id=? AND qa.subject_id=? AND qa.is_active=1 AND s.user_id=? "
            "ORDER BY qa.started_at DESC LIMIT 1",
            (user_id, subject_id, user_id)).fetchone()
        return self._attempt(row) if row else None

    @staticmethod
    def _attempt(row) -> dict:
        if row is None:
            return {}
        d = dict(row)
        for col in ("topic_ids_json", "topic_stack_json", "topics_verified_json", "verdict_log_json"):
            if col in d and d[col]:
                d[col.replace("_json", "")] = json.loads(d[col])
        return d

    def expire_stale_attempts(self, older_than_seconds: float) -> int:
        """Maintenance (not user-scoped): mark abandoned active attempts as finished."""
        return self.db.execute(
            "UPDATE quiz_attempts SET is_active=0, finished_at=? "
            "WHERE is_active=1 AND started_at<?",
            (time.time(), time.time() - older_than_seconds)).rowcount

    def list_attempt_answers(self, user_id: int, subject_id: int, attempt_id: int) -> list[dict]:
        """Per-question results for one of this user's attempts."""
        rows = self.db.execute(
            "SELECT aa.*, mi.question, mi.options, mi.answer_index, mi.explanation, "
            "mi.topic_path, t.name AS topic_name "
            "FROM attempt_answers aa "
            "JOIN quiz_attempts qa ON qa.id=aa.attempt_id "
            "JOIN subjects s ON s.id=qa.subject_id "
            "JOIN mcq_items mi ON mi.id=aa.item_id "
            "LEFT JOIN topics t ON t.id=mi.topic_id "
            "WHERE aa.attempt_id=? AND qa.user_id=? AND qa.subject_id=? AND s.user_id=? "
            "ORDER BY aa.id",
            (attempt_id, user_id, subject_id, user_id)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["options"] = json.loads(d["options"])
            out.append(d)
        return out

    # ----------------------------------------------------------- proctoring summary

    def proctoring_summary(self, user_id: int, subject_id: int, attempt_id: int) -> dict:
        """Trust score and event breakdown for one of this user's attempts."""
        row = self.db.execute(
            "SELECT qa.behavior_score, qa.total_tab_switches, "
            "qa.total_fullscreen_exits, qa.total_copy_attempts "
            "FROM quiz_attempts qa JOIN subjects s ON s.id=qa.subject_id "
            "WHERE qa.id=? AND qa.user_id=? AND qa.subject_id=? AND s.user_id=?",
            (attempt_id, user_id, subject_id, user_id)).fetchone()
        if row is None:
            return {}
        events = self.db.execute(
            "SELECT event_type, COUNT(*) AS n FROM quiz_proctoring_events "
            "WHERE attempt_id=? GROUP BY event_type", (attempt_id,)).fetchall()
        return {
            "trust_score":          max(0, min(100, round(row["behavior_score"]))),
            "total_tab_switches":   row["total_tab_switches"],
            "total_fullscreen_exits": row["total_fullscreen_exits"],
            "total_copy_attempts":  row["total_copy_attempts"],
            "event_counts":         {e["event_type"]: e["n"] for e in events},
        }

    # ----------------------------------------------------------- topic progress

    def topic_progress(self, user_id: int, subject_id: int) -> list[dict]:
        """All topic_progress rows for this user+subject, with topic name + path."""
        rows = self.db.execute(
            "SELECT tp.topic_id, t.name, t.path, tp.answered, tp.correct, "
            "tp.mastery, tp.state, tp.updated_at "
            "FROM topic_progress tp "
            "JOIN topics t ON t.id=tp.topic_id "
            "JOIN subjects s ON s.id=t.subject_id "
            "WHERE tp.user_id=? AND tp.subject_id=? AND s.user_id=? ORDER BY t.ordinal",
            (user_id, subject_id, user_id)).fetchall()
        return [dict(r) for r in rows]

    def weak_topics(self, user_id: int, subject_id: int, limit: int = 5) -> list[dict]:
        """Topics with lowest mastery (where answered >= 2), owned by this user."""
        rows = self.db.execute(
            "SELECT tp.topic_id, t.name, t.path, tp.answered, tp.correct, tp.mastery, tp.state "
            "FROM topic_progress tp "
            "JOIN topics t ON t.id=tp.topic_id "
            "JOIN subjects s ON s.id=t.subject_id "
            "WHERE tp.user_id=? AND tp.subject_id=? AND s.user_id=? AND tp.answered>=2 "
            "ORDER BY tp.mastery ASC LIMIT ?",
            (user_id, subject_id, user_id, limit)).fetchall()
        return [dict(r) for r in rows]

    # ----------------------------------------------------------- prerequisites

    def list_prereqs(self, user_id: int, subject_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT tp.topic_id, t1.name AS topic_name, tp.prereq_id, "
            "t2.name AS prereq_name, tp.confirmed, tp.origin "
            "FROM topic_prereqs tp "
            "JOIN topics t1 ON t1.id=tp.topic_id "
            "JOIN topics t2 ON t2.id=tp.prereq_id "
            "JOIN subjects s ON s.id=t1.subject_id "
            "WHERE t1.subject_id=? AND s.user_id=? ORDER BY t1.ordinal",
            (subject_id, user_id)).fetchall()
        return [dict(r) for r in rows]

    def set_prereq(self, user_id: int, subject_id: int, topic_id: int, prereq_id: int) -> bool:
        """Create/confirm a prerequisite edge. Both topics must be in this user's subject."""
        count = self.db.execute(
            "SELECT COUNT(*) FROM topics t JOIN subjects s ON s.id=t.subject_id "
            "WHERE t.id IN (?,?) AND s.id=? AND s.user_id=?",
            (topic_id, prereq_id, subject_id, user_id)).fetchone()[0]
        if count != 2 or topic_id == prereq_id:
            return False
        # Guard against simple 2-cycle
        cycle = self.db.execute(
            "SELECT 1 FROM topic_prereqs WHERE topic_id=? AND prereq_id=? AND confirmed=1",
            (prereq_id, topic_id)).fetchone()
        if cycle:
            return False
        self.db.execute(
            "INSERT INTO topic_prereqs(topic_id, prereq_id, confirmed, origin) VALUES (?,?,1,'manual') "
            "ON CONFLICT(topic_id, prereq_id) DO UPDATE SET confirmed=1",
            (topic_id, prereq_id))
        return True

    def delete_prereq(self, user_id: int, subject_id: int, topic_id: int, prereq_id: int) -> bool:
        count = self.db.execute(
            "SELECT COUNT(*) FROM topics t JOIN subjects s ON s.id=t.subject_id "
            "WHERE t.id=? AND s.id=? AND s.user_id=?",
            (topic_id, subject_id, user_id)).fetchone()[0]
        if count != 1:
            return False
        return self.db.execute(
            "DELETE FROM topic_prereqs WHERE topic_id=? AND prereq_id=?",
            (topic_id, prereq_id)).rowcount == 1

