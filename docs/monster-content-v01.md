# Monster Content Integration v0.1

## Architecture proposal before implementation

Base main dfe8345; isolated worktree /private/tmp/luma-monster-content-v01, branch feature/monster-content-v01.

Preserve PR #19's 30-slot MonsterDefinition and stable Dex numbers, independent of Companion. Replace the approved 15 Alpha slots with confirmed identities/tags; retain the other 15 provisional slots. Add contentReady without weakening enabled/production metadata validation. PIP stays production; 14 approved identities remain disabled and asset-unready.

Authority: server Domain rarity defaults own capture references and encounter weights. Desktop receives checked static projections, never computes rarity economics. Package the same Dex content with the server; the server joins enabled DB masters to production-ready content, failing closed for missing/unready content and inconsistent production master metadata. m_monster continues owning DB identity, level range and operator use_yn; no new master rows or invented levels are needed. Existing PIP capture formula retains its HP term and obtains the same 0.35 base from the Domain default.

No migration is necessary: content-only definitions do not need runtime DB IDs until a separately reviewed Spawn × Encounter integration and asset delivery. Alternatives of seeding 14 disabled rows or widening m_monster are deferred to avoid invented combat levels and parallel Flyway conflicts. V1–V5 remain byte-for-byte unchanged. No Inventory/Shop UI, Spawn Director implementation, native focus or Companion changes.

Approved Alpha adds FIRE/MOON/NIGHT archetypes and LOWER_CORNER metadata. Existing Spawn Director does not support LOWER_CORNER yet; it remains disabled and is not connected here. PIP's approved NEAR_DOCK tag uses its existing supported zone; the director remains disabled by default. Contract tests must reflect the new approved metadata rather than the old provisional Alpha coverage.

Unspecified balance defaults are conservative initial configuration for human review, not finalized balance: COMMON 100/0.35, UNCOMMON 50/0.25, RARE 20/0.15, EPIC 5/0.10, SPECIAL 1/0.05 (weight/base capture). PIP visualScale stays0.8; other new Alpha definitions use neutral1.0 pending assets. Metadata scales are not a renderer/panel size change.

Architecture and balance remain HUMAN_REVIEW_REQUIRED; user authorizes implementation, not automatic merge.

## Confirmed Alpha content

All display names equal their code, assetIdentity is lowercase code. Scale is reference metadata only. `enabled/contentReady` is true/true only for PIP; all other Alpha false/false. Production status remains PROVISIONAL until approved assets are delivered, independently of the now-confirmed identity.

| Dex | Code / Display | Rarity | Archetype | Movement | Behavior | Spawn | Condition | Weight | Base Capture | Scale | Asset Identity | Enabled / Ready |
|---|---|---|---|---|---|---|---|---:|---:|---:|---|---|
| 1 | PIP | COMMON | BEAST | GROUND | PLAYFUL | NEAR_DOCK | ANY_TIME | 100 | 0.35 | 0.8 | pip | true / true |
| 2 | MELLO | COMMON | SLIME | JUMP | CURIOUS | BOTTOM | ANY_TIME | 100 | 0.35 | 1 | mello | false / false |
| 3 | MOSSY | COMMON | PLANT | GROUND | SLEEPY | LOWER_CORNER | ANY_TIME | 100 | 0.35 | 1 | mossy | false / false |
| 4 | CHIRP | COMMON | BIRD | FLYING | CURIOUS | TOP | ANY_TIME | 100 | 0.35 | 1 | chirp | false / false |
| 6 | BUBU | COMMON | AQUATIC | JUMP | PLAYFUL | BOTTOM | ANY_TIME | 100 | 0.35 | 1 | bubu | false / false |
| 7 | PEBB | COMMON | ROCK | GROUND | PASSIVE | NEAR_DOCK | ANY_TIME | 100 | 0.35 | 1 | pebb | false / false |
| 8 | PUFF | COMMON | SPIRIT | FLOATING | CURIOUS | FREE_AREA | ANY_TIME | 100 | 0.35 | 1 | puff | false / false |
| 10 | TIKKI | UNCOMMON | MECHANICAL | GROUND | CURIOUS | BOTTOM | ANY_TIME | 50 | 0.25 | 1 | tikki | false / false |
| 13 | MIMI | UNCOMMON | MIMIC | STATIC | TRICKSTER | EDGE | ANY_TIME | 50 | 0.25 | 1 | mimi | false / false |
| 14 | WISP | UNCOMMON | SPIRIT | FLOATING | TIMID | FREE_AREA | ANY_TIME | 50 | 0.25 | 1 | wisp | false / false |
| 15 | SHADE | UNCOMMON | SHADOW | EDGE | TRICKSTER | EDGE | NIGHT | 50 | 0.25 | 1 | shade | false / false |
| 16 | EMBER | RARE | FIRE | FREE_2D | AGGRESSIVE | FREE_AREA | ANY_TIME | 20 | 0.15 | 1 | ember | false / false |
| 19 | LUNET | RARE | MOON | FLOATING | TIMID | FREE_AREA | NIGHT | 20 | 0.15 | 1 | lunet | false / false |
| 21 | NOVA | RARE | COSMIC | FREE_2D | CURIOUS | FREE_AREA | ANY_TIME | 20 | 0.15 | 1 | nova | false / false |
| 28 | NOCT | SPECIAL | NIGHT | EDGE | TIMID | EDGE | NIGHT | 1 | 0.05 | 1 | noct | false / false |

Alpha rarity distribution: COMMON7 / UNCOMMON4 / RARE3 / EPIC0 / SPECIAL1. The full thirty-slot Dex distribution remains8/7/6/5/4. Non-Alpha slots retain their original provisional codes and zero-weight/null-rate references.

