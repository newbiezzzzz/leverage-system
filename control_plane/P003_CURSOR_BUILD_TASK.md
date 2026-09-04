# P-003-E001 — Cursor Build Task

## Objective
Build the first playable Roblox prototype for Leverage: **The Floor Is Voted**.

## Execution
Use the connected `Roblox_Studio` MCP server directly. Do not ask the Owner to copy/paste Luau code into Roblox Studio.

Read these project files first:
- `control_plane/P003_AI_ENTERTAINMENT_FACTORY.md`
- `control_plane/P003_GAME_IDEA_ENGINE.json`
- `data/p003_game_ideas_v1.json`
- `control_plane/P003_GAME_FACTORY.md` (when present)

### Build the smallest complete playable prototype
1. Modular tiled arena.
2. Player spawn.
3. Short countdown.
4. Clear voting UI.
5. Vote determines the next floor change/hazard.
6. Tiles disappear or become dangerous according to the winning choice.
7. Eliminated players are handled cleanly.
8. Winner detection.
9. Respawn and automatic next round.
10. Simple, polished, distinctive visual presentation.

## Iteration loop
`inspect -> construct -> script -> play -> observe -> fix -> retest -> polish`

Use Roblox-native parts and Luau. Avoid paid assets or external dependencies.

## Safety boundaries
- Do not publish.
- Do not configure monetization.
- Do not spend money.
- Do not change credentials.

## Completion evidence
Before reporting completion, verify:
- the experience is playable in Studio;
- at least one complete round can be run;
- the round resets for another round;
- voting affects the arena;
- no blocking script errors remain;
- modifications were performed through MCP rather than manual code copy/paste.

## Final report
Return:
- created components;
- current playability status;
- tests performed;
- remaining defects;
- exact Studio/MCP state.
