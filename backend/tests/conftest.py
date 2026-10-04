"""Test harness for the Django backend.

PostgreSQL when backend/.env says DB_ENGINE=postgresql (the suite then uses the database <DB_NAME>_test; set
NEXUS_TEST_DB=sqlite to run on SQLite instead). Each database path a test opens gets its own PostgreSQL schema
(slice/pg.py), emptied before the test; Django's own tables live in the test database's public schema.

On SQLite every test uses its own SQLite file (STUDYHUB_DB, set by fixtures). The learning engine opens that file itself; here Django is made
to follow it too: its connection reads the current path, and a fresh file gets Django's tables from a schema template built once
per run (running `migrate` for every test would be far slower). Nothing here changes how the app behaves outside tests.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

_HOME = Path(tempfile.mkdtemp(prefix="nexus-tests-"))
os.environ["STUDYHUB_DB"] = str(_HOME / "bootstrap.db")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexus_api.settings")
os.environ.setdefault("STUDYHUB_FACULTY_REVIEW", "off")      # existing tests use questions straight away; test_faculty.py turns review on


def _dotenv() -> dict:
    """Only the DB_* lines of backend/.env (the settings module skips .env under pytest)."""
    f = Path(__file__).resolve().parent.parent / ".env"
    out = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip().startswith("DB_"):
                out[k.strip()] = v.strip()
    return out


_cfg = {**_dotenv(), **{k: v for k, v in os.environ.items() if k.startswith("DB_")}}
PG = os.environ.get("NEXUS_TEST_DB", "").lower() != "sqlite" and _cfg.get("DB_ENGINE", "").lower() in ("postgres", "postgresql")
if PG:
    os.environ.update({k: v for k, v in _cfg.items()})
    os.environ["DB_NAME"] = _cfg.get("DB_NAME", "nexus") + "_test"
    os.environ["STUDYHUB_PG_SCHEMA_PER_PATH"] = "1"
    import psycopg2

    from slice import pg

    _c = psycopg2.connect(**{**pg.dsn(), "dbname": "postgres"})
    _c.autocommit = True
    with _c.cursor() as _cur:
        _cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (os.environ["DB_NAME"],))
        if not _cur.fetchone():
            _cur.execute(f'CREATE DATABASE "{os.environ["DB_NAME"]}"')
    _c.close()
else:
    os.environ["DB_ENGINE"] = "sqlite"

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402
from django.db.backends.signals import connection_created  # noqa: E402
from django.db.backends.sqlite3.base import DatabaseWrapper  # noqa: E402

from studyhub import settings as engine  # noqa: E402


def _sqlite_harness():
    global _fresh_django_connection
    # 1. Django's schema, once: migrate the bootstrap file and keep its CREATE statements.
    call_command("migrate", verbosity=0)
    with sqlite3.connect(_HOME / "bootstrap.db") as _c:
        _SCHEMA = [sql for (sql,) in _c.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type='index', name")]
        _MIGRATIONS = _c.execute("SELECT app, name, applied FROM django_migrations").fetchall()
    connections.close_all()

    # 2. Django connects to whatever STUDYHUB_DB is right now.
    _params = DatabaseWrapper.get_connection_params


    def _current_params(self):
        params = _params(self)
        params["database"] = str(Path(engine.db_path()).resolve())
        return params


    DatabaseWrapper.get_connection_params = _current_params


    # 3. A file without Django's tables gets them from the template.
    def _ensure_schema(sender, connection, **kwargs):
        if connection.vendor != "sqlite":
            return
        cur = connection.connection.cursor()
        if cur.execute("SELECT 1 FROM sqlite_master WHERE name='django_migrations'").fetchone():
            return
        for sql in _SCHEMA:
            cur.execute(sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1).replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", 1)
                        .replace("CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ", 1))
        cur.executemany("INSERT INTO django_migrations(app, name, applied) VALUES (?, ?, ?)", _MIGRATIONS)
        connection.connection.commit()


    connection_created.connect(_ensure_schema)


    @pytest.fixture(autouse=True)
    def _fresh_django_connection():
        """Each test starts with Django disconnected, so it reconnects to that test's own file."""
        connections.close_all()
        yield
        connections.close_all()


if PG:
    call_command("migrate", verbosity=0)
    connections.close_all()

    @pytest.fixture(autouse=True)
    def _fresh_django_connection():
        """Each test gets emptied engine schemas (slice/pg.py) and a fresh Django connection."""
        pg.new_test()
        connections.close_all()
        yield
        connections.close_all()
else:
    _sqlite_harness()

