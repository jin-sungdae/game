# Companion Evolution Stage 3 — NEBLA v0.1

Base: origin/main `3a42e60`. Branch: `feature/companion-evolution-stage3-v01`. Existing Evolution domain, HTTP endpoint, row locking, history table, bootstrap and Glow→Reveal presentation are extended without replacement.

## Contract

| From | To | Server requirements |
|---|---|---|
| MOA / Stage1 | MOKORI / Stage2 | Level >=3 and Bond >=5 (unchanged) |
| MOKORI / Stage2 | NEBLA / Stage3 | Level >=6 and Bond >=12 |

Species remains `MOA`; Stage3 display name is `NEBLA`; asset identity is `moa/stage03`. Stage4/5 have no enabled transition. No gold/item cost, combat bonus, skill or progression change.

The existing GET `/api/v1/companions/active/evolution` returns LOCKED/AVAILABLE and server requirements. Existing bodyless POST `/api/v1/companions/active/evolve` rechecks the next eligible transition under the existing player then active-companion PostgreSQL row locks. It updates stage and inserts history atomically. The existing unique companion/from/to constraint guarantees one history row per transition. Completed history for the current stage returns ALREADY_EVOLVED when no further transition is available. Stage3 with recorded history is terminal ALREADY_EVOLVED; a manually seeded Stage3 without history remains the existing NOT_ELIGIBLE terminal contract. No Stage4 transition is enabled.

POST retains the existing next-eligible-transition semantics: a new explicit request from eligible Stage2 means Stage2→3, even if a previous Stage1→2 history exists. The worker does not automatically retry evolution mutations; it reconciles bootstrap/status after connection restoration. Clients must not replay an old Stage1 command as a new Stage2 intent when Stage2 is already eligible. Stage3 retries/concurrent requests cannot advance beyond Stage3.

## Persistence and assets

No migration is added or edited. Main already contains the NEBLA Stage3 master, a stage-capable companion row and V4 history with adjacent-stage FKs, uniqueness and audit fields. Main's latest migration is V9. History supports ordered `(1,2)` and `(2,3)` records without a new table. Level, EXP, Bond, Gold and companion identity are unchanged by evolution.

`companions.json` adds the stage03 canonical manifest path, NEBLA name and explicit `stageAssetStatus[3]=NOT_SUPPLIED`. There is no production PNG, generated placeholder PNG, animation or manifest scaffold. Existing loaders request only stage03 paths and cache missing results; they never borrow stage01/02 assets. Existing diagnostic rendering shows `NEBLA`, `Stage 3 · asset pending`, and the current behavior state. The validator accepts explicitly NOT_SUPPLIED absent manifests only with `--allow-missing`; strict animation delivery still fails for missing assets. Present malformed assets remain validated. Companion and Monster pipelines stay separate.

Before the server EVOLVED acknowledgement the identity remains Stage2. During acknowledged Glow, the renderer retains the previous MOKORI identity; Reveal exposes Stage3 diagnostic identity. Bootstrap restores Stage3 directly without replaying the transition. Movement, entity/window position, Battle, Inventory, Monster Spawn, focus/native code and Tao patch are unchanged.

## Validation

AUTOMATED PASS:

- Java/PostgreSQL: 139 tests, 0 failures/errors/skips. Stage2 Lv5/Bond12 and Lv6/Bond11 LOCKED; Lv6/Bond12 AVAILABLE. Four concurrent Stage3 requests produce one EVOLVED and three ALREADY_EVOLVED, exactly one Stage3 history. Retry, progression preservation and whole-transaction rollback on history conflict verified.
- Rust: 142 passed, 13 explicit live/platform ignores. Existing live evolution harness additionally executed twice against real Spring/PostgreSQL. Server-derived Stage3 identity, Glow→Reveal, unchanged position, restart and retry behavior verified.
- Animation/Content/Base/Monster and Presentation suites, including NEBLA missing-animation/missing-base isolation and actual diagnostic component DOM. Asset parser/validator 27 tests and automation 9 tests pass.
- npm build, Java bootJar, Rust clippy (`--no-deps -- -D warnings`), formatting, diff check, Tao integrity pass. Existing upstream Tao warnings remain; exactly three documented Tao files differ.
- Validator `--allow-missing`: 0 errors, 28 unprovided assets (existing animation/base supply gaps plus NEBLA). This is not a production-animation-delivery PASS.

Real restart evidence (2026-09-22): isolated `luma_stage3_live_test` on PostgreSQL port55483, real production bootJar port18103. Evolve MOA at Lv3/Bond5; set test-only progression to Lv6/EXP2345/Bond12/Gold73, then invoke the production API from compiled Desktop World. Result is NEBLA Stage3 with all progression preserved. Stop Spring PID80590 and start new PID80848 against the same DB; launch a fresh World in a new test process. Bootstrap/status restore Stage3 NEBLA and retry returns ALREADY_EVOLVED. DB has ordered histories 1→2 at Lv3/Bond5 and 2→3 at Lv6/Bond12, exactly two rows.

Reproduce using a fresh isolated `_test` database, bootJar and test-only SQL progression. Run `cargo test --manifest-path src-tauri/Cargo.toml live_evolution_world_slice -- --ignored --nocapture` with `LUMA_GAME_SERVER_URL` and `LUMA_EVOLUTION_FIXTURE=stage3-available`. Actually restart Spring against the same DB, then run with `LUMA_EVOLUTION_FIXTURE=stage3-restored`. No production RNG/progression override is introduced.

## Known limitations and human checks

Current `CombatRules.level(exp)` caps progression at Lv5. Consequently ordinary play cannot reach Lv6 yet. This request explicitly excludes Battle/progression changes, so the cap remains unchanged; Stage3 eligibility is implemented and tested with a Lv6 server fixture, not claimed naturally unlockable in current gameplay. Existing reward logic may recompute fixture levels through that same capped formula; this PR does not change it. A separately approved progression design is needed for natural access.

NEBLA assets remain NOT_SUPPLIED; only diagnostic rendering is expected. Real interactive NSPanel focus, typing, drag, transition appearance and on-screen visual sizing are MANUAL_REQUIRED / NOT_RUN. Compiled World/HTTP/SQL tests are not an interactive desktop visual audit.

No automatic merge. Rule activation and the Lv5/Lv6 product boundary require human review. Two automatic test repair iterations were used (unknown-stage fixture moved to Stage4; explicit absent Stage3 manifest/validator fixtures). Parallel overlap is limited to Evolution rule/repository/service, companion registry, backend evolution response validation and their tests; main.rs, Behavior, Movement, Battle, Inventory and Monster content/assets are untouched.
