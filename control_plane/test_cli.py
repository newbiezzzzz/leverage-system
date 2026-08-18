"""Smoke tests for the owner-facing Leverage CLI."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from cli.leverage import build_parser, main


class LeverageCliTests(unittest.TestCase):
    def test_parser_accepts_status_report_health_and_readiness(self):
        for command in ("status", "report", "health", "readiness", "workers"):
            args = build_parser().parse_args([command])
            self.assertEqual(args.command, command)

    def test_help_is_human_readable(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["help"])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("project new", text)
        self.assertIn("report", text)
        self.assertIn("readiness", text)
        self.assertIn("payout prepare", text)

    def test_readiness_command_returns_success_under_baseline(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["readiness"])
        self.assertEqual(code, 0)
        self.assertIn("Status      : READY", output.getvalue())

    def test_project_new_command_is_valid(self):
        args = build_parser().parse_args(["project", "new"])
        self.assertEqual(args.project_command, "new")

    def test_project_status_command_is_valid(self):
        args = build_parser().parse_args(["project", "status", "trading-toolkit"])
        self.assertEqual(args.project_command, "status")
        self.assertEqual(args.project, "trading-toolkit")


if __name__ == "__main__":
    unittest.main()
