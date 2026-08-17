import unittest

import dispatcher


PROJECTS = {
    "leverage": {"id": "leverage", "status": "operate"},
    "other-project": {"id": "other-project", "status": "operate"},
}


class DispatcherTests(unittest.TestCase):
    def test_valid_analysis_task_is_ready(self):
        workers = {
            "research-worker": {
                "status": "online",
                "projects": ["leverage"],
                "risk_level": "analysis-only",
                "capabilities": ["research", "report"],
            }
        }
        task = {
            "id": "T001",
            "project": "leverage",
            "worker": "research-worker",
            "description": "Analyze BTC event outcomes",
            "action": "research",
            "status": "queued",
        }
        self.assertEqual(dispatcher.validate_task(task, workers, PROJECTS), [])

    def test_unknown_worker_is_rejected(self):
        task = {
            "id": "T002",
            "project": "leverage",
            "worker": "missing-worker",
            "description": "test",
            "status": "queued",
        }
        self.assertIn("unknown worker: missing-worker", dispatcher.validate_task(task, {}, PROJECTS))

    def test_non_capability_action_is_blocked(self):
        workers = {
            "code-worker": {
                "status": "online",
                "projects": ["*"],
                "risk_level": "code-only",
                "capabilities": ["build", "test"],
            }
        }
        task = {
            "id": "T003",
            "project": "leverage",
            "worker": "code-worker",
            "description": "test",
            "action": "move_money",
            "status": "queued",
        }
        errors = dispatcher.validate_task(task, workers, PROJECTS)
        self.assertTrue(any("owner approval required" in error for error in errors))
        self.assertTrue(any("live money movement is disabled" in error for error in errors))

    def test_wrong_project_is_rejected(self):
        workers = {
            "research-worker": {
                "status": "online",
                "projects": ["leverage"],
                "risk_level": "analysis-only",
                "capabilities": ["research"],
            }
        }
        task = {
            "id": "T004",
            "project": "other-project",
            "worker": "research-worker",
            "description": "test",
            "action": "research",
            "status": "queued",
        }
        errors = dispatcher.validate_task(task, workers, PROJECTS)
        self.assertIn("worker not authorized for project: other-project", errors)


if __name__ == "__main__":
    unittest.main()
