from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import buyer_pipeline_store


class BuyerPipelineStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "buyer_pipeline.json"
        self.patch = patch.object(buyer_pipeline_store, "REGISTRY_PATH", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_new_prospect_is_candidate(self):
        pipeline = buyer_pipeline_store.ensure_prospect("prospect-a")
        self.assertEqual(pipeline["stage"], "candidate")
        self.assertEqual(pipeline["customer_status"], "not_customer")

    def test_stage_requires_evidence_and_approval(self):
        with self.assertRaises(ValueError):
            buyer_pipeline_store.transition_pipeline("prospect-a", "validated")
        result = buyer_pipeline_store.transition_pipeline("prospect-a", "validated", evidence=["validation_evidence"])
        self.assertEqual(result["stage"], "validated")

    def test_contact_cannot_happen_without_approval(self):
        buyer_pipeline_store.transition_pipeline("prospect-a", "validated", evidence=["validation_evidence"])
        buyer_pipeline_store.transition_pipeline("prospect-a", "offer_draft")
        buyer_pipeline_store.transition_pipeline("prospect-a", "approved", approvals=["approved"])
        with self.assertRaises(ValueError):
            buyer_pipeline_store.transition_pipeline("prospect-a", "contacted")
        result = buyer_pipeline_store.transition_pipeline("prospect-a", "contacted", approvals=["contacted"])
        self.assertEqual(result["send_status"], "sent")

    def test_registry_persists(self):
        buyer_pipeline_store.ensure_prospect("prospect-a")
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIn("prospect-a", raw["pipelines"])


if __name__ == "__main__":
    unittest.main()
