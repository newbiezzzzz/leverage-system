import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runner

class RunnerTests(unittest.TestCase):
    def test_empty_csv_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.csv"
            p.write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "zero data rows"):
                runner.load_bars(p)

    def test_bad_ohlc_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.csv"
            p.write_text(
                "timestamp,open,high,low,close,volume\n"
                "2026-01-05T02:30:00+00:00,100,90,95,98,1\n",
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid OHLC"):
                runner.load_bars(p)

    def test_summary_reports_wins_losses_and_costs(self):
        trades = [
            {"net_rm": 20.0, "gross_rm": 25.0, "costs_rm": 5.0,
             "entry_time": "2026-01-01T00:00:00+00:00", "exit_time": "2026-01-02T00:00:00+00:00"},
            {"net_rm": -10.0, "gross_rm": -5.0, "costs_rm": 5.0,
             "entry_time": "2026-01-03T00:00:00+00:00", "exit_time": "2026-01-04T00:00:00+00:00"},
        ]
        result = runner.summarize(trades, 1000)
        self.assertEqual(result["trades"], 2)
        self.assertEqual(result["wins"], 1)
        self.assertEqual(result["losses"], 1)
        self.assertEqual(result["total_costs_rm"], 10.0)
        self.assertEqual(result["net_return_rm"], 10.0)

if __name__ == "__main__":
    unittest.main()
