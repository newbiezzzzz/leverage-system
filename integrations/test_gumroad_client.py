from __future__ import annotations

import os
import unittest

from integrations.gumroad_client import GumroadClient, GumroadError, self_test


class GumroadClientTests(unittest.TestCase):
    def test_self_test_does_not_require_network(self):
        old = os.environ.pop("GUMROAD_ACCESS_TOKEN", None)
        try:
            result = self_test()
            self.assertEqual(result["integration"], "gumroad")
            self.assertEqual(result["status"], "missing_secret")
            self.assertFalse(result["secret_persisted_in_repo"])
        finally:
            if old is not None:
                os.environ["GUMROAD_ACCESS_TOKEN"] = old

    def test_from_env_requires_secret(self):
        old = os.environ.pop("GUMROAD_ACCESS_TOKEN", None)
        try:
            with self.assertRaises(GumroadError):
                GumroadClient.from_env()
        finally:
            if old is not None:
                os.environ["GUMROAD_ACCESS_TOKEN"] = old

    def test_client_reads_secret_from_environment(self):
        old = os.environ.get("GUMROAD_ACCESS_TOKEN")
        os.environ["GUMROAD_ACCESS_TOKEN"] = "test-secret"
        try:
            client = GumroadClient.from_env()
            self.assertEqual(client.token, "test-secret")
        finally:
            if old is None:
                os.environ.pop("GUMROAD_ACCESS_TOKEN", None)
            else:
                os.environ["GUMROAD_ACCESS_TOKEN"] = old


if __name__ == "__main__":
    unittest.main()
