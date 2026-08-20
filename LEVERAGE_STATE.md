# LEVERAGE STATE

_Last aligned: 20 Aug 2026_

## Mission
Build a zero-cost, reusable AI/data/automation company that can discover opportunities, validate demand, launch projects, acquire customers, deliver outcomes, measure results, and scale evidence-backed winners with minimal Boss involvement.

## Core Identity
Leverage is **not a digital-product generator** and it is not a Gumroad company. Digital products are one project type; Gumroad is one possible marketplace channel. The reusable company capability is the full business loop:

**Discover -> Validate -> Build -> Publish -> Acquire -> Convert -> Deliver -> Support -> Measure -> Decide**

## Operating Model
- Boss = Owner / final approval for consequential external actions and spending.
- Worker = AI/automation execution layer.
- Prefer RM0 / free and replaceable providers.
- Keep projects reversible until evidence supports further investment.
- Never invent financial balances, quotas, traffic, revenue or payout confirmations.
- Build reusable company infrastructure before duplicating project infrastructure.
- Separate company, system and project responsibilities.
- Progressively automate safe, observable and reversible work.
- Never bypass platform rules, spam, impersonate, sign contracts, move money or create binding commitments without the required authorization boundary.

## Company State
- Company: Leverage
- Type: owner-operated technology company
- Stage: system-build / business-loop validation
- Base currency: MYR
- Money movement: disabled
- Lifecycle: intake -> validation -> build -> launch -> operate -> revenue -> payout-ready -> paused -> retired

## Current Leverage Progress
The dashboard's 98% figure represents completion of the current infrastructure milestone, not completion of the ultimate autonomous-income capability.

- Foundation & architecture: 100% complete
- Core worker fleet: 100% complete
- Control Plane v1: 100% complete
- Company Operating System v1: 100% complete
- Owner Command Center: 100% complete
- Quota-independent worker runtime: 90%, active
- Full end-to-end business-loop capability: **not yet validated**
- Project-type compatibility dry run: **passed** for software/micro-SaaS and the existing modeled project types

## Current Worker Fleet
- research-worker: online
- data-worker: online
- code-worker: online
- digital-product-worker: online
- project-manager: online
- operations-worker: online
- customer-worker: online
- acquisition-worker: online
- conversion-worker: online
- delivery-worker: online
- finance-worker: online
- business-loop-worker: online
- architecture-validator: online

The acquisition worker supports campaign planning and traceable tracking-link preparation. Conversion, delivery, business-loop and architecture-validation workers are explicit bounded capabilities.

## Revenue Project #1 — Experiment A
### Fabrication Shop Profit & Quote System
- Project ID: engineering-quote-toolkit
- Type: digital-product
- Status: live
- Lifecycle stage: launch
- Channel instance: Gumroad marketplace
- Price: USD 19
- Capital deployed: RM0
- Verified sales: 0
- Verified revenue: USD0
- Product: no-macro workbook for small fabrication, welding and machine shops covering shop-rate calculation, quoting, job costing, profit protection and change-order control.
- Published: 19 Aug 2026
- Role in Leverage: first live experiment for validating the **full business loop**, not the definition of Leverage itself.

## Current Experiment Gate
**Traffic -> first buyer -> conversion evidence -> iterate**

A first-class traffic/funnel metrics schema exists at `control_plane/project_metrics.json`.

Current measurement state:
- Verified sales: 0
- Verified revenue: USD0
- Traffic: NOT CONNECTED / UNKNOWN
- Unknown traffic must never be treated as zero.

No new product should be created merely to avoid the current validation problem. We need to prove the reusable business engine first.

## Business Loop Validation Target
The important Leverage milestone is no longer "create a digital product".

It is:

> **Can Leverage take an approved opportunity from zero to validated demand and measurable revenue with minimal Boss involvement?**

Current capability expansion:
- Acquisition/campaign planning: available, external publishing remains approval/policy gated.
- Conversion experimentation: available, live offer/pricing changes remain approval gated.
- Delivery orchestration: available, authoritative fulfillment evidence is required.
- Customer support/feedback: available.
- Measurement: traffic/funnel schema exists; authoritative channel data is not yet connected.
- Decisioning: project gates remain evidence-gated.
- Project-type registry: available via `control_plane/project_types.json`.
- Channel registry: available via `control_plane/channels.json`.
- Project dashboard: now surfaces project type plus allowed channel, delivery and revenue-event adapters.
- Architecture validator: available via `workers/architecture_validator.py`.

## Project-Type Agnostic Architecture
The core engine must not contain marketplace-specific assumptions.

Project types currently modeled:
- digital product
- software / micro-SaaS
- automation service
- data product
- content / media
- lead generation

Channel adapters currently modeled:
- marketplace
- direct
- search
- social
- lead generation
- video
- newsletter
- web
- subscription

A specific platform such as Gumroad is an **instance of a channel adapter**, never the core business architecture.

## Architecture Validation
A dry-run scenario for a software/micro-SaaS project is recorded at `control_plane/architecture_validation.json`.

Validated scenario:
- Project type: software
- Business model: subscription
- Channel: web
- Delivery: hosted service / account access
- Revenue events: subscription / churn
- Launch: false
- Capital deployed: RM0
- External actions: none

The compatibility validator checks project type, channel, delivery and revenue-event compatibility without publishing, spending, or changing live projects.

## Dashboard Direction
Keep Company and Project views separated.

Company view should answer:
- Is Leverage healthy?
- What workers are online?
- What resources/limits exist?
- What is the company doing?
- What value/revenue/traffic is being generated?
- Which business-loop capabilities are automated vs manual?
- Which project types/channels are active?

Project view should answer:
- What is this project?
- What business model and channel are being used?
- What stage is it in?
- What has been built?
- What traffic/sales/revenue does it have?
- How much manual Boss work is required?
- What is the next gate?
- Should we improve, scale, pause or retire it?

## Continuity Rule
When continuing Leverage, align against the current repository state first, then dashboard/project data, then conversation context. Do not assume a product, worker, project stage, metric or milestone is missing without checking current state.
