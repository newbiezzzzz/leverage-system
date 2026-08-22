from __future__ import annotations

import unittest
from control_plane.buyer_pipeline import advance, can_advance, new_pipeline


class BuyerPipelineTests(unittest.TestCase):
    def test_cannot_contact_without_approval(self):
        p = new_pipeline("prospect-1")
        p = advance(p, "validated", evidence={"validation_evidence"})
        p = advance(p, "offer_draft")
        p = advance(p, "approved", approvals={"approved"})
        result = can_advance(p, "contacted")
        self.assertFalse(result.ok)
        self.assertIn("approval required", result.reason)

    def test_purchase_requires_evidence(self):
        p = new_pipeline("prospect-1")
        p = advance(p, "validated", evidence={"validation_evidence"})
        p = advance(p, "offer_draft")
        p = advance(p, "approved", approvals={"approved"})
        p = advance(p, "contacted", approvals={"contacted"})
        p = advance(p, "replied", evidence={"response_evidence"})
        p = advance(p, "interested")
        p = advance(p, "sample_or_trial")
        result = can_advance(p, "purchased", approvals={"purchased"})
        self.assertFalse(result.ok)
        self.assertIn("purchase_evidence", result.reason)

    def test_verified_revenue_requires_authoritative_evidence(self):
        p = new_pipeline("prospect-1")
        for target, approvals, evidence in [
            ("validated", set(), {"validation_evidence"}),
            ("offer_draft", set(), set()),
            ("approved", {"approved"}, set()),
            ("contacted", {"contacted"}, set()),
            ("replied", set(), {"response_evidence"}),
            ("interested", set(), set()),
            ("sample_or_trial", set(), set()),
            ("purchased", {"purchased"}, {"purchase_evidence"}),
        ]:
            p = advance(p, target, approvals=approvals, evidence=evidence)
        result = can_advance(p, "verified_revenue", approvals={"verified_revenue"})
        self.assertFalse(result.ok)
        self.assertIn("authoritative_revenue_evidence", result.reason)

    def test_valid_path_reaches_verified_revenue(self):
        p = new_pipeline("prospect-1")
        for target, approvals, evidence in [
            ("validated", set(), {"validation_evidence"}),
            ("offer_draft", set(), set()),
            ("approved", {"approved"}, set()),
            ("contacted", {"contacted"}, set()),
            ("replied", set(), {"response_evidence"}),
            ("interested", set(), set()),
            ("sample_or_trial", set(), set()),
            ("purchased", {"purchased"}, {"purchase_evidence"}),
            ("verified_revenue", {"verified_revenue"}, {"authoritative_revenue_evidence"}),
        ]:
            p = advance(p, target, approvals=approvals, evidence=evidence)
        self.assertEqual(p["stage"], "verified_revenue")


if __name__ == "__main__":
    unittest.main()
