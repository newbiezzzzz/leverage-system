import tempfile
import unittest
from pathlib import Path

from workers.digital_product_worker import build_job_log_csv, build_quote_workbook, self_test


class DigitalProductWorkerTests(unittest.TestCase):
    def test_self_test_is_zero_cost(self):
        result = self_test()
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["cost"]["amount"], 0)

    def test_build_quote_workbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "quote.xml"
            result = build_quote_workbook(str(target))
            self.assertTrue(target.exists())
            text = target.read_text(encoding="utf-8")
            self.assertIn("ENGINEERING JOB QUOTATION TOOLKIT", text)
            self.assertEqual(result["cost_rm"], 0)

    def test_build_job_log_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "job_log.csv"
            result = build_job_log_csv(str(target), rows=5)
            lines = target.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 6)
            self.assertEqual(result["rows"], 6)


if __name__ == "__main__":
    unittest.main()
