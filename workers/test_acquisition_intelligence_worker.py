from __future__ import annotations

import unittest

from workers.acquisition_intelligence_worker import analyze


class AcquisitionIntelligenceTests(unittest.TestCase):
    def test_no_traffic_does_not_invent_metrics(self):
        report = analyze({"events": 0, "page_views": 0, "unique_visitors": None, "calculated_quotes": 0, "pro_clicks": 0, "conversion_rate": None, "traffic_sources": []})
        self.assertEqual(report["mode"], "deterministic")
        self.assertIn("No verified traffic totals are available yet.", report["evidence"])
        self.assertEqual(report["financial_action"], "none")

    def test_analyser_prioritizes_source_and_cta(self):
        report = analyze({
            "events": 20,
            "page_views": 10,
            "unique_visitors": 7,
            "calculated_quotes": 4,
            "pro_clicks": 0,
            "conversion_rate": 0.0,
            "traffic_sources": [{"name": "google", "views": 8}],
        })
        self.assertTrue(any("google" in item.lower() for item in report["recommendations"]))
        self.assertTrue(any("call-to-action" in item.lower() for item in report["recommendations"]))


if __name__ == "__main__":
    unittest.main()
