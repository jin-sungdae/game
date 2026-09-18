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

Implementation and validation pending. Use an isolated PostgreSQL database, never the user's acceptance DB. Record AUTOMATED, PLATFORM_REQUIRED and MANUAL_REQUIRED separately. No unexecuted native validation is a PASS.
