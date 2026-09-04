# P-003 — Game Factory

## Purpose
Turn a selected P-003 game concept into a small, playable Roblox experience through the connected AI development workflow with minimal Owner work.

## First build target
- Experiment ID: `P003-E001`
- Game ID: `floor-is-voted`
- Title: `The Floor Is Voted`
- Build type: small multiplayer prototype
- Initial scope: one modular arena, tile removal, voting UI, round loop, respawn/win state

## Build principles
1. Build the smallest complete fun loop first.
2. Prefer Roblox-native parts, Luau, and simple UI before custom assets.
3. Keep systems modular so AI can replace individual components without rebuilding the whole experience.
4. Make the first 60 seconds understandable and playable.
5. Prioritize visual clarity and a distinctive presentation; do not ship a technically working but visually generic prototype.
6. All game content must be original or use assets with clear permission/licensing.
7. No paid dependencies or services are required for the prototype.
8. Do not publish publicly or change monetization without Owner approval.

## Required prototype loop
1. Players spawn into the arena.
2. A short countdown starts the round.
3. Players move across a tiled floor.
4. The game presents a clear vote between floor hazards/modifiers.
5. The winning vote changes which tiles disappear or become dangerous.
6. Surviving players remain active while eliminated players enter a spectator state.
7. A winner is declared when the round ends.
8. Players respawn and another round begins.

## Acceptance criteria
- Playable in Roblox Studio.
- No blocking script errors during a normal round.
- Player movement and camera remain usable.
- Vote UI is understandable without external instructions.
- At least one complete round can be played from spawn to result.
- Round reset works repeatedly.
- Prototype remains responsive with multiple local test players where supported.
- Changes can be made through MCP without manual code copy/paste.

## Build sequence
`inspect -> plan -> construct -> script -> test -> observe errors -> fix -> retest -> polish -> report`

## Deliverables
- Roblox Studio experience state updated by MCP.
- A concise build report stored in `data/p003_experiments/P003-E001/build_report.json` after the proof.
- Any important scripts/components documented so later factory stages can modify them.

## Stop conditions
Stop and report instead of publishing when:
- a required Roblox permission or account action is needed;
- an external paid service is required;
- an irreversible external change is required;
- the MCP connection is lost;
- the prototype cannot reach a playable state after reasonable repair cycles.
