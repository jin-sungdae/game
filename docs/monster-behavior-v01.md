# Monster Behavior AI v0.1

## Design before implementation

Base origin/main0d78e93 (all15 Alpha active). Add a small Rust decision layer: content BehaviorProfile → scheduled semantic decision → existing MovementController intent → position. Parse profile once per placement; keep per-encounter controller and seeded stream stable across reconciliation. No React/native entity recreation, schema, backend command or gameplay formula change.

Profiles: CURIOUS uses separate approach/stop radii and finite slow steps; TIMID avoids nearby Companion then idles/wanders; PLAYFUL mixes sparse wander/burst/approach; AGGRESSIVE approaches but cannot initiate battle; SLEEPY starts paused and mostly pauses; STATIC TRICKSTER always pauses, EDGE TRICKSTER shifts vertically on its current safe side; PASSIVE mostly idles with short slow wander. Missing Companion yields safe idle/wander. Companion is a read-only reference: production proximity does not issue Companion reactions; explicit/debug interaction contracts remain.

Use bounded2–4 second decision intervals, at most one decision per due tick, no catch-up. Between deadlines and during suspension no RNG is drawn; scheduled pause decisions may resample after their deadline; resume waits a fresh bounded interval. Complete finite motion before a new random decision; current proximity can stop an approach without rerolling. Existing World tick owns scheduling. No new thread, timer, polling, framework or pathfinding.

Movement adapter owns absolute targets, profile constraints and cached cursor/window safety. Preserve GROUND/JUMP, confine FLYING to its upper band, EDGE to the current safe side, STATIC to no movement. FLOATING may translate horizontally through the existing interpolation while retaining vertical bobbing so CURIOUS/TIMID can act without replacing its profile. Add safe-start/safe-step wrappers around the existing controller, sharing existing unobstructed checks for all production profiles. Unknown windows deny motion. No OS calls in the decision layer.

Battle ACTIVE/request, terminal encounter, menu/items/evolution interaction, mouse-down or Companion drag suspend/cancel ambient movement. Only an authoritative still-ACTIVE encounter may resume; terminal never resumes even if reconciliation arrives later. Decision layer has no backend/Companion mutation APIs.

Alternatives rejected: direct position writes or per-tick random choices bypass movement safety and create jitter; behavior trees/new engines are unnecessary. Existing behavior-independent movement regressions will retain bounds/profile/identity assertions while timing expectations adapt to intentional pauses. Add deterministic actual World traces for seven representative species plus all15 regression, suspension/locks and safety tests. Architecture acceptance and merge remain HUMAN_REVIEW_REQUIRED. Visible native focus/input and visual comfort remain MANUAL_REQUIRED; no auto merge.

## Implemented contract

`monster_behavior.rs` owns seven content profiles, semantic intents,2–4 second intervals and radii (approach280, stop180, timid trigger220, safe320 logical points). A finite behavior step is normally40 points at14 points/sec; Sleepy16/8, Passive24/10, ShortBurst48/24. Actual motion follows the existing engine: e.g. FREE_2D retains its finite outbound/descent, while FLOATING translates on X and bobs vertically. Idle/pauses have zero displacement. No global RNG or time source is called by decisions.

World constructs one controller at accepted placement using its existing seed mixed with Encounter UUID. Same-ID reconciliation preserves it and its deadline; a new encounter receives a fresh stream. `Random` permits a scripted deterministic test adapter; production uses a local seeded stream. At a due opportunity three bounded draws choose behavior, direction and next deadline. A moving finite intent completes before another decision. No per-tick reroll, catch-up loop or background execution. Resume waits2 seconds. The production snapshot/React/native identity contract is unchanged.

CURIOUS has hysteresis and stops pursuing near the Companion; a running Jump finishes its finite landing before pausing (avoids freezing in mid-air). TIMID maintains avoidance until outside the safe radius. PLAYFUL uses20% short burst,20% eligible approach,40% wander,20% pause. AGGRESSIVE has no battle authority and only requests an approach intent when far enough. SLEEPY starts paused, then80% pause opportunities. TRICKSTER remains STATIC pause for MIMI and intermittent vertical EDGE shifts for SHADE. PASSIVE uses65% idle opportunities. Probabilities here are ambient decisions only, never server encounter selection/capture.

The active Companion is read only; no identity/position means idle/wander fallback. Production ambient proximity no longer invokes the old debug PIP Companion reaction; explicit interaction and debug lifecycle remain. A separate otherwise-identical Companion simulation is compared at every World trace tick to prove no behavior mutation. MOA/MOKORI state/data are unchanged.

