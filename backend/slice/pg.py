"""PostgreSQL behind the sqlite3 interface the engine was written against.

The engine's SQL is plain SQL with `?` placeholders. This module runs that SQL on PostgreSQL: it rewrites the few SQLite-only
spellings (placeholders, INSERT OR IGNORE, COLLATE NOCASE, REAL/BLOB in DDL), returns rows that read like sqlite3.Row
(row[0], row["name"], dict(row)), keeps `lastrowid`, and raises sqlite3's exception types so every existing
`except sqlite3.IntegrityError` keeps working. Full-text search and vectors are not translated here: retrieval has its own
PostgreSQL path (tsvector) and vectors go through FAISS (semantic.py).

Each StudyHub "path" maps to a schema: `public` normally; with STUDYHUB_PG_SCHEMA_PER_PATH=1 (the test suite) every database
path gets its own schema, so tests stay isolated exactly as they were with one SQLite file each.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import threading
import uuid
from decimal import Decimal
from functools import lru_cache

import psycopg2
import psycopg2.extensions as ext
import psycopg2.extras

# Numbers come back as Python numbers (AVG/ROUND give NUMERIC), bytes as bytes, and True/False go in as 1/0 like SQLite.
ext.register_type(ext.new_type(ext.DECIMAL.values, "NEXUS_DEC2FLOAT", lambda v, c: None if v is None else float(Decimal(v))))
ext.register_type(ext.new_type(psycopg2.BINARY.values, "NEXUS_BYTES", lambda v, c: None if v is None else bytes(psycopg2.BINARY(v, c))))
ext.register_adapter(bool, lambda b: ext.AsIs(int(b)))


def enabled() -> bool:
    return os.environ.get("DB_ENGINE", "sqlite").lower() in ("postgres", "postgresql")


def dsn() -> dict:
    return {"host": os.environ.get("DB_HOST", "127.0.0.1").replace("localhost", "127.0.0.1"),
            "port": int(os.environ.get("DB_PORT", "5432")), "user": os.environ.get("DB_USER", "postgres"),
            "password": os.environ.get("DB_PASSWORD", ""), "dbname": os.environ.get("DB_NAME", "nexus")}


def schema_for(path: str) -> str:
    if path == ":memory:":
        return "m_" + uuid.uuid4().hex[:16]
    if os.environ.get("STUDYHUB_PG_SCHEMA_PER_PATH") == "1":
        return _test_slot(os.path.abspath(path))
    return os.environ.get("STUDYHUB_PG_SCHEMA", "public")


# The test suite: every database path a test opens gets a slot schema (t_0, t_1, ...). Slots are reused from test to test and
# emptied on first use (DELETE is milliseconds; creating 35 tables is a fifth of a second), so 900 tests stay fast and isolated.
_slots: dict[str, str] = {}
_admin = None
_RESET = """DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = '{s}' AND tablename <> 'schema_version' LOOP
    EXECUTE format('DELETE FROM %I.%I', '{s}', r.tablename); END LOOP;
  FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = '{s}' LOOP
    EXECUTE format('ALTER SEQUENCE %I.%I RESTART', '{s}', r.sequencename); END LOOP;
