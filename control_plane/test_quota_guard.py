from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_plane import quota_guard


class QuotaGuardTests(unittest.TestCase):
    def test_unknown_quota_enters_safe_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resource = root / "resource.json"
            config = root / "config.json"
            resource.write_text(json.dumps({"resources": [{"provider": "Gemini", "status": "unknown_quota_safe_mode"}], "policy": {"no_unbounded_retry": True, "zero_cost_core": True}}), encoding="utf-8")
            config.write_text(json.dumps({"channels": [{"name": "linkedin", "daily_target": 20}]}), encoding="utf-8")
            with patch.object(quota_guard, "RESOURCE_STATE", resource), patch.object(quota_guard, "ACQUISITION_CONFIG", config):
                budget = quota_guard.acquisition_budget()
            self.assertTrue(budget["safe_mode"])
            self.assertEqual(budget["daily_content_target"], 9)
            self.assertEqual(budget["daily_prospect_validation_cap"], 5)

    def test_known_quota_keeps_safe_bounded_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resource = root / "resource.json"
            config = root / "config.json"
            resource.write_text(json.dumps({"resources": [{"provider": "GitHub", "status": "safe"}], "policy": {"no_unbounded_retry": True, "zero_cost_core": True}}), encoding="utf-8")
            config.write_text(json.dumps({"channels": [{"name": "linkedin", "daily_target": 2}, {"name": "seo_content", "daily_target": 3}]}), encoding="utf-8")
            with patch.object(quota_guard, "RESOURCE_STATE", resource), patch.object(quota_guard, "ACQUISITION_CONFIG", config):
                budget = quota_guard.acquisition_budget()
            self.assertFalse(budget["safe_mode"])
            self.assertEqual(budget["daily_content_target"], 5)
            self.assertEqual(budget["daily_prospect_validation_cap"], 10)


if __name__ == "__main__":
    unittest.main()
