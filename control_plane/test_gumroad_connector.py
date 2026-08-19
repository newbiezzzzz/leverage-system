from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from control_plane.gumroad_connector import health_check, list_products, list_sales


class GumroadConnectorTests(unittest.TestCase):
    def test_requires_local_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                health_check()

    @patch("control_plane.gumroad_connector._get")
    def test_health_is_non_secret(self, get):
        get.return_value = {"user": {"id": "user-1", "email": "owner@example.com"}}
        with patch.dict(os.environ, {"GUMROAD_ACCESS_TOKEN": "secret"}, clear=True):
            result = health_check()
        self.assertEqual(result["status"], "healthy")
        self.assertTrue(result["account_id_present"])
        self.assertTrue(result["email_present"])
        self.assertNotIn("secret", str(result))
        self.assertTrue(result["read_only"])
        self.assertFalse(result["money_movement"])

    @patch("control_plane.gumroad_connector._get")
    def test_product_and_sales_readers(self, get):
        get.side_effect = [{"products": [{"id": "p1"}]}, {"sales": [{"id": "s1"}]}]
        with patch.dict(os.environ, {"GUMROAD_ACCESS_TOKEN": "secret"}, clear=True):
            self.assertEqual(list_products(), [{"id": "p1"}])
            self.assertEqual(list_sales(), [{"id": "s1"}])


if __name__ == "__main__":
    unittest.main()
