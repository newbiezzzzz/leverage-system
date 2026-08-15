import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dispatcher


class DispatcherTests(unittest.TestCase):
    def test_valid_analysis_task_is_ready(self):
        workers = {
            "research-worker": {
                "status": "online",
                "projects": ["leverage"],
                "risk_level": "analysis-only",
            }
        }
        task = {
            "id": "T001",
            "project": "leverage",
            "worker": "research-worker",
            "description": "Analyze BTC event outcomes",
            "status": "queued",
        }
        self.assertEqual(dispatcher.validate_task(task, workers), [])

    def test_unknown_worker_is_rejected(self):
        task = {
            "id": "T002",
            "project": "leverage",
            "worker": "missing-worker",
            "description": "test",
            "status": "queued",
        }
        self.assertIn("unknown worker: missing-worker", dispatcher.validate_task(task, {}))

    def test_non_analysis_worker_is_blocked(self):
        workers = {
            "code-worker": {
                "status": "online",
                "projects": ["*"],
                "risk_level": "code-only",
            }
        }
        task = {
            "id": "T003",
            "project": "leverage",
            "worker": "code-worker",
            "description": "test",
            "status": "queued",
        }
        self.assertIn(
            "phase 1 dispatcher only routes analysis-safe workers",
            dispatcher.validate_task(task, workers),
        )

    def test_wrong_project_is_rejected(self):
        workers = {
            "research-worker": {
                "status": "online",
                "projects": ["leverage"],
                "risk_level": "analysis-only",
            }
        }
        task = {
            "id": "T004",
            "project": "other-project",
            "worker": "research-worker",
            "description": "test",
            "status": "queued",
        }
        self.assertIn(
            "worker not authorized for project: other-project",
            dispatcher.validate_task(task, workers),
        )


if __name__ == "__main__":
    unittest.main()
