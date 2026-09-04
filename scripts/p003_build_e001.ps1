$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

Write-Host 'P-003 E001 — The Floor Is Voted' -ForegroundColor Cyan
Write-Host "Workspace: $RepoRoot"

if (-not (Get-Command agent -ErrorAction SilentlyContinue)) {
    throw 'Cursor Agent CLI is not installed or not on PATH.'
}

$prompt = @'
You are the P-003 Game Factory worker. Execute the build task below completely.

READ FIRST:
- control_plane/P003_GAME_FACTORY.md
- control_plane/P003_CURSOR_BUILD_TASK.md
- control_plane/P003_GAME_IDEA_ENGINE.json
- data/p003_experiments/P003-E001/build_report.json
- data/p003_game_ideas_v1.json

TARGET:
Experiment P003-E001 / Game ID floor-is-voted / Title The Floor Is Voted.

OBJECTIVE:
Create the smallest complete, polished, playable Roblox multiplayer prototype directly in the currently connected Roblox Studio instance using Roblox_Studio MCP. Do NOT ask the Owner to copy/paste code into Roblox Studio.

BUILD LOOP:
inspect -> construct -> script -> test -> inspect output/errors -> fix -> retest -> polish -> report

REQUIRED:
- One compact modular tiled arena.
- Player spawning.
- Short readable countdown.
- Movement across the tiled floor.
- Clear voting UI with at least two modifiers/hazards.
- Winning vote changes the next hazard/layout.
- Tile removal/danger behavior is visually obvious.
- Eliminated players become spectators or otherwise cannot interfere.
- Winner detection and clear result state.
- Respawn and automatic next round.
- Basic distinctive visual identity and readable UI.
- Keep all systems modular and named clearly for later factory automation.

TECHNICAL RULES:
- Prefer Roblox-native Parts, Luau and built-in UI.
- No paid services/assets/dependencies.
- Do not publish.
- Do not change monetization.
- Keep changes inside the open Studio place.

VERIFICATION:
- Run/playtest the experience through MCP.
- Confirm at least one full round from spawn to result.
- Fix blocking script/runtime errors.
- Confirm round reset works.
- Inspect the final DataModel for the expected systems.

OUTPUT:
1. Give a concise summary of what you built.
2. Report playtest results and any remaining issues.
3. Update data/p003_experiments/P003-E001/build_report.json with the actual result.
4. Do not claim success unless the game was actually tested.
'@

Write-Host 'Starting Cursor Agent in non-interactive mode...' -ForegroundColor Yellow
agent -p $prompt --output-format text --approve-mcps Roblox_Studio

Write-Host 'P-003 E001 agent run finished.' -ForegroundColor Green
