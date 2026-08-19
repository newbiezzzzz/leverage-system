import tempfile
import unittest
from pathlib import Path

from workers.runtime import ExecutorRegistry, build_default_registry, execute


class WorkerRuntimeTests(unittest.TestCase):
    def test_data_worker_runs_without_external_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            path.write_text("value\n10\n20\n30\n", encoding="utf-8")
            result = execute("data-worker", {"id": "data-1", "input_path": str(path), "column": "value"})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["executor"], "local-python")
        self.assertEqual(result["result"]["mean"], 20.0)

    def test_digital_product_worker_creates_artifact_without_external_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "quote.xml"
            result = execute("digital-product-worker", {"id": "product-1", "artifact_type": "quote_workbook", "output_path": str(target)})
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["executor"], "local-python")
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 100)

    def test_router_falls_back_to_next_executor(self):
        registry = ExecutorRegistry()
        registry.register("data-worker", "failing-provider", lambda task: (_ for _ in ()).throw(RuntimeError("quota")))
        registry.register("data-worker", "local-python", lambda task: {"ok": True})
        result = execute("data-worker", {"id": "data-2"}, registry)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["executor"], "local-python")

    def test_registry_exposes_local_product_executor(self):
        registry = build_default_registry()
        self.assertIn("local-python", registry.available("digital-product-worker"))

    def test_no_executor_is_explicit_error(self):
        with self.assertRaisesRegex(RuntimeError, "no executor available"):
            execute("finance-worker", {"id": "finance-1"})


if __name__ == "__main__":
    unittest.main()
