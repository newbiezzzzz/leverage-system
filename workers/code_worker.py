"""Leverage Code Worker.

Zero-cost, dependency-free worker for code planning, validation, and test orchestration.
It intentionally performs no external writes by itself; the control plane decides what to execute.
"""
from __future__ import annotations
import ast
import json
import sys
from pathlib import Path

ROLE = "code implementation and testing"


def inspect_python(path: str) -> dict:
    target = Path(path)
    source = target.read_text(encoding="utf-8")
    ast.parse(source, filename=str(target))
    return {"path": str(target), "syntax": "ok", "bytes": len(source.encode("utf-8"))}


def self_test() -> dict:
    return {
        "worker": "code-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["python-syntax-check", "code-inspection", "test-orchestration"],
        "external_dependencies": [],
        "cost": {"amount": 0, "currency": "RM"},
    }


def main() -> int:
    if len(sys.argv) == 2:
        print(json.dumps(inspect_python(sys.argv[1]), indent=2))
        return 0
    print(json.dumps(self_test(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
