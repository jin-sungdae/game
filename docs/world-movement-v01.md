# World Movement Engine v0.1

## Architecture

Companion behavior → MovementIntent → MovementProfile → MovementController →
bottom-center world position → existing NSPanel placement.

The existing CompanionState transition policy remains authoritative and unchanged.
WALKING creates a movement intent; movement completion produces the existing
Finished event, returning the Companion to IDLE. Movement never invents a state,
chooses a personality behavior or changes React/animation state. Existing WALKING
animation represents all three connected movement profiles in this version.

`src-tauri/src/movement/` contains pure simulation/data rules and deterministic
tests. `companion/mod.rs` owns intent selection, interruptions and state events.
`behaviors.rs` forwards environmental exclusion rectangles to the Companion.
`overlay.rs`/the added read-only native metadata function supply window bounds.
Existing NSPanel creation/activation policy, safe-area calculation, bottom-center
projection, Single Instance and Tao patch are unchanged.

## Profiles, intent and configuration

MovementProfile has serialized names GROUND, JUMP, FREE_2D, FLOATING, FLYING, EDGE,
STATIC. MovementIntent carries profile, target (logical AppKit points), duration
(seconds) and height. Controller start normalizes targets through full bounds
clamp; each tick clamps the full entity again.

MOA_MOVEMENT is local master configuration:

| Setting | Value |
| --- | --- |
| Default | GROUND |
| Allowed | GROUND, JUMP, FREE_2D |
| Eligible WALKING profile weights | 90 / 7 / 3 |
| Initial and post-excursion cooldown | 180 seconds |
| Excursion horizontal radius | 60 pt from current position |
| Maximum elevation | 48 pt above safe ground |
| Excursion duration | 2 seconds |
| Cursor exclusion half-width/height | 100 pt |

Existing behavior/Personality weights, idle timing, 180 pt ground walk radius and
40 pt/s ground speed are unchanged. Only WALKING decisions can select an
excursion, and the default remains GROUND when blocked, cooling down, or missing
window metadata. Rejected excursions do not trigger retries in a tick. Movement
uses its own seeded random stream so it does not consume behavior RNG samples.
Real-time environmental changes still affect decisions, so deterministic replay
requires the same cursor/window/safe-area input sequence as well as the seed.

Future species/monsters can supply a different allowed-profile/configuration and
issue the same intents without replacing CompanionState. RUU/NOX instances or
species selection/evolution behavior are not added here.

## Connected motion

- GROUND: preserves capped-dt constant-speed X movement along the safe ground
  line. Targets use the existing clamping and WALKING timeout.
- JUMP: `x = lerp(startX,targetX,p)`,
  `y = groundY + height * 4*p*(1-p)`. Height is capped by available headroom.
  Completion lands exactly at groundY.
- FREE_2D: chooses a clamped target within the local bottom band, linearly
  interpolates to it during the first half, then descends at target X during
  the second half. It always lands; it cannot remain at screen center.

The controller accumulates injected simulation dt (existing cap 0.1 s/tick),
normalizes elapsed/duration to [0,1], and reports completion. No physics engine,
additional timers, rendering-derived clock or OS calls exist inside simulation.
The existing behavior deadline also cancels/lands motion after a long suspension.

## Monster foundation only

These profiles are implemented as deterministic finite motions, but are excluded
from MOA's allowed profiles and have no Monster gameplay/lifecycle wiring:

- FLOATING: one bounded half-sine bob, returning to the starting altitude.
- FLYING: direct bounded linear interpolation to a target, holding there on
  completion until another intent. No pathfinding/collision physics.
- EDGE: one straight segment along the lower safe edge. Full perimeter traversal
  and wall transitions are intentionally not implemented in v0.1.
- STATIC: holds the clamped start position for the requested duration.

## Safe area, cursor and window interference

