# Companion Progression v0.2 — Stage3 Reachability

Base: origin/main `b3b635f` (Battle Personality implementation included). Branch `feature/companion-progression-v02`. Existing progression is extended inside CombatRules; no new engine, schema/migration, client eligibility logic or configuration subsystem.

## Existing and updated contracts

`CombatRules.level(long)` maps **cumulative EXP** to Level. Old thresholds 0/100/300/600/1000 implied successive costs100/200/300/400, but stopped at5. Preserve these exactly and extend the same arithmetic series: `levelThreshold(L) = 50L * L * (L-1)`. Production `MAX_LEVEL=20` is defined once in CombatRules. Each additional level costs100 more EXP than the preceding step; this is not exponential growth.

| Level | Before cumulative EXP | v0.2 cumulative EXP |
|---:|---:|---:|
|1|0|0|
|2|100|100|
|3|300|300|
|4|600|600|
|5|1000 (cap)|1000|
|6|unsupported|1500|
|7|unsupported|2100|
|8|unsupported|2800|
|9|unsupported|3600|
|10|unsupported|4500|
|11|unsupported|5500|
|12|unsupported|6600|
|13|unsupported|7800|
|14|unsupported|9100|
|15|unsupported|10500|
|16|unsupported|12000|
|17|unsupported|13600|
|18|unsupported|15300|
|19|unsupported|17100|
|20|unsupported|19000|

`level` walks eligible thresholds with a bounded while loop (at most19 comparisons). It derives the final level from the entire cumulative EXP, so a large reward can cross multiple levels without discarding EXP. No per-level subtraction/reset. At max level, cumulative EXP continues to be stored. Existing `Math.addExact` rejects signed-bigint overflow and rolls back the complete reward transaction, including gold/history/turn; EXP never wraps or silently saturates. This exceptional storage-limit case retains the existing server 5xx failure contract.

`BattleService.reward` still grants `Monster Level *20` EXP, `Monster Level *10` gold and1 bond once per victory. Existing player lock, battle/encounter row locks, reward uniqueness and transaction remain unchanged. Single-active-encounter constraints mean concurrent attacks compete for the same terminal reward; one commits and later requests reject. No JVM mutex.

For LEVEL_UP feedback compare the new level with the **persisted previous level**, not the new curve applied to old EXP. This matters for existing players with saved Level5 and EXP beyond1500. Such rows retain their current persisted level on bootstrap and reconcile upward on their next successful Battle reward. No migration/backfill or bootstrap write is introduced.

Bootstrap reads persisted Level/EXP/Bond. Existing EvolutionRules still require Level3/Bond5 for MOKORI and Level6/Bond12 for NEBLA. Evolution and ItemService remain server-authoritative and unchanged. A normal reward can now unlock NEBLA; Stage4/5 requirements are not enabled.

## Pacing simulation

Unchanged production monster levels1–3 grant20/40/60 EXP per victory. Deterministic unit simulation starts at cumulative EXP0, carries overshoot forward and checks the real CombatRules thresholds:

| Transition |20 EXP wins|40 EXP wins|60 EXP wins|
|---|---:|---:|---:|
|1→2|5|3|2|
|2→3|10|5|3|
|3→4|15|7|5|
|4→5|20|10|7|
|5→6|25|13|8|
|Total1→6|75|38|25|

