import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import project_admin


class ProjectAdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.files = {
            "projects": root / "projects.json",
            "tasks": root / "tasks.json",
            "audit": root / "audit_log.json",
            "ledger": root / "financial_ledger.json",
        }
        self.files["projects"].write_text(json.dumps({"version": 1, "projects": [{"id": "retired", "name": "Retired", "status": "paused", "lifecycle_stage": "paused", "capital_deployed": 0}]}), encoding="utf-8")
        self.files["tasks"].write_text(json.dumps({"version": 1, "tasks": [{"id": "t1", "project": "retired", "status": "queued"}]}), encoding="utf-8")
        self.files["audit"].write_text(json.dumps({"version": 1, "events": []}), encoding="utf-8")
        self.files["ledger"].write_text(json.dumps({"version": 1, "entries": [], "payout_queue": []}), encoding="utf-8")
        self.patches = [
            patch.object(project_admin, "PROJECTS_FILE", self.files["projects"]),
            patch.object(project_admin, "TASKS_FILE", self.files["tasks"]),
            patch.object(project_admin, "AUDIT_FILE", self.files["audit"]),
            patch.object(project_admin, "LEDGER_FILE", self.files["ledger"]),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.tmp.cleanup()

    def test_remove_paused_project_preserves_audit_and_removes_work(self):
        result = project_admin.remove_project("retired")
        self.assertEqual(result["removed_tasks"], 1)
        projects = json.loads(self.files["projects"].read_text(encoding="utf-8"))
        tasks = json.loads(self.files["tasks"].read_text(encoding="utf-8"))
        audit = json.loads(self.files["audit"].read_text(encoding="utf-8"))
        self.assertEqual(projects["projects"], [])
        self.assertEqual(tasks["tasks"], [])
        self.assertEqual(audit["events"][-1]["event_type"], "project_removed")

    def test_remove_rejects_active_project(self):
        data = json.loads(self.files["projects"].read_text(encoding="utf-8"))
        data["projects"][0]["status"] = "operate"
        self.files["projects"].write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "paused or retired"):
            project_admin.remove_project("retired")


if __name__ == "__main__":
    unittest.main()
