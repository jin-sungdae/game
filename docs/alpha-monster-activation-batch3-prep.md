# Alpha Monster Gameplay Activation — Batch 3 Preparation v0.1

Base origin/main 1822e58 includes Advanced Spawn #27, asset delivery #28 and Batch1 activation #26. Batch2 is independent. This PR adds no Flyway migration, production monster row, content flag change or production asset allowlist change. No migration version is reserved.

## Support and boundary

Reuse #27's existing CalendarClock, provider injection, Spawn Runtime, World and MovementController. Test-only fixtures read the actual Batch3 content and supplied PNGs, inject candidate readiness and a fixed local clock, and execute the existing World routing. Production ContentProvider still rejects all five. No new engine, element system, native window or client rarity calculation.

The single production behavior change permits UNCOMMON/RARE/SPECIAL in the server CombatRules capture gate. Base rates still come from MonsterContent.rarity; the existing HP term (1 - hp/maxHp)*0.50 and clamp0.05..0.95 are unchanged. ItemRules still adds Charm0.10 with its existing clamp. COMMON is unchanged, EPIC/unknown rarities remain unsupported. Rarity and NIGHT remain independent: NOCT is SPECIAL + NIGHT, never SPECIAL_EVENT.

Tests use disabled use_yn=false rows only in a dedicated *_test PostgreSQL database. They explicitly create fixture encounters with the existing repository, bypassing selection only inside test code. They assert production selection/readiness stays closed. These fixtures are not proof of final production activation. No test helper or override ships in bootJar.

## Future final activation after Batch2 merge

Start from then-current origin/main and inspect the migration history; choose the next migration version at that time. Add exactly these master values using an additive migration after final activation approval:

| code / name | rarity | movement_profile | min_level | max_level | encounter_weight | final use_yn | archetype | behavior | spawn | condition |
|---|---|---|---|---|---|---|---|---|---|---|
| SHADE | UNCOMMON | EDGE | 1 | 3 | 50 | true | SHADOW | TRICKSTER | EDGE | NIGHT |
| EMBER | RARE | FREE_2D | 1 | 3 | 20 | true | FIRE | AGGRESSIVE | FREE_AREA | ANY_TIME |
| LUNET | RARE | FLOATING | 1 | 3 | 20 | true | MOON | TIMID | FREE_AREA | NIGHT |
| NOVA | RARE | FREE_2D | 1 | 3 | 20 | true | COSMIC | CURIOUS | FREE_AREA | ANY_TIME |
| NOCT | SPECIAL | EDGE | 1 | 3 | 1 | true | NIGHT | TIMID | EDGE | NIGHT |

Rarity capture bases: SHADE0.25, EMBER/LUNET/NOVA0.15, NOCT0.05. No capture column/schema extension is needed. Existing server defaults own these values. Levels1–3 retain Batch1's level-based formula contract; test fixtures use level1 and formula boundary tests.

Final content flags would be contentReady=true / productionStatus=PRODUCTION / enabled=true for each species only after final production selection, live integration and manual approval. In this PR every one remains false / PROVISIONAL / false. Retain assetIdentity shade/ember/lunet/nova/noct, scale1 and all existing profile/condition metadata.

Final activation must also add these five approved bytes/codes to the production `spawn/assets.rs` and Runtime startup asset-validation list (rebased on Batch2's additions). This prep deliberately does not edit those shared activation lists. Current fixture presence comes from actual PNG bytes matched against compile-time approved assets, not fake pixels. Run strict-alpha and final DB/content mismatch and weighted-pool tests against the merged candidate pool. Do not assume the current five-candidate pool after Batch2.

## Verification

- Asset: existing strict-alpha validator, immutable delivery hashes, fixture actual file bytes/asset identity.
- Each species: real content identity, rarity, profile, condition, safe movement, same encounter restart, production-disabled rejection, missing asset, mismatched name/rarity/movement and unknown-window fail closed; discovery only after successful placement.
- NIGHT for SHADE/LUNET/NOCT:21:59 reject,22:00 allow,05:59 allow,06:00 reject using #27 local CalendarClock. EMBER/NOVA allow all four. EDGE tests exercise both safe sides for SHADE and NOCT; FREE_2D tests require both X/Y movement; FLOATING requires vertical movement within safe bounds.
- PostgreSQL + actual Spring HTTP fixtures: each species Battle/Attack/Hit, victory/defeat/reward, failed capture, successful capture and repeat Collection count/first timestamp, full/half/zero HP rarity formula, Charm+0.10 and same-ID active GET without a new POST. Unknown rarity/invalid HP fail closed.
- Optional live fixture: `LUMA_BATCH3_LIVE=1` when running `Batch3PreparationTest` launches the ignored Rust `live_batch3_fixture` against that test's random-port Spring server and isolated database. Each species uses actual HTTP GET→World placement/movement→fresh World restore→Battle/Hit→Capture→Collection→despawn/cooldown. It does not POST a production encounter. Run with the frontend built and a writable CARGO_TARGET_DIR; no user's database.

Local and SHA-bound CI execution results are recorded in the PR. Default Rust suite intentionally ignores opt-in live fixtures. Full Batch1 and Advanced Spawn tests remain in the regression suite. Auto-repair iterations: three (Capture DTO field syntax; old COMMON-only test expectation plus explicit EPIC exclusion; preserve null-rarity fail-closed behavior); maximum three.

## Risks and manual checks

Production remains unactivated: no master, readiness flags or asset allowlist entry for these five. Final activation must merge Batch2 first and integrate the lists and tests above. Shared file overlap is limited to CombatRules, the existing MonsterContent capture test and the Runtime test-module declaration; retain both branches' tests when integrating. No Batch2-specific file is edited.

MANUAL_REQUIRED / NOT_RUN: visible WKWebView movement/timing, real focus/typing/mouse, single-instance, multi-monitor/Dock and visual acceptance. Live World is compiled gameplay state with injected local night and safe-area fixtures, not a visible native session. Native CI compilation does not prove focus behavior. No automatic merge.

## Executed local evidence

AUTOMATED PASS: frontend build;58 animation/content tests;50 presentation tests;27 asset tests;9 automation tests; strict-alpha15/15; Tao integrity; Rust124 deterministic tests (11 opt-in ignored by default), fmt/clippy; Java113 tests and bootJar against fresh isolated PostgreSQL16 on loopback55463. The new ignored live fixture was explicitly run once for each of the five species via LUMA_BATCH3_LIVE=1, all PASS. The other ten opt-in Rust fixtures were NOT_RUN. Existing Batch1 and #27 deterministic regression tests passed. No native visible UI launch was performed.
