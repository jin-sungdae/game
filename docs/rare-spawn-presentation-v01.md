# Rare / Special Monster Spawn Presentation v0.1

Base origin/main a113be1 includes fifteen-species production activation and Monster Behavior #32. Presentation consumes the validated MonsterIdentity.rarity already selected by the server and checked against Content. No rarity inference from code, art, time, spawn zone or weight. No selection, NIGHT eligibility, server, DB, capture formula, Behavior AI controller, native panel or production asset changes.

## Duration and lifecycle

New tier durations are centralized in `src/presentation/spawnDurations.json`, read by TypeScript and compiled into the Rust presentation module:

| Tier | Effect | Visual duration | World SPAWNING hold |
|---|---|---|---|
| COMMON | Existing gp-appear unchanged | 300ms | existing600ms |
| UNCOMMON | Small soft green highlight | 400ms | existing600ms |
| RARE | Soft blue glow and one small static sparkle | 750ms | 750ms |
| SPECIAL | Slightly stronger violet glow and sparkle | 1000ms | 1000ms |

EPIC/unknown/debug do not receive a new tier effect; legacy presentation remains. COMMON's existing CSS animation remains byte-identical. Existing World spawning deadline is the maximum of its legacy600ms and tier duration. Thus movement/Behavior does not begin before the intended arrival interval, and waits at most1s. Uses the existing monotonic World tick/state transition, no additional scheduler. Behavior AI decisions/weights/timers are unchanged. Reduced motion uses the same bounded hold for deterministic state timing but only very faint opacity feedback, no sparkle, translation, scale pulse or flash.

## Composition, identity and cleanup

One aria-hidden, pointer-transparent span is placed inside the existing Creature. It is inset12px/9px/7px within the96×104 panel. No particle engine, sound, modal, fullscreen surface or new native panel. Glow uses a radial gradient and opacity only, never transform/filter. Existing pose → impulse → visual → sprite/facing layers remain unchanged. Enhanced tiers suppress only legacy outer arrival animation so it cannot scale-pulse under the new layer.

The layer exists only for SPAWNING with a recognized non-COMMON tier, no battle, no busy request and no gameplay effect. Battle/Hit/Capture interrupts it without blocking input or server actions. React removes it when the existing entity state changes; CSS opacity reaches zero at animation end, with no persistent visual fill. UNCOMMON has an invisible tail until the legacy600ms state exits. No local animation state, completion callback, RAF, timeout or polling is created, so interruption/unmount requires no timer cleanup.

Encounter id, MonsterIdentity, creature instance, native panel and world position are not replaced by the layer. Restoring an ACTIVE encounter follows the existing SPAWNING path and replays the bounded arrival; a restored battle suppresses the layer immediately. It never causes a new encounter POST. NIGHT remains entirely in #27 eligibility and is never reevaluated by presentation. NOCT gets violet through SPECIAL rarity, with no species hard-code; EMBER/LUNET/NOVA share RARE.

## Verification

New presentation tests cover tier durations, COMMON/unknown behavior, interruption/state-exit cleanup, all fifteen metadata identities, reduced-motion/CSS transform contracts and absence of timers/focus calls. New Rust World test covers all fifteen: no movement before the existing presentation deadline, transition into Roaming afterward, stable encounter identity and battle/capture before/after arrival. Existing full15 behavior traces and restart/night restoration tests run unchanged.

Full regression includes frontend build/animation/presentation/assets/automation, strict-alpha15/15, Rust fmt/tests/clippy/native link, Java/PostgreSQL and bootJar, Tao integrity and whitespace. Final counts and SHA-bound CI are recorded in the PR.

## Limits and manual acceptance

MANUAL_REQUIRED / NOT_RUN: visible WKWebView glow strength and timing on light/dark backgrounds, reduced-motion OS toggle, Edge placement visual inspection, real typing/clicking Never Steal Focus, single-instance and multi-monitor/Dock acceptance. Automated policy checks and native compilation are not observed desktop focus evidence. Current effect is intentionally subtle and inset; native screenshots may motivate presentation-only tuning after review. A delayed webview snapshot may shorten or clip the visual timeline at World state exit; gameplay does not wait for browser animation completion. No autonomous merge.
