import unittest
from control_plane.opportunity_engine import rank_opportunities, score_opportunity
from control_plane.opportunity_scan import load_opportunities, scan


class OpportunityScanTests(unittest.TestCase):
    def test_registry_contains_evidence_backed_candidates(self):
        opportunities = load_opportunities()
        self.assertGreaterEqual(len(opportunities), 4)
        self.assertTrue(all(item.get("evidence") for item in opportunities))

    def test_ranked_candidates_have_valid_scores(self):
        ranked = rank_opportunities(load_opportunities())
        self.assertEqual(len(ranked), 4)
        self.assertEqual(ranked, sorted(ranked, key=lambda item: item["score"], reverse=True))
        self.assertTrue(all(0 <= item["score"] <= 100 for item in ranked))

    def test_missing_evidence_prevents_candidate_decision(self):
        result = score_opportunity({"id": "x", "first_revenue_speed": 100})
        self.assertEqual(result.decision, "needs-evidence")
        self.assertTrue(result.missing_evidence)

    def test_scan_keeps_owner_gate(self):
        result = scan()
        self.assertEqual(result["count"], 4)
        self.assertIn("Owner approval", result["owner_gate"])


if __name__ == "__main__":
    unittest.main()
