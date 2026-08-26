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
        self.prospects.write_text(json.dumps({"version": 2, "prospects": [
            {"id": "p-high", "name": "High Fit Workshop", "fit": 90, "category": "fabrication", "location": "Selangor", "candidate_workflow": "quote follow-up", "public_contact_available": True, "validation_status": "fresh_candidate", "why_fit": "observable quote workflow", "evidence": ["public quote page"]},
            {"id": "p-low", "name": "Low Fit Business", "fit": 50, "category": "other", "location": "Selangor", "candidate_workflow": "unknown", "public_contact_available": True, "validation_status": "unvalidated"},
        ]}), encoding="utf-8")
        self.qpatch = patch.object(acquisition_campaign, "QUEUE_PATH", self.queue)
        self.ppatch = patch.object(acquisition_campaign, "PROSPECTS_PATH", self.prospects)
        self.qpatch.start(); self.ppatch.start()

    def tearDown(self):
        self.ppatch.stop(); self.qpatch.stop(); self.tmp.cleanup()

    def test_public_acquisition_surface_is_live_cloudflare_site(self):
        self.assertEqual("https://leverage-tools.pages.dev/", acquisition_campaign.LANDING_URL)
        self.assertTrue(acquisition_campaign.tracked_url("linkedin", "2026-08-22").startswith(acquisition_campaign.LANDING_URL + "?"))

    def test_legacy_queued_destination_is_repaired(self):
        old = "https://newbiezzzzz.github.io/leverage-system/p001/?utm_source=seo_content"
        self.queue.write_text(json.dumps({
            "version": 3,
            "items": [{"key": "legacy", "destination": old, "call_to_action": old}],
            "prospect_validation": [],
            "tracking": {"landing_url": "https://newbiezzzzz.github.io/leverage-system/p001/"},
        }), encoding="utf-8")
        data = acquisition_campaign._load()
        self.assertEqual("https://leverage-tools.pages.dev/?utm_source=seo_content", data["items"][0]["destination"])
        self.assertEqual("https://leverage-tools.pages.dev/?utm_source=seo_content", data["items"][0]["call_to_action"])
        self.assertEqual("https://leverage-tools.pages.dev/", data["tracking"]["landing_url"])

    def test_daily_queue_creates_concrete_prospect_validation_work(self):
        result = acquisition_campaign.generate_daily_queue(datetime(2026, 8, 22, tzinfo=timezone.utc))
        self.assertGreater(result["created"], 0)
        self.assertEqual(result["prospects_created"], 2)
        self.assertEqual(result["top_candidate"]["id"], "p-high")
        data = json.loads(self.queue.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 3)
        self.assertEqual(data["prospect_validation"][0]["prospect_id"], "p-high")
        self.assertEqual(data["prospect_validation"][0]["status"], "research_required")
        self.assertEqual(data["prospect_validation"][0]["why_fit"], "observable quote workflow")
        self.assertEqual(data["prospect_validation"][0]["evidence"], ["public quote page"])

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
        self.assertEqual(direct["prospect_fit_score"], 90)
        self.assertEqual(direct["prospect_status"], "research_required")
        self.assertEqual(direct["personalization_basis"], "quote follow-up")
        self.assertEqual(direct["status"], "draft")


if __name__ == "__main__": unittest.main()
