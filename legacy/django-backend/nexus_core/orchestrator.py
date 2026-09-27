"""
nexus_core/orchestrator.py
NEXUS Agent Orchestrator.
Called immediately after a quiz session is submitted.
Fires all 5 agent Celery tasks in parallel and returns their task IDs.
The frontend listens via WebSocket for each task ID to complete.
"""
import importlib
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Map of agent name -> (module path, task attribute name)
AGENT_TASKS = {
    "analytics":  ("analytics.tasks", "update_digital_twin"),
    "evaluator":  ("evaluator_agent.tasks", "evaluate_session"),
    "planner":    ("planner_agent.tasks", "generate_study_plan"),
    "tutor":      ("tutor_agent.tasks", "prepare_tutor_session"),
}


def fire_all_agents(session_id: str, user_id: str) -> Dict[str, str]:
    """
    Fire all NEXUS agents in parallel (non-blocking Celery .delay()).
    Returns: {agent_name: celery_task_id} for WebSocket tracking.

    Call this immediately after QuizSession.status = 'completed'.

    Tasks are dispatched by importing and calling the task object directly
    (task.delay(...)), not via current_app.signature(path).delay(). The
    signature route resolves through Celery's remote-dispatch path
    (effectively send_task by name), which always publishes to the broker —
    it does NOT take the task_always_eager in-process shortcut the way a
    directly-bound task's apply_async does. That distinction only matters
    without a running broker/worker (e.g. this dev setup); against a real
    Redis + worker pool both routes behave identically.
    """
    task_ids = {}
    errors = []

    for agent_name, (module_path, attr) in AGENT_TASKS.items():
        try:
            task = getattr(importlib.import_module(module_path), attr)
            # analytics + evaluator take session_id
            if agent_name in ("analytics", "evaluator"):
                result = task.delay(session_id)
            # planner + tutor take user_id
            else:
                result = task.delay(user_id)

            task_ids[agent_name] = result.id
            logger.info(f"[Orchestrator] Fired {agent_name} agent: task_id={result.id}")

        except Exception as e:
            logger.error(f"[Orchestrator] Failed to fire {agent_name}: {e}")
            errors.append({"agent": agent_name, "error": str(e)})

    return {
        "session_id": session_id,
        "user_id": user_id,
        "agent_tasks": task_ids,
        "errors": errors,
    }