`movement/ambient.rs` translates relative semantic decisions to the existing MovementIntent, owns bounds/upper FLYING band/same-side EDGE/STATIC constraints, and applies cached swept-window/cursor checks at start and every movement step. FREE_2D's descent is included in start-path safety. Unknown windows deny motion; newly occupied paths cancel conservatively. Dock/MenuBar safety comes from final DesktopSafeArea, never raw screen bounds. STATIC never receives displacement.

World suspends on battle ACTIVE or pending action, menu/items/evolution lock, mouse-down, Companion drag or engaged/despawning state. It cancels motion without replacing the Entity. Authoritative terminal encounter status permanently prevents resume for that controller; a non-ACTIVE battle whose encounter remains ACTIVE can resume after the delay. No automatic battle/attack API is called by behavior.

## Deterministic World evidence

Actual production ContentProvider/assets/World/MovementController simulations:15 species ×1,800 ticks over60 simulated seconds with a fixed seed/Encounter identity, negative-origin monitor and retained Dock/MenuBar safe area. NIGHT is test-clock injected. Seven representative decision sequences are asserted distinct; identical World inputs replay identical positions. All ticks retain bounds, profile restrictions, Encounter identity and unmodified Companion trajectory. No battle/request appears from AGGRESSIVE.

| Representative |60-second scheduled decisions | Intent counts |
|---|---|---|
| MELLO / CURIOUS |20 |4 Approach,16 Pause |
| WISP / TIMID |21 |9 Wander,12 Pause (far); separate near-World test confirms Avoid |
| PIP / PLAYFUL |20 |12 Wander,1 ShortBurst,2 Approach,5 Pause |
| EMBER / AGGRESSIVE |20 |5 Approach,15 Pause; no auto battle |
| MOSSY / SLEEPY |21 |15 Pause,6 short Wander; initial Pause |
| SHADE / TRICKSTER |21 |9 EdgeShift,12 Pause; constant X |
| PEBB / PASSIVE |21 |9 Wander,12 Idle |

MIMI:21 Pause decisions, unchanged X/Y. CHIRP remains within the upper flight band; NOCT keeps its edge X; all GROUND remains grounded. Summary with exact decision sample positions: `docs/evidence/monster-behavior-v01/trace-summary.json`. First/last positions there are decision samples, not the final render frame. Full trace reproduction: set LUMA_BEHAVIOR_TRACE to a writable JSON path when running `cargo test --manifest-path src-tauri/Cargo.toml all_fifteen_world_traces -- --nocapture`.

## Verification and performance

Local AUTOMATED PASS:137 Rust tests (12 pre-existing opt-in HTTP/live tests NOT_RUN in this change); native link; fmt/clippy (pre-existing Tao warnings only); npm build;58 Animation/Base/Dex/Content/Asset tests;52 Presentation tests;27 Python asset tests;9 automation tests; strict-alpha15/15; ordinary asset validator; Tao integrity; diff check. Old placement/movement regression tests now allow intentional idle periods instead of demanding continuous movement in a short sample. Their safety/profile/restart/identity checks remain, engine motion completion tests remain, and new full World behavior traces cover all15.

Performance is a functional budget assertion, not a CPU benchmark: fifteen controllers at30Hz for60 seconds make at most30 decisions each, rather than1,800; no catch-up after a long time jump. Concrete World traces made19–21 decisions/species. Between opportunities, existing tick does constant-time state/deadline checks and existing cached collision checks; no JSON parsing or OS call per tick. No new timer, thread, RAF, dependency, framework or pathfinding. Server/PostgreSQL and macOS SHA-bound CI evidence is on PR #32.

## Risks, manual checks and future expansion

Visual comfort and subjective personality need human acceptance. Conservative obstacle checks may pause movement. Explicit interaction/battle suspension freezes the current motion; resume uses the existing controller from that position and never recreates the entity. Existing FREE_2D descent and upper-band flying are intentional physical constraints, so semantic approach need not reach the Companion on every profile. Decisions are local ambient state, not persisted across process restart; authoritative Encounter identity still restores normally.

MANUAL_REQUIRED / NOT_RUN: visible WKWebView/NSPanel motion, Never Steal Focus while typing/clicking, physical monitors/Dock and visual comfort; native compilation and deterministic World simulation do not certify these. No new DB schema, skills/elements, automated combat, sound, quests or stage evolution. Future profiles may extend the small decision policy and movement adapter with deterministic tests; no behavior-tree/pathfinding framework is introduced. Content activation flags,15-species weights961, all PNGs, server formulas/migrations, Companion/backend/native/Tao code remain unchanged. Auto-repair iterations used:2 of3. No auto merge.
