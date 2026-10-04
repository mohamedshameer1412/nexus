"""Slow work (model calls) done off the request: answering questions, writing practice questions, the roadmap coach,
reading skills out of a job description and worked examples.

Where the work runs (submit_task):
  * Celery + Redis when a broker answers (CELERY_BROKER_URL, default redis://127.0.0.1:6379/0): the job is queued and a Celery
    worker runs it (`celery -A nexus_api worker --pool=solo -c 1`; one at a time, a local model on a small GPU cannot do two);
  * otherwise one worker thread in this process, so the app keeps working without Redis;
  * with STUDYHUB_QA_INLINE=1 (tests, scripts) inside the request.
Framework-free: the Django views call submit_*; nothing here knows about HTTP.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from studyhub import career, mcq, models, qa, roadmap, settings, tutor
from studyhub import db as studydb
from studyhub.repo import Repo

# Which models answer a question. A module attribute so tests (and other deployments) can swap it: (db, user) -> (tiers, notes).
tier_factory = models.build_tiers


def tiers_for(db, user, task: str = "answer"):
    """The models for one kind of work. Tests replace `tier_factory` with a two-argument function, which is still accepted."""
    try:
        return tier_factory(db, user, task=task)
    except TypeError:
        return tier_factory(db, user)


_worker: ThreadPoolExecutor | None = None
_worker_lock = threading.Lock()


@contextmanager
def _open_store():
    store = studydb.open_db()
    try:
        yield store
    finally:
        store.close()


def process_doubt(doubt_id: int, user_id: int) -> None:
    """Answer one pending question. Runs in the worker thread, with its own connection."""
    with _open_store() as store:
        repo = Repo(store.db)
        try:
            tiers, notes = tiers_for(store.db, repo.get_user(user_id), "answer")
            qa.run_doubt(store, user_id, doubt_id, tiers, notes)
        except Exception as e:                                # the student must never be left on a spinner
            repo.finish_doubt(user_id, doubt_id, status="failed", tier=None, model=None, dropped=0, claims=[], sources=[],
                              reason=f"Something went wrong while answering ({type(e).__name__}). Please try again.")


def submit_doubt(doubt_id: int, user_id: int) -> None:
    submit_task(process_doubt, doubt_id, user_id)


def process_mcq(job_id: int, user_id: int) -> None:
    """Write the questions of one pending job. Runs in the worker thread, with its own connection."""
    with _open_store() as store:
        repo = Repo(store.db)
        try:
            tiers, notes = tiers_for(store.db, repo.get_user(user_id), "write")
            mcq.run_job(store, user_id, job_id, tiers, notes)
        except Exception as e:
            store.db.execute("UPDATE mcq_jobs SET status='failed', reason=?, finished_at=? "
                             "WHERE id=? AND user_id=? AND status='pending'",
                             (f"Something went wrong while writing questions ({type(e).__name__}). Please try again.", time.time(), job_id, user_id))


def submit_task(fn, *args) -> None:
    """Run a slow job (a model call): on Celery when a broker is reachable, else on the single worker thread."""
    global _worker
    if settings.qa_inline():
        fn(*args)
        return
    if fn.__name__ in TASKS and celery_ready():
        from nexus_api.celery import run_job
        run_job.delay(fn.__name__, *args)
        return
    with _worker_lock:
        if _worker is None:
            _worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qa")
        _worker.submit(fn, *args)


# The jobs a Celery worker may run, by name (nexus_api/celery.py). Nothing else can be queued.
TASKS = {"process_doubt", "process_mcq", "process_coach", "process_career", "process_example"}
_broker = {"ok": False, "at": 0.0}


def broker_url() -> str:
    return os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")


def celery_ready() -> bool:
    """Is a Celery broker reachable? Checked at most every 30 s. STUDYHUB_CELERY=off forces the in-process worker."""
    if os.environ.get("STUDYHUB_CELERY", "auto").lower() in ("off", "0", "false"):
        return False
    now = time.time()
    if now - _broker["at"] < 30:
        return _broker["ok"]
    try:
        import redis
        redis.Redis.from_url(broker_url(), socket_connect_timeout=0.3, socket_timeout=0.3).ping()
        ok = True
    except Exception:
        ok = False
    _broker.update(ok=ok, at=now)
    return ok


class _CoachOut(BaseModel):
    text: str


def process_coach(user_id: int, subject_id: int) -> None:
    """Write the coach paragraph for a subject's roadmap: the cloud first when the student allowed it, then the local model, then plain rules."""
    from slice.budget import Budget
    from slice.records import RunState
    store = studydb.open_db()
    try:
        repo = Repo(store.db)
        user, subject = repo.get_user(user_id), repo.get_subject(user_id, subject_id)
        if user is None or subject is None:
            return
        profile = roadmap.get_profile(store.db, user_id, subject_id)
        info = roadmap.skill_gaps(store.db, user_id, subject_id, subject.get("level"))
        plan = roadmap.build(info, subject_id, profile["hours_per_week"], profile["target_date"])
        digest_ = roadmap.plan_hash(info, profile)
        run_id = store.create_run("roadmap", {"subject_id": subject_id})
        text, model = None, None
        tiers, _notes = tiers_for(store.db, user, "plan")
        for tier in tiers:
            try:
                out = mcq._call(tier, Budget(store, run_id, tier.settings), [{"role": "system", "content": roadmap.COACH_SYSTEM},
                                {"role": "user", "content": roadmap.coach_prompt(subject["name"], info, plan, profile)}], _CoachOut, f"roadmap_coach_{tier.name}")
                text = roadmap.clean_coach(out.text, info)
                if text:
                    model = tier.model
                    break
            except Exception:
                continue
        if not text:
            text, model = roadmap.rule_coach(info, plan), "rules (no model answered)"
        store.db.execute("UPDATE study_plans SET coach_status='done', coach_text=?, coach_model=?, coach_hash=?, coach_at=? WHERE subject_id=? AND user_id=?",
                         (text, model, digest_, time.time(), subject_id, user_id))
        store.set_state(run_id, RunState.COMPLETE)
    except Exception:
        store.db.execute("UPDATE study_plans SET coach_status='failed' WHERE subject_id=? AND user_id=?", (subject_id, user_id))
    finally:
        store.close()