END $$;"""


def new_test() -> None:
    _slots.clear()


def _test_slot(key: str) -> str:
    global _admin
    with _pool_lock:
        if key in _slots:
            return _slots[key]
        name = _slots[key] = f"t_{len(_slots)}"
        if _admin is None or _admin.closed:
            _admin = psycopg2.connect(**dsn())
            _admin.autocommit = True
            _admin.cursor().execute("SET session_replication_role = replica")   # no FK or append-only triggers while emptying
        _admin.cursor().execute(_RESET.format(s=name))
        return name


# ------------------------------------------------------------------------------------------------ SQL dialect

_QUOTED = re.compile(r"('(?:[^']|'')*')")


@lru_cache(maxsize=4096)
def translate(sql: str) -> str:
    """SQLite spelling -> PostgreSQL spelling, for statements run with parameters."""
    s = sql.replace("%", "%%")
    parts = _QUOTED.split(s)
    for i in range(0, len(parts), 2):                     # outside string literals only
        parts[i] = parts[i].replace("?", "%s")
    s = "".join(parts)
    s = re.sub(r"\bBEGIN\s+(IMMEDIATE|EXCLUSIVE|DEFERRED)\b", "BEGIN", s, flags=re.I)
    s = re.sub(r"\s+COLLATE\s+NOCASE\b", "", s, flags=re.I)  # the columns are CITEXT: comparisons already ignore case
    s = re.sub(r"\bAS\s+REAL\b", "AS DOUBLE PRECISION", s, flags=re.I)
    s = re.sub(r"\binstr\(", "strpos(", s, flags=re.I)
    s = re.sub(r"\bdate\(([^,()]+),\s*'unixepoch'\)", r"to_char(to_timestamp(\1) AT TIME ZONE 'UTC', 'YYYY-MM-DD')", s, flags=re.I)
    if re.match(r"\s*INSERT\s+OR\s+IGNORE\b", s, re.I):
        s = re.sub(r"^\s*INSERT\s+OR\s+IGNORE", "INSERT", s, flags=re.I).rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return s


@lru_cache(maxsize=256)
def translate_ddl(script: str) -> str:
    """A migration script -> PostgreSQL DDL. FTS5 tables and SQLite triggers are dropped: PostgreSQL has its own (see db.py)."""
    s = re.sub(r"CREATE\s+VIRTUAL\s+TABLE[^;]*;", "", script, flags=re.I)
    s = re.sub(r"CREATE\s+TRIGGER.*?\bEND;", "", s, flags=re.I | re.S)
    s = re.sub(r"\bid\s+INTEGER\s+PRIMARY\s+KEY\b", "id SERIAL PRIMARY KEY", s)
    s = re.sub(r"\bTEXT\b([^,\n]*?)\s+COLLATE\s+NOCASE", r"CITEXT\1", s)
    s = re.sub(r"\bREAL\b", "DOUBLE PRECISION", s)
    s = re.sub(r"\bBLOB\b", "BYTEA", s)
    return s


# ------------------------------------------------------------------------------------------------- pool

_pool: dict[tuple, list] = {}
_pool_lock = threading.Lock()
_ready: set[tuple] = set()          # schemas already created in this process
MAX_IDLE = int(os.environ.get("STUDYHUB_PG_POOL", "12"))


def _checkout(key: tuple, schema: str):
    with _pool_lock:
        idle = _pool.get(key)
        if idle:
            return idle.pop()
    raw = psycopg2.connect(**dict(key[0]), connect_timeout=10)
    raw.autocommit = True                                # like sqlite3 with isolation_level=None: explicit BEGIN/COMMIT
    with raw.cursor() as cur:
        if key not in _ready:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            _ready.add(key)
        cur.execute(f'SET search_path TO "{schema}", public')
    return raw


def _checkin(key: tuple, raw) -> None:
    try:
        if raw.closed:
            return
        if raw.get_transaction_status() != ext.TRANSACTION_STATUS_IDLE:
            raw.rollback()
        with _pool_lock:
            idle = _pool.setdefault(key, [])
            if sum(len(v) for v in _pool.values()) < MAX_IDLE:
                idle.append(raw)
                return
        raw.close()
    except Exception:
        try:
            raw.close()
        except Exception:
            pass


def drain_pool() -> None:
    with _pool_lock:
        conns = [c for v in _pool.values() for c in v]
        _pool.clear()
        _ready.clear()
    for c in conns:
        try:
            c.close()
        except Exception:
            pass


# ------------------------------------------------------------------------------------------- connection

def _wrap(e: psycopg2.Error) -> sqlite3.Error:
    # P0001 = a trigger's RAISE EXCEPTION, which SQLite's RAISE(ABORT) reports as an integrity error
    cls = sqlite3.IntegrityError if isinstance(e, psycopg2.IntegrityError) or e.pgcode == "P0001" else sqlite3.OperationalError
    err = cls(str(e).strip())
    err.pgcode = e.pgcode
    return err


class Cursor:
    def __init__(self, conn: "Connection", cur):
        self._conn, self._cur = conn, cur

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    @property
    def lastrowid(self) -> int | None:
        return self._conn._lastval()

    @property
    def description(self):
        return self._cur.description

    def fetchone(self):
        return self._cur.fetchone() if self._cur.description else None

    def fetchall(self):
        return self._cur.fetchall() if self._cur.description else []

    def fetchmany(self, n: int = 1):
        return self._cur.fetchmany(n) if self._cur.description else []

    def __iter__(self):
        return iter(self.fetchall())

    def close(self) -> None:
        self._cur.close()


class _Empty:
    rowcount, lastrowid, description = 0, None, None

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def __iter__(self):
        return iter(())


class Connection:
    """The subset of sqlite3.Connection the engine uses: execute, executemany, executescript, close, commit, rollback."""
    pg = True

    def __init__(self, path: str):
        self.path = path
        self.schema = schema_for(path)
        self._key = (tuple(sorted(dsn().items())), self.schema)
        self._raw = _checkout(self._key, self.schema)

    @property
    def in_transaction(self) -> bool:
        return self._raw.get_transaction_status() != ext.TRANSACTION_STATUS_IDLE

    def _cursor(self):
        if self._raw is None:
            raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
        return self._raw.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def _lastval(self) -> int | None:
        cur = self._raw.cursor()
        try:
            cur.execute("SELECT lastval()")
            return int(cur.fetchone()[0])
        except psycopg2.Error:
            return None

    def execute(self, sql: str, params=()):
        head = sql.lstrip()[:8].upper()
        if head.startswith("PRAGMA"):
            return _Empty()
        cur = self._cursor()
        # Inside a transaction a failed INSERT/UPDATE must not poison the rest of it (SQLite carries on): a savepoint per write,
        # on its own cursor so the statement's rowcount survives.
        sp = self._raw.cursor() if self.in_transaction and head.startswith(("INSERT", "UPDATE", "DELETE")) else None
        try:
            if sp:
                sp.execute("SAVEPOINT nexus_stmt")
            cur.execute(translate(sql), tuple(params) if not isinstance(params, dict) else params)
            if sp:
                sp.execute("RELEASE SAVEPOINT nexus_stmt")
        except psycopg2.Error as e:
            if sp:
                try:
                    sp.execute("ROLLBACK TO SAVEPOINT nexus_stmt")
                except psycopg2.Error:
                    pass
            raise _wrap(e) from e
        return Cursor(self, cur)

    def executemany(self, sql: str, seq) -> Cursor:
        cur = self._cursor()
        try:
            cur.executemany(translate(sql), [tuple(p) for p in seq])
        except psycopg2.Error as e:
            raise _wrap(e) from e
        return Cursor(self, cur)

    def executescript(self, script: str) -> None:
        cur = self._cursor()
        try:
            cur.execute(translate_ddl(script))
        except psycopg2.Error as e:
            if self.in_transaction:
                self._raw.rollback()
            raise _wrap(e) from e

    def commit(self) -> None:
        if self.in_transaction:
            self._raw.cursor().execute("COMMIT")

    def rollback(self) -> None:
        if self.in_transaction:
            self._raw.cursor().execute("ROLLBACK")

    def iterdump(self):
        """Every row of every table in this schema as text (tests use it to prove a secret is stored nowhere)."""
        for (t,) in self.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()").fetchall():
            for (row,) in self.execute(f'SELECT "{t}"::text FROM "{t}"').fetchall():
                yield f"{t} {row}\n"

    def close(self) -> None:
        raw, self._raw = self._raw, None
        if raw is not None:
            _checkin(self._key, raw)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        (self.rollback if exc_type else self.commit)()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def drop_schemas(prefix: str) -> int:
    """Remove every schema whose name starts with `prefix` (the test suite's per-test schemas)."""
    raw = psycopg2.connect(**dsn())
    raw.autocommit = True
    try:
        cur = raw.cursor()
        cur.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE %s", (prefix + "%",))
        names = [r[0] for r in cur.fetchall()]
        for n in names:
            cur.execute(f'DROP SCHEMA IF EXISTS "{n}" CASCADE')
        return len(names)
    finally:
        raw.close()


def tsquery(match: str) -> str:
    """A StudyHub FTS5 expression ('"a" OR "b"', or '"a" "b"' meaning both) as to_tsquery text: 'a' | 'b', 'a' & 'b'."""
    groups = []
    for g in re.split(r"\s+OR\s+", match or ""):
        words = ["'" + w.replace("'", "''").replace("\\", "") + "'" for w in re.findall(r'"([^"]*)"', g) if w.strip()]
        if words:
            groups.append("(" + " & ".join(words) + ")")
    return " | ".join(groups)
