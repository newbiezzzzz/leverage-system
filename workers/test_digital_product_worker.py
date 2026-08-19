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
        self.assertIn("xlsx-workbook", result["capabilities"])

    def test_build_quote_workbook_is_real_xlsx_with_functional_formulas(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "quote.xlsx"
            result = build_quote_workbook(str(target))
            self.assertTrue(target.exists())
            self.assertEqual(result["format"], "xlsx")
            self.assertEqual(result["cost_rm"], 0)
            self.assertEqual(result["product_name"], "Fabrication Shop Profit & Quote System")
            self.assertEqual(result["sheets"], ["Quote", "Shop_Rates", "Job_Log", "Change_Orders"])
            self.assertGreaterEqual(result["formula_count"], 35)
            with ZipFile(target, "r") as archive:
                names = set(archive.namelist())
                required = {
                    "[Content_Types].xml", "_rels/.rels", "xl/workbook.xml",
                    "xl/_rels/workbook.xml.rels", "xl/worksheets/sheet1.xml",
                    "xl/worksheets/sheet2.xml", "xl/worksheets/sheet3.xml",
                    "xl/worksheets/sheet4.xml",
                }
                self.assertTrue(required.issubset(names))
                workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
                quote_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                rates_xml = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
                jobs_xml = archive.read("xl/worksheets/sheet3.xml").decode("utf-8")
                changes_xml = archive.read("xl/worksheets/sheet4.xml").decode("utf-8")
                for sheet in ("Quote", "Shop_Rates", "Job_Log", "Change_Orders"):
                    self.assertIn(sheet, workbook_xml)
                self.assertIn("C8*E8", quote_xml)
                self.assertIn("SUM(G8:G27)", quote_xml)
                self.assertIn("(B30+B32)/(1-D4/100)", quote_xml)
                self.assertIn("B11+B13", rates_xml)
                self.assertIn("SUM(F3:J3)", jobs_xml)
                self.assertIn("E3-K3", jobs_xml)
                self.assertIn("D3-E3", changes_xml)

    def test_build_job_log_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "job_log.csv"
            result = build_job_log_csv(str(target), rows=5)
            lines = target.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 6)
            self.assertEqual(result["rows"], 6)


if __name__ == "__main__":
    unittest.main()
