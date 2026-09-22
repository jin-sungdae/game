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
