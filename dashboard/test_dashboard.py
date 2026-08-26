from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class DashboardContractTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (ROOT / name).read_text(encoding="utf-8")

    def test_command_center_is_dark_and_uses_shared_shell(self):
        html = self.read("command.html")
        self.assertIn('href="styles.css', html)
        self.assertIn('href="layout.css', html)
        self.assertIn('href="command.css', html)
        self.assertNotRegex(html, r"background\s*:\s*white|background-color\s*:\s*white")

    def test_command_center_exposes_acquisition_queue(self):
        html = self.read("command.html")
        js = self.read("command.js")
        self.assertIn("INCOME ACQUISITION", html)
        self.assertIn('id="acquisitionQueue"', html)
        self.assertIn("/api/acquisition-queue", js)
        self.assertIn("prospect-validation", js)

    def test_command_center_exposes_buyer_funnel(self):
        html = self.read("command.html")
        js = self.read("command.js")
        css = self.read("command.css")
        self.assertIn("BUYER FUNNEL", html)
        self.assertIn('id="buyerFunnel"', html)
        self.assertIn("/api/buyer-pipeline", js)
        self.assertIn("buyer-row", css)

    def test_command_center_exposes_product_drilldown(self):
        html = self.read("command.html")
        js = self.read("command.js")
        css = self.read("command.css")
        self.assertIn("PRODUCTS", js)
        self.assertIn("product-mini", css)
        self.assertIn("project-detail.html", js)
        self.assertIn("&product=", js)
        self.assertIn("Product 1", html)

    def test_command_center_exposes_traffic_view(self):
        html = self.read("command.html")
        js = self.read("command.js")
        css = self.read("command.css")
        self.assertIn("TRAFFIC VIEW", html)
        for element_id in ("trafficVisitors", "trafficEvents", "trafficQuotes", "trafficClicks", "trafficConversion", "trafficSources"):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn("/api/project-metrics", js)
        self.assertIn("renderTraffic", js)
        self.assertIn("traffic-source", css)

    def test_project_detail_uses_same_theme(self):
        html = self.read("project-detail.html")
        self.assertIn('href="styles.css', html)
        self.assertIn('href="layout.css', html)
        self.assertIn('href="command.css', html)
        self.assertIn('href="project-detail.css', html)
        self.assertNotRegex(html, r"background\s*:\s*white|background-color\s*:\s*white")

    def test_project_detail_is_local_api_first(self):
        js = self.read("project-detail.js")
        for endpoint in ("/api/projects", "/api/project-types", "/api/project-metrics", "/api/snapshot"):
            self.assertIn(endpoint, js)
        self.assertIn("/api/projects/", js)
        self.assertNotIn("raw.githubusercontent.com", js)
        self.assertNotIn("github.com/newbiezzzzz/leverage-system/raw", js)

    def test_product_query_renders_product_detail(self):
        js = self.read("project-detail.js")
        self.assertIn("params.get('product')", js)
        self.assertIn("renderProductDetail", js)
        self.assertIn("fabrication-shop-profit-quote-system", js)
        css = self.read("project-detail.css")
        self.assertIn("product-detail-link", css)

    def test_project_detail_has_no_embedded_light_theme(self):
        html = self.read("project-detail.html")
        self.assertNotIn("background:#fff", html.replace(" ", ""))
        self.assertNotIn("background: #fff", html)
        self.assertNotIn("color:#111", html.replace(" ", ""))

    def test_project_detail_escapes_rendered_values(self):
        js = self.read("project-detail.js")
        self.assertIn("function esc", js)
        self.assertIn("esc(p.name)", js)
        self.assertIn("esc(p.id)", js)
        self.assertIn("esc(p.description", js)

    def test_required_dashboard_files_exist(self):
        for name in ("index.html", "command.html", "command.js", "projects.html", "projects.js", "project-detail.html", "project-detail.js", "styles.css", "layout.css", "command.css", "project-detail.css"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