The8-wins final60-EXP step starts with1020 EXP carried from prior wins. Starting **exactly at1000 EXP**, Lv5→6 requires25/13/**9** victories at20/40/60 EXP. Level6 requires1500 total EXP. At fixed reward values, MOA→MOKORI eligibility is reached after15/8/5 wins, and NEBLA eligibility after75/38/25 wins. Each victory adds1 bond, so both bond thresholds are naturally met on these uninterrupted victory paths. Mixed monster levels fall between25 and75 wins; real wall-clock pacing additionally depends on spawn opportunities, battle outcomes and player actions. No timing or damage rebalance is made. Seventy-five victories on only level1 monsters is the slow case; product review should assess whether that grind is acceptable.

## Verification

AUTOMATED PASS: Java21/PostgreSQL184 tests, zero failures/errors/skips. Rust142 passed,13 explicitly ignored live/platform fixtures. Animation/Content/Base/Presentation, Asset27 and automation9 tests, npm build, bootJar, clippy, formatting, diff check and Tao integrity pass. Tao retains exactly its three documented patches; native focus behavior is not claimed manually verified.

New checks include all20 exact thresholds and immediately-below boundaries; Lv1,4→5,5→6,6→7; synthetic large reward crossing multiple levels; MAX_LEVEL and Long.MAX_VALUE; cumulative EXP preservation; real unchanged rewards; competing winning attacks with one committed reward; storage overflow rolling back the whole turn; legacy Level5/high-EXP multi-level reconciliation with LEVEL_UP; MOKORI Lv6/Bond11 LOCKED; real Berry purchase/use to Bond12 AVAILABLE; NEBLA evolution preserving progression; continued NEBLA Battle rewards to Lv7.

A fresh initial MOA fixture performs **75 actual HTTP Battle victories with no progression-field writes during the path**. It evolves to MOKORI after win15, reaches Lv5 after win50, Lv6 after win75, and evolves to NEBLA. Exactly75 reward records and cumulative1500 EXP prove reachability without a Lv6 fixture. Test-only fixed RNG selects existing PIP Level1; no production RNG/weights/HP/reward changes.

Separate live process validation: isolated PostgreSQL `luma_progression_live_test`, port55487; existing test-only Spring LiveValidationServer, port18107. Initial fixture MOKORI Lv5/EXP1480/Bond10/Gold100. Real Battle produces Lv6/EXP1500/Bond11/Gold110 and LOCKED. Stop Spring PID49789, start PID49890 against the same DB: values persist. Purchase Berry at unchanged30 gold, use its unchanged+1 effect: Bond12, AVAILABLE, EVOLVED NEBLA; EXP1500/Level6/Bond12/Gold80 preserved by evolution. Stop/restart Spring again and verify NEBLA bootstrap/retry persistence.

Reproduce with a dedicated loopback `_test` database and `./server/gradlew -p server liveValidation`. Set `LUMA_DB_URL`, `LUMA_DB_USER`, `LUMA_SERVER_PORT`. After initial fixture setup, run `LUMA_PROGRESSION_TEST_URL=http://127.0.0.1:18107 LUMA_ISOLATED_TEST=1 python3 tests/live/progression.py reward`. Actually stop/start Spring, run phase `berry-evolve`, stop/start again, run phase `restored`. The script mutates only the explicitly selected isolated test server, and performs no SQL progression changes itself. Production bootJar does not include the fixed-RNG test configuration.

## Boundaries and review

Production changes: CombatRules progression mapping and BattleService LEVEL_UP comparison only. Existing damage/HP/Capture/weights/Personality/Behavior/Discovery/Shop/Item effects remain unchanged. Higher naturally reachable levels use the existing damage formula; this is a consequence of progression, not a new combat bonus. Old cap data reconcile on next reward, not startup. MAX_LEVEL20 may enable future evolution rules but supplies no new stages/content by itself. NEBLA remains the existing diagnostic fallback when its assets are NOT_SUPPLIED.

Changed files: CombatRules.java, BattleService.java; BattleIntegrationTest.java, ProgressionTest.java, ProgressionIntegrationTest.java; tests/live/progression.py; this document. Shared overlap is the existing server formula/reward test surface; no Desktop/native code, assets, migrations or dependency changes.

MANUAL_REQUIRED / NOT_RUN: interactive desktop focus/typing/drag, visible level-up and NEBLA diagnostic transition, and real-play pacing assessment. HTTP/PostgreSQL process restart checks are not a manual Desktop visual audit. CI PASS is not approval to merge. Human review of progression pacing remains required; do not auto merge. One automatic correction iteration addressed legacy-cap LEVEL_UP feedback.
