import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane.company_core import Project
from control_plane import company_ops


class CompanyOpsEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.files = {
            "projects": root / "projects.json",
            "tasks": root / "tasks.json",
            "approvals": root / "approvals.json",
            "audit": root / "audit_log.json",
            "ledger": root / "financial_ledger.json",
        }
        self.files["projects"].write_text(json.dumps({"version": 1, "projects": []}), encoding="utf-8")
        self.files["tasks"].write_text(json.dumps({"version": 4, "tasks": []}), encoding="utf-8")
        self.files["approvals"].write_text(json.dumps({"version": 1, "approvals": []}), encoding="utf-8")
        self.files["audit"].write_text(json.dumps({"version": 1, "events": []}), encoding="utf-8")
        self.files["ledger"].write_text(json.dumps({"version": 1, "entries": [], "payout_queue": [], "policy": {"live_money_movement": False}}), encoding="utf-8")
        self.patches = [
            patch.object(company_ops, "PROJECTS_FILE", self.files["projects"]),
            patch.object(company_ops, "TASKS_FILE", self.files["tasks"]),
            patch.object(company_ops, "APPROVALS_FILE", self.files["approvals"]),
            patch.object(company_ops, "AUDIT_FILE", self.files["audit"]),
            patch.object(company_ops, "LEDGER_FILE", self.files["ledger"]),
        ]
        import control_plane.company_core as cc
        import control_plane.finance_core as fc
        self.patches += [
            patch.object(cc, "PROJECTS_FILE", self.files["projects"]),
            patch.object(cc, "APPROVALS_FILE", self.files["approvals"]),
            patch.object(fc, "LEDGER_FILE", self.files["ledger"]),
            patch.object(fc, "APPROVALS_FILE", self.files["approvals"]),
        ]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def test_project_plan_is_idempotent(self):
        project = company_ops.intake_project(Project(id="demo", name="Demo Income Project", type="saas"))
        first = company_ops.create_project_plan(project.id)
        second = company_ops.create_project_plan(project.id)
        self.assertEqual([task["id"] for task in first], [task["id"] for task in second])
        stored = json.loads(self.files["tasks"].read_text())["tasks"]
        self.assertEqual(len(stored), 8)
        audit = json.loads(self.files["audit"].read_text())
        self.assertIn("project_plan_reused", [e["event_type"] for e in audit["events"]])

    def test_task_completion_advances_project_gates(self):
        project = company_ops.intake_project(Project(id="demo", name="Demo Income Project", type="saas"))
        tasks = company_ops.create_project_plan(project.id)
        by_action = {task["action"]: task for task in tasks}
        for action in ["plan", "research", "validate"]:
            task = by_action[action]
            company_ops.claim_task(task["id"], task["worker"])
            company_ops.complete_task(task["id"], f"{action} complete", task["worker"])
        stored_project = json.loads(self.files["projects"].read_text())["projects"][0]
        self.assertEqual(stored_project["lifecycle_stage"], "build")

        for action in ["build", "test"]:
            task = by_action[action]
            company_ops.claim_task(task["id"], task["worker"])
            company_ops.complete_task(task["id"], f"{action} complete", task["worker"])
        stored_project = json.loads(self.files["projects"].read_text())["projects"][0]
        self.assertEqual(stored_project["lifecycle_stage"], "launch")

    def test_dependency_aware_project_to_payout_ready_flow(self):
        project = company_ops.intake_project(Project(id="demo", name="Demo Income Project", type="saas"))
        tasks = company_ops.create_project_plan(project.id)
        self.assertEqual(len(tasks), 8)
        by_action = {task["action"]: task for task in tasks}
        self.assertEqual(by_action["build"]["depends_on"], [by_action["research"]["id"], by_action["validate"]["id"]])
        self.assertEqual(by_action["test"]["depends_on"], [by_action["build"]["id"]])
        self.assertEqual(by_action["verify"]["depends_on"], [by_action["test"]["id"]])
        self.assertEqual(by_action["reconcile"]["depends_on"], [by_action["verify"]["id"], by_action["intake"]["id"]])

        with self.assertRaisesRegex(ValueError, "dependencies incomplete"):
            company_ops.claim_task(by_action["build"]["id"], "code-worker")

        execution_order = ["plan", "research", "validate", "build", "test", "verify", "intake", "reconcile"]
        for action in execution_order:
            task = by_action[action]
            claimed = company_ops.claim_task(task["id"], task["worker"])
            self.assertEqual(claimed["status"], "running")
            company_ops.complete_task(task["id"], f"{action} complete", task["worker"])

        summary = company_ops.project_task_summary(project.id)
        self.assertEqual(summary["completed"], 8)
        self.assertEqual(summary["progress"], 100.0)
        self.assertEqual(summary["waiting_on_dependencies"], 0)

        revenue = company_ops.record_revenue(project.id, 100.0, "demo sale", "test-sale-001")
        self.assertTrue(revenue["verified"])
        payout = company_ops.prepare_payout(project.id, 50.0, "owner-destination", "owner profit share")
        self.assertEqual(payout["status"], "prepared")
        self.assertEqual(json.loads(self.files["projects"].read_text())["projects"][0]["status"], "payout-ready")

        approval = company_ops.approve_payout(payout["id"])
        self.assertEqual(approval["type"], "owner_payout")
        ledger = json.loads(self.files["ledger"].read_text())
        request = ledger["payout_queue"][0]
        self.assertEqual(request["status"], "approved")
        self.assertFalse(ledger["policy"]["live_money_movement"])

        audit = json.loads(self.files["audit"].read_text())
        event_types = [e["event_type"] for e in audit["events"]]
        self.assertIn("project_created", event_types)
        self.assertIn("project_plan_created", event_types)
        self.assertIn("project_stage_advanced", event_types)
        self.assertIn("revenue_recorded", event_types)
        self.assertIn("payout_prepared", event_types)
        self.assertIn("owner_payout_approved", event_types)


if __name__ == "__main__":
    unittest.main()
