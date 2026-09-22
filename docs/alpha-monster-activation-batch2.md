# Alpha Monster Gameplay Activation — Batch 2 v0.1

## Proposal before implementation

Base origin/main 1822e58 includes Advanced Spawn #27 and production asset delivery #28. Existing strict-alpha validates all 15 PNGs (0 errors, 0 missing). This isolated feature/alpha-monster-activation-batch2 worktree owns V7 only, adding PEBB/PUFF/TIKKI/MIMI/WISP masters with content-matching names, profiles, levels1–3 and rarity-default weights. Previous migrations/masters and Batch3 content remain unchanged.

Reuse Monster Content, Asset Registry, Spawn runtime, MovementController and server selection/combat/inventory/collection. Extend exact approved asset loading for these five; permit UNCOMMON alongside COMMON in the existing server capture formula. COMMON0.35/UNCOMMON0.25 plus existing HP term, Charm+0.10 and clamps remain server-owned. Preserve STATIC/EDGE for MIMI, FLOATING/FREE_AREA for PUFF/WISP, GROUND for PEBB/TIKKI; do not replace profiles. Seven COMMON weight100 and three UNCOMMON weight50 total850. No desktop probability calculation.

Activation requires per-species asset/master/World/server acceptance, including same-ID restart without CREATE, movement, battle, potion/charm capture, collection and cooldown. Implement tests with production definitions and commit readiness only after isolated PostgreSQL + Spring + actual Desktop World vertical slices pass. No new engine, schema columns, production art, dependencies or native focus changes.

Alternatives rejected: flag-only activation bypasses integration evidence; replacing STATIC with GROUND changes MIMI's contract; client capture/selection violates server authority. Existing adapters and additive tests suffice. Gameplay activation acceptance and merge remain HUMAN_REVIEW_REQUIRED; no auto merge. Native visible focus/input/visual acceptance remains MANUAL_REQUIRED even after automated World/native compilation checks.

## Completed activation and evidence

| Species | Profile / zone | Rarity / weight / capture base | Asset / master / readiness | World / battle / capture / collection / restart |
|---|---|---|---|---|
| PEBB | GROUND / NEAR_DOCK | COMMON /100 /0.35 | PASS | PASS |
| PUFF | FLOATING / FREE_AREA | COMMON /100 /0.35 | PASS | PASS |
| TIKKI | GROUND / BOTTOM | UNCOMMON /50 /0.25 | PASS | PASS |
| MIMI | STATIC / EDGE | UNCOMMON /50 /0.25 | PASS | PASS |
| WISP | FLOATING / FREE_AREA | UNCOMMON /50 /0.25 | PASS | PASS |

All five now have contentReady=true, productionStatus=PRODUCTION, enabled=true. Only these three fields change for these five content records. All other content records, production PNGs, V1–V6 migration bytes, MovementController, Advanced Spawn, native/Tao and gameplay formulas remain unchanged. Server capture adds UNCOMMON to the accepted rarity guard; HP term and item clamp are unchanged. This PR owns additive V7__alpha_monster_batch2.sql only, with no UPDATE of previous masters.

The server pool is PIP/MELLO/MOSSY/CHIRP/BUBU/PEBB/PUFF (COMMON100 each), TIKKI/MIMI/WISP (UNCOMMON50 each). Exhaustive850 selection boundaries yield100 per COMMON and50 per UNCOMMON; seeded selection reaches all10. Probability remains server-owned. Desktop asset loading uses the same byte-exact delivery gate for the approved10 only; Batch3 remains unavailable for production placement despite delivered art.

### Executed automated checks

- Java21 + isolated PostgreSQL16:114 tests,0 failures/errors/skips; test + bootJar passed. Fresh migrations V1–V7 applied. Includes exact masters, weights, disabled exclusion, name/rarity/profile/weight mismatch rejection, per-species victory/defeat, capture formula, Potion/Charm, captureCount2 and unchanged firstCapturedAt. Batch1 tests explicitly isolate their existing five-member pool; the new Batch2 suite verifies the combined10.
- Rust124 deterministic tests passed,11 optional live tests ignored by default. The Batch2 and Batch1 live tests were then explicitly executed and both passed; the other9 optional live fixtures are NOT_RUN. Native linking, fmt and Clippy --no-deps -D warnings passed (pre-existing vendor warnings only).
- Animation/Base/Dex/Content/Asset58 tests; Presentation51 (including the real Batch2 HTTP Collection response); Python asset27 tests; automation9 tests passed. npm build, optional asset validation, strict-alpha (0 errors/0 missing), rarity projection sync, Tao integrity and diff checks passed.
- No production RNG hook: deterministic live selection is confined to server/src/test/LiveValidationServer.java and excluded from bootJar.

### Actual live vertical slices

Separate loopback PostgreSQL *_test databases, Spring test harness and compiled Rust Api + actual Desktop World were used. Batch2: each of PEBB/PUFF/TIKKI/MIMI/WISP was created once, placed with its own asset/profile/rarity, sampled over120 World movement ticks, reconciled into a fresh World via GET with the same ID/no CREATE, battled, attacked, healed with Potion, armed with Charm and captured. COMMON after one hit:base0.55 +0.10 =0.65; UNCOMMON:base0.45 +0.10 =0.55. Server database confirmed exactly5 encounters, all CAPTURED,0 ACTIVE, and captureCount1 for each species. Actual Collection JSON was passed into the production TypeScript Dex model, checking CAPTURED/count/timestamp/rarity/own asset.

MIMI's X/Y remained identical throughout roaming; EDGE placement used #27's existing safe side path. PUFF/WISP used the existing vertical FLOATING excursion (no artificial horizontal movement). PEBB/TIKKI stayed grounded. Full entity bounds remained inside the negative-origin safe area. Missing/corrupt/wrong-species assets and unsupported profiles fail closed without discovery. Existing Advanced Spawn tests retain Dock/MenuBar/window and left/right exclusion coverage. Every captured species despawned and entered Director cooldown. The same HTTP/World chain was rerun successfully for all five Batch1 species against a separate fresh database with the full10 candidate pool.

Reproduction uses Java21 and an explicit isolated *_test DB: `./server/gradlew -p server test bootJar`; run `liveValidation` with LUMA_TEST_BATCH2=1, LUMA_DB_URL and LUMA_SERVER_PORT; fund only that isolated test player's gold for item purchases, then run `cargo test --manifest-path src-tauri/Cargo.toml live_batch2_world_capture_and_collection -- --ignored --nocapture` with LUMA_GAME_SERVER_URL. LUMA_TEST_COLLECTION_OUTPUT optionally exports the received Collection JSON and feeds `npm run test:presentation`. Use a fresh test DB for each live run. These are explicit opt-in fixtures, not production setup instructions.

## Known risks and manual boundary

Server/desktop content and V7 must deploy together. The pool intentionally changes from5 equal COMMON candidates to10 weighted candidates. Missing/mismatched bundle bytes remain fail-closed; readiness is build-time, not hot reload. FLOATING safety may conservatively pause near obstacles. Desktop restart evidence recreates the actual World/API flow, not an OS process with visible NSPanel. Local test DBs are isolated; no user/production DB is altered.

MANUAL_REQUIRED / NOT_RUN: real AppKit/WKWebView focus, typing/clicking, physical monitor/Dock changes, sprite visual acceptance, and human gameplay acceptance. Automated World tests and native compilation do not certify these. SHADE/EMBER/LUNET/NOVA/NOCT remain unchanged and disabled. Inventory/Evolution/Collection implementation/schema are unchanged. Review status and final SHA-bound CI are recorded in PR #29; no automatic merge.
