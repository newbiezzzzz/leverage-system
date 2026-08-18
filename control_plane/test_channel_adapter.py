from __future__ import annotations

import unittest

from control_plane.channel_adapter import ChannelJob, ChannelPolicy, GuardedChannel


class StubAdapter:
    def __init__(self):
        self.policy = ChannelPolicy("stub", enabled=True, read_jobs=True, submit_proposals=True)

    def discover_jobs(self):
        return [ChannelJob(id="job-1", title="Example job")]

    def prepare_proposal(self, job, offer):
        from control_plane.channel_adapter import ChannelAction
        return ChannelAction(action="submit_proposal", channel_id="stub", target_id=job.id)


class ChannelAdapterTests(unittest.TestCase):
    def test_disabled_channel_cannot_discover(self):
        channel = GuardedChannel(ChannelPolicy("stub", enabled=False, read_jobs=True))
        self.assertEqual(channel.discover_jobs(StubAdapter()), [])

    def test_proposal_requires_enabled_submission(self):
        channel = GuardedChannel(ChannelPolicy("stub", enabled=True, submit_proposals=False))
        with self.assertRaises(PermissionError):
            channel.prepare_proposal(StubAdapter(), ChannelJob(id="1", title="x"), "offer")

    def test_owner_approval_defaults_on(self):
        channel = GuardedChannel(ChannelPolicy("stub", enabled=True, submit_proposals=True))
        action = channel.prepare_proposal(StubAdapter(), ChannelJob(id="1", title="x"), "offer")
        self.assertTrue(action.approval_required)
        self.assertTrue(action.created_at)


if __name__ == "__main__":
    unittest.main()
