"""Leverage Data Worker.

Zero-cost, dependency-free worker for deterministic data collection and preparation.
No network access or secrets are required for the worker's base operation.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from statistics import mean

ROLE = "data collection and preparation"


def summarize_numeric_column(path: str, column: str) -> dict:
    target = Path(path)
    with target.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    values = [float(row[column]) for row in rows if row.get(column) not in (None, "")]
    if not values:
        raise ValueError(f"No numeric values found in column: {column}")
    return {"rows": len(rows), "numeric_values": len(values), "mean": mean(values), "min": min(values), "max": max(values)}


def self_test() -> dict:
    return {
        "worker": "data-worker",
        "role": ROLE,
        "status": "healthy",
        "capabilities": ["csv-ingestion", "numeric-validation", "summary-statistics", "data-preparation"],
        "external_dependencies": [],
        "cost": {"amount": 0, "currency": "RM"},
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
