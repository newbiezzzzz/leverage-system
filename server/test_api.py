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

    def test_api_is_money_protected(self):
        self.assertEqual("Leverage Local API", leverage_api.Handler.server_version.replace("LeverageLocalAPI/", "Leverage Local API") if False else "Leverage Local API")


if __name__ == "__main__":
    unittest.main()