class _SkillOut(BaseModel):
    skill: str
    importance: str = "required"
    quote: str = ""


class _SkillsOut(BaseModel):
    skills: list[_SkillOut]


def process_career(user_id: int, goal_id: int) -> None:
    """Read the skills out of a job description: the cloud first when the student allowed it, then the local model, then plain rules. Only skills whose quote is really in the text are kept."""
    from slice.budget import Budget
    from slice.records import RunState
    store = studydb.open_db()
    try:
        repo = Repo(store.db)
        user, goal = repo.get_user(user_id), career.get(store.db, user_id, goal_id)
        if user is None or goal is None:
            return
        run_id = store.create_run("career", {"goal_id": goal_id})
        skills, model = [], None
        tiers, _notes = tiers_for(store.db, user, "plan")
        for tier in tiers:
            try:
                out = mcq._call(tier, Budget(store, run_id, tier.settings), [{"role": "system", "content": career.SYSTEM},
                                {"role": "user", "content": career.prompt(goal["title"], goal["jd_text"])}], _SkillsOut, f"career_skills_{tier.name}")
                skills = career._valid([s.model_dump() for s in out.skills], goal["jd_text"])
                if skills:
                    model = tier.model
                    break
            except Exception:
                continue
        if not skills:
            skills, model = career.rule_skills(goal["jd_text"]), "rules (no model answered)"
        store.db.execute("UPDATE career_goals SET status=?, skills_json=?, model=?, updated_at=? WHERE id=? AND user_id=?",
                         ("done" if skills else "failed", json.dumps(skills), model, time.time(), goal_id, user_id))
        store.set_state(run_id, RunState.COMPLETE)
    except Exception:
        store.db.execute("UPDATE career_goals SET status='failed', updated_at=? WHERE id=? AND user_id=?", (time.time(), goal_id, user_id))
    finally:
        store.close()


def process_example(user_id: int, subject_id: int, iid: int) -> None:
    """Write a worked example from a topic's own passages: the cloud first when the student allowed it, then the local model, then the plain key-passages walk-through."""
    from slice.budget import Budget
    from slice.records import RunState
    store = studydb.open_db()
    try:
        repo = Repo(store.db)
        user, row = repo.get_user(user_id), tutor.get(store.db, user_id, subject_id, iid)
        if user is None or row is None:
            return
        texts = tutor.passages(store.db, subject_id, row["topic_id"])
        run_id = store.create_run("worked_example", {"subject_id": subject_id, "topic_id": row["topic_id"]})
        example, model = None, None
        tiers, _notes = tiers_for(store.db, user, "answer")
        for tier in tiers:
            try:
                out = mcq._call(tier, Budget(store, run_id, tier.settings), [{"role": "system", "content": tutor.SYSTEM},
                                {"role": "user", "content": tutor.prompt(row["topic"], row["level"], texts)}], tutor.ExampleOut, f"worked_example_{tier.name}")
                example = tutor.clean_example(out, texts)
                if example:
                    model = tier.model
                    break
            except Exception:
                continue
        if not example:
            example, model = tutor.key_passages(row["topic"], texts), "rules (no model answered)"
        now = time.time()
        store.db.execute("UPDATE interventions SET status=?, payload_json=?, model=?, updated_at=? WHERE id=? AND user_id=?",
                         ("done" if example else "failed", json.dumps(example or {}), model, now, iid, user_id))
        store.set_state(run_id, RunState.COMPLETE)
    except Exception:
        store.db.execute("UPDATE interventions SET status='failed', updated_at=? WHERE id=? AND user_id=?", (time.time(), iid, user_id))
    finally:
        store.close()


def submit_mcq(job_id: int, user_id: int) -> None:
    submit_task(process_mcq, job_id, user_id)
