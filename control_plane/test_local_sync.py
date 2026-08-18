"""Tests for sanitized local-state publication."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from control_plane import local_sync


class LocalSyncTests(unittest.TestCase):
    def test_snapshot_is_sanitized(self):
        with patch("control_plane.local_sync.company_os_readiness", return_value={
            "ready": True,
            "status": "ready",
            "release_gate": "Build next income project",
            "checks": [{"name": "safety", "status": "pass", "detail": "secret detail"}],
        }), patch("control_plane.local_sync.company_health", return_value={"status": "green", "summary": {"total": 0}}), patch(
            "control_plane.local_sync.system_snapshot",
            return_value={
                "projects": 0,
                "active_projects": 0,
                "tasks": {"queued": 0, "running": 0, "completed": 0, "failed": 0, "blocked": 0},
                "live_money_movement": False,
                "revenue_entries": 3,
                "payouts_prepared": 2,
            },
        ), patch("control_plane.local_sync.list_projects", return_value=[]):
            snapshot = local_sync.build_snapshot()

        self.assertTrue(snapshot["readiness"]["ready"])
        self.assertNotIn("detail", snapshot["readiness"]["checks"][0])
        self.assertNotIn("revenue_entries", snapshot["company"])
        self.assertNotIn("payouts_prepared", snapshot["company"])
        self.assertEqual(snapshot["privacy"], "sanitized-no-finance-no-audit")


if __name__ == "__main__":
    unittest.main()
