import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from workers.digital_product_worker import build_job_log_csv, build_quote_workbook, self_test


class DigitalProductWorkerTests(unittest.TestCase):
    def test_self_test_is_zero_cost(self):
        result = self_test()
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["cost"]["amount"], 0)
        self.assertEqual(result["format"] if "format" in result else "xlsx-workbook", "xlsx-workbook")

    def test_build_quote_workbook_is_real_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "quote.xlsx"
            result = build_quote_workbook(str(target))
            self.assertTrue(target.exists())
            self.assertEqual(result["format"], "xlsx")
            self.assertEqual(result["cost_rm"], 0)
            with ZipFile(target, "r") as archive:
                names = set(archive.namelist())
                self.assertIn("[Content_Types].xml", names)
                self.assertIn("xl/workbook.xml", names)
                self.assertIn("xl/worksheets/sheet1.xml", names)
                workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
                self.assertIn("Quote", workbook_xml)

    def test_build_job_log_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "job_log.csv"
            result = build_job_log_csv(str(target), rows=5)
            lines = target.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 6)
            self.assertEqual(result["rows"], 6)


if __name__ == "__main__":
    unittest.main()
