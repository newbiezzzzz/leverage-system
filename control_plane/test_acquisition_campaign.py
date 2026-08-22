from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from control_plane import acquisition_campaign


class AcquisitionCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.queue = root / "acquisition_queue.json"
        self.prospects = root / "prospects.json"
        self.queue.write_text(json.dumps({"version": 2, "items": []}), encoding="utf-8")
        self.prospects.write_text(json.dumps({"version": 1, "prospects": [
            {"id": "p-high", "name": "High Fit Workshop", "fit": 90, "category": "fabrication", "location": "Selangor", "candidate_workflow": "quote follow-up", "public_contact_available": True},
            {"id": "p-low", "name": "Low Fit Business", "fit": 50, "category": "other", "location": "Selangor", "candidate_workflow": "unknown", "public_contact_available": True},
        ]}), encoding="utf-8")
        self.qpatch = patch.object(acquisition_campaign, "QUEUE_PATH", self.queue)
        self.ppatch = patch.object(acquisition_campaign, "PROSPECTS_PATH", self.prospects)
        self.qpatch.start(); self.ppatch.start()

    def tearDown(self):
        self.ppatch.stop(); self.qpatch.stop(); self.tmp.cleanup()

    def test_daily_queue_creates_concrete_prospect_validation_work(self):
        result = acquisition_campaign.generate_daily_queue(datetime(2026, 8, 22, tzinfo=timezone.utc))
        self.assertGreater(result["created"], 0)
        self.assertEqual(result["prospects_created"], 2)
        data = json.loads(self.queue.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 3)
        self.assertEqual(data["prospect_validation"][0]["prospect_id"], "p-high")
        self.assertEqual(data["prospect_validation"][0]["status"], "research_required")

    def test_daily_queue_is_idempotent(self):
        now = datetime(2026, 8, 22, tzinfo=timezone.utc)
        first = acquisition_campaign.generate_daily_queue(now)
        second = acquisition_campaign.generate_daily_queue(now)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["prospects_created"], 0)
        self.assertEqual(first["queue_size"], second["queue_size"])

    def test_direct_outreach_is_tied_to_candidate_not_customer(self):
        result = acquisition_campaign.generate_daily_queue(datetime(2026, 8, 22, tzinfo=timezone.utc))
        direct = next(item for item in result["queue"] if item["channel"] == "direct_outreach")
        self.assertEqual(direct["prospect_id"], "p-high")
        self.assertEqual(direct["prospect_status"], "research_required")
        self.assertEqual(direct["status"], "draft")


if __name__ == "__main__":
    unittest.main()
