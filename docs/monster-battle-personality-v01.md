# Monster Battle Personality v0.1

## Implementation proposal

Base origin/main 3a42e60. Reuse existing BattleService transactions, turn counter, RandomSource boundary, CombatRules, ItemRules, terminal/reward and Collection persistence. Add a separate BattlePersonality enum and pure decision policy (ATTACK/WAIT), mapped explicitly by one field in the existing Monster content JSON. Ambient BehaviorProfile remains independent. No engine, migration, armor, stat multiplier or client RNG.

A server decision occurs only at the existing monster counterattack opportunity (nonlethal player attack or failed capture while ACTIVE). WAIT skips that counterattack; it does not reduce the player's damage, add a turn, or grant armor. Kill turns still resolve victory first. Capture success and terminal battles never request an action. Preserve existing damage/HP/capture/reward formulas and Item contracts.

Use the existing injectable RandomSource for server decisions; a pure policy accepts seeded RandomSource for replay/simulation. Random draws are bounded and validated. Tests fix decision RNG while preserving production selection/capture boundaries. Add compact MONSTER_WAIT feedback via the existing event contract if supported, not another UI stream.

Initial tuning question: legacy BALANCED attacks100% of opportunities. To make AGGRESSIVE more attack-prone, proposed BALANCED85% / AGGRESSIVE100% / DEFENSIVE45%, ERRATIC alternating25%/90% by existing turn parity. This is provisional evidence, not final balance approval. Exact BALANCED behavior choice is pending user preference. No damage multiplier or new attack opportunity will be introduced to force differentiation.

Simulate many deterministic seeds and levels1–3 against companion level1, recording average player actions, attack ratio and turn-count histogram. Player attack damage and monster HP remain unchanged, so attack-only victory length is still3/4/5 player actions at levels1/2/3. Failed-capture loops remain user-driven as before; do not claim a global wall-clock bound.

Alternatives rejected: merging ambient/combat enums, desktop probability decisions, separate engine, per-species damage buffs, extra attacks or blocking presentation timers. Gameplay design approval and main merge remain HUMAN_REVIEW_REQUIRED. No auto merge.
