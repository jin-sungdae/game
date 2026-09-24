# Alpha Vertical Slice v1 — integration certification

Status: READY_FOR_HUMAN_REVIEW after CI passes. No automatic merge.
Base: origin/main `69553f3` (Bond progression #41). Isolated branch `test/alpha-vertical-slice-v1`.

## Environment and evidence boundaries

AUTOMATED: newly initialized PostgreSQL 16 cluster/database, actual Spring Boot bootJar, separately compiled Rust World processes, production frontend build. No user database or pre-existing save was used. The opt-in runner shuts down and removes its database cluster. Local execution evidence was produced on 2026-09-24 under `/tmp/luma-alpha-certification-01` from this working tree before its certification commit; it must not be mistaken for an execution of that later commit.

BROWSER: a production-built, read-only harness renders actual exported World frames using the existing CompanionVisual, render identity, evolution and Dex projections. This verifies the production rendering components and PNG loading, not an end-to-end native NSPanel input session.

CLOCK_FIXTURE: World time advances between spawn opportunities; the local calendar is injected as NIGHT while preserving the current UTC instant. Only `last_bond_interaction_at` is set to 300 seconds ago in the new test DB to exercise cooldown expiry. No SQL changes to EXP, Bond, Gold, level, stage, rewards, inventory or monster selection. Server RNG and production rules remain unchanged. Battle counts below describe this random run, not balance guarantees or elapsed playtime.

## Certification matrix

PASS means the stated automated scope passed. Native manual checks below remain outstanding.

| Category | Result | Evidence / limits |
|---|---|---|
| Fresh Bootstrap | PASS | New save: MOA/Stage1/Lv1/EXP0/Bond0/Gold0; empty inventory; 30 Dex entries UNDISCOVERED; consistent HTTP/World projections. |
| MOA | PASS | Production stage01 PNG in browser; World movement, behavior, interaction and same-stage fallback regression. |
| 15 Monster Pool | PASS | Real migrated masters: 15 enabled identities, weights 700+200+60+1=961. All 961 boundaries at levels1 and3 tested. |
| Spawn | PASS | Production Director/HTTP/placement in fresh journey; all15 movement and safe-placement contracts in deterministic World regression. |
| NIGHT | PASS | SHADE/LUNET/NOCT 21:59 reject,22:00 allow,05:59 allow,06:00 reject; NOCT SPECIAL/NIGHT/EDGE preserved. |
| Discovery | PASS | DTO alone leaves UNDISCOVERED; successful placement then POST persists CHIRP without capture; new Spring/World restores DISCOVERED with zero captures. |
| Behavior | PASS | All15 actual World trajectories, 1,800 ticks each; seven behavior patterns and movement constraints; battle/drag/terminal suspension. |
| Battle Personality | PASS | Controlled Spring integration exercises BALANCED/DEFENSIVE/AGGRESSIVE/ERRATIC, ATTACK/WAIT and formula preservation. |
| Battle | PASS | Actual bootJar encounters and39 victories; defeat covered by controlled HTTP integration, not observed in this random journey. |
| Capture | PASS | Actual36 successes/4 failures; controlled tests verify rarity bases .35/.25/.15/.05, HP term, Charm .10, clamp and EPIC fail-closed. |
| Dex | PASS | Server-backed UNDISCOVERED/DISCOVERED/CAPTURED, masking and all15 identity/rarity/asset mapping regression. |
| Reward | PASS | Every live victory verifies level×20 EXP, level×10 Gold and unchanged Bond. |
| Shop | PASS | Actual earned Gold purchases all3 items; inventory and Gold persist across restart. Insufficient-funds duplicate purchase rejected. |
| Potion | PASS | Used after actual damage, min(30,missingHP) recovery, one consumption; subsequent empty-inventory use rejected. |
| Charm | PASS | Live capture bonus .10, one consumption, repeat empty-inventory use rejected; failed-capture behavior covered separately by HTTP tests. |
| Interaction | PASS | First+1, immediate retry+0 without extending cooldown, timestamp fixture then+1. |
| Bond | PASS | Two awarded interactions plus10 real Berry transactions; battle Bond0; Berry independent of interaction cooldown. |
| MOKORI | PASS | Lv3/Bond5 gate, transaction/history, duplicate rejection; old identity before acknowledgment and during Glow, stage02 on Reveal. |
| Lv6 Progression | PASS | Actual battle rewards through Lv5 toLv6; EXP1520; threshold/MAX_LEVEL regressions unchanged. |
| NEBLA | PASS | Lv6/Bond11 LOCKED; actual Berry→12 AVAILABLE; evolve, Glow→Reveal; real stage03/base.png 256×256, no diagnostic fallback. |
| Restart | PASS | New JVM/new World: entire state comparison equal; NEBLA, progression, Gold, inventory, Dex, collection, eligibility and both histories preserved. No evolution replay. |
| Failure Recovery | PASS | Stopped server bootstrap/interaction failures leave Bond unchanged; discovery four bounded attempts; duplicate capture/evolution rejected; invalid content/unknown asset fail-closed regression. |
| Performance | PASS | No production polling/interval/RAF/network loop introduced; existing15-controller scheduling and World trajectory budgets pass. Not a native CPU/GPU benchmark. |

### Actual journey

- Fresh→MOKORI: **9 victories**, Lv3/EXP340/Bond5/Gold20.
- Fresh→NEBLA: **39 victories**, Lv6/EXP1520/Bond12/Gold400.
- Two awarded interactions; one additional cooldown request awarded zero.
-10 Berry (300 Gold),1 Potion (20 Gold),1 Charm (40 Gold): **760 earned−360 spent=400 remaining**.
-40 capture outcomes:36 success,4 failure. One early Charm capture ended an encounter before victory; therefore capture attempts and victory counts differ.
- Actual random journey discovered/captured14 species: PIP, MELLO, MOSSY, CHIRP, BUBU, PEBB, PUFF, TIKKI, MIMI, WISP, SHADE, EMBER, LUNET, NOVA. **NOCT random bootJar encounter: NOT_RUN** (not drawn). Its production master, weighted boundary, NIGHT/EDGE, asset and World behavior are covered by deterministic tests. No forced RNG or fabricated encounter was used in the journey.
- **Random bootJar defeat: NOT_RUN**; controlled real HTTP/PostgreSQL battle integration covers defeat.
- Shop requests do not have general idempotency keys: another funded purchase is a new purchase. This certification proves transaction/funds safety and existing busy guards, not arbitrary purchase deduplication.

### Restart and history

Exactly two ordered transitions, unchanged after restart:

| Transition | Level | Bond | Persisted time |
|---|---:|---:|---|
| MOA→MOKORI |3|5|2026-09-24T21:17:03.333733+09:00|
| MOKORI→NEBLA |6|12|2026-09-24T21:17:03.809668+09:00|

All three consumed inventory rows remain quantity0. Duplicate evolution requests return ALREADY without another history. [State comparison](evidence/alpha-vertical-slice-v1/restart-comparison.json), [before history](evidence/alpha-vertical-slice-v1/history-before.json), [after history](evidence/alpha-vertical-slice-v1/history-after.json).

## Integration defect and scope

Found and fixed one display inconsistency: Dex said discovery records were limited to the current run although the server persists them. Updated that single hint to “발견·포획 기록은 서버에 저장됩니다” and added a rendered-copy regression. No feature, balance, schema, dependency, architecture, runtime authority or Tao changes. One test-harness build correction wrapped startup in an async function for the existing Vite target; it was not a gameplay defect.

No automated functional blockers remain in the tested scope. Native certification is incomplete until the manual checks below are performed.

## Reproduction and regression

From the isolated worktree, use Java21 and PostgreSQL16. Build bootJar with `./server/gradlew -p server bootJar --no-daemon` (set JAVA_HOME). Then:

```sh
PG_BIN=/opt/homebrew/opt/postgresql@16/bin \
JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home \
python3 scripts/analysis/run_alpha_vertical_slice.py --output /tmp/luma-alpha-new-run
```

The output must not already exist. This ignored live test is intentionally opt-in; ordinary cargo tests do not run a bootJar journey. The runner invokes it in fresh/offline/progress/restored processes and owns all service lifecycle and database state.

Renderer: `LUMA_ALPHA_WEB_OUT=/tmp/luma-alpha-web npx vite build --config tests/live/alpha-vite.config.ts`; copy exported `frames-*.json` into the output's `evidence/` directory; serve that output and open `/tests/live/alpha.html`. It has no mutation controls and is not a production app entry point. Browser inspection confirmed stage01→stage02→stage03 PNGs, each256×256 and no diagnostic fallback; [observed renderer results](evidence/alpha-vertical-slice-v1/renderer.json).

Local AUTOMATED results:

| Suite | Result |
|---|---|
| Spring/PostgreSQL + bootJar |196 tests,0 failures/errors/skipped; PASS|
| Rust locked tests |146 passed,16 ignored; PASS (new ignored live test executed separately in all4 phases)|
| cargo clippy --no-deps -- -D warnings |PASS; existing vendored Tao warnings remain|
| npm production build / animation / presentation |PASS; build and presentation repeated after copy fix|
| Asset tests / automation tests |30 /18 passed|
| Asset Validator allow-missing |0 errors;27 existing NOT_SUPPLIED entries|
| strict-alpha |PASS,0 missing production monster bases|
| Tao integrity |PASS|
| Read-only renderer production build |PASS|

Relevant exhaustive tests: `Batch3ActivationTest.finalFifteenProductionMastersAndEveryWeightedBoundary`, `MonsterContentTest`, `BattlePersonalityIntegrationTest`, `BattleIntegrationTest`, Rust `batch3_assets_metadata_motion_night_and_restart`, `batch3_both_edges_and_fail_closed_per_species`, `daytime_night_restore_resolves_same_id_without_create_spam`, `all_fifteen_world_traces_preserve_identity_constraints_and_companion`, `seeded_replay_bias_and_fifteen_controller_tick_budget`, and discovery sync bounded retry/idempotence tests. These validate controlled edge cases independently of random journey observations.

Compact checked-in evidence: [summary](evidence/alpha-vertical-slice-v1/summary.json), [masters](evidence/alpha-vertical-slice-v1/masters.json), [offline](evidence/alpha-vertical-slice-v1/offline.json), restart/history and renderer JSON above. Full local logs and frames remain in `/tmp/luma-alpha-certification-01`; regression logs are `/tmp/luma-alpha-{server,rust,desktop,final-desktop,renderer-build}.log`. GitHub CI results are attached to the PR's current commit and must be checked separately from this local record.

## Focus, platform and manual verification

Static diff: no new key-window, activateApp or focus-stealing APIs; no runtime timers, RAF or per-frame network calls added. Test-only World helpers and renderer do not alter native window behavior.

**PLATFORM_REQUIRED / MANUAL_REQUIRED (NOT_RUN):** actual macOS NSPanel typing/click-through/drag during evolution and battle; Never Steal Focus while another application receives typing; multi-monitor/Dock/MenuBar placement on real displays; native visual pacing and long-running CPU/GPU observation. Browser frames and compiled World simulations do not substitute for these checks.

Changed files: test-only backend module registration and `alpha_vertical_slice.rs`; lifecycle runner; three `tests/live/alpha*` harness files; this report and seven evidence JSON files; CollectionDex hint and its presentation test. No overlap with production gameplay/content/asset changes from parallel work.
