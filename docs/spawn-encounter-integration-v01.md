# Spawn × Encounter Integration v0.1

## Proposal before implementation

Base main 6ba7593; separate worktree, branch feature/spawn-encounter-integration-v01.

Connect existing Director opportunity to the bounded backend worker, with explicit completion events. The worker retains all HTTP; AppKit/World only evaluate monotonic schedules and placement. No server selection fields are sent. Keep the current 120–300s seeded cooldown and budget1. Startup reconciliation precedes any POST; failures use5/10/30s backoff and reconcile before retrying uncertain POST.

A server-owned encounter occupies budget even without a visible entity. Content-ready metadata resolves code/profile/asset identity after server selection. Placement uses the cached DesktopSafeArea/cursor/window samples. Retry the same encounter locally with a bounded schedule; unsupported metadata/zone/condition or exhausted placement invokes the existing server Ignore resolution, reconciling before each retry. Offline resolution retains authority and retries at bounded backoff, never creates replacement encounters. Local expiry hides the visual but only authoritative terminal/empty reconciliation releases the budget.

Discovery requires successful visible placement, not a received DTO. Keep debug PIP separate from authority/discovery/scheduling; a production encounter replaces a debug visual in the existing single panel. Generalize production identity and reuse MovementController. No new native windows/architecture, polling, timer, migration, balance/formula, Inventory/Shop/Evolution/schema or PNG changes.

Alternatives rejected: local monster selection violates server authority; repeatedly POSTing after placement failure duplicates opportunities; local-only discard leaves server ACTIVE; new worker/engine duplicates existing foundations. Existing passive backend reconciliation stays on its current5s worker cycle, with explicit spawn commands carrying independent acknowledgements/backoff.

Architecture/protocol review is HUMAN_REVIEW_REQUIRED. User authorizes implementation; do not merge automatically. Live acceptance uses isolated PostgreSQL/Spring and World with fake monotonic time, never reduced production cooldown. Physical macOS mouse/focus remains a separate manual boundary.

## Implemented runtime

- `spawn/runtime.rs` owns the existing Director, selected encounter, monotonic lease, one in-flight action, placement attempts and resolution backoff. WAITING → REQUESTING → ACTIVE → COOLDOWN is enabled in World. The seeded120–300s schedule is unchanged. After a terminal cooldown has elapsed, an empty reconciliation does not impose a second cooldown.
- `backend::battle::Command::Spawn` and `Event::SpawnCompleted` route GET-active / empty-body POST through the existing bounded worker. No AppKit HTTP. The worker starts passive encounter tracking only after authority is acquired, avoiding a startup duplicate GET and avoiding empty-catalog polling. Active reconciliation uses the existing worker cycle; passive errors also back off5/10/30 instead of repeatedly polling every5s. No new timer/thread/RAF/interval or HTTP-per-world-tick path.
- Startup GET restores the authoritative ID without POST. Unknown/lost mutation responses reconcile before another creation. Existing active battle/encounter occupies budget even while invisible; debug PIP does not count toward server budget. Production authority replaces a debug visual in the same panel. Debug spawn never produces server requests or discovery.
- `ContentProvider` joins the selected code to immutable content metadata after selection; enabled/contentReady/PRODUCTION and ANY_TIME are required. DTO movement and rarity must match. Seven existing movement wire types are preserved. LOWER_CORNER explicitly maps to the existing LowerCorner zone; unknown zones fail closed. Other Alpha monsters and NIGHT content remain disabled.
- Placement uses current cached DesktopSafeArea, cursor and existing window observations. Unknown observations deny placement. Sixteen candidates per attempt; initial attempt plus local retries after5/10/30s (absolute0/5/15/45). Same encounter throughout, no new POST. Unsupported content/zone/condition or exhausted placement requests existing Ignore API. Before a resolution retry, GET-active ensures a committed/lost Ignore isn't repeated and a different current ID isn't ignored. Offline resolution retains authority with5/10/30s bounded request spacing.
- Entity identity contains monsterCode, encounterId, rarity, level, movementProfile and assetIdentity from authority/content. Same native panel/size and bottom-center bounds. Existing MovementController drives production movement; PIP remains24pt/s GROUND. Debug behavior is retained. React only renders identity; existing MonsterVisual priority remains animation → same-monster base → diagnostic.
- Discovery is session evidence only after successful placement; received, unplaced and debug entities do not reveal the Dex. Existing captured Collection persistence/masking is unchanged. Local lease expiration fades the entity but retains authority until the server confirms terminal/empty state. Battle ACTIVE suspends both lease holders. Server terminal results drive cooldown.

## Failure policy and boundaries

Automatic Ignore is intentional for an encounter this client cannot safely display after the bounded placement budget. No local-only terminal state is invented. A server outage can retain an invisible active encounter until reconciliation succeeds; this blocks replacement POST rather than duplicating authority. Unknown/mismatched production content is not guessed into a position or another asset.

