# Leverage Unattended Web Automation

Leverage now uses an API-first automation design:

1. Gumroad API performs supported low-risk product updates and verification.
2. Browserbase + Stagehand handles UI-only actions when the API cannot do them.
3. n8n schedules the automation so no recurring copy/paste is required.

## One-time setup

### Gumroad
Create or retrieve a Gumroad access token with the `edit_products` scope and expose it to the n8n process as:

`GUMROAD_ACCESS_TOKEN`

Gumroad documents manual access-token generation for your own account and the `edit_products` OAuth scope. Keep the token secret.

### Browserbase fallback
Create a Browserbase API key and one persistent context dedicated to the Gumroad login:

`BROWSERBASE_API_KEY`
`BROWSERBASE_GUMROAD_CONTEXT_ID`

The context is reused between browser sessions so the automation does not need repeated logins. Browserbase currently provides a free plan for initial testing; ongoing usage may exceed the free allowance.

### n8n
Import:

`n8n/leverage-gumroad-public-web-automation.json`

Run it self-hosted on the Leverage machine. The workflow calls:

`python -m automation.web_automation_router update_gumroad_public_web_cta`

The router tries the Gumroad API first. If that fails, it uses Browserbase/Stagehand when `BROWSERBASE_API_KEY` is configured; otherwise it uses the existing local browser bridge.

## Current P-001 automation target

The buyer-facing Gumroad description is maintained with a clickable CTA to:

`https://leverage-tools.pages.dev/fabrication-quote-calculator/`

The CTA is tracked with UTM parameters for the Gumroad source.

## Guardrails

No automation in this layer changes price, payout settings, bank/payment credentials, account email/password, or moves money. These remain Owner-controlled.

## Zero-cost policy

Leverage should use the Gumroad API whenever possible because it avoids browser compute. Browserbase is a fallback for UI-only actions, not the default path.
