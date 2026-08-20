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
- Project-type compatibility dry run: **passed** for software/micro-SaaS and the existing modeled project types
- Channel adapter dry run: **passed** for marketplace, web and social contracts
- First web-channel publishing test: **owner-verified live**
- Controlled end-to-end business-loop execution: **not yet passed**

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
- external-action-worker: online
- channel-adapter-worker: online
- measurement-worker: online

The acquisition worker supports campaign planning and traceable tracking-link preparation. Conversion, delivery, business-loop, architecture-validation, external-action, channel-adapter and measurement workers are explicit bounded capabilities.

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
- Measurement: provider-agnostic traffic/funnel adapter now exists; authoritative source still requires configuration.
- Decisioning: project gates remain evidence-gated.
- Project-type registry: available via `control_plane/project_types.json`.
- Channel registry: available via `control_plane/channels.json`.
- Project dashboard: now surfaces project type plus allowed channel, delivery and revenue-event adapters.
- Architecture validator: available via `workers/architecture_validator.py`.
- Controlled execution test definition: available via `control_plane/execution_test.json`.
- Generic external-action queue: available via `control_plane/external_action_queue.json`.
- External-action worker: prepares actions, routes approval, tracks status and verifies completion evidence; it does not directly publish, send, bind customers or move money.
- Generic channel-adapter interface: available via `control_plane/channel_adapters.json` and `workers/channel_adapter_worker.py`.
- Measurement adapter: available via `control_plane/measurement_adapters.json` and `workers/measurement_worker.py`.

## Controlled Execution Test
A controlled execution test records an observable end-to-end run against Experiment A without adding capital or inventing external evidence.

Current result:
- Discover: passed
- Validate: passed
- Build: passed
- Publish: passed
- Acquire: blocked by missing authoritative channel measurement / approved external distribution execution
- Convert: waiting
- Deliver: ready
- Support: ready
- Measure: partial
- Decide: waiting

Success criteria require every completed stage to have evidence, no paid acquisition, no fabricated metrics, and approval-gated external actions.

## First Web Channel Execution Test
A public web landing page was added at `dashboard/project-launch/index.html` as a real Web Channel execution test for Experiment A. The existing GitHub Pages workflow is configured to publish the dashboard directory. The Owner confirmed the public page is live, so deployment is now **owner-verified**. The resulting execution is recorded in `control_plane/channel_execution.json`.

Current state:
- Action: publish_public_landing_page
- Capital: RM0
- Approval: Owner proceed
- Status: live / owner-verified
- Page views: UNKNOWN
- Unique visitors: UNKNOWN
- Traffic source measurement: NOT CONNECTED
- Downstream destination: marketplace product page

This test is specifically a **web channel execution test**. It does not make Gumroad the Leverage architecture.

## Measurement
A provider-agnostic measurement layer is now available at `control_plane/measurement_adapters.json`.

Current RM0 option:
- GoatCounter hosted analytics: currently offered as a free hosted service for reasonable public usage and supports simple JavaScript integration on static sites. The provider is privacy-oriented and supports referrers/campaigns/page views. citeturn955167search0turn955167search4
- Leverage status: **ready for configuration**, not yet connected.
- Required external configuration: provider site code.
- Credentials are never stored in the repository.

Measurement rule:
**UNKNOWN remains UNKNOWN until an authoritative provider returns evidence.**

## Channel Adapter Dry Run
A dry-run contract is recorded at `control_plane/channel_adapter_dry_run.json`.

Validated adapter contracts without external side effects:
- Marketplace / Gumroad: prepare + validate passed; execute skipped; measurement blocked without authoritative source.
- Web / generic web app: prepare + validate passed; execute skipped; measurement blocked without live source.
- Social / generic social platform: prepare + validate passed; execute skipped; measurement blocked without live source.

This proves the interface is platform-agnostic, but **does not prove real external execution**. The web publishing test above is the first actual external execution attempt and is now owner-verified as live.

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
