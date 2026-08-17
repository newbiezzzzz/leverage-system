# Leverage Control Plane

The control plane is the shared coordination and safety layer for the Leverage company operating system.

## Company model

Leverage is one owner-operated company with a reusable operating system. New projects are plugged into the same lifecycle instead of rebuilding management, workers, finance tracking and safety controls for each project.

**Project lifecycle**

`intake → validation → build → launch → operate → revenue → payout-ready`

Projects can also move to `paused` or `retired`.

## Worker fleet

- `research-worker` — opportunity and market research.
- `data-worker` — collection, validation, transformation and caching.
- `code-worker` — implementation, testing and packaging.
- `project-manager` — intake, planning, routing and lifecycle coordination.
- `operations-worker` — health monitoring, verification, alerts and safe recovery.
- `customer-worker` — customer intake, support and feedback.
- `finance-worker` — reconciliation, revenue reporting and payout preparation.

The ChatGPT-based AI Manager remains the owner-facing coordination layer. Worker implementations remain replaceable.

## Financial safety boundary

Finance automation is deliberately split into three different authorities:

1. Workers may **prepare** a payout request from verified records.
2. The owner must **approve** the payout.
3. A future external payment integration may **execute** it only after the company explicitly enables live money movement.

Leverage v1 has live money movement disabled. No worker can approve a payout, change bank details, or transfer funds.

The same pattern applies to destructive external actions and other consequential changes: plan/prepare first, owner approval second, external execution last.

## Data stores

- `company.json` — company mission, operating principles and lifecycle.
- `projects.json` — project portfolio and lifecycle state.
- `workers.json` — worker registry and capability contracts.
- `tasks.json` — work queue.
- `approvals.json` — owner approval records.
- `financial_ledger.json` — verified financial entries and payout queue.
- `resource_state.json` / `resource_limits.json` — provider quota/resource controls.

## Design goals

- Build reusable company infrastructure before duplicating project infrastructure.
- Keep company, system and project responsibilities separate.
- Route tasks through explicit worker capability contracts.
- Never invent balances, quotas, revenue or payout confirmations.
- Keep financial and destructive actions behind owner approval and external confirmation.
- Prefer low-cost, replaceable providers.
- Make every new project capable of following the same operating lifecycle.
