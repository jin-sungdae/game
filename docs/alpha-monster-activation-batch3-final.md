# Alpha Monster Gameplay Activation — Batch 3 Final v0.1

## Proposal before implementation

Base origin/main4885cbe includes Batch2 #29 and preparation #30. Inspected migration history V1–V7: this branch owns additive V8 only. Use the five reviewed #30 master rows exactly (levels1–3, use_yn=true): SHADE/UNCOMMON/EDGE/50; EMBER/RARE/FREE_2D/20; LUNET/RARE/FLOATING/20; NOVA/RARE/FREE_2D/20; NOCT/SPECIAL/EDGE/1. Names equal codes. Strict-alpha must pass all15 before validation.

Reuse existing Content, Spawn/Encounter, CalendarClock, MovementController, CombatRules, Inventory and Collection. Add five deliveries to the existing byte-exact runtime asset lists and stage only their three readiness flags for validation. Commit activation only after all five production HTTP + Desktop World vertical slices pass. No new engine, formula, art or native change. Keep NIGHT22:00 inclusive to06:00 exclusive; daytime selection resolves the same authoritative encounter without replacement spam. SPECIAL and NIGHT remain independent; EPIC remains fail-closed.

Final pool: COMMON7*100 + UNCOMMON4*50 + RARE3*20 + SPECIAL1 =961. Verify every weighted boundary and exact DB/content identity plus reviewed1–3 level range. The existing master gate needs a narrow reviewed Alpha level-range check because it currently permits arbitrary valid DB ranges; use_yn=false remains excluded by the existing repository query. Do not add content/schema fields or selection logic.

Alternatives rejected: retaining prep provider/master bypasses would not prove production selection; flag-only changes skip live acceptance; desktop probabilities or replacement movement/capture engines violate authority and scope. Retain preparation tests by promoting their fixtures to real production provider/assets and HTTP selection. Preserve disabled/provisional rejection using actual remaining provisional slots or explicit in-memory readiness test inputs.

Separate loopback *_test PostgreSQL databases and test-only deterministic Spring RNG will exercise production POST→placement→movement→same-ID restore→battle/hit→capture/Charm→collection→despawn/cooldown for all5, plus existing10 regression. Native visible focus/input, physical monitors/Dock and human visual/gameplay acceptance remain MANUAL_REQUIRED. Gameplay/architecture review and merge are human decisions; no automatic merge.

## Final activation evidence

| Species | Rarity / weight / capture base | Movement / spawn / condition | Asset, master, readiness, gameplay, restart |
|---|---|---|---|
| SHADE | UNCOMMON /50 /0.25 | EDGE / EDGE / NIGHT | PASS |
| EMBER | RARE /20 /0.15 | FREE_2D / FREE_AREA / ANY_TIME | PASS |
| LUNET | RARE /20 /0.15 | FLOATING / FREE_AREA / NIGHT | PASS |
| NOVA | RARE /20 /0.15 | FREE_2D / FREE_AREA / ANY_TIME | PASS |
| NOCT | SPECIAL /1 /0.05 | EDGE / EDGE / NIGHT | PASS |

The final content transitions only these five records' enabled/contentReady to true and productionStatus to PRODUCTION. Other content fields and all previous10 records are unchanged. Runtime uses ContentProvider and the actual startup byte-exact asset loader for all15; the Batch3 preparation provider and manual asset-presence bypass were removed from final acceptance tests. Only calendar/environment injection remains. V8 is INSERT-only and V1–V7 are byte-identical to main; existing masters are not updated. Production art, CombatRules/ItemRules formulas, MovementController/World behavior, native/Tao, Inventory/Evolution/Collection implementation/schema and dependencies are unchanged.

The production server gate rejects name/rarity/profile/weight mismatches and reviewed Alpha level ranges other than1–3. use_yn=false is excluded by the existing query. The final migrated pool is15 with COMMON7, UNCOMMON4, RARE3, SPECIAL1 (EPIC0), total961. Every one of the961 integer selection boundaries was checked at both level1 and level3: expected outcome counts100 each COMMON,50 each UNCOMMON,20 each RARE and1 NOCT. Selection remains entirely server-owned.

## Executed checks

AUTOMATED local PASS:

- Java21 + isolated PostgreSQL16:131 tests,0 failures/errors/skips; bootJar. Includes migrated rows, all961 boundaries, exact metadata/range gates, disabled exclusion, all four capture bases and HP term, EPIC/null/unknown rejection, failed capture, victory/defeat, Charm, repeat captureCount and preserved firstCapturedAt. Existing Batch1/Batch2 suites keep their original subset expectations using test-only candidate isolation; final Batch3 tests assert the full15 pool.
- Rust127 deterministic tests,0 failures. Twelve opt-in live tests are ignored in default execution; three were explicitly executed below, the remaining9 are NOT_RUN. fmt, native link and Clippy --no-deps -D warnings PASS (unchanged upstream vendor warnings remain visible).
- Animation/Base/Dex/Content/Asset58 tests, Presentation52 tests, Python asset27 tests and automation9 tests PASS. npm build, optional asset validator, strict-alpha15/15 (0 errors/0 missing), rarity projection sync, Tao integrity and diff checks PASS.
- NIGHT21:59/22:00/23:59/00:00/05:59/06:00 boundaries use the existing CalendarClock. SHADE/NOCT left/right EDGE, EMBER/NOVA X/Y FREE_2D, LUNET FLOATING, negative-coordinate full bounds and Dock/MenuBar safety are exercised through real production provider/assets. Daytime restoration suppresses rendering/discovery, resolves the same ID, preserves authority through offline backoff and never generates CREATE across1,000 retry ticks; terminal confirmation starts cooldown. Actual remaining UTC lease is separate from local eligibility.

### Live production vertical slices

Fresh loopback *_test PostgreSQL databases and test-only Spring RNG drove actual HTTP POST selection. The compiled Rust Api and Desktop World used production content/provider/startup asset loading. Each Batch3 species completed POST→Placement→Movement→same-ID GET reconciliation into a new World→Battle→Hit→Potion→Charm→Capture→Collection→Despawn→Cooldown. No DB-inserted encounters, provider readiness overrides or synthetic asset presence were used. A fixed local-night timezone was injected while retaining the actual current UTC instant for server leases; no OS timezone change.

The Batch3 DB contained exactly5 encounters, all CAPTURED,0 ACTIVE, one per species (no duplicate restore POST). Capture after one hit plus Charm: SHADE0.55, EMBER/LUNET/NOVA0.45, NOCT0.35. Actual Collection JSON passed the production TypeScript Dex model: DISCOVERED/CAPTURED transitions, code/name/own asset/rarity, captureCount1 and firstCapturedAt. Independent DB-backed repeat-capture tests verify count2 and unchanged first timestamp.

The existing Batch1 and Batch2 live HTTP/World tests were explicitly rerun against two fresh databases with the full961-weight pool. All previous10 completed their production slices. These deterministic fixture RNG switches exist only under server/src/test and are absent from bootJar. They do not add client probability logic or a production species selector.

Reproduce with Java21 and an explicit isolated *_test DB: `./server/gradlew -p server test bootJar`. For live production, run `liveValidation` with LUMA_TEST_BATCH3=1, explicit LUMA_DB_URL/LUMA_SERVER_PORT, fund only the isolated test player's item purchases, then run `cargo test --manifest-path src-tauri/Cargo.toml live_batch3_production -- --ignored --nocapture` with LUMA_GAME_SERVER_URL. LUMA_TEST_BATCH3_COLLECTION_OUTPUT exports Collection JSON and optionally feeds `npm run test:presentation`. Use fresh databases for live runs; these are validation instructions, not production data setup.

## Risks and final review boundary

Deploy V8 and matching server/desktop content together. The larger weighted pool intentionally changes encounter distribution; daytime NIGHT selections consume an authoritative resolution/cooldown rather than being rerolled. This follows the existing anti-spam policy. Advanced movement can conservatively pause at unsafe obstacles. Noct remains SPECIAL/NIGHT, never SPECIAL_EVENT; EPIC and the other provisional slots stay inactive.

MANUAL_REQUIRED / NOT_RUN: visible native AppKit/WKWebView launch, single-instance behavior, Never Steal Focus while typing/clicking, physical monitor/Dock changes and visual/gameplay acceptance. Automated native compilation and a reconstructed World are not a visible OS-process restart. Test services are isolated from the user's database; they are stopped after validation. PR #31 records the final SHA-bound CI and human-review status. No automatic merge. Auto-repair iterations used:0.
