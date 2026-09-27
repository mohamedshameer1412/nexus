"""Schema and migrations. One SQLite file holds the spine tables (runs, versions, ...) and these.

Each migration is applied once, atomically, and recorded in `schema_version`. Later phases append to MIGRATIONS;
they never edit an earlier one.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from slice.store import Store

from . import settings

MIGRATIONS: list[tuple[int, str]] = [
    (1, """
    BEGIN;

    CREATE TABLE users (
        id             INTEGER PRIMARY KEY,
        username       TEXT NOT NULL UNIQUE COLLATE NOCASE,
        pw_salt        BLOB NOT NULL,
        pw_hash        BLOB NOT NULL,
        scrypt_params  TEXT NOT NULL,
        cloud_consent  INTEGER NOT NULL DEFAULT 0 CHECK (cloud_consent IN (0, 1)),
        created_at     REAL NOT NULL
    );

    -- Only the SHA-256 of the session token is stored: a copy of this table cannot be replayed as cookies.
    CREATE TABLE sessions (
        token_hash  TEXT PRIMARY KEY,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        csrf        TEXT NOT NULL,
        created_at  REAL NOT NULL,
        expires_at  REAL NOT NULL
    );
    CREATE INDEX sessions_by_user ON sessions(user_id);

    CREATE TABLE login_attempts (
        username  TEXT NOT NULL,
        ip        TEXT NOT NULL,
        at        REAL NOT NULL,
        ok        INTEGER NOT NULL
    );
    CREATE INDEX login_attempts_by_name ON login_attempts(username, at);
    CREATE INDEX login_attempts_by_ip   ON login_attempts(ip, at);

    CREATE TABLE subjects (
        id           INTEGER PRIMARY KEY,
        user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name         TEXT NOT NULL COLLATE NOCASE,
        description  TEXT NOT NULL DEFAULT '',
        created_at   REAL NOT NULL,
        UNIQUE (user_id, name)
    );

    INSERT INTO schema_version(v) VALUES (1);
    COMMIT;
    """),
    (2, """
    BEGIN;

    -- One uploaded file. The original bytes live on disk (data/uploads/<user>/<sha256>), never in SQLite.
    CREATE TABLE documents (
        id           INTEGER PRIMARY KEY,
        subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        kind         TEXT NOT NULL CHECK (kind IN ('txt', 'pdf', 'docx', 'url')),
        title        TEXT NOT NULL,
        source       TEXT NOT NULL,                   -- the file name as uploaded, or the URL
        sha256       TEXT NOT NULL,
        bytes        INTEGER NOT NULL,
        pages        INTEGER,
        status       TEXT NOT NULL CHECK (status IN ('parsed', 'empty', 'failed')),
        warnings     TEXT NOT NULL DEFAULT '[]',      -- JSON list of things the student should know
        created_at   REAL NOT NULL,
        UNIQUE (subject_id, sha256)
    );

    CREATE TABLE topics (
        id          INTEGER PRIMARY KEY,
        subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        name        TEXT NOT NULL,
        path        TEXT NOT NULL,                    -- "Chapter 3 > Trees"
        ordinal     INTEGER NOT NULL,
        origin      TEXT NOT NULL CHECK (origin IN ('heading', 'document', 'manual')),
        UNIQUE (subject_id, path)
    );

    CREATE TABLE chunks (
        id            INTEGER PRIMARY KEY,
        subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        document_id   INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        topic_id      INTEGER REFERENCES topics(id) ON DELETE SET NULL,
        ordinal       INTEGER NOT NULL,
        page_start    INTEGER,
        page_end      INTEGER,
        heading_path  TEXT NOT NULL DEFAULT '',
        text          TEXT NOT NULL,
        sha256        TEXT NOT NULL
    );
    CREATE INDEX chunks_by_subject ON chunks(subject_id, document_id, ordinal);
    CREATE INDEX chunks_by_topic ON chunks(topic_id);

    -- Keyword index (BM25). Searches always join back to chunks and filter by subject_id.
    CREATE VIRTUAL TABLE chunks_fts USING fts5(text, content='chunks', content_rowid='id', tokenize='porter unicode61');
    CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
    END;
    CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    END;

    INSERT INTO schema_version(v) VALUES (2);
    COMMIT;
    """),
    (3, """
    BEGIN;

    -- One question a student asked about a subject, and how it ended.
    CREATE TABLE doubts (
        id           INTEGER PRIMARY KEY,
        user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        question     TEXT NOT NULL,
        status       TEXT NOT NULL CHECK (status IN ('pending', 'answered', 'abstained', 'extractive', 'failed')),
        tier         TEXT,                             -- local | cloud | none
        model        TEXT,
        reason       TEXT NOT NULL DEFAULT '',         -- plain-words reason for an abstention or failure
        run_id       TEXT,                             -- the spine run holding the append-only trace
        dropped      INTEGER NOT NULL DEFAULT 0,       -- statements removed because a citation failed verification
        feedback     TEXT CHECK (feedback IN ('helpful', 'wrong')),
        created_at   REAL NOT NULL,
        finished_at  REAL
    );
    CREATE INDEX doubts_by_subject ON doubts(user_id, subject_id, created_at);

    -- Only statements whose citations all passed code verification are stored here.
    CREATE TABLE doubt_claims (
        doubt_id  INTEGER NOT NULL REFERENCES doubts(id) ON DELETE CASCADE,
        ordinal   INTEGER NOT NULL,
        text      TEXT NOT NULL,
        PRIMARY KEY (doubt_id, ordinal)
    );
    -- Snapshots (no foreign key to chunks): the history stays readable after a document is deleted.
    CREATE TABLE doubt_citations (
        doubt_id       INTEGER NOT NULL,
        claim          INTEGER NOT NULL,
        n              INTEGER NOT NULL,
        chunk_id       INTEGER,
        quote          TEXT NOT NULL,
        doc_title      TEXT NOT NULL,
        page_start     INTEGER,
        page_end       INTEGER,
        heading_path   TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (doubt_id, claim, n),
        FOREIGN KEY (doubt_id, claim) REFERENCES doubt_claims(doubt_id, ordinal) ON DELETE CASCADE
    );
    -- The passages retrieved for the question (what the model was allowed to see, or the closest ones on abstention).
    CREATE TABLE doubt_sources (
        doubt_id      INTEGER NOT NULL REFERENCES doubts(id) ON DELETE CASCADE,
        rank          INTEGER NOT NULL,
        chunk_id      INTEGER,
        doc_title     TEXT NOT NULL,
        page_start    INTEGER,
        page_end      INTEGER,
        heading_path  TEXT NOT NULL DEFAULT '',
        text          TEXT NOT NULL,
        matched       TEXT NOT NULL DEFAULT '[]',
        PRIMARY KEY (doubt_id, rank)
    );

    -- Tokens sent to a cloud model, for the daily caps.
    CREATE TABLE cloud_usage (
        id       INTEGER PRIMARY KEY,
        user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        day      TEXT NOT NULL,
        model    TEXT NOT NULL,
        tokens   INTEGER NOT NULL,
        at       REAL NOT NULL
    );
    CREATE INDEX cloud_usage_by_day ON cloud_usage(day, user_id);

    INSERT INTO schema_version(v) VALUES (3);
    COMMIT;
    """),
    (4, """
    BEGIN;
    -- Passages that read as orders to an AI: stored and searchable, never given to a model to write answers.
    ALTER TABLE chunks ADD COLUMN quarantined INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE chunks ADD COLUMN flag_reason TEXT NOT NULL DEFAULT '';
    -- The explainable answer: 'supported' or 'conflict' (the materials disagree), and the model's step-by-step reasoning.
    ALTER TABLE doubts ADD COLUMN kind TEXT NOT NULL DEFAULT 'supported';
    ALTER TABLE doubts ADD COLUMN explanation TEXT NOT NULL DEFAULT '';
    INSERT INTO schema_version(v) VALUES (4);
    COMMIT;
    """),
    (5, """
    BEGIN;

    -- One request to generate multiple-choice questions, and how it ended.
    CREATE TABLE mcq_jobs (
        id           INTEGER PRIMARY KEY,
        user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        topic_id     INTEGER,                          -- NULL = the whole subject
        scope        TEXT NOT NULL DEFAULT '',         -- plain-words label of what was asked for
        requested    INTEGER NOT NULL,
        produced     INTEGER NOT NULL DEFAULT 0,
        rejected     INTEGER NOT NULL DEFAULT 0,       -- candidate questions that failed a check and were not kept
        status       TEXT NOT NULL CHECK (status IN ('pending', 'done', 'failed')),
        reason       TEXT NOT NULL DEFAULT '',
        tier         TEXT,
        model        TEXT,
        run_id       TEXT,                             -- the spine run holding the append-only trace
        created_at   REAL NOT NULL,
        finished_at  REAL
    );
    CREATE INDEX mcq_jobs_by_subject ON mcq_jobs(user_id, subject_id, created_at);

    -- The question bank. Only questions that passed every check are stored. Source details are snapshots, so a question
    -- stays readable (and shows where it came from) after the document is deleted.
    CREATE TABLE mcq_items (
        id            INTEGER PRIMARY KEY,
        subject_id    INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        topic_id      INTEGER REFERENCES topics(id) ON DELETE SET NULL,
        job_id        INTEGER REFERENCES mcq_jobs(id) ON DELETE SET NULL,
        topic_path    TEXT NOT NULL DEFAULT '',
        question      TEXT NOT NULL,
        options       TEXT NOT NULL,                   -- JSON list of exactly 4, already shuffled by the app
        answer_index  INTEGER NOT NULL CHECK (answer_index BETWEEN 0 AND 3),
        explanation   TEXT NOT NULL DEFAULT '',
        quote         TEXT NOT NULL,                   -- exact words from the material that support the answer
        chunk_id      INTEGER,
        doc_title     TEXT NOT NULL DEFAULT '',
        page_start    INTEGER,
        page_end      INTEGER,
        heading_path  TEXT NOT NULL DEFAULT '',
        solver        TEXT NOT NULL DEFAULT 'skipped' CHECK (solver IN ('agreed', 'skipped')),
        model         TEXT,
        key           TEXT NOT NULL,                   -- normalised question text, to refuse exact duplicates
        created_at    REAL NOT NULL
    );
    CREATE UNIQUE INDEX mcq_items_unique ON mcq_items(subject_id, key);
    CREATE INDEX mcq_items_by_topic ON mcq_items(subject_id, topic_id);

    INSERT INTO schema_version(v) VALUES (5);
    COMMIT;
    """),
    (6, """\
    BEGIN;

    -- One quiz attempt by a student on a subject's MCQ bank.
    -- topic_ids_json = JSON list of topic IDs included (empty = whole subject).
    -- topic_stack_json = JSON list of topic IDs currently being worked through (backward-pass stack).
    -- topics_verified_json = JSON list of topic IDs that received a PASS this attempt.
    CREATE TABLE quiz_attempts (
        id                    INTEGER PRIMARY KEY,
        user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id            INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        topic_ids_json        TEXT NOT NULL DEFAULT '[]',
        started_at            REAL NOT NULL,
        finished_at           REAL,
        is_active             INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
        score                 REAL NOT NULL DEFAULT 0,
        max_score             REAL NOT NULL DEFAULT 0,
        correct_answers       INTEGER NOT NULL DEFAULT 0,
        incorrect_answers     INTEGER NOT NULL DEFAULT 0,
        -- Behaviour (adapted from ai_learnmate QuizSession)
        total_tab_switches    INTEGER NOT NULL DEFAULT 0,
        total_fullscreen_exits INTEGER NOT NULL DEFAULT 0,
        total_copy_attempts   INTEGER NOT NULL DEFAULT 0,
        avg_response_time     REAL NOT NULL DEFAULT 0,
        behavior_score        REAL NOT NULL DEFAULT 100,
        -- Backward-pass state (from tracer/flow.py)
        current_difficulty    INTEGER NOT NULL DEFAULT 1 CHECK (current_difficulty BETWEEN 1 AND 3),
        topic_stack_json      TEXT NOT NULL DEFAULT '[]',
        depth                 INTEGER NOT NULL DEFAULT 0,
        topics_verified_json  TEXT NOT NULL DEFAULT '[]',
        had_timeout           INTEGER NOT NULL DEFAULT 0 CHECK (had_timeout IN (0, 1)),
        attempt_number        INTEGER NOT NULL DEFAULT 1,
        -- Backward-pass callback state: waiting | step_back | retry | none
        callback_state        TEXT NOT NULL DEFAULT 'none' CHECK (callback_state IN ('none', 'waiting', 'step_back', 'retry', 'timeout')),
        -- Append-only JSON list of verdict dicts (topic_id, status, objections, prerequisite_id)
        -- Kept on the row for simplicity; never mutated, only appended via JSON_EACH / Python.
        verdict_log_json      TEXT NOT NULL DEFAULT '[]'
    );
    CREATE INDEX quiz_attempts_by_subject ON quiz_attempts(user_id, subject_id, started_at);
    CREATE INDEX quiz_attempts_active ON quiz_attempts(user_id, is_active);

    -- One answered (or skipped) MCQ within an attempt.
    CREATE TABLE attempt_answers (
        id                    INTEGER PRIMARY KEY,
        attempt_id            INTEGER NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
        item_id               INTEGER NOT NULL REFERENCES mcq_items(id) ON DELETE CASCADE,
        chosen_index          INTEGER,         -- NULL if not yet answered
        is_correct            INTEGER,         -- NULL if not yet answered
        response_time         REAL,            -- seconds from question display to submit
        hesitation_count      INTEGER NOT NULL DEFAULT 0,  -- times answer changed before submit
        confidence_level      REAL NOT NULL DEFAULT 0.5,   -- 0-1 computed from time+hesitations
        answered_at           REAL
    );
    CREATE INDEX attempt_answers_by_attempt ON attempt_answers(attempt_id);

    -- Proctoring events recorded by browser JS (adapted from ai_learnmate ProctoringEvent).
    -- severity scale: tab_switch=60, full_screen_exit=30, copy_attempt=20, paste_attempt=20, browser_resize=10
    CREATE TABLE quiz_proctoring_events (
        id          INTEGER PRIMARY KEY,
        attempt_id  INTEGER NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
        event_type  TEXT NOT NULL CHECK (event_type IN (
                        'tab_switch', 'full_screen_exit', 'copy_attempt',
                        'paste_attempt', 'browser_resize', 'auto_submit')),
        severity    INTEGER NOT NULL DEFAULT 0,
        details_json TEXT NOT NULL DEFAULT '{}',
        captured_at REAL NOT NULL
    );
    CREATE INDEX proctor_events_by_attempt ON quiz_proctoring_events(attempt_id);

    -- Per-topic mastery derived from attempt_answers (recomputable from scratch).
    -- state: unknown | learning | mastered | weak
    CREATE TABLE topic_progress (
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        topic_id    INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
        answered    INTEGER NOT NULL DEFAULT 0,
        correct     INTEGER NOT NULL DEFAULT 0,
        mastery     REAL NOT NULL DEFAULT 0.0,
        state       TEXT NOT NULL DEFAULT 'unknown' CHECK (state IN ('unknown', 'learning', 'mastered', 'weak')),
        updated_at  REAL NOT NULL,
        PRIMARY KEY (user_id, subject_id, topic_id)
    );

    -- Prerequisite graph edges. Only confirmed=1 edges are ever followed in code.
    -- origin: 'manual' (user set it), 'suggested' (auto-detected, not yet confirmed).
    CREATE TABLE topic_prereqs (
        topic_id    INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
        prereq_id   INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
        confirmed   INTEGER NOT NULL DEFAULT 0 CHECK (confirmed IN (0, 1)),
        origin      TEXT NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual', 'suggested')),
        PRIMARY KEY (topic_id, prereq_id)
    );

    INSERT INTO schema_version(v) VALUES (6);
    COMMIT;
    """),
    (7, """    BEGIN;
    -- The mode a quiz was started in, so resuming it keeps the same rules (assessment = focus events counted, copy/paste blocked).
    ALTER TABLE quiz_attempts ADD COLUMN mode TEXT NOT NULL DEFAULT 'practice' CHECK (mode IN ('practice', 'assessment'));
    INSERT INTO schema_version(v) VALUES (7);
    COMMIT;
    """),
    (8, """    BEGIN;
    -- Backtracking: questions added to a running quiz because a related earlier question was missed.
    ALTER TABLE attempt_answers ADD COLUMN backtrack_from INTEGER;            -- topic whose miss caused this question (NULL = a normal question)
    ALTER TABLE attempt_answers ADD COLUMN depth INTEGER NOT NULL DEFAULT 0;   -- how many steps back from the original question
    ALTER TABLE quiz_attempts ADD COLUMN kind TEXT NOT NULL DEFAULT 'standard' CHECK (kind IN ('standard', 'diagnostic', 'revision'));
    INSERT INTO schema_version(v) VALUES (8);
    COMMIT;
    """),
    (9, """    BEGIN;
    -- Saved answers (bookmarks) and spaced-repetition state of practice questions.
    ALTER TABLE doubts ADD COLUMN saved INTEGER NOT NULL DEFAULT 0 CHECK (saved IN (0, 1));
    CREATE TABLE card_reviews (
        user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        item_id        INTEGER NOT NULL REFERENCES mcq_items(id) ON DELETE CASCADE,
        ease           REAL NOT NULL DEFAULT 2.5,
        interval_days  REAL NOT NULL DEFAULT 0,
        reps           INTEGER NOT NULL DEFAULT 0,
        lapses         INTEGER NOT NULL DEFAULT 0,
        due            REAL NOT NULL,
        last_at        REAL NOT NULL,
        PRIMARY KEY (user_id, item_id)
    );
    CREATE INDEX card_reviews_due ON card_reviews(user_id, due);
    INSERT INTO schema_version(v) VALUES (9);
    COMMIT;
    """),
    (10, """\
    BEGIN;
    -- What the student says they already know (asked once, after the first upload), and how hard each practice question is.
    ALTER TABLE subjects ADD COLUMN level TEXT CHECK (level IN ('new', 'intermediate', 'professional'));
    ALTER TABLE mcq_items ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard'));
    ALTER TABLE mcq_jobs ADD COLUMN purpose TEXT NOT NULL DEFAULT 'practice' CHECK (purpose IN ('practice', 'diagnostic'));

    -- Notes: written by the student, or saved from a chat answer.
    CREATE TABLE notes (
        id          INTEGER PRIMARY KEY,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        title       TEXT NOT NULL,
        body        TEXT NOT NULL DEFAULT '',
        source      TEXT NOT NULL DEFAULT 'own' CHECK (source IN ('own', 'chat')),
        doubt_id    INTEGER REFERENCES doubts(id) ON DELETE SET NULL,
        created_at  REAL NOT NULL,
        updated_at  REAL NOT NULL
    );
    CREATE INDEX notes_by_subject ON notes(user_id, subject_id, updated_at);

    -- Weekly progress e-mail: opt-in, with the address the student gave.
    ALTER TABLE users ADD COLUMN email TEXT;
    ALTER TABLE users ADD COLUMN weekly_email INTEGER NOT NULL DEFAULT 0 CHECK (weekly_email IN (0, 1));
    ALTER TABLE users ADD COLUMN last_digest_at REAL;
    INSERT INTO schema_version(v) VALUES (10);
    COMMIT;
    """),
    (11, """\
    BEGIN;
    -- E-mail one-time codes (password reset, address verification) and the counters that limit guessing and flooding.
    ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0 CHECK (email_verified IN (0, 1));
    CREATE UNIQUE INDEX users_verified_email ON users(lower(email)) WHERE email_verified=1;
    CREATE TABLE email_otps (
        id          INTEGER PRIMARY KEY,
        purpose     TEXT NOT NULL CHECK (purpose IN ('reset', 'verify')),
        user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
        email       TEXT NOT NULL,
        code_hash   TEXT NOT NULL,                 -- HMAC of the code; the code itself is never stored
        salt        BLOB NOT NULL,
        created_at  REAL NOT NULL,
        expires_at  REAL NOT NULL,
        attempts    INTEGER NOT NULL DEFAULT 0,
        consumed_at REAL,
        ip          TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX email_otps_lookup ON email_otps(email, purpose, created_at);
    CREATE TABLE security_events (
        id    INTEGER PRIMARY KEY,
        kind  TEXT NOT NULL,
        key   TEXT NOT NULL,
        at    REAL NOT NULL
    );
    CREATE INDEX security_events_lookup ON security_events(kind, key, at);
    INSERT INTO schema_version(v) VALUES (11);
    COMMIT;
    """),
    (12, """\
    BEGIN;
    -- The student's study profile for one subject (goal, weekly hours, target date) and the coach paragraph written for it.
    CREATE TABLE study_plans (
        subject_id     INTEGER PRIMARY KEY REFERENCES subjects(id) ON DELETE CASCADE,
        user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        goal           TEXT NOT NULL DEFAULT '',
        hours_per_week REAL NOT NULL DEFAULT 5,
        target_date    TEXT,
        coach_status   TEXT NOT NULL DEFAULT 'idle' CHECK (coach_status IN ('idle', 'pending', 'done', 'failed')),
        coach_text     TEXT NOT NULL DEFAULT '',
        coach_model    TEXT,
        coach_hash     TEXT,
        coach_at       REAL,
        updated_at     REAL NOT NULL
    );
    INSERT INTO schema_version(v) VALUES (12);
    COMMIT;
    """),
    (13, """\
    BEGIN;
    -- How sure the student feels about a topic (1 to 5), to compare with what their answers show.
    CREATE TABLE self_ratings (
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        topic_id   INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
        rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        updated_at REAL NOT NULL,
        PRIMARY KEY (user_id, topic_id)
    );
    -- A job description the student wants to be ready for, and the skills read from it.
    CREATE TABLE career_goals (
        id          INTEGER PRIMARY KEY,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title       TEXT NOT NULL,
        jd_text     TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'failed')),
        skills_json TEXT NOT NULL DEFAULT '[]',
        model       TEXT,
        created_at  REAL NOT NULL,
        updated_at  REAL NOT NULL
    );
    CREATE INDEX career_goals_by_user ON career_goals(user_id, created_at);
    CREATE TABLE career_snapshots (
        id        INTEGER PRIMARY KEY,
        goal_id   INTEGER NOT NULL REFERENCES career_goals(id) ON DELETE CASCADE,
        at        REAL NOT NULL,
        readiness REAL,
        verified  INTEGER NOT NULL,
        total     INTEGER NOT NULL
    );
    CREATE INDEX career_snapshots_by_goal ON career_snapshots(goal_id, at);
    INSERT INTO schema_version(v) VALUES (13);
    COMMIT;
    """),
    (14, """    BEGIN;
    -- Academic setup, exam date, what a document is for (notes, syllabus, past papers), and the study actions the student took with what came of them.
    ALTER TABLE users ADD COLUMN department TEXT NOT NULL DEFAULT '';
    ALTER TABLE users ADD COLUMN semester INTEGER;
    ALTER TABLE subjects ADD COLUMN exam_date TEXT;
    ALTER TABLE documents ADD COLUMN role TEXT NOT NULL DEFAULT 'notes' CHECK (role IN ('notes', 'syllabus', 'pyq'));
    CREATE TABLE interventions (
        id              INTEGER PRIMARY KEY,
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id      INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        topic_id        INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
        kind            TEXT NOT NULL CHECK (kind IN ('worked_example', 'flashcards', 'revision', 'practice')),
        status          TEXT NOT NULL DEFAULT 'done' CHECK (status IN ('pending', 'done', 'failed')),
        payload_json    TEXT NOT NULL DEFAULT '{}',
        model           TEXT,
        level           TEXT,
        conf_before     REAL,
        answered_before INTEGER NOT NULL DEFAULT 0,
        outcome         TEXT CHECK (outcome IN ('improved', 'no_change', 'worse')),
        conf_after      REAL,
        verified_at     REAL,
        created_at      REAL NOT NULL,
        updated_at      REAL NOT NULL
    );
    CREATE INDEX interventions_by_topic ON interventions(user_id, subject_id, topic_id, created_at);
    INSERT INTO schema_version(v) VALUES (14);
    COMMIT;
    """),
    (15, "rebuild_documents"),         # a Python step (see _rebuild_documents): images and OCR need a wider CHECK on documents.kind
    (16, """\
    BEGIN;
    -- Local embeddings of every passage (semantic.py). A plain table so deleting a document cascades without any extension.
    CREATE TABLE IF NOT EXISTS chunk_embeddings (
        chunk_id  INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
        model     TEXT NOT NULL,
        dim       INTEGER NOT NULL,
        vec       BLOB NOT NULL
    );
    -- What each of the six agents concluded after a quiz (agents.py): the Agent Console reads this.
    CREATE TABLE agent_runs (
        id          INTEGER PRIMARY KEY,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        attempt_id  INTEGER REFERENCES quiz_attempts(id) ON DELETE SET NULL,
        trigger     TEXT NOT NULL,
        steps_json  TEXT NOT NULL DEFAULT '[]',
        summary     TEXT NOT NULL DEFAULT '',
        ms          INTEGER NOT NULL DEFAULT 0,
        created_at  REAL NOT NULL
    );
    CREATE INDEX agent_runs_by_subject ON agent_runs(user_id, subject_id, created_at);
    -- Hot paths of the dashboard and analytics pages.
    CREATE INDEX IF NOT EXISTS attempt_answers_by_item ON attempt_answers(item_id);
    CREATE INDEX IF NOT EXISTS quiz_attempts_finished ON quiz_attempts(user_id, is_active, finished_at);
    CREATE INDEX IF NOT EXISTS doubts_by_user_time ON doubts(user_id, created_at);
    CREATE INDEX IF NOT EXISTS documents_by_subject ON documents(subject_id, created_at);
    INSERT INTO schema_version(v) VALUES (16);
    COMMIT;
    """),
    (17, """\
    BEGIN;
    -- Smart notes (smartnotes.py): notes built from a topic's own passages. Nothing references notes, so a plain rebuild is safe.
    CREATE TABLE notes_new (
        id          INTEGER PRIMARY KEY,
        user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        title       TEXT NOT NULL,
        body        TEXT NOT NULL DEFAULT '',
        source      TEXT NOT NULL DEFAULT 'own' CHECK (source IN ('own', 'chat', 'smart')),
        doubt_id    INTEGER REFERENCES doubts(id) ON DELETE SET NULL,
        topic_id    INTEGER REFERENCES topics(id) ON DELETE SET NULL,
        created_at  REAL NOT NULL,
        updated_at  REAL NOT NULL
    );
    INSERT INTO notes_new(id, user_id, subject_id, title, body, source, doubt_id, created_at, updated_at)
        SELECT id, user_id, subject_id, title, body, source, doubt_id, created_at, updated_at FROM notes;
    DROP TABLE notes;
    ALTER TABLE notes_new RENAME TO notes;
    CREATE INDEX notes_by_subject ON notes(user_id, subject_id, updated_at);
    CREATE INDEX notes_by_topic ON notes(subject_id, topic_id, source);
    INSERT INTO schema_version(v) VALUES (17);
    COMMIT;
    """),
]


def _rebuild_documents(db: sqlite3.Connection) -> None:
    """SQLite cannot change a CHECK constraint in place, so `documents` is rebuilt (the documented 12-step way): foreign keys
    off, copy into a new table with 'image' allowed and an `ocr_pages` count, swap, check the keys, foreign keys back on."""
    db.execute("PRAGMA foreign_keys=OFF")
    try:
        db.executescript("""
        BEGIN;
        CREATE TABLE documents_new (
            id           INTEGER PRIMARY KEY,
            subject_id   INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            kind         TEXT NOT NULL CHECK (kind IN ('txt', 'pdf', 'docx', 'url', 'image')),
            title        TEXT NOT NULL,
            source       TEXT NOT NULL,
            sha256       TEXT NOT NULL,
            bytes        INTEGER NOT NULL,
            pages        INTEGER,
            status       TEXT NOT NULL CHECK (status IN ('parsed', 'empty', 'failed')),
            warnings     TEXT NOT NULL DEFAULT '[]',
            created_at   REAL NOT NULL,
            role         TEXT NOT NULL DEFAULT 'notes' CHECK (role IN ('notes', 'syllabus', 'pyq')),
            ocr_pages    INTEGER NOT NULL DEFAULT 0,
            UNIQUE (subject_id, sha256)
        );
        INSERT INTO documents_new(id, subject_id, kind, title, source, sha256, bytes, pages, status, warnings, created_at, role)
            SELECT id, subject_id, kind, title, source, sha256, bytes, pages, status, warnings, created_at, role FROM documents;
        DROP TABLE documents;
        ALTER TABLE documents_new RENAME TO documents;
        INSERT INTO schema_version(v) VALUES (15);
        COMMIT;
        """)
        bad = db.execute("PRAGMA foreign_key_check").fetchall()
        if bad:
            raise RuntimeError(f"foreign key check failed after rebuilding documents: {len(bad)} rows")
    finally:
        db.execute("PRAGMA foreign_keys=ON")


_STEPS = {"rebuild_documents": _rebuild_documents}



def migrate(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS schema_version (v INTEGER NOT NULL)")
    current = db.execute("SELECT MAX(v) FROM schema_version").fetchone()[0] or 0
    for version, script in MIGRATIONS:
        if version > current:
            if script in _STEPS:
                _STEPS[script](db)
            else:
                db.executescript(script)


def open_db(path: str | None = None) -> Store:
    """Open (creating if needed) the StudyHub database. Returns the spine's Store; its `.db` is the connection."""
    path = path or settings.db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    store = Store(path)
    db = store.db
    db.execute("PRAGMA synchronous=NORMAL")        # safe with WAL (a power cut can lose the last commit, never corrupt the file)
    db.execute("PRAGMA temp_store=MEMORY")
    db.execute("PRAGMA cache_size=-16000")         # 16 MB page cache per connection
    migrate(db)
    return store
