# Leverage Control Plane

The Control Plane is the shared coordination, state and safety layer for the Leverage company operating system.

## End goal

Leverage is **not a trading system** and not a single product. It is a reusable company machine: Boss chooses the direction, the Control Plane turns opportunities into governed projects, workers perform bounded work, and the company measures evidence, revenue and profit.

The infrastructure is deliberately reusable so the first income project does not become a one-off automation.

## Company model

One owner-operated company, many replaceable projects.

**Project lifecycle**

`intake → validation → build → launch → operate → revenue → payout-ready`

Projects can also move to `paused` or `retired`. Explicit transitions prevent projects from skipping required gates.

## Worker fleet

- `research-worker` — opportunity and market research.
- `data-worker` — collection, validation, transformation and caching.
- `code-worker` — implementation, testing and packaging.
- `project-manager` — intake, planning, routing and lifecycle coordination.
- `operations-worker` — health monitoring, verification, alerts and safe recovery.
- `customer-worker` — customer intake, support and feedback.
- `acquisition-worker` — prospect discovery, qualification, outreach preparation and response tracking under guarded rules.
- `finance-worker` — reconciliation, revenue reporting and payout preparation.

Workers expose capability contracts. The dispatcher validates worker status, project authorization, capabilities, task dependencies and safety policy before work becomes ready.

## Task engine

Task states are:

`queued → ready → running → completed`

with `waiting-on-dependency`, `blocked`, `failed` and `cancelled` represented by task state/readiness information.

The dispatcher provides:

- validated worker queues
- dependency-aware readiness
- capability checks
- project authorization checks
- restricted-action checks
- worker queue summaries for the dashboard and CLI

A worker can claim only its own validated work. Completing work can advance the project's lifecycle when the corresponding gate evidence is complete.

## Owner Command Center

The dashboard separates company control from project detail.

**Company view** shows:

- company health
- project count
- active projects
- worker readiness/queues
- OS readiness
- verified revenue
- verified profit
- money-movement protection
- project intake

**Project view** shows project lifecycle, gates, progress, revenue state and decisions.

The local API is the only component allowed to mutate company state from the dashboard.

## Financial safety boundary

Finance automation is deliberately split into three authorities:

1. Workers may **prepare** a payout from verified records.
2. Boss must **approve** the payout.
3. A future external payment integration may **execute** it only after live money movement is explicitly enabled.

Leverage v1 has live money movement disabled. No worker can transfer funds or silently change financial destinations.

Revenue is recorded only as verified ledger income. Dashboard profit is verified income minus verified expenses; it is not a forecast.

The same prepare → approve → execute boundary applies to destructive external actions and consequential changes.

## Data stores

- `company.json` — company mission and operating principles.
- `projects.json` — project portfolio and lifecycle state.
- `workers.json` — worker registry and capability contracts.
- `tasks.json` — work queue and dependencies.
- `approvals.json` — owner approval records.
- `financial_ledger.json` — verified financial entries and payout queue.
- `resource_state.json` / `resource_limits.json` — provider quota/resource controls.
- `audit_log.json` — operational event history.

## Infrastructure v1 release boundary

The reusable company infrastructure is considered ready when it can safely do all of the following without a project-specific redesign:

1. accept a project brief;
2. create an idempotent project plan;
3. route tasks to bounded workers;
4. enforce dependencies and lifecycle gates;
5. expose worker queues and project progress;
6. monitor health, readiness and resources;
7. record verified revenue/profit evidence;
8. prepare and owner-gate payouts without moving money;
9. publish sanitized state to the dashboard; and
10. run regression tests and release-gate checks.

At that point, further infrastructure work should be driven by a real project requirement rather than building infrastructure for its own sake.

## Design goals

- Build reusable company infrastructure before duplicating project infrastructure.
- Keep company, system and project responsibilities separate.
- Route tasks through explicit worker capability contracts.
- Never invent balances, quotas, revenue or payout confirmations.
- Keep financial and destructive actions behind owner approval and external confirmation.
- Prefer zero-cost/low-cost, replaceable providers.
- Minimize Boss manual work while keeping consequential decisions visible.
- Make every new project capable of following the same operating lifecycle.
