from __future__ import annotations

import unittest

from control_plane.offer_engine import draft_offer


class OfferEngineTests(unittest.TestCase):
    def test_offer_is_personalized_from_evidence(self):
        offer = draft_offer({
            "id": "prospect-skid",
            "name": "SKID Systems",
            "fit": 96,
            "candidate_workflow": "quote preparation and job costing",
            "why_fit": "fabrication projects with budget control",
            "evidence": ["public fabrication services", "budget-focused positioning"],
            "public_contact": {"email": "info@example.com"},
        })
        self.assertEqual(offer["status"], "draft")
        self.assertEqual(offer["prospect"], "SKID Systems")
        self.assertIn("quote preparation", offer["offer"])
        self.assertEqual(offer["send_status"], "not_sent")
        self.assertTrue(offer["owner_approval_required"])
        self.assertEqual(offer["price_usd"], 19)

    def test_offer_never_claims_customer_status(self):
        offer = draft_offer({"id": "p", "name": "Candidate", "fit": 70})
        self.assertNotIn("customer", offer["status"].lower())
        self.assertIn("no_claim_of_customer_status", offer["safety"])


if __name__ == "__main__":
    unittest.main()
