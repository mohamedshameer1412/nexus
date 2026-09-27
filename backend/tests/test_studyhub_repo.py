"""StudyHub data layer: subjects, ownership and LEAKAGE. (UNIT.)

The leakage tests are the point of this file: user B, holding a valid account, must not be able to read, change, list or
delete anything of user A through any Repo method.
"""
from __future__ import annotations

import inspect
import sqlite3

import pytest

from studyhub import auth
from studyhub.db import MIGRATIONS, migrate, open_db
from studyhub.repo import Repo, SubjectError

PW = "correct horse battery"


@pytest.fixture(autouse=True)
def fast_scrypt(monkeypatch):
    monkeypatch.setenv("STUDYHUB_SCRYPT_N", "1024")


@pytest.fixture()
def world(tmp_path):
    store = open_db(str(tmp_path / "repo.db"))
    db = store.db
    alice, bob = auth.register(db, "alice", PW), auth.register(db, "bob", PW)
    yield Repo(db), alice, bob, db
    store.close()


# ------------------------------------------------------------------ CRUD

def test_a_user_can_create_list_read_update_and_delete_their_subjects(world):
    repo, alice, _, _ = world
    sid = repo.create_subject(alice, "Databases", "SQL and design")
    assert [s["name"] for s in repo.list_subjects(alice)] == ["Databases"]
    assert repo.get_subject(alice, sid)["description"] == "SQL and design"
    assert repo.update_subject(alice, sid, "Database Systems", "updated") is True
    assert repo.get_subject(alice, sid)["name"] == "Database Systems"
    assert repo.delete_subject(alice, sid) is True
    assert repo.get_subject(alice, sid) is None and repo.list_subjects(alice) == []


def test_any_number_of_subjects_sorted_by_name(world):
    repo, alice, _, _ = world
    for name in ["zoology", "Algebra", "biology"]:
        repo.create_subject(alice, name)
    assert [s["name"] for s in repo.list_subjects(alice)] == ["Algebra", "biology", "zoology"]


def test_names_are_tidied_and_validated(world):
    repo, alice, _, _ = world
    sid = repo.create_subject(alice, "  Data    Structures \n", "  a \t b ")
    s = repo.get_subject(alice, sid)
    assert (s["name"], s["description"]) == ("Data Structures", "a b")
    for bad, msg in [("", "name"), ("   ", "name"), ("x" * 81, "80")]:
        with pytest.raises(SubjectError, match=msg):
            repo.create_subject(alice, bad)
    with pytest.raises(SubjectError, match="500"):
        repo.create_subject(alice, "ok", "y" * 501)


def test_a_duplicate_name_is_refused_per_user_ignoring_case_but_allowed_across_users(world):
    repo, alice, bob, _ = world
    repo.create_subject(alice, "Databases")
    with pytest.raises(SubjectError, match="already have"):
        repo.create_subject(alice, "DATABASES")
    assert repo.create_subject(bob, "databases") > 0, "another user may use the same name"
    sid = repo.create_subject(alice, "Networks")
    with pytest.raises(SubjectError, match="already have"):
        repo.update_subject(alice, sid, "databases")


def test_sql_metacharacters_in_names_are_stored_as_text(world):
    repo, alice, _, db = world
    evil = "x'); DROP TABLE subjects;--"
    sid = repo.create_subject(alice, evil, evil)
    assert repo.get_subject(alice, sid)["name"] == evil
    assert db.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 1


# ---------------------------------------------------------------- LEAKAGE

def test_user_b_cannot_read_user_as_subject_by_id(world):
    repo, alice, bob, _ = world
    sid = repo.create_subject(alice, "Secret notes", "private")
    assert repo.get_subject(bob, sid) is None
    assert repo.get_subject(bob, sid + 1000) is None, "and cannot tell 'not yours' from 'does not exist'"


def test_user_b_cannot_list_user_as_subjects(world):
    repo, alice, bob, _ = world
    repo.create_subject(alice, "Secret notes")
    assert repo.list_subjects(bob) == []


def test_user_b_cannot_change_or_delete_user_as_subject(world):
    repo, alice, bob, _ = world
    sid = repo.create_subject(alice, "Secret notes", "private")
    assert repo.update_subject(bob, sid, "hacked", "hacked") is False
    assert repo.delete_subject(bob, sid) is False
    s = repo.get_subject(alice, sid)
    assert (s["name"], s["description"]) == ("Secret notes", "private"), "untouched"


def test_guessing_ids_never_reaches_someone_elses_rows(world):
    repo, alice, bob, _ = world
    for i in range(20):
        repo.create_subject(alice, f"subject {i}")
    assert [repo.get_subject(bob, n) for n in range(0, 60)] == [None] * 60


def test_every_repo_method_that_takes_a_subject_also_takes_a_user(world):
    """Structural: there is no way to fetch a subject by id alone."""
    for name, fn in inspect.getmembers(Repo, inspect.isfunction):
        params = inspect.signature(fn).parameters
        if "subject_id" in params:
            assert "user_id" in params, f"Repo.{name} takes subject_id without user_id"


# ----------------------------------------------------- schema and migrations

def test_deleting_a_user_deletes_their_subjects_and_sessions(world):
    repo, alice, bob, db = world
    repo.create_subject(alice, "A1")
    repo.create_subject(bob, "B1")
    auth.create_session(db, alice)
    db.execute("DELETE FROM users WHERE id=?", (alice,))
    assert db.execute("SELECT COUNT(*) FROM subjects WHERE user_id=?", (alice,)).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    assert [s["name"] for s in repo.list_subjects(bob)] == ["B1"], "the other user is untouched"


def test_foreign_keys_are_enforced(world):
    _, _, _, db = world
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO subjects(user_id, name, created_at) VALUES (99999, 'orphan', 0)")


def test_migrations_are_idempotent_and_recorded_once(tmp_path):
    path = str(tmp_path / "m.db")
    open_db(path).close()
    store = open_db(path)
    migrate(store.db)
    versions = [r[0] for r in store.db.execute("SELECT v FROM schema_version ORDER BY v")]
    assert versions == [v for v, _ in MIGRATIONS]
    tables = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "sessions", "login_attempts", "subjects", "runs", "versions"} <= tables, \
        "StudyHub tables and the spine's tables live in one file"
    store.close()
