"""Tests for guarded financial behavior."""
from finance_core import can_execute_payout


def test_unapproved_payout_is_blocked():
    ok, reason = can_execute_payout("missing-payout")
    assert ok is False
    assert reason == "payout request not found"
