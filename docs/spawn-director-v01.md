# Desktop Spawn Director Foundation v0.1

## Architecture decision (before implementation)

Add an isolated Rust orchestration module consuming DesktopSafeArea, Size and MovementProfile. Production automatic scheduling remains disabled: the existing manual PIP / server Encounter path remains authoritative and unchanged. No backend scheduler, new polling loop, UI, dependency or database change.

Alternatives: replacing MonsterSelector would violate server authority; integrating the unmerged Monster Dex branch would couple parallel work; enabling automatic POST now would change gameplay. All are deferred. Human architecture review is required before merge.

Implementation and validation details follow in this PR.

## State machine and scheduling

`Director` owns WAITING → REQUESTING → ACTIVE → COOLDOWN → WAITING. It returns `Reconcile` or `RequestEncounter`, never sends HTTP or creates an entity. Startup starts unreconciled: a confirmed active lookup is mandatory before a new request. A confirmed empty response schedules a conservative 120–300 second cooldown. REQUESTING and ACTIVE suppress all opportunities. Only server-confirmed removal releases ACTIVE; a local presentation lease cannot do so.

`Clock` uses monotonic durations; `WorldClock` adapts existing World time, `SystemClock` uses Instant, tests use FakeClock. A separate seeded generator makes schedules repeatable without consuming Companion RNG. Before `next_spawn_at`, tick does no RNG/provider/OS/allocation work. At cooldown expiry one tick transitions to WAITING and the following tick evaluates eligibility. No RAF, interval, background scheduler or new OS loop is added.

## Budget, cooldown and backoff

Default maxWildMonsters=1. Occupancy includes debug PIP; a server active encounter blocks even when no panel is visible. Configuration supports budgets 2/3 but enabling multiple presentation entities requires a future integration change. Blocked opportunities defer for a full cooldown. Failures defer by 5, 10, then 30 seconds, capped at 30. Recovery resets the failure count. A failed POST might have committed, so every failure requires active reconciliation before another POST. The future adapter must serialize completion callbacks and use the existing bounded HTTP timeout; REQUESTING intentionally never independently retries a still-running request.

## Spawn zones and safe area

Placement accepts the selected monitor's `DesktopSafeArea.final_luma_safe_area`, entity Size and existing movement environment metadata. Coordinates are AppKit bottom-center, +Y up; negative/fractional monitor origins are supported. The native integral bounds projection is checked against cursor/windows and detected Dock bounds. Menu Bar, retained Dock reservation, and edge margins come from the existing safe-area policy. Up to 16 seeded candidates are tried; exhausted/unknown/invalid metadata yields no placement.

| Zone | Candidate |
|---|---|
| BOTTOM | Safe bottom band |
| TOP | Safe top band |
| LEFT_EDGE / RIGHT_EDGE | Whole entity at safe side |
| FREE_AREA | Interior of usable rectangle |
| NEAR_DOCK | Safe bottom above reserved Dock region, including conservative bottom fallback for side/unknown Dock |
| LOWER_CORNER | Left or right safe lower corner |

Cursor clearance is 100 logical points using movement's existing `unobstructed` policy. Missing cursor or window metadata denies placement. No Accessibility permission, global hook, window title or screen capture access. Placement is authoritative for initial coordinates; MovementController is not asked to choose the spawn position.

## Encounter integration boundary and Monster Dex adapter

World owns a disabled Director and invokes its cheap tick guard. There is deliberately no activation flag, backend dispatch, debug spawn or changed PIP placement in production v0.1. The existing Encounter/Battle/Capture/Collection and server MonsterSelector remain unchanged.

Future wiring: opportunity → existing serialized backend request (no client monster selection) → validated Encounter DTO → `intent_for_encounter` → safe placement → existing entity lifecycle. Reuse current selected safe area/cursor/window snapshots only at opportunity/placement time. If placement fails after POST, keep the active server encounter reconciled and budget occupied; never POST another monster. Re-check live occupancy and environment before committing an entity; never apply a cached placement after monitor/environment changes. Cancel or ignore stale completions when replacing an adapter session. These runtime adapter behaviors are not enabled or claimed tested here.