World continues using DesktopSafeArea.final_luma_safe_area. The movement layer
never substitutes NSScreen.frame/visibleFrame for that safe area. All targets,
intermediate full entity bounds and existing native presentation are clamped.
Changing safe area cancels an active motion and returns to the new ground; panels
that cannot fit still follow the existing hide policy. Negative monitor origins
and different entity sizes use the same geometry contract.

Before an elevated intent, the conservative swept rectangle (whole entity from
start through target/arc apex) must avoid both cursor exclusion and known normal
application windows. The current cursor is rechecked each simulation tick; window
metadata is refreshed once per second. If interference appears, cancel and land.
GROUND is intentionally exempt from this extra rule, preserving existing UX.

A public CGWindowListCopyWindowInfo on-screen metadata query reads only PID,
layer and bounds. It ignores LUMA's own process and non-normal window layers,
converts Quartz top-left points to AppKit bottom-left using the primary-screen
origin contract, and caches at most 64 rectangles. No window title/image capture,
AX API, keyboard hook, focus/activation or permission request is added. Nil data,
unreadable bounds or capacity overflow produces unknown metadata and suppresses
excursions. Ordinary maximized windows commonly suppress all excursions, which
is an intentional conservative outcome rather than a reason to bypass checks.

Drag start cancels automatic motion without moving the grab point. While dragging,
existing cursor-relative full-bounds clamp is preserved. Release returns to ground
and IDLE; the existing small-motion click classification may separately produce
REACTING. PIP reaction interrupts movement, lands and uses the existing reaction
state/duration. PIP lifecycle/spawn/motion are unchanged.

## Tests and results

- Rust: 43 PASS (all prior 30 retained, 13 movement/integration tests added).
- Added coverage: ground speed; jump midpoint/landing; free2D completion;
  left/right/top/bottom full bounds with negative coordinates and different sizes;
  final DesktopSafeArea integration; area change; size change/cancel;
  finite floating/flying/edge/static; local target bounds; cursor/window/unknown
  metadata exclusions; allowed profile weights; drag interruption/release;
  seeded excursions/cooldown; behavior RNG isolation.
- Animation/registry: 27 PASS; asset validator: 12 PASS; policy regression: 8 PASS.
- npm build, application clippy, Rust formatting and Tao patch integrity: PASS.
  Existing upstream Tao dependency warnings remain unchanged.
- Asset scaffold validation: 0 errors, 18 PENDING clips; no production PNG added.
- Native bridge compiled/linked by macOS cargo test/clippy. Actual long-running
  desktop interaction/focus, real window metadata availability and CPU/memory
  measurements: NOT_RUN / MANUAL_REQUIRED. Unit tests do not establish native UX.

## Performance and known risks

The existing 33 ms simulation timer is reused. Motion interpolation is constant
work; exclusion checking is O(window count), bounded at 64 cached rectangles.
There is one public window metadata query per second on the AppKit main thread,
plus bounded vector copies during world updates. CoreGraphics query latency and
actual CPU/memory overhead need measurement on the user's desktop. No new
libraries/dependencies/assets/animation loops are added.

Window metadata may be incomplete and is up to one second stale. Non-normal
floating windows/popovers are not an exhaustive interference map; this is a
best-effort UX policy, not a guarantee that no other window can move beneath an
entity. Cursor checks use the existing sample cadence. Obstruction/area change,
reaction or timeout cancellation lands immediately and may look abrupt; smooth
emergency landing is future polish, not physics in this PR. The conservative
swept rectangle can reject a path whose actual curve would be clear.

Manual review: run the existing app with another app focused; confirm normal
GROUND walking and typing, then leave a clear lower desktop corridor and cursor
far away. After the initial 180 s cooldown, rare eligible WALKING decisions may
jump or make a short local excursion. Check feet return to ground, drag in flight,
Dock bounds, window/cursor approach and the existing PIP proximity reaction. Do
not interpret lack of excursions under a maximized window as a failed engine.
