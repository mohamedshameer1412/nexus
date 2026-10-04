"""Celery app: background question generation, answers and other model calls (studyhub.jobs), with Redis as the broker.

    celery -A nexus_api worker --pool=solo -c 1        # Windows needs the solo pool; one job at a time suits one local GPU

When no broker is reachable, studyhub.jobs runs the same functions on an in-process thread instead.
"""
from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexus_api.settings")

app = Celery("nexus")
app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0"),
    task_serializer="json", accept_content=["json"], task_acks_late=True, worker_prefetch_multiplier=1,
    task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER") == "1",
)


@app.task(name="nexus.run_job")
def run_job(name: str, *args) -> None:
    import django
    django.setup()                                         # loads .env and the database settings in the worker process
    from studyhub import jobs
    if name not in jobs.TASKS:                             # only the known jobs, never an arbitrary function name
        raise ValueError(f"unknown job {name!r}")
    getattr(jobs, name)(*args)
