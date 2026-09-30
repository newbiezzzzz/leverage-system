# Leverage AI Decision Governance

## Purpose

Prevent strategy drift caused by treating every new idea from an AI conversation as a replacement for the current Leverage direction.

This document is a persistent project rule. It is more authoritative than a conversational suggestion.

## Fixed decision hierarchy

1. Owner North Star
2. Current approved approach
3. Evidence from experiments and real operation
4. AI proposals and alternatives

AI proposals do not become decisions automatically.

## Anti-drift rules

- A new idea is an **ALTERNATIVE** until explicitly adopted.
- Never call a new idea "the best" merely because it is newer, more sophisticated, or more interesting.
- When a new problem appears, first diagnose whether the current approach can still achieve the objective.
- Prefer **KEEP** or **IMPROVE** over **REPLACE** when the current approach remains viable.
- A **REPLACE** decision requires evidence that the current approach cannot adequately meet the objective, or an explicit Owner decision.
- A new experiment can be run without changing the approved direction.
- Temporary tool errors, implementation bugs, slow progress, or one failed experiment are not by themselves proof that the overall approach should be replaced.
- Separate facts, hypotheses, alternatives, experiments, and decisions.
- Never present a hypothesis as a verified result.
- Never declare success from activity alone; success requires the defined evidence gates.
- Preserve previous decisions and reasons for changing them.

## Required response behavior for future Leverage discussions

Before recommending a directional change:

1. Read the current decision state.
2. State the current approved approach.
3. Identify the concrete problem.
4. Determine whether it is a **FIX**, **IMPROVEMENT**, or **REPLACEMENT** case.
5. Give the evidence supporting that classification.
6. Only then discuss alternatives.

When the Owner asks for a new idea, generate ideas freely but label them **ALTERNATIVE — NOT ADOPTED** unless the Owner explicitly adopts one or the change gate is satisfied.

## Change gate

A direction change is valid only when one or more of these is true:

- The current approach has a demonstrated structural blocker against the objective.
- Repeated verified evidence shows the current approach cannot satisfy a required gate.
- A material new constraint makes the current approach invalid.
- The Owner explicitly changes the objective or approves a replacement.

"ChatGPT has a better idea" is not a change condition.

## Owner communication rule

Owner-level updates should prioritize:

- current state
- actual progress
- verified result
- blocker requiring Owner action
- justified decision changes

Do not make the Owner repeatedly re-approve the same direction.
