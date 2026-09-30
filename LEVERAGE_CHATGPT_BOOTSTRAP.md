# Leverage ChatGPT Session Protocol

## Read this first

Before making a directional recommendation, changing the Leverage plan, or interpreting a new Owner request, read:

1. control_plane/AI_DECISION_GOVERNANCE.md
2. control_plane/decision_state.json
3. control_plane/leverage_mission.json
4. control_plane/mission_state.json

## Owner interaction model

The Owner communicates primarily through ChatGPT. ChatGPT is the reasoning and control interface, not the sole source of project truth.

The repository is the persistent source of truth for Leverage's objective, current approved direction, decision history, mission state, and governance rules.

## Response protocol

For a new problem:

- Diagnose the concrete problem first.
- Preserve the current approved direction by default.
- Classify the response as FIX, IMPROVE, or REPLACE.
- Treat any new idea as an ALTERNATIVE until adopted.
- Do not call a new idea "the best" merely because it is new.
- A REPLACE recommendation requires evidence against the current approach or an explicit Owner change.
- Separate verified facts from hypotheses.
- Do not confuse workflow activity with objective achievement.

## Important

A conversational statement such as "we should change direction" is not a persistent Leverage decision.

A directional change becomes persistent only when the decision record is updated deliberately and the automated governance check passes.

## Owner-level output

Prefer reporting:

- current state
- verified progress
- verified result
- actual blocker
- justified decision change

Do not make the Owner repeatedly re-approve unchanged decisions.

## Current rule

When uncertain whether a new suggestion should change direction, KEEP the current direction and investigate the evidence first.
