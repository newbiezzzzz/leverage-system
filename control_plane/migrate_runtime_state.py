"""Reconcile mutable runtime project state with the tracked Company OS registry.

The runtime directory is intentionally not source-controlled. This migration is
used after a structural project-model change so an older local runtime cannot
silently reintroduce retired projects into the Dashboard/API.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACKED = ROOT / "projects.json"
RUNTIME_DIR = ROOT / "runtime"
RUNTIME = RUNTIME_DIR / "projects.json"
BACKUP_DIR = RUNTIME_DIR / "backups"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def project_ids(data: dict) -> set[str]:
    return {str(item.get("id")) for item in data.get("projects", []) if item.get("id")}


def main() -> int:
    tracked = load(TRACKED)
    tracked_ids = project_ids(tracked)

    if not RUNTIME.exists():
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TRACKED, RUNTIME)
        print("RUNTIME PROJECT STATE: initialized from tracked registry")
        return 0

    runtime = load(RUNTIME)
    runtime_ids = project_ids(runtime)

    if runtime_ids == tracked_ids:
        print("RUNTIME PROJECT STATE: already aligned")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUP_DIR / f"projects-{stamp}.json"
    shutil.copy2(RUNTIME, backup)
    shutil.copy2(TRACKED, RUNTIME)

    print("RUNTIME PROJECT STATE: migrated")
    print(f"  previous: {sorted(runtime_ids)}")
    print(f"  current : {sorted(tracked_ids)}")
    print(f"  backup  : {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
