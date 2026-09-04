# P-003 — AI Entertainment Factory

## Mission
Create a zero-cost entertainment production system that can repeatedly generate small games/content experiments, attract players/viewers, measure results, improve winners, and monetize validated attention with minimal Owner work.

## Operating constraints
- Startup cost target: RM0 until revenue.
- No financial action is authorized by this project foundation.
- Prefer free/local/open tools first.
- Owner approval remains required for public release, monetization changes, credentials, and other irreversible external actions unless explicitly delegated later.
- Do not build the full factory before the first end-to-end technical proof succeeds.

## First proof target
Demonstrate this chain with one tiny Roblox experience:

`Leverage -> AI coding workflow -> Roblox Studio -> run/test -> modify -> repeat`

Success means the AI can create and change a small playable experience without repeated manual copy/paste of code into Roblox Studio.

## Factory stages
1. Foundation
2. Roblox Studio setup
3. AI <-> Roblox Studio connection
4. Game idea engine
5. Game factory
6. AI playtester
7. Content factory
8. Distribution
9. Traffic & analytics
10. AI game optimizer
11. Monetization
12. Winner detection
13. Full automation loop

## Step 1 — Foundation checklist
- [x] Create dedicated P-003 project definition.
- [x] Define RM0 operating boundary.
- [x] Define Owner approval boundary.
- [x] Define first technical proof.
- [x] Preserve existing P-001/P-002 work; do not replace it.
- [ ] Verify local `D:\Leverage` working copy is synced with the P-003 branch.
- [x] Verify Roblox Studio is installed and launches.
- [x] Verify the selected MCP/AI bridge can connect to Roblox Studio.
- [ ] Execute the first tiny game proof.

## Step 4 — Game Idea Engine
- [x] Create machine-readable idea-engine contract: `control_plane/P003_GAME_IDEA_ENGINE.json`.
- [x] Add deterministic ranking worker: `workers/game_idea_worker.py`.
- [x] Score ideas across hook/first-minute, replayability/retention, social/co-play, content/shareability, novelty/differentiation, buildability/iteration speed, monetization fit, and discovery/metadata fit.
- [x] Add hard-reject rules for paid-core-loop dependency, copying, deceptive metadata/rewards, non-prototypable concepts, high unmanaged platform/safety risk, and slow experiment cycles.
- [x] Define thresholds: 80+ preferred build candidate, 70–79 prototype-only, below 70 reject.
- [ ] Connect an AI ideation prompt to generate candidate concepts automatically.
- [ ] Generate and rank the first live batch of concepts.

## Data to track from day one
Every game experiment should have a stable game/experiment ID and eventually capture:
- build version
- publish status
- visits/players
- acquisition source where available
- session/engagement metrics
- retention metrics
- monetization metrics
- experiment changes
- outcome: kill / improve / scale

## Next gate
Step 4 is complete when an AI-generated batch of ideas can be scored, rejected/ranked, and one build candidate can be handed to the Game Factory without manual restructuring.