The scheduling policy controls automatic requests. The existing explicit user Encounter command remains manual; the server still reuses its one active encounter. A queue-full response releases the pending opportunity into reconciliation backoff. Bootstrap/Evolution/menu reads retain the existing bounded worker, with error backoff; the schedule does not manufacture gameplay values.

## Changed files

- Orchestration: `src-tauri/src/spawn/runtime.rs`, `spawn/mod.rs`, `spawn/dex_adapter.rs`, new `spawn/runtime/tests.rs`.
- World/worker wiring: `behaviors.rs`, `backend/mod.rs`, one Command variant in `backend/battle.rs`, `main.rs`.
- Cached safe-area accessor only: `overlay.rs`; no native bridge/NSPanel/Tao code changes.
- Rendered identity: `src/types/entity.ts`, `Creature.tsx`, `Interaction.tsx`.
- Regression fixtures: `spawn/tests.rs`, `backend/tests.rs`, `backend/items/tests.rs`, `collection_dex.rs`, `tests/presentation/collection-dex.cjs`.
- This document.

No server source, migration, balance/formula, production PNG, Collection schema, Movement Engine, Companion behavior, Inventory/Shop/Evolution implementation, dependency or lockfile changes.

## Regression evidence

AUTOMATED PASS:

- Rust112 deterministic tests (baseline96 +16 integration/contract tests), plus two opt-in live slices documented below. The seven existing specialized live fixtures are NOT_RUN for this PR; their deterministic regressions are retained. Native compile/link, fmt and clippy PASS;18 upstream Tao warnings unchanged.
- Server91 tests on isolated PostgreSQL17 (`luma_spawn_test`, loopback55444): full Inventory/Evolution/Battle/Encounter/content gate regression. No server code changes.
- Frontend107 (animation/base/Monster registry/Dex/content58 + presentation/polish/evolution/items/Collection49); assets22; automation policy9. Build, strict-base validation, Tao integrity and whitespace PASS.40 intentionally unprovided assets remain pending (including14 Alpha base PNGs), not errors.
- Existing main had a Collection test using removed provisional MONSTER_002. Its null-asset/unknown-name contract now uses still-provisional MONSTER_005 (Dex slot5). Collection implementation/masking is unchanged; confirmed MELLO already has a delivery-registry URL and is unsuitable for the original null-asset assertion. This is a merge-era fixture correction, not a weakened expectation.
- Existing World tests now explicitly inject a known safe placement environment. Receiving a DTO without placement no longer proves discovery. Sandbox socket restrictions required the normal loopback-enabled test execution; no test weakening or architecture workaround.

## Live vertical slice

Spring test-only fixed RNG server18087 + PostgreSQL55444; existing bounded Backend worker + compiled Rust World on macOS. A test-only loopback HTTP proxy18088 audits requests. Fake monotonic time advances the actual Director schedule; production cooldown constants stay120–300s.

Slice1 PASS: empty startup → scheduled request → server PIP → NEAR_DOCK (negative monitor ground y=-592) → entity movement → fresh World restore of same ID → Battle → Capture → despawn/cooldown → reconciliation → next PIP → Ignore → despawn/cooldown. Discovery deduplicates PIP. Automatic Encounter POST2; restore POST0. Actual HTTP total19: bootstrap GET4, evolution GET4, active GET6, encounter POST2, battle POST1, capture POST1, ignore POST1. Every request succeeds; create bodies are empty. These counts include existing backend refresh reads, not just the spawn requests.

Slice2 PASS: real server60-second TTL, no shortened constants or SQL expiry fixture. After local lease fade the budget stays ACTIVE, GET-active lazily expires the server record, then World enters COOLDOWN.60.25s elapsed. Actual HTTP3: initial active GET1 + create POST1 + terminal active GET1. Combined two live slices:22 HTTP requests,3 encounter POST,0 HTTP errors. No production gameplay values changed.

## Performance / manual / risks

Cheap Director checks execute on the existing World tick; while waiting there is no HTTP, selection or content parsing. Placement search is bounded16×4 per encounter. Existing OS samples are cached; passing environment copies bounded sample data, with no new OS tracking/permission. HTTP stays on the same single worker with bounded queues and3s request timeout. CPU/RSS delta is not measured; no performance benchmark claim.

AUTOMATED macOS Rust World and native link are not proof of visible NSPanel UX. Actual screen placement, cursor/window avoidance in the user's arrangement, mouse Battle/Capture and continuous typing/Never Steal Focus remain MANUAL_REQUIRED / NOT_RUN. No unavailable access_programs calls, permissions or system settings changes.

Conservative window avoidance may resolve encounters when the safe area stays fully obstructed. Non-GROUND profiles use existing deterministic foundation behavior but remain content-disabled; future activation needs specific visual acceptance. A stale or incompatible server/content deployment fails closed. Metadata has no hot reload. PR final CI/commit/status are recorded separately; no automatic merge.
