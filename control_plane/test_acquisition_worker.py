"""Tests for the reusable acquisition worker."""
from __future__ import annotations
import unittest

from workers.acquisition_worker import prepare_outreach, qualify_prospect, self_test


class AcquisitionWorkerTests(unittest.TestCase):
    def test_qualifies_high_fit_prospect(self):
        result = qualify_prospect("Example", 85, ["public business profile"])
        self.assertEqual(result["status"], "qualified")
        self.assertEqual(result["next_action"], "prepare_personalized_value_offer")

    def test_outreach_is_draft_and_guarded(self):
        result = prepare_outreach({"prospect": "Example"}, "Free sample", "public_business_email")
        self.assertEqual(result["status"], "draft")
        self.assertTrue(result["requires_owner_or_policy_approval"])
        self.assertIn("respect_channel_rules", result["safety_checks"])

    def test_self_test_is_healthy(self):
        result = self_test()
        self.assertEqual(result["worker"], "acquisition-worker")
        self.assertEqual(result["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
