"""Reusable external-channel adapter boundary.

This module defines the safe boundary between Leverage and external customer
platforms. It stores no credentials and performs no direct network activity.
Project-specific integrations can implement the adapter contract separately.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class ChannelPolicy:
    channel_id: str
    enabled: bool = False
    read_jobs: bool = False
    submit_proposals: bool = False
    send_messages: bool = False
    accept_contracts: bool = False
    collect_payment: bool = False
    requires_owner_approval: bool = True


@dataclass
class ChannelJob:
    id: str
    title: str
    description: str = ""
    budget: float | None = None
    currency: str = ""
    source_url: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ChannelAction:
    action: str
    channel_id: str
    target_id: str
    status: str = "draft"
    approval_required: bool = True
    created_at: str = ""


class ExternalChannelAdapter(Protocol):
    policy: ChannelPolicy

    def discover_jobs(self) -> list[ChannelJob]: ...

    def prepare_proposal(self, job: ChannelJob, offer: str) -> ChannelAction: ...


class GuardedChannel:
    """Policy gate used by acquisition logic before any external action."""

    def __init__(self, policy: ChannelPolicy):
        self.policy = policy

    def discover_jobs(self, adapter: ExternalChannelAdapter) -> list[ChannelJob]:
        if not self.policy.enabled or not self.policy.read_jobs:
            return []
        return adapter.discover_jobs()

    def prepare_proposal(self, adapter: ExternalChannelAdapter, job: ChannelJob, offer: str) -> ChannelAction:
        if not self.policy.enabled or not self.policy.submit_proposals:
            raise PermissionError(f"proposal submission disabled for channel: {self.policy.channel_id}")
        action = adapter.prepare_proposal(job, offer)
        action.approval_required = self.policy.requires_owner_approval
        action.created_at = datetime.now(timezone.utc).isoformat()
        return action

    def assert_external_action_allowed(self, action: str) -> None:
        allowed = {
            "read_jobs": self.policy.read_jobs,
            "submit_proposals": self.policy.submit_proposals,
            "send_messages": self.policy.send_messages,
            "accept_contracts": self.policy.accept_contracts,
            "collect_payment": self.policy.collect_payment,
        }
        if not self.policy.enabled or not allowed.get(action, False):
            raise PermissionError(f"external action disabled: {action}")


DEFAULT_CHANNEL_POLICIES = {
    "linkedin": ChannelPolicy("linkedin", enabled=False, read_jobs=False, submit_proposals=False, send_messages=False),
    "contra": ChannelPolicy("contra", enabled=False, read_jobs=False, submit_proposals=False, send_messages=False),
    "collateam": ChannelPolicy("collateam", enabled=False, read_jobs=False, submit_proposals=False, send_messages=False),
    "freelancing-my": ChannelPolicy("freelancing-my", enabled=False, read_jobs=False, submit_proposals=False, send_messages=False),
}
