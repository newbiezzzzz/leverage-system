# Leverage Product Factory v2

## Purpose

This is the implementation contract for the pre-Product-#1 digital-product factory.

### Core rule

> A deliverable is not finished when it merely works. It must also be useful, visually strong, understandable, and conversion-ready.

## Operating loop

1. Research demand and buyer problem.
2. Score opportunities.
3. Select one product for the daily queue.
4. Build the product.
5. Run functional QA.
6. Run Creative Director / visual QA.
7. Run conversion QA.
8. Generate public website assets.
9. Generate marketplace listing package.
10. Publish through an API where supported, otherwise prepare a guarded browser-automation action.
11. Generate organic marketing assets.
12. Measure traffic/funnel results.
13. Feed evidence back into the next opportunity decision.

## Creative quality gate

Every public-facing asset receives scores for:

- usability
- visual hierarchy
- typography
- spacing
- responsive behavior
- accessibility/readability
- brand consistency
- originality/creative quality
- conversion clarity

Default automatic publish threshold: 85/100. Below threshold returns to the responsible worker for revision.

## Resource policy

The factory is hybrid:

- local Windows machine: n8n, browser automation, local models, heavy sequential jobs
- Cloudflare: public website, lightweight APIs, public telemetry and cloud infrastructure
- GitHub: source control and deployment

The local machine is protected by sequential execution and resource checks. No requirement exists to run all workers simultaneously.

## Money/security boundary

No worker may:

- change payout/bank credentials
- move money
- approve a payout
- bypass marketplace rules
- perform mass spam
- make binding commitments

Sensitive actions remain owner-controlled.

## Product #1 readiness

The factory is ready to create Product #1 only after the dry-run pipeline passes without a real sale:

`research -> build -> functional QA -> creative QA -> conversion QA -> website package -> marketplace package -> marketing package -> analytics package -> safety audit`

The dry-run must not publish a real paid offer or move money.
