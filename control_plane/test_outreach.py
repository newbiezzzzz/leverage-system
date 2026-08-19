import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import outreach


class OutreachTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.prospects = root / "prospects.json"
        self.queue = root / "outreach_queue.json"
        self.prospects.write_text(json.dumps({"prospects": [{
            "id": "p1", "business_name": "Example Services", "contact_name": "Owner",
            "public_contact_available": True, "preferred_public_channel": "email",
            "observed_problem": "slow enquiry follow-up"
        }]}), encoding="utf-8")
        self.patches = [
            patch.object(outreach, "PROSPECTS", self.prospects),
            patch.object(outreach, "OUTREACH", self.queue),
        ]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def test_prepare_creates_draft_and_requires_approval(self):
        item = outreach.prepare_outreach("p1", "one workflow audit")
        self.assertEqual(item["status"], "draft")
        self.assertTrue(item["approval_required"])
        self.assertIn("Example Services", item["message"])

    def test_unknown_prospect_rejected(self):
        with self.assertRaises(KeyError):
            outreach.prepare_outreach("missing", "offer")

    def test_no_public_contact_rejected(self):
        data = json.loads(self.prospects.read_text())
        data["prospects"][0]["public_contact_available"] = False
        self.prospects.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            outreach.prepare_outreach("p1", "offer")


if __name__ == "__main__":
    unittest.main()
