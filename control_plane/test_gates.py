import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import gates


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.projects = root / "projects.json"
        self.tasks = root / "tasks.json"
        self.ledger = root / "financial_ledger.json"
        self.gates_file = root / "gates.json"
        self.projects.write_text(json.dumps({"version": 1, "projects": [{"id": "demo", "name": "Demo", "description": "demo", "lifecycle_stage": "validation", "status": "validation"}]}), encoding="utf-8")
        self.tasks.write_text(json.dumps({"version": 2, "tasks": [
            {"id": "r", "project": "demo", "action": "research", "status": "completed"},
            {"id": "d", "project": "demo", "action": "validate", "status": "queued"},
            {"id": "b", "project": "demo", "action": "build", "status": "queued"},
            {"id": "t", "project": "demo", "action": "test", "status": "queued"},
        ]}), encoding="utf-8")
        self.ledger.write_text(json.dumps({"version": 1, "entries": [], "payout_queue": []}), encoding="utf-8")
        self.gates_file.write_text(json.dumps({"version": 1, "decisions": []}), encoding="utf-8")
        self.patches = [
            patch.object(gates, "PROJECTS_FILE", self.projects),
            patch.object(gates, "TASKS_FILE", self.tasks),
            patch.object(gates, "LEDGER_FILE", self.ledger),
            patch.object(gates, "GATES_FILE", self.gates_file),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_validation_waits_for_data_validation(self):
        result = gates.evaluate_gate("demo", "validation")
        self.assertEqual(result["status"], "waiting")
        self.assertIn("validate task is not completed", result["reasons"])

    def test_launch_requires_build_and_test(self):
        result = gates.evaluate_gate("demo", "launch")
        self.assertEqual(result["status"], "waiting")
        self.assertIn("build task is not completed", result["reasons"])

    def test_owner_decision_is_recorded(self):
        result = gates.save_gate_decision("demo", "launch", "hold", "Need more customer evidence")
        self.assertEqual(result["decision"], "hold")
        saved = json.loads(self.gates_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["decisions"][0]["project_id"], "demo")


if __name__ == "__main__":
    unittest.main()
