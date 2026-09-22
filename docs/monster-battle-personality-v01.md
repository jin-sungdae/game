# Monster Battle Personality v0.1

## Implementation proposal

Base origin/main 3a42e60. Reuse existing BattleService transactions, turn counter, RandomSource boundary, CombatRules, ItemRules, terminal/reward and Collection persistence. Add a separate BattlePersonality enum and pure decision policy (ATTACK/WAIT), mapped explicitly by one field in the existing Monster content JSON. Ambient BehaviorProfile remains independent. No engine, migration, armor, stat multiplier or client RNG.

A server decision occurs only at the existing monster counterattack opportunity (nonlethal player attack or failed capture while ACTIVE). WAIT skips that counterattack; it does not reduce the player's damage, add a turn, or grant armor. Kill turns still resolve victory first. Capture success and terminal battles never request an action. Preserve existing damage/HP/capture/reward formulas and Item contracts.

Use the existing injectable RandomSource for server decisions; a pure policy accepts seeded RandomSource for replay/simulation. Random draws are bounded and validated. Tests fix decision RNG while preserving production selection/capture boundaries. Add compact MONSTER_WAIT feedback via the existing event contract if supported, not another UI stream.

Initial tuning question: legacy BALANCED attacks100% of opportunities. To make AGGRESSIVE more attack-prone, proposed BALANCED85% / AGGRESSIVE100% / DEFENSIVE45%, ERRATIC alternating25%/90% by existing turn parity. This is provisional evidence, not final balance approval. Exact BALANCED behavior choice is pending user preference. No damage multiplier or new attack opportunity will be introduced to force differentiation.

Simulate many deterministic seeds and levels1–3 against companion level1, recording average player actions, attack ratio and turn-count histogram. Player attack damage and monster HP remain unchanged, so attack-only victory length is still3/4/5 player actions at levels1/2/3. Failed-capture loops remain user-driven as before; do not claim a global wall-clock bound.

Alternatives rejected: merging ambient/combat enums, desktop probability decisions, separate engine, per-species damage buffs, extra attacks or blocking presentation timers. Gameplay design approval and main merge remain HUMAN_REVIEW_REQUIRED. No auto merge.

## User-specified mapping (not yet applied)

| Personality | Alpha monsters |
|---|---|
| BALANCED | PIP, MELLO, BUBU, PUFF, TIKKI |
| DEFENSIVE | MOSSY, PEBB, WISP, LUNET |
| AGGRESSIVE | EMBER, NOCT |
| ERRATIC | CHIRP, MIMI, SHADE, NOVA |

## Preliminary proposal simulation, not server validation

Read-only Python model, seeds0..9999, levels1–3 distributed3334/3333/3333, companion level1, attack-only player strategy. Uses the existing12 damage and monster HP30/40/50. No repository gameplay code or DB was changed.

| Proposed policy | Attack decision ratio | Average player actions | Battle length histogram |
|---|---|---|---|
| Legacy100% | 1.0000 | 3.9999 | 3:3334,4:3333,5:3333 |
| BALANCED85% | .8516 | 3.9999 | same |
| AGGRESSIVE100% | 1.0000 | 3.9999 | same |
| DEFENSIVE45% | .4464 | 3.9999 | same |
| ERRATIC25%/90% | .5410 | 3.9999 | same |

This checks the proposed design's bounded attack-only length, not Java RandomSource reproducibility or implemented server behavior. Java/domain simulation and integration regression remain NOT_RUN until tuning is approved and implementation proceeds. These proposed thresholds are not final balance.

Automatic approval review rejected the initial production edit because the optional personality preference had no submitted response. No production code was changed. Explicit approval of tuning is now pending; do not interpret elapsed time as approval.

## Approved implementation v0.1 (supersedes pending-status notes above)

The user explicitly approved #35's architecture, mapping and tuning after its merge. The original proposal and preliminary Python evidence above are retained as history. The Java results below are the implementation evidence and replace Python results for acceptance. Implementation base: origin/main dc160d8; follow-up branch feature/monster-battle-personality-implementation-v01.

`monster-dex.json` is the only fifteen-species mapping source. New `battlePersonality` is separate from ambient behaviorProfile; provisional non-Alpha slots use null. Java and TypeScript validate the enum and require it for Alpha content. Rates live only in the server BattleDecision policy: BALANCED85, DEFENSIVE45, AGGRESSIVE100, ERRATIC25 on even completed turns /90 on odd. Initial persisted turn_no=0 therefore uses25; each existing attack/failed-capture save increments turn exactly once. GET/restart retains parity. No new counter, clock or stored RNG state.

