# LEVERAGE STATE

_Last aligned: 25 Aug 2026 — Product Factory v2 implementation_

## Mission
Build a zero-cost, reusable AI/data/automation company that can discover opportunities, validate demand, launch projects, acquire customers, deliver outcomes, measure results, and scale evidence-backed winners with minimal Boss involvement.

## Operating Rules
- Boss = Owner / final approval for consequential external actions and spending.
- Worker = AI/automation execution layer.
- Prefer RM0 / free and replaceable providers.
- Keep projects reversible until evidence supports further investment.
- Never invent financial balances, quotas, traffic, revenue or payout confirmations.
- No spam, impersonation, binding commitments, money movement, or platform-rule bypass.
- UNKNOWN traffic remains UNKNOWN until an authoritative source provides evidence.
- A product is not finished when it merely works: visual quality, UX, responsive behavior, originality and conversion presentation are mandatory gates.
- Heavy local jobs run sequentially; cloud/local quotas are guarded.

## Company State
- Company: Leverage
- Type: owner-operated technology company
- Stage: Product Factory v2 pre-Product-#1 implementation
- Base currency: MYR
- Money movement: disabled
- Daily product target: 1
- Startup cost policy: RM0 until revenue

## Product Factory v2 — IMPLEMENTED IN REPOSITORY
- Factory orchestration contract: `control_plane/product_factory.py`
- Factory runtime policy: `control_plane/product_factory_config.json`
- Creative Director worker: `workers/creative_director_worker.py`
- Design/UX QA worker: `workers/design_qa_worker.py`
- Content/marketing worker: `workers/content_marketing_worker.py`
- Marketplace worker: `workers/marketplace_worker.py`
- Visual design system: `website/design-system.json`
- Public website factory contract: `website/PUBLIC_SITE_FACTORY.md`
- n8n dry-run workflow: `n8n/leverage-product-factory-dry-run.json`
- Windows setup helper: `tools/setup-product-factory.cmd`
- CI preflight: `.github/workflows/product-factory-preflight.yml`
- Worker registry updated to v14.

## Quality Contract
- Minimum automatic publish score: 85/100.
- Functional QA: required.
- Creative/visual QA: required.
- Responsive/mobile QA: required.
- Conversion QA: required.
- Safety audit: required.
- Below threshold: redesign/rework, not publish.

## Hybrid Runtime
- Local Windows PC: n8n, local AI, browser automation, heavy/sequential jobs.
- Cloudflare: public website, lightweight APIs, telemetry and public infrastructure.
- GitHub: source control and deployment.
- No requirement to run all AI workers simultaneously.

## Marketplace Automation Boundary
- API-first where a platform supports the required action.
- Guarded browser automation where an API does not provide the required publishing action.
- Marketplace worker may prepare listings and publishing actions.
- Account credentials, payout/bank changes, money movement and other sensitive actions remain Owner-controlled.

## Public Website Acquisition System
`research -> information architecture -> visual design -> implementation -> functional QA -> responsive QA -> creative QA -> conversion QA -> SEO metadata -> deploy -> telemetry`

Content must be useful and differentiated; no low-quality mass/duplicate SEO publishing.

## Pre-Product-#1 Gate
The factory must pass a non-financial dry run before the first real product is created:

`research -> select -> build -> functional_qa -> creative_qa -> conversion_qa -> website_package -> marketplace_package -> marketing_package -> analytics_package -> safety_audit`

Dry-run rules:
- no real paid offer
- no money movement
- no payout changes
- no credential changes

## Existing Projects

### Project P-001 — Fabrication Shop Profit & Quote System
- Status: paused
- Channel: Gumroad
- Price: USD19
- Capital deployed: RM0
- Verified sales: 0
- Verified revenue: USD0

### Project P-002 — Leverage Free Fabrication Tool Network
- Status: active / acquire
- Production: https://leverage-tools.pages.dev/
- Hosting: Cloudflare Pages
- Capital deployed: RM0
- Verified sales: 0
- Verified revenue: USD0

P-002 remains an existing asset and acquisition surface; the Product Factory now provides the reusable engine for the next product cycle rather than replacing existing work.

## Current Status
Repository implementation is complete for the pre-Product-#1 architecture. The remaining environment-bound step is installing/running local n8n on the Owner's Windows machine and executing the dry-run, because this chat cannot directly control the Owner's PC process/session.

Do not create Product #1 until the dry-run passes.
