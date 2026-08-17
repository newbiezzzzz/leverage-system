"""Smoke tests for the owner-facing Leverage CLI."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from cli.leverage import build_parser, main


class LeverageCliTests(unittest.TestCase):
    def test_parser_accepts_status(self):
        args = build_parser().parse_args(["status"])
        self.assertEqual(args.command, "status")

    def test_help_is_human_readable(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["help"])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("project create", text)
        self.assertIn("payout prepare", text)

    def test_project_status_command_is_valid(self):
        args = build_parser().parse_args(["project", "status", "trading-toolkit"])
        self.assertEqual(args.project_command, "status")
        self.assertEqual(args.project, "trading-toolkit")


if __name__ == "__main__":
    unittest.main()