`SpawnCandidateProvider` looks up presentation metadata by the server-selected code. PipProvider recognizes only PIP. A future Monster Dex adapter supplies zone, size, movement profile, lifetime hint and condition via this minimal Rust contract, without importing the parallel branch's types or owning rarity/stats/capture rules. `intent_for_encounter` preserves the current supported PIP/GROUND compatibility, validates matching code/condition, and caps the presentation hint by the caller's authoritative remaining lease. Broader server support needs an explicit later adapter change. ANY_TIME is the only enabled condition; DAY/NIGHT/FOCUS_SESSION/SPECIAL_EVENT are contract-only and perform no tracking.

## Validation and known risks

Initial pre-integration AUTOMATED: 80 Rust tests passed (including 7 grouped Spawn acceptance tests); 5 live server/DB tests ignored, NOT_RUN. Existing TypeScript/Vite build, animation, presentation, 16 asset tests, 9 automation tests and Tao integrity check passed. Asset validation in existing --allow-missing mode reports 26 previously unprovided assets; this does not certify those assets. Rust native link passed locally. CI results are recorded on the PR at the final commit.

PLATFORM_REQUIRED / MANUAL_REQUIRED: real multi-monitor/Dock/typing/click Never Steal Focus, single-instance behavior and live gameplay visual checks NOT_RUN. The disabled foundation and fake-clock failure tests are not an end-to-end automatic spawn rollout. Safe-area fallback inherits existing conservative Dock assumptions; 16 candidates can miss an available gap. Ground movement for elevated future zones requires profile/lifecycle integration review before enabling. No DB/Flyway/m_monster migration, dependency change, UI, new asset, Tao or native panel change.

## Parallel changes

Base was fetched origin/main c482fec before this work started. Inventory PR #18 subsequently merged: overlap is src-tauri/src/main.rs and src-tauri/src/behaviors.rs, consisting of independent additive wiring; check final merge for context conflicts. Monster Dex PR #19 has no overlapping files at inspection. At initial implementation neither branch was a dependency. Following the user's follow-up, latest origin/main 29ea7c3 containing both merged PRs was integrated into this feature branch without conflicts. Final approval/merge remains HUMAN_REVIEW_REQUIRED.


## Merged Monster Dex compatibility

After the requested main integration, PipProvider consumes a narrow projection of the authoritative content file `src/entities/monster-dex.json`. No duplicate monster registry, rarity, stats or visual scale is introduced. Rust SpawnCondition uses the same serde strings as the TypeScript contract; existing MovementProfile is reused. A compatibility test parses every merged Dex record and verifies known spawn vocabulary, while only enabled production PIP/GROUND/ANY_TIME is accepted by the provider.

Content spawnProfile and concrete SpawnZone have different responsibilities. BOTTOM/TOP/NEAR_DOCK map directly; FREE_AREA/FLOATING_AREA map to interior; EDGE/NEAR_DESKTOP_EDGE map to LOWER_CORNER for a conservative deterministic edge candidate. LEFT_EDGE and RIGHT_EDGE remain explicit placement options for future reviewed policy. Unknown profiles fail closed. Size and lifetime remain presentation inputs absent from the Dex contract; visualScale is not applied again. Metadata parsing happens only at provider lookup, never in the World tick.

Inventory source and migrations are unchanged relative to latest main; the upstream Inventory V5 migration is present only through the requested main merge, not introduced by this PR. Textual merge completed cleanly. Post-integration regression and CI are re-run on the final PR head.

Final local post-integration AUTOMATED PASS: 93 Rust tests (8 Spawn/adapter groups), 7 live fixtures ignored/NOT_RUN; Rust fmt and clippy; TypeScript/Vite build; 47 animation/base/Dex tests; 40 presentation/evolution/item tests; 16 asset tests; 9 automation-policy tests; existing optional-asset validation and Tao integrity. Native focus harness compile passed (runtime remains NOT_RUN). Latest-main diff contains only Spawn files and the 9 lines of World/module wiring; no Inventory or Monster Dex source/registry modifications.
