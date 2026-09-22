# Alpha Monster Gameplay Activation — Batch 1

## Proposal before implementation

Base origin/main b81ce45. Independent feature/alpha-monster-activation-batch1 worktree. Retain the existing ContentProvider, Spawn Runtime, World, MovementController, server MonsterSelector and Battle/Capture/Inventory formulas. Add only the four approved master rows in V6; existing migrations and PIP master remain unchanged. Reuse COMMON weight100, capture base0.35, level1–3. Five equal weights imply20% each at selection boundaries.

Gate activation on the supplied assets and per-species server/Desktop World vertical slices. Preserve MELLO/BUBU BOTTOM/JUMP, MOSSY LOWER_CORNER/GROUND and CHIRP TOP/FLYING. Keep all other content disabled. Fail closed on unavailable assets, identity/content mismatch, unsupported movement and unsafe placement. Preserve native96×104 panels, visible scale, source RIGHT and bottom-center anchor. No new engine, schema column, formula or production PNG edits.

Alternatives rejected: only toggling enabled skips master/placement/movement validation; replacing MOSSY zone or grounding CHIRP changes approved content; client selection/capture calculations violate server authority. Existing runtime adapters and additive tests are sufficient. Review of gameplay activation and architecture remains HUMAN_REVIEW_REQUIRED; no auto merge.

Verification will use a new isolated loopback PostgreSQL *_test database and test-only deterministic Spring server plus compiled Desktop World, never the user's DB. Native visible NSPanel focus/input acceptance remains a separate manual boundary.

## Final activation matrix

| Monster | contentReady | productionStatus | enabled | V6/current master use_yn | Automated blocker |
|---|---|---|---|---|---|
| PIP | true | PRODUCTION | true | true (unchanged V2) | none |
| MELLO | true | PRODUCTION | true | true | none |
| MOSSY | true | PRODUCTION | true | true | none |
| CHIRP | true | PRODUCTION | true | true | none |
| BUBU | true | PRODUCTION | true | true | none |

The other ten named Alpha candidates remain contentReady=false, enabled=false, PROVISIONAL and have no production DB master. The remaining provisional slots also remain disabled. Readiness and enabled are still separate fields; no parser/server contract merges the concepts.

V6__alpha_monster_batch1.sql is additive INSERT only, with no schema expansion or PIP UPDATE. Existing V1–V5 bytes are unchanged. All five weights are100 (PIP's legacy value equals current COMMON default); exhaustive500 boundary draws produce100 outcomes per species,20% each, and1000 seeded draws reach all five. Level1–3 and COMMON capture0.35 + existing HP term are unchanged. All production formulas and Inventory implementation are unchanged.

## Runtime and safety

The existing content adapter now permits only the five reviewed code/profile pairs and checks COMMON rarity and canonical asset identity. Server DTO name, code, rarity, level1–3 and movement must match supported content. Existing server gate rejects enabled master name/rarity/profile/weight mismatch; non-ready content cannot enter the selector even if its DB row is enabled.

At startup, the existing Tauri asset resolver loads each actual frontend bundle base and compares it byte-for-byte with the source delivery compiled into Rust. Unknown, missing, wrong-species or corrupted bytes are unavailable. Missing source PNG prevents compilation; immutable source-hash/PNG validator tests verify the approved deliveries. World placement reads the validated asset set and otherwise uses the existing authoritative Resolve/Ignore path without discovery or replacement POST. Release assets are immutable embedded resources. Development requires npm build before native startup so frontendDist exists; changing a dev asset after startup requires restart/revalidation. This adds no asset decoder, dependency, timer or engine. A broken renderer may still show same-species diagnostic fallback; it never substitutes PIP art.

Existing MovementController handles BOTTOM/JUMP for MELLO/BUBU, LOWER_CORNER/GROUND for MOSSY, TOP/FLYING for CHIRP. World motion, panel sizing and engine formulas required no changes. Tests cover jump ascent/landing, upper-band flight, horizontal motion, safe bounds, identity, facing, restart restoration and discovery only after accepted placement. Native size96×104, PIP scale0.8 and other scale1 remain unchanged; source hashes and prior measured visible bounds59.45×53.04 /72.39×69.83 /72.39×72.39 /73.03×57.34 /67.59×68.23 remain applicable because neither pixels nor rendering geometry changed.

## Executed verification

AUTOMATED local PASS:

- Build,58 animation/asset/content/Dex tests,50 presentation/Collection tests,25 Python asset tests,9 automation-policy tests, Tao integrity, sync_monster_content --check, git diff --check.
- Rust116 deterministic tests, native link, fmt and Clippy --no-deps -D warnings. Ten opt-in live fixtures are ignored in default execution; the new Batch1 live fixture was then explicitly executed and passed. Existing unrelated live fixtures remain NOT_RUN for this PR.
- Java21:102 tests,0 failures/errors/skips against a new isolated PostgreSQL16 cluster on loopback55461. V1–V6 applied from scratch. Tests include five masters, exact weights/seeded selection, content gates, per-species Battle attack/victory/defeat, HP formula, potion heal, Charm0.10, repeated capture count2 with unchanged firstCapturedAt, disabled exclusion and mismatch rejection. Earlier PIP-only tests explicitly scope their fixture to PIP and restore all candidates afterwards.
- Five production PNGs pass the existing validator; four approved source hashes match. Alpha-only reports0 errors /10 unrelated missing assets. No unrelated content was enabled to make tests pass.

Live vertical slice PASS uses separate luma_batch1_live_test, Spring test-only deterministic RNG on18091 and actual Rust Api + Desktop World. Five create requests return PIP, MELLO, MOSSY, CHIRP, BUBU in order. Each moves, restores the same ACTIVE ID into a fresh World via GET (no restore POST), starts Battle, attacks/receives hit, captures, reads Collection, despawns and enters Director cooldown. MELLO/BUBU jump and land; MOSSY starts at lower safe corner; CHIRP stays in the top region. Observed negative-origin ground y=-992 versus CHIRP y=-112. DB confirms exactly5 encounters, all CAPTURED,0 ACTIVE, and one persistent Collection capture per species. Actual HTTP Collection JSON also passed the real TypeScript collectionDexModel: Dex numbers1/2/3/4/6, names, COMMON rarity, independent own asset paths, captureCount1, first timestamp and CAPTURED all correct. Counts are server data, never synthesized by Desktop.

The test fixture RNG switch lives only in server/src/test and is absent from bootJar. No production random override, selection request parameter or client weight calculation. The local test DB is newly created and isolated; user database and existing running services are untouched.

## Review and manual boundary

Final SHA-bound CI result is on PR #26. Core gameplay activation plus main.rs require HUMAN_REVIEW_REQUIRED even when automated tests pass. No automatic merge.

MANUAL_REQUIRED / NOT_RUN: visible native WKWebView motion/timing, Never Steal Focus during real typing/clicking, single-instance launch, multi-monitor/Dock arrangements and human visual acceptance. Automated Desktop World and native link are not a visible native UI run. Existing static render/source-hash evidence is preserved rather than claimed as new native measurement.

Known risks: readiness is build/deployment metadata, not hot reload; deployment must include V6 and matching server/desktop content. Five equal candidates change encounter distribution intentionally. Discovery stays session-local. Window avoidance can conservatively reject placement and use existing server resolution. Test data remains only in isolated test databases until cleanup; no production state has been activated by running tests.
