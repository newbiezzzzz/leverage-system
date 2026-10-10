"""Regression tests for holdout isolation in Strategy Hunter failure analysis."""
import unittest

from failure_analysis import classify


class HoldoutIsolationTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "selection_total_return": 0.12,
            "selection_profit_factor": 1.4,
            "selection_max_drawdown": -0.06,
            "selection_trades_per_month": 3.0,
        }

    def test_classification_uses_selection_metrics_not_holdout(self):
        first = dict(self.row, holdout_total_return=-0.90,
                     holdout_profit_factor=0.1, holdout_max_drawdown=-0.99,
                     holdout_trades_per_month=0.1)
        second = dict(self.row, holdout_total_return=5.0,
                      holdout_profit_factor=9.0, holdout_max_drawdown=0.0,
                      holdout_trades_per_month=50.0)
        self.assertEqual(classify(first), "too_few_trades")
        self.assertEqual(classify(second), "too_few_trades")

    def test_selection_drawdown_is_a_failure_gate(self):
        row = dict(self.row, selection_trades_per_month=8.0,
                   selection_max_drawdown=-0.15)
        self.assertEqual(classify(row), "drawdown_failure")

    def test_positive_selection_classification_ignores_holdout(self):
        first = dict(self.row, selection_trades_per_month=8.0,
                     holdout_total_return=-0.95, holdout_profit_factor=0.01)
        second = dict(self.row, selection_trades_per_month=8.0,
                      holdout_total_return=10.0, holdout_profit_factor=100.0)
        self.assertEqual(classify(first), "robustness_failure")
        self.assertEqual(classify(second), "robustness_failure")

    def test_missing_selection_metrics_fail_closed(self):
        self.assertEqual(classify({"holdout_total_return": 10.0}),
                         "insufficient_selection_evidence")


if __name__ == "__main__":
    unittest.main()