BattleService calls this pure policy only at the two existing counterattack sites: surviving player attack and failed ACTIVE capture. It uses injected RandomSource.nextLong(100); tests provide java.util.Random seeds. Unknown/missing personality and out-of-bound RNG fail closed via GameUnavailable and roll back the transaction. WAIT returns unchanged companion HP and emits MONSTER_WAIT; player damage, monster HP, turn progression and state transitions remain unchanged. AGGRESSIVE has one normal counterattack, never an extra attack or multiplier. Victory, terminal retries and successful capture have no personality RNG call. Existing capture1,000,000-bound draws remain separate calls on the same injectable RNG; added decision draws intentionally change stream consumption, not the capture formula or distribution. Production restart does not promise RNG replay, only persisted turn parity; same seed plus identical policy calls is reproducible in tests.

The Battle events array is extended additively; no DTO field or stream is required. Desktop shows one existing status line, '<monster> waits', only for ACTIVE/ACTIVE with MONSTER_WAIT. Terminal/capture feedback keeps priority, and refresh has no stale WAIT replay. No new animation, native surface, timer or Desktop probability computation.

### Actual Java Domain simulation

BattleDecisionTest runs30,000 seeded battles for each personality (120,000 total), seeds0..29999, monster levels1–3 equally distributed, companion level1, repeated player Attack. It calls the implemented BattleDecision and CombatRules, not a reimplemented probability formula. Baseline legacy always-counter behavior has the same3/4/5 player-action lengths; AGGRESSIVE is its100% counterattack case. This scenario does not model user think time or repeated capture attempts.

| Personality | ATTACK ratio | WAIT ratio | Average player actions | Average monster counterattacks | Terminal consistency |
|---|---:|---:|---:|---:|---|
| BALANCED | .849322 | .150678 | 4.000000 | 2.547967 | 30000/30000 VICTORY |
| DEFENSIVE | .450244 | .549756 | 4.000000 | 1.350733 | 30000/30000 VICTORY |
| AGGRESSIVE | 1.000000 | .000000 | 4.000000 | 3.000000 | 30000/30000 VICTORY |
| ERRATIC | .539089 | .460911 | 4.000000 | 1.617267 | 30000/30000 VICTORY |

Each histogram is3 actions:10000,4:10000,5:10000. ERRATIC's aggregate is not57.5% because these battles have more even opportunities:5 even versus4 odd across levels1–3. Exhaustive100-roll tests independently verify exactly25/90 attacks at even/odd parity, plus85/45/100 for other policies. Seed42 replay is identical; seed43 produces bounded variation for stochastic policies, and AGGRESSIVE correctly stays identical. These approved initial values are tuning evidence, not a claim of final game balance.

### Verification and changed files

Local AUTOMATED PASS: Java/PostgreSQL174 tests, bootJar; Rust141 deterministic tests (13 opt-in live fixtures NOT_RUN), clippy/fmt/native link; npm build;59 animation/content tests;57 presentation tests;27 asset tests;9 automation tests; strict-alpha15/15; content projection sync; Tao integrity; whitespace.

New tests cover15 mappings, exhaustive thresholds/parity, seeded replay, actual Java simulation,15-species HTTP WAIT/ATTACK/player damage/one-counter cap/Potion/Charm/Capture/Collection,15-species victory/reward/terminal no-action, failed capture parity after GET, invalid RNG rollback of turn/damage/Charm, and one-time Charm consumption even on WAIT. Existing all15 activation tests still force valid attack decisions for their original baseline assertions; old capture-failure mocks now target the1,000,000 capture bound only, preserving those assertions instead of returning an invalid decision roll.

Changed files: content JSON and TypeScript parser; new BattlePersonality/BattleDecision; MonsterContent parser; BattleService's two counterattack sites; compact Interaction/model feedback; new Java policy/integration tests and existing capture mock specificity; frontend content/feedback tests; this document. CombatRules, ItemRules, migrations, assets, Spawn, ambient Behavior controller, Discovery persistence, rarity presentation and native code remain unchanged. Existing regression suites for each run in local checks and final SHA-bound CI.

MANUAL_REQUIRED: native compact feedback/readability, focus/typing/clicking, and human gameplay feel/tuning acceptance. No new desktop launch is claimed. RandomSource remains the existing production RNG; seeded simulations are reproducibility evidence, not live encounter predictions. No auto merge. One local repair iteration fixed nullable Battle typing in the feedback helper.
