# Leverage Control Plane

The control plane is the shared coordination layer for Leverage workers.

## Design goals

- Keep worker roles separate.
- Keep projects reusable.
- Record tasks and results in a machine-readable format.
- Keep analysis workers separate from actions that can move money or change external systems.
- Make providers/workers replaceable as better technology becomes available.
- Operate within free-tier budgets wherever possible.

## Current workers

- `research-worker`: active research/analysis worker.
- `code-worker`: planned implementation/testing worker.
- `data-worker`: planned data collection/preparation worker.

## Safety boundary

The current research worker is analysis-only. No live trading, financial transaction, or external destructive action is authorized by this control plane.
