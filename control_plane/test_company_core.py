"""Tests for company/project lifecycle validation."""
import unittest

from company_core import Project, approval_required, validate_project


class CompanyCoreTests(unittest.TestCase):
    def test_project_validation_accepts_intake(self):
        project = Project(id="demo", name="Demo", type="saas")
        self.assertEqual(validate_project(project), [])

    def test_project_validation_rejects_invalid_stage(self):
        project = Project(id="demo", name="Demo", lifecycle_stage="unknown", status="intake")
        self.assertIn("invalid lifecycle stage: unknown", validate_project(project))

    def test_restricted_actions_require_approval(self):
        self.assertTrue(approval_required("move_money"))
        self.assertFalse(approval_required("research"))


if __name__ == "__main__":
    unittest.main()
