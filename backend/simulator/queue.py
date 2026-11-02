"""Causal view of satellite tasks; future and expired tasks stay out of policies."""

from backend.contracts import Task
from .energy import finite_number


def visible_tasks(tasks: list[Task], now_s: float) -> list[Task]:
    now = finite_number(now_s, "now_s")
    return [task.model_copy(deep=True) for task in sorted(tasks, key=lambda task: (task.arrival_s, task.task_id))
            if task.arrival_s <= now <= task.deadline_s and task.remaining_bytes > 0]
