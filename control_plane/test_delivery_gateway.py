"""Tests for the reusable customer delivery gateway."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import delivery_gateway


class DeliveryGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "customer_orders.json"
        self.path.write_text(json.dumps({"version": 1, "orders": []}), encoding="utf-8")
        self.patch = patch.object(delivery_gateway, "ORDERS_FILE", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_order_lifecycle(self):
        order = delivery_gateway.create_order("customer-1", "Excel cleanup", "service-test")
        self.assertEqual(order["status"], "awaiting_payment")
        order = delivery_gateway.update_payment(order["id"], "test", "payment-123")
        self.assertEqual(order["status"], "paid")
        order = delivery_gateway.start_processing(order["id"])
        self.assertEqual(order["status"], "processing")
        order = delivery_gateway.attach_output(order["id"], {"name": "result.xlsx", "kind": "file", "locator": "local://result.xlsx"})
        self.assertEqual(order["status"], "ready")
        order = delivery_gateway.mark_delivered(order["id"], "delivery-123")
        self.assertEqual(order["status"], "delivered")

    def test_processing_requires_verified_payment(self):
        order = delivery_gateway.create_order("customer-1", "Excel cleanup", "service-test")
        with self.assertRaisesRegex(ValueError, "paid"):
            delivery_gateway.start_processing(order["id"])

    def test_output_requires_manifest_fields(self):
        order = delivery_gateway.create_order("customer-1", "Excel cleanup", "service-test")
        delivery_gateway.update_payment(order["id"], "test", "payment-123")
        delivery_gateway.start_processing(order["id"])
        with self.assertRaisesRegex(ValueError, "artifact requires"):
            delivery_gateway.attach_output(order["id"], {"name": "result.xlsx"})


if __name__ == "__main__":
    unittest.main()
