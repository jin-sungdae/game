# Advanced Monster Spawn Conditions v0.1

## Design before implementation

Extend the existing Rust Spawn Director/runtime, content adapter and MovementController without replacing them. Add one injectable desktop calendar-clock boundary: NIGHT is local time >=22:00 or <06:00, independent of server UTC encounter leases and monotonic scheduling. Evaluate conditions only when attempting placement. An already visible encounter keeps its authoritative lease through dawn; a restart/new placement outside NIGHT uses existing Resolve and bounded backoff, never a replacement POST while authority is held.

Map EDGE content to safe left/right placement; reuse the existing controller for vertical edge motion and FREE_2D/FLOATING. Keep rarity as validated server/content metadata, never a desktop probability or placement rule. SPECIAL rarity never implies SPECIAL_EVENT. Use a test-only provider/asset fixture through the same World path while all production Batch3 flags and PNGs remain unchanged.

Alternatives rejected: server time for desktop-local conditions, enabling Batch3 to test, new movement engine, and changing combat/capture probabilities. Human review required before merge.

## Clock and eligibility contract

`spawn/conditions.rs` owns NIGHT: local hour >=22 or <6. `CalendarClock` supplies an offset-aware local snapshot; LocalClock is the sole new system-time adapter and uses the desktop OS timezone at evaluation time. Tests inject a fixed-offset fake clock. Cooldowns/backoff still use WorldClock monotonic durations; server spawned/expires timestamps remain UTC leases. No UTC hour is used to decide NIGHT. Changing timezone affects the next placement evaluation; daylight-saving ambiguity does not affect the local-hour predicate.

ANY_TIME is always eligible. NIGHT is evaluated at placement after authoritative server selection. DAY, FOCUS_SESSION and SPECIAL_EVENT remain unsupported/fail-closed; no OS activity tracking. Content readiness (enabled + contentReady + PRODUCTION) is still mandatory and is distinct from supporting a condition.

## Placement, movement and safety

EDGE/NEAR_DESKTOP_EDGE content maps to concrete safe side candidates. A seeded starting side and alternating attempts explore LEFT_EDGE/RIGHT_EDGE, so a blocked side can fall back to the other within the existing sixteen-attempt cap. LOWER_CORNER retains its existing mapping. Positions use only final DesktopSafeArea, native full-bounds projection and existing cursor/window/Dock exclusion. No raw screen placement or new monitor policy.

MovementController EDGE now follows the nearest usable vertical side, preserving spawn height instead of forcing the lower horizontal edge. World chooses bounded vertical targets and reverses at limits. FREE_2D preserves its initial Y at motion start, then uses the existing outbound/descent behavior (not a new physics model). FLOATING retains its finite sinusoidal excursion. The advanced profiles check existing cached window/cursor metadata before starting and before applying each step; unknown metadata prevents motion. Safety can pause movement rather than route around an obstacle. Batch1 GROUND/JUMP/FLYING routing is unchanged.

## Authority, rarity and failure policy

Server selection remains authoritative. The adapter validates COMMON/UNCOMMON/RARE/EPIC/SPECIAL metadata and existing movement wire values without desktop weights/probabilities. Rarity is absent from the placement Candidate and cannot choose a zone. NOCT stays SPECIAL + NIGHT, never SPECIAL_EVENT. Runtime and World share the same candidate/identity provider, with the production provider unchanged by test fixtures.

At night, ACTIVE reconciliation restores the same encounter ID without CREATE. At daytime restart, NIGHT fails closed: retain authority/budget, do not discover or render it, request the existing Resolve action for that same ID. A rejected/offline resolution uses the existing 5/10/30 second capped backoff; no new CREATE before server terminal confirmation and cooldown/reconciliation. Once an encounter is successfully visible, reaching dawn does not revoke it: it continues under its authoritative lease/battle policy. This deliberate distinction prevents wall-clock polling or client-only encounter expiration.

## Fixture and validation evidence

Test-only in-memory provider/asset-presence fixtures enter the real World apply/complete/tick route with actual content profiles, without changing production content, DB or PNGs:

| Fixture | Profile / condition / rarity |
|---|---|
| SHADE-like | EDGE / NIGHT / UNCOMMON |
| EMBER-like | FREE_2D / ANY_TIME / RARE |
| LUNET-like | FLOATING / NIGHT / RARE |
| NOVA-like | FREE_2D / ANY_TIME / RARE |
| NOCT-like | EDGE / NIGHT / SPECIAL |

Tests cover 21:59=false, 22:00=true, 23:59=true, 00:00=true, 05:59=true, 06:00=false; local +09 versus UTC; ANY_TIME; unsupported conditions; left/right and blocked-side placement; negative monitor origins; retained Dock/MenuBar-safe bounds; cursor/unknown windows; X/Y FREE_2D motion; fixed-X EDGE motion; FLOATING + NIGHT; rarity/identity mismatch; same-ID restart; daytime Resolve/backoff/recovery; and absence of extra clock reads/requests across 1,000 active ticks. A separate adapter fixture stages metadata in memory to verify all five rarity strings preserve zone/profile/condition, while real Batch3 ContentProvider candidates remain rejected.

Local AUTOMATED PASS: 122 Rust tests, cargo fmt/clippy, npm build; 58 animation/base/Dex/content/asset tests; 50 presentation tests; 25 asset tests; 9 automation tests; Tao integrity. Ten pre-existing optional live HTTP/server fixtures are NOT_RUN. The new World fixtures are in-process integration tests, not live HTTP or native desktop gameplay. CI head-bound Java/PostgreSQL and native checks are reported in the PR.

## Performance and known risks

No new RAF, timers, intervals, OS polling, window hooks, dependencies or permissions. Director still checks monotonic timestamps. Calendar evaluation and provider lookup occur only on an eligible placement attempt, not every World tick; already placed/resolving/backoff states return first. Motion safety reuses the existing tick and cached window array with no OS read or RNG. Production assets/readiness remain independent gates: adding conditions does not supply Batch3 art or authorize release.

Batch3 enabled/contentReady/productionStatus, production PNGs, Monster master/schema, server weighted selection, Battle/Capture formulas, Inventory, Evolution and Collection are unchanged. Batch1's five active species preserve production placement/movement/restart regression. Future Batch3 activation still needs approved assets, readiness/master integration and supported combat/capture (current COMMON capture support is not widened here).

MANUAL_REQUIRED: real WKWebView/AppKit launch/focus/input, physical multi-monitor/Dock changes, sleep/timezone transitions, and live Batch3 combat/visual acceptance. Fixed-offset clock/World fixtures and native compilation cannot certify those. EDGE behavior intentionally changes from the old lower horizontal foundation to safe vertical sides; its regression expectation was updated accordingly. Architecture approval and merge remain human decisions.
