"""Tests for guarded financial behavior."""
import unittest

from finance_core import can_execute_payout


class FinanceCoreTests(unittest.TestCase):
    def test_unapproved_payout_is_blocked(self):
        ok, reason = can_execute_payout("missing-payout")
        self.assertFalse(ok)
        self.assertEqual(reason, "payout request not found")


if __name__ == "__main__":
    unittest.main()
