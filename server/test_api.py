from __future__ import annotations
import unittest
from unittest.mock import patch
from server.leverage_api import Handler, origin_ok


class ApiTests(unittest.TestCase):
    def test_origin_allowlist(self):
        self.assertIsNotNone(origin_ok("https://newbiezzzzz.github.io"))
        self.assertIsNone(origin_ok("https://evil.example"))

    def test_money_not_exposed(self):
        self.assertEqual("127.0.0.1", __import__("server.leverage_api", fromlist=["HOST"]).HOST)
        self.assertEqual(8765, __import__("server.leverage_api", fromlist=["PORT"]).PORT)


if __name__ == "__main__":
    unittest.main()