## Authority, gate and delivery procedure

- `server/src/main/resources/content/rarity-defaults.json` is the single Domain balance source. `scripts/sync_monster_content.py` materializes its Alpha values into the Dex projection; `--check` runs under existing animation CI. No Desktop formula is added.
- `server/build.gradle` packages the exact `src/entities/monster-dex.json` into bootJar resources. `MonsterContent` reads once, validates unique identities, bounds, readiness and rarity projections, exposes immutable definitions and checks DB candidates. There is no second copied server registry.
- `m_monster` keeps persistent IDs, level ranges and the operator `use_yn` switch. Repository candidates must pass **DB use_yn + positive weight + known content + enabled + contentReady + PRODUCTION**. Production code/name/rarity/movement/weight must match reviewed content or fail closed. Positive DB weight/enable alone cannot bypass readiness. Missing/non-ready definitions are excluded before the existing weighted selector.
- PIP keeps its DB ID, name, COMMON/GROUND, level1–3, weight100, base0.35, asset `/assets/monsters/pip/base.png`, visualScale0.8. The HP capture term and COMMON-only combat support are unchanged. Uncommon/etc references are content definitions, not new playable combat support. Its approved tags become PLAYFUL/NEAR_DOCK only as metadata; default Spawn Director remains off. If explicitly enabled, the existing adapter resolves the already-supported NearDock zone.
- Asset delivery must add approved PNG + production asset registry entry and pass image validation. Then separately review contentReady/productionStatus and enabled, DB master/levels, supported capture rules and Spawn × Encounter integration. A PNG path or DB flag alone is not activation. `contentReady=true,enabled=false` can represent ready-but-not-released content. Public Dex still lists enabled entries only; all15 remain available for diagnostic resolution.
- NIGHT is metadata only for SHADE/LUNET/NOCT. No clock-based spawning, new AI or movement execution is added. LOWER_CORNER remains deliberately unsupported by the current director until its integration PR.

## Changed files

- Content contract/data: `src/entities/monster-dex.json`, `src/entities/monsterDex.ts`.
- Server authority/gate: `MonsterContent.java`, `GameRepository.java`, `CombatRules.java`, `content/rarity-defaults.json`, `server/build.gradle`.
- Projection check: `scripts/sync_monster_content.py`, `scripts/test-animation.sh`.
- Tests: `tests/animation/monster-content.cjs`, updated `monster-dex.cjs`, `MonsterContentTest.java`, `MonsterContentIntegrationTest.java`. Only the **test module** in `src-tauri/src/spawn/dex_adapter.rs` changes to assert approved PIP NearDock and disabled-only unsupported LOWER_CORNER; no Spawn Director implementation changes.
- Documentation: this file and the thirty-slot table in `docs/monster-dex-v01.md`.

DB migration: **none**. V1–V5, production PNGs, Inventory/Shop UI, Companion domain, native panels, Tao, dependency versions and lockfiles are unchanged.

## Validation

AUTOMATED PASS:

- Server91 tests: existing84 including Inventory32 and Evolution regressions, plus7 content unit/integration tests on an isolated PostgreSQL17 database (`luma_content_test`, port55443). Tests insert all14 unready Alpha DB masters with use_yn=true/positive weights plus unknown content: production candidates remain exactly PIP; disabling PIP leaves none. Transactions roll back fixture masters. PIP DB mismatch fails closed.
- Rust93 PASS /7 opt-in live tests NOT_RUN. The first restricted sandbox run could not bind loopback HTTP test sockets; rerun with local network permission passed. No tests weakened. cargo fmt and clippy `--no-deps -- -D warnings` PASS; existing vendor warnings unchanged.
- Frontend92: animation28/base8/Dex11/newcontent5; gameplay4/polish18/evolution5/itemmodel8/itemUI5. Exact15 mappings, uniqueness, distribution, night flags, economic projections, scale/identity, fallback/readiness and PIP compatibility covered.
- Assets16, policy9, strict base asset validation0errors/26 intentionally unprovided companion animation/base slots. npm build, Tao patch integrity and git diff whitespace PASS.
- No actual macOS UI launch performed for this content-only change. Native link is covered by Rust tests; physical focus/mouse/visual acceptance remains MANUAL_REQUIRED / NOT_RUN, not claimed PASS.

## Parallel PRs and known risks

At inspection PR #21 (Collection Dex UI, e3d284d) and #22 (Monster Production Asset Delivery, d005e90) each contain only their separate proposal document, so currently no changed-file overlap. Their future implementations may touch `monsterDex.ts`, `monster-dex.json`, `monsters.ts`, asset tests and `scripts/test-animation.sh`; recheck on synchronization. #21 must retain the contentReady gate and existing undiscovered masking. #22 must preserve confirmed names/identities and coordinate asset registration/readiness without silently enabling encounters. Never overwrite either parallel branch.

Balance defaults and neutral visual scales await content review; no final art/design is implied. Non-COMMON combat, conditional spawning and MOSSY LOWER_CORNER execution are intentionally not connected. A mismatched production DB master returns unavailable rather than silently switching gameplay values. Updated content is packaged into the server artifact and requires a rebuild/restart; it is not hot-reloaded. Registry initialization is once, candidate filtering is O(number of enabled DB masters), no new per-frame/UI work or HTTP polling. CPU/memory delta is not measured.

Final-head GitHub CI and commit SHA will be recorded on the PR. End state: READY_FOR_HUMAN_REVIEW only after CI PASS; never auto-merge.
