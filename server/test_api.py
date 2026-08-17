from __future__ import annotations
import unittest

from server import leverage_api


class ApiTests(unittest.TestCase):
    def test_local_service_is_bound_to_loopback(self):
        self.assertEqual("127.0.0.1", leverage_api.HOST)
        self.assertEqual(8765, leverage_api.PORT)

    def test_dashboard_root_is_local_command_center(self):
        target = leverage_api.safe_dashboard_path("/")
        self.assertIsNotNone(target)
        self.assertEqual("command.html", target.name)

    def test_money_protection_is_explicit(self):
        self.assertEqual("LeverageLocalAPI/1.3", leverage_api.Handler.server_version)

    def test_projects_and_gate_routes_exist(self):
        self.assertTrue(callable(leverage_api.project_gate_report))
        self.assertTrue(callable(leverage_api.list_projects))


if __name__ == "__main__":
    unittest.main()
