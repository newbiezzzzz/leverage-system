# Leverage Income Automation

## Current target
Identify paid AI-agent work with zero Owner spend and no local-PC execution.

## Primary adapter
AgentJob.

AgentJob currently advertises platform-covered gas, free agent registration, USDC settlement, and an MCP/API interface for autonomous agents. Runtime discovery can use the public Task Square feed without an API key; authenticated agent operations use `AGENTJOB_API_KEY`.

## Leverage rules
- RM0-first: never require Owner funding for gas, bids, ads, or subscriptions.
- No local-PC execution: production work must run on approved remote runners.
- Quota-aware polling and task handling.
- No spam, impersonation, platform-rule bypass, binding commitments, or money movement without the existing policy boundary.
- Revenue is only recorded after authoritative settlement evidence.

## Success condition
A paid task is assigned, completed remotely, accepted, and the resulting USDC credit is verified.
