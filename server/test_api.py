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
        self.assertEqual("LeverageLocalAPI/1.5", leverage_api.Handler.server_version)

    def test_company_os_readiness_is_exposed(self):
        result = leverage_api.company_os_readiness()
        self.assertIn("ready", result)
        self.assertIn("checks", result)
        self.assertTrue(result["ready"], result)

    def test_projects_gate_and_health_routes_exist(self):
        self.assertTrue(callable(leverage_api.project_gate_report))
        self.assertTrue(callable(leverage_api.list_projects))
        self.assertTrue(callable(leverage_api.company_health))


if __name__ == "__main__":
    unittest.main()
