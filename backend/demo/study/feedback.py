"""Real-tester feedback, stored the way everything else in a run is stored.

Feedback is a `feedback` row in the append-only `versions` table, so it is durable,
timestamped, attributed (`tester:<name>`), replayable, and appears in the execution trace
with no new table and no new mechanism. Several testers can each add a row to one run.

Two things are deliberate:

  * The server, not the tester, records WHICH draft they were shown and what state the run
    was in. Feedback on "the study pack" means nothing unless you know which one.
  * Feedback never moves a run. It is not a review decision: it cannot approve, reject or
    resume anything. Only the human-review step does that.

Nothing here invents feedback. There is no fixture, no default, no sample. If nobody has
submitted any, every function returns an empty list.
"""
from __future__ import annotations

from pydantic import ValidationError

from slice.store import Store

from .schema import Feedback


class FeedbackError(ValueError):
    """The feedback was not recorded because it was not valid. The message says why."""


def _explain(e: ValidationError) -> str:
    parts = []
    for err in e.errors()[:3]:
        where = ".".join(str(x) for x in err["loc"]) or "feedback"
        parts.append(f"{where}: {err['msg']}")
    return "; ".join(parts)


def submit(store: Store, run_id: str, raw: object) -> dict:
    """Validate `raw` and append it to the run. Returns the stored record.

    Raises KeyError for a run that does not exist (from the store) and FeedbackError for
    input that is not valid feedback. Nothing is written in either case."""
    state = store.get_state(run_id)                       # KeyError: no such run
    try:
        fb = Feedback.model_validate(raw)
    except ValidationError as e:
        raise FeedbackError(_explain(e)) from e
    payload = {**fb.model_dump(),
               "draft": len(store.history(run_id, "draft")),   # what they were shown
               "run_state": state.value}                       # ... and where the run was
    seq = store.append(run_id, "feedback", payload, produced_by=f"tester:{fb.tester}")
    return {"run_id": run_id, "seq": seq, **payload}


def for_run(store: Store, run_id: str) -> list[dict]:
    """Every piece of feedback on one run, oldest first, each with its time."""
    return [{"run_id": run_id, "seq": v.seq, "submitted_at": v.created_at, **v.payload}
            for v in store.history(run_id, "feedback")]


def everything(store: Store) -> list[dict]:
    """All feedback across all runs, with the run's mode and state - what a person
    collecting test results wants in one place."""
    out: list[dict] = []
    for run in reversed(store.list_runs(limit=100_000)):          # oldest run first
        for item in for_run(store, run["id"]):
            out.append({**item, "run_mode": store.meta(run["id"]).get("mode"),
                        "run_state_now": run["state"]})
    return out
