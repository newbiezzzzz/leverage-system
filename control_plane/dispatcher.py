"""Leverage Control Plane task dispatcher.

Phase 1 is intentionally conservative: it validates queued tasks and routes
only to registered, analysis-safe workers. It does not execute arbitrary code,
place trades, spend money, or modify external systems.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKERS_FILE = ROOT / "workers.json"
TASKS_FILE = ROOT / "tasks.json"

ALLOWED_STATUSES = {"queued", "running", "blocked", "completed", "failed", "cancelled"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def worker_index():
    registry = load_json(WORKERS_FILE)
    return {worker["id"]: worker for worker in registry["workers"]}


def validate_task(task: dict, workers: dict) -> list[str]:
    errors = []
    required = {"id", "project", "worker", "description", "status"}
    missing = required - task.keys()
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
        return errors

    if task["status"] not in ALLOWED_STATUSES:
        errors.append(f"invalid status: {task['status']}")

    worker = workers.get(task["worker"])
    if worker is None:
        errors.append(f"unknown worker: {task['worker']}")
        return errors

    if worker["status"] != "online":
        errors.append(f"worker is not online: {task['worker']}")

    projects = worker.get("projects", [])
    if "*" not in projects and task["project"] not in projects:
        errors.append(f"worker not authorized for project: {task['project']}")

    if worker.get("risk_level") != "analysis-only":
        errors.append("phase 1 dispatcher only routes analysis-safe workers")

    return errors


def dispatch() -> int:
    workers = worker_index()
    task_store = load_json(TASKS_FILE)
    tasks = task_store.get("tasks", [])

    print("LEVERAGE CONTROL PLANE")
    print("=" * 60)
    print(f"Workers registered: {len(workers)}")
    print(f"Tasks queued: {sum(task.get('status') == 'queued' for task in tasks)}")

    failures = 0
    for task in tasks:
        if task.get("status") != "queued":
            continue

        errors = validate_task(task, workers)
        if errors:
            task["status"] = "blocked"
            task["validation_errors"] = errors
            failures += 1
            print(f"BLOCKED {task.get('id', '<unknown>')}: {'; '.join(errors)}")
            continue

        # Phase 1 only validates routing. Actual worker execution will be
        # connected in a later phase after the routing contract is tested.
        task["routing"] = {
            "worker": task["worker"],
            "validated": True,
            "execution": "not-enabled-in-phase-1",
        }
        print(f"READY   {task['id']} -> {task['worker']}")

    save_json(TASKS_FILE, task_store)
    print(f"Dispatcher completed with {failures} blocked task(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(dispatch())
