"""Minimal provider-independent worker runtime for Leverage.

Routes approved tasks to deterministic local worker functions first. External
AI/model providers are optional adapters and may be unavailable; task results
must never depend on a single ChatGPT quota. No network calls are performed by
this base runtime.
"""
from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class WorkerResult:
    task_id: str
    worker: str
    status: str
    executor: str
    started_at: float
    finished_at: float
    result: dict[str, Any]
    error: str | None = None

class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: dict[str, list[tuple[str, Callable[..., dict[str, Any]]]]] = {}

    def register(self, worker: str, executor: str, fn: Callable[..., dict[str, Any]]) -> None:
        self._executors.setdefault(worker, []).append((executor, fn))

    def available(self, worker: str) -> list[str]:
        return [name for name, _ in self._executors.get(worker, [])]

    def run(self, worker: str, task: dict[str, Any]) -> WorkerResult:
        candidates = self._executors.get(worker, [])
        if not candidates:
            raise RuntimeError(f"no executor available for {worker}")
        last_error = None
        for executor_name, fn in candidates:
            started = time.time()
            try:
                result = fn(task)
                return WorkerResult(task.get("id", str(uuid.uuid4())), worker, "completed", executor_name, started, time.time(), result)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
        return WorkerResult(task.get("id", str(uuid.uuid4())), worker, "failed", candidates[-1][0], started, time.time(), {}, last_error)


def _data_summary(task: dict[str, Any]) -> dict[str, Any]:
    try:
        from .data_worker import summarize_numeric_column
    except ImportError:
        from data_worker import summarize_numeric_column
    return {"type": "data_summary", **summarize_numeric_column(task["input_path"], task["column"])}


def _code_inspect(task: dict[str, Any]) -> dict[str, Any]:
    try:
        from .code_worker import inspect_python
    except ImportError:
        from code_worker import inspect_python
    return {"type": "python_inspection", **inspect_python(task["input_path"])}


def _build_product(task: dict[str, Any]) -> dict[str, Any]:
    try:
        from .digital_product_worker import build_quote_workbook, build_job_log_csv
    except ImportError:
        from digital_product_worker import build_quote_workbook, build_job_log_csv
    output_dir = Path(task.get("output_dir", "."))
    output_dir.mkdir(parents=True, exist_ok=True)
    quote_path = output_dir / task.get("quote_filename", "engineering_quote_toolkit.xlsx")
    log_path = output_dir / task.get("job_log_filename", "job_log_template.csv")
    quote = build_quote_workbook(str(quote_path))
    job_log = build_job_log_csv(str(log_path), int(task.get("job_log_rows", 20)))
    return {"type": "digital_product", "quote": quote, "job_log": job_log}


def build_default_registry() -> ExecutorRegistry:
    registry = ExecutorRegistry()
    registry.register("data-worker", "local-python", _data_summary)
    registry.register("code-worker", "local-python", _code_inspect)
    registry.register("digital-product-worker", "local-python", _build_product)
    return registry


def execute(worker: str, task: dict[str, Any], registry: ExecutorRegistry | None = None) -> dict[str, Any]:
    result = (registry or build_default_registry()).run(worker, task)
    return asdict(result)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Run an approved Leverage worker task without requiring ChatGPT.")
    parser.add_argument("worker")
    parser.add_argument("task_json")
    args = parser.parse_args()
    task = json.loads(args.task_json)
    print(json.dumps(execute(args.worker, task), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
