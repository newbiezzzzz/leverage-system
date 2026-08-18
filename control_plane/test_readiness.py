"""Tests for the Company OS release gate."""
from __future__ import annotations

import unittest
from control_plane.readiness import company_os_readiness


class ReadinessTests(unittest.TestCase):
    def test_company_os_is_ready_under_repository_baseline(self):
        result = company_os_readiness()
        self.assertTrue(result["ready"], result)
        self.assertEqual(result["status"], "ready")
        self.assertIn("Build next income project", result["release_gate"])
        self.assertTrue(all(check["status"] == "pass" for check in result["checks"]))

    def test_readiness_has_explicit_financial_boundary_check(self):
        result = company_os_readiness()
        names = {check["name"] for check in result["checks"]}
        self.assertIn("financial_boundary", names)
        self.assertIn("resource_safety", names)
        self.assertIn("worker_fleet", names)


if __name__ == "__main__":
    unittest.main()
