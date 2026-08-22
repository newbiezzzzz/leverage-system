"""Tests for company/project lifecycle validation."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane.company_core import Project, approval_required, can_change_stage, change_stage, validate_project


class CompanyCoreTests(unittest.TestCase):
    def test_project_validation_accepts_intake(self):
        project = Project(id="demo", name="Demo", type="saas")
        self.assertEqual(validate_project(project), [])

    def test_project_validation_accepts_active_project_at_acquire_gate(self):
        project = Project(id="demo", name="Demo", status="active", lifecycle_stage="acquire")
        self.assertEqual(validate_project(project), [])

    def test_project_validation_rejects_invalid_stage(self):
        project = Project(id="demo", name="Demo", lifecycle_stage="unknown", status="active")
        self.assertIn("invalid lifecycle stage: unknown", validate_project(project))

    def test_project_validation_rejects_invalid_operational_status(self):
        project = Project(id="demo", name="Demo", lifecycle_stage="validation", status="unknown")
        self.assertIn("invalid operational status: unknown", validate_project(project))

    def test_restricted_actions_require_approval(self):
        self.assertTrue(approval_required("move_money"))
        self.assertFalse(approval_required("research"))

    def test_lifecycle_transition_map_blocks_gate_skipping(self):
        self.assertTrue(can_change_stage("intake", "validation"))
        self.assertFalse(can_change_stage("intake", "operate"))
        self.assertFalse(can_change_stage("build", "revenue"))
        self.assertTrue(can_change_stage("launch", "acquire"))
        self.assertTrue(can_change_stage("acquire", "operate"))
        self.assertTrue(can_change_stage("operate", "revenue"))

    def test_change_stage_preserves_operational_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "projects.json"
            path.write_text(json.dumps({
                "version": 1,
                "projects": [{
                    "id": "demo", "name": "Demo", "type": "general",
                    "status": "active", "lifecycle_stage": "intake",
                    "revenue_status": "none", "capital_deployed": 0,
                    "currency": "MYR", "owner_approval_required_for_spend": True,
                    "description": "", "next_gate": ""
                }]
            }), encoding="utf-8")
            with patch("control_plane.company_core.PROJECTS_FILE", path):
                with self.assertRaisesRegex(ValueError, "invalid lifecycle transition: intake -> operate"):
                    change_stage("demo", "operate", "bad jump")
                updated = change_stage("demo", "validation", "Validate the opportunity")
                self.assertEqual(updated.status, "active")
                self.assertEqual(updated.lifecycle_stage, "validation")


if __name__ == "__main__":
    unittest.main()
