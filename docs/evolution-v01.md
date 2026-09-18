# Evolution v0.1 — MOA → MOKORI

## Design and review boundary

Server-authoritative, explicit opt-in evolution extends the existing JDBC backend and bounded Rust worker. No behavior, movement, native window, focus, combat formula or production asset changes. The existing compact interaction panel is reused; no new NSPanel is created.

Alternative rejected: desktop eligibility or optimistic stage changes could disagree with PostgreSQL and duplicate transitions. A generic rule engine is unnecessary for one approved transition.

## Domain and persistence

EvolutionRules owns MOA stage 1 → 2, level ≥ 3 and bond ≥ 5. GET status never mutates. POST accepts no client progression. LOCAL_PLAYER is locked before the active companion FOR UPDATE. The next master must exist. Stage update and V4 history insert share one transaction. UNIQUE(companion, from, to) protects the history invariant. No progression or gold is consumed.

Only stage 1 → 2 is enabled. Stage 2 without another enabled rule is LOCKED, not eligible for stage 3. Stage 5 reports MAX_STAGE. A retry after the recorded 1 → 2 transition returns ALREADY_EVOLVED. Enabling future transitions requires revisiting request idempotency before expanding this endpoint.

## Desktop and assets

The existing worker transports status and authoritative bootstrap identity. The UI displays server requirements without computing eligibility. Explicit EVOLVE waits for success before a bounded 1.6-second local presentation. Position and native windows are retained. Restart restores identity from bootstrap. Stage 2 resolves moa/stage02; missing PNG/frames use a labelled MOKORI Stage 2 diagnostic fallback and never stage 1 production assets.

## Validation

Validation uses an isolated PostgreSQL database, never the user's acceptance DB. The evidence below distinguishes AUTOMATED PASS, PLATFORM PASS, MANUAL_REQUIRED and ENVIRONMENT_BLOCKED.

## API contract

- `GET /api/v1/companions/active/evolution`: server status, current species/stage/name, optional next stage/name and level/bond requirements (`required/current/met`). Unconfigured transitions return LOCKED with null next/requirements; stage 5 returns MAX_STAGE.
- `POST /api/v1/companions/active/evolve`: no body or query parameters. Returns `{result: EVOLVED | ALREADY_EVOLVED, evolution, bootstrap}`. Ineligible and maximum-stage commands return 409 NOT_ELIGIBLE/MAX_STAGE; missing active companion/master returns 503 GAME_UNAVAILABLE. Client progression fields return 400.
- A lost POST response never triggers automatic mutation retries. Subsequent status polling detects a changed identity and retrieves bootstrap. Only an acknowledged EVOLVED response plays the effect; ALREADY_EVOLVED restores identity without replaying it.

## Migration and invariants

`V4__companion_evolution_history.sql` adds a separate history table with identity PK, companion FK, species FK, source/target master FKs, consecutive stage and nonnegative progression checks, transition uniqueness, timestamp and master-reference indexes. V1/V2/V3 are unchanged. Updating stage and inserting history are atomic; an audit insertion failure rolls the stage update back. No rows are written to Collection. Player locking follows the existing battle/reward serialization order.

## Desktop implementation

`backend/evolution.rs` validates wire identity, owns the explicit request guard and the GLOW → REVEAL → IDLE timeline (0.8 + 0.8 seconds). `World` stores authoritative identity separately from the existing CompanionState/movement entity. React renders the snapshot only. The existing bounded worker polls eligibility on its five-second cycle; no new worker, timer, dependency, panel or keyboard hook is added. The existing interaction panel is anchored to MOA for evolution and retains PIP encounter behavior otherwise.

`src/entities/companions.json` registers moa/stage02 and MOKORI. Its manifest uses the existing schema and empty clip directories. No PNG is generated. Missing stage 2 images are cached failures, with a labelled diagnostic placeholder; neither stage 1 base nor animation clips are substituted. Reduced-motion CSS disables the new pulse/fade. Existing frame controller timing is unchanged.

## Validation evidence (2026-09-18/19 local macOS)

### AUTOMATED PASS

- Real PostgreSQL 17.10 server suite: **52 tests**, including **15 evolution integration tests**. Covers locked level/bond/both, available without mutation, preserved progression, exactly-once/concurrent/retry behavior, rollback, missing master/active state, MAX_STAGE and level-based battle after evolution.
- Rust: **73 passed**, five explicit live tests excluded from the default suite. Formatting and clippy `--no-deps -- -D warnings` pass; pre-existing upstream Tao warnings remain visible.
- Animation **28**, base renderer **8**, gameplay **4**, character polish **18**, evolution presentation **5**, asset validator **16**, repository policy **9** tests pass. `npm run build`, strict delivered-base validation and Tao three-file patch integrity pass.
- Actual isolated PostgreSQL `luma-evolution-test` on **55440**, Spring Boot on **18082**, Rust Desktop World: LOCKED (Lv1/Bond0) → isolated fixture Lv3/EXP321/Bond5/Gold73 → AVAILABLE → explicit POST → MOKORI Stage2. History query returns exactly one 1→2 row. All four progression values are preserved. Repeated POST returns ALREADY_EVOLVED.
- Spring Boot process **93776** was stopped; new process **94831** used the same database. New HTTP bootstrap and a fresh Rust World restored MOKORI Stage2. This is an actual server restart, in addition to the integration test's fresh-service read. User acceptance database on 55439/server 18081 was not modified.
- Existing live encounter, battle/capture/reward and gameplay-presentation Rust slices pass with the evolved companion (level-based attack damage 16, no stage bonus).

### PLATFORM PASS

Local macOS native compilation/linking and debug `.app` bundling completed. This proves a native build, **not** actual UI/focus acceptance.

### ENVIRONMENT_BLOCKED

Final native display validation encountered `The access_programs parameter is not enabled for this organization.` The unavailable tool/permission was not retried or bypassed. No system settings, permissions, architecture or tests were changed to work around it. A preliminary view was insufficient to establish Stage2 UI success and is not counted as PASS.

### MANUAL_REQUIRED

On a permitted macOS session, verify the explicit ✦ entry opens the compact panel; EVOLVE alone triggers server execution; loading prevents duplicates; GLOW/fade/reveal is comfortable; MOKORI Stage2 diagnostic fallback is visible (no stage1 PNG); position/anchor/clipping remain correct; reduced motion is quiet; and clicking EVOLVE/LATER, dragging and subsequent typing never steal application/key focus. Actual native app restart appearance is manual; **server restart persistence and fresh Desktop World identity are automated PASS**.

## Known risks / next stages

- MOKORI production base/animation assets are intentionally absent. The diagnostic fallback is not final character art.
- Stage 2 is LOCKED for further evolution. Stage 3–5, RUU/NOX rules and stage combat bonuses are not implemented. Before enabling sequential transitions, add a transition-specific idempotency contract so delayed retries cannot request the next evolution.
- Eligibility polling adds one bounded local HTTP read per five-second cycle; effect phase changes use the existing Rust tick and emit only at transitions. No new JS animation loop. CPU/RSS deltas have not been benchmarked.
- Native focus/presentation acceptance remains manual due to environment tooling, not an observed evolution regression. No blanket native focus PASS is claimed.
- Local synced duplicate `* 2` source files were preserved and excluded. Generated duplicate Node type directories required `npm ci`; no dependency/version workaround was introduced.
- PR stays unmerged, READY_FOR_HUMAN_REVIEW after final CI passes.
