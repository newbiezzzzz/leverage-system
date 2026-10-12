import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import strategy_research_test2 as study


class Test2Rules(unittest.TestCase):
    def test_donchian_excludes_current_candle(self):
        bars = [
            {"high": 10.0, "low": 8.0, "close": 9.0},
            {"high": 11.0, "low": 9.0, "close": 10.0},
            {"high": 15.0, "low": 10.0, "close": 14.0},
        ]
        upper = study.donchian_upper(bars, 2)
        self.assertIsNone(upper[0])
        self.assertIsNone(upper[1])
        self.assertEqual(upper[2], 11.0)
        self.assertGreater(bars[2]["close"], upper[2])

    def test_spot_position_requires_cash_for_notional_and_entry_costs(self):
        self.assertTrue(study.can_afford_spot_long(1000.0, 50000.0, qty=0.005))
        self.assertFalse(study.can_afford_spot_long(200.0, 50000.0, qty=0.005))
        self.assertFalse(study.can_afford_spot_long(250.0, 50000.0, qty=0.005))

    def test_qualification_requires_sample_and_edge_on_both_splits(self):
        good = {"trades": 25, "net_return_usdt": 15, "profit_factor": 1.25,
                "max_drawdown_pct_mark_to_market": 8.0}
        hold = {"trades": 12, "net_return_usdt": 8, "profit_factor": 1.2,
                "max_drawdown_pct_mark_to_market": 9.0}
        self.assertTrue(study.is_qualified(good, hold))
        self.assertFalse(study.is_qualified(good, dict(hold, net_return_usdt=-1)))
        self.assertFalse(study.is_qualified(dict(good, trades=19), hold))


if __name__ == "__main__":
    unittest.main()
