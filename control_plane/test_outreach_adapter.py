from __future__ import annotations

import unittest

from control_plane.outreach_adapter import prepare_outreach, self_test


class OutreachAdapterTests(unittest.TestCase):
    def test_self_test_is_healthy_and_guarded(self):
        result = self_test()
        self.assertEqual("healthy", result["status"])
        self.assertTrue(result["approval_guard"])
        self.assertEqual(["gmail", "outlook"], result["providers"])

    def test_provider_ready_draft_requires_approval_and_email(self):
        offer = {
            "prospect_id": "p1",
            "prospect": "Workshop",
            "public_contact": {"email": "sales@example.com"},
            "value_proposition": "Save quoting time.",
        }
        with self.assertRaises(ValueError):
            prepare_outreach(offer, "gmail", approved=False)
        draft = prepare_outreach(offer, "gmail", approved=True)
        self.assertEqual("gmail", draft.provider)
        self.assertEqual("not_sent", draft.send_status)
        self.assertTrue(draft.owner_approval_required)

    def test_unknown_provider_rejected(self):
        offer = {"public_contact": {"email": "sales@example.com"}}
        with self.assertRaises(ValueError):
            prepare_outreach(offer, "telegram", approved=True)


if __name__ == "__main__":
    unittest.main()
