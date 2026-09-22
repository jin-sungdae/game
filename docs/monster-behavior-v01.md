# Monster Behavior AI v0.1

## Design before implementation

Base origin/main0d78e93 (all15 Alpha active). Add a small Rust decision layer: content BehaviorProfile → scheduled semantic decision → existing MovementController intent → position. Parse profile once per placement; keep per-encounter controller and seeded stream stable across reconciliation. No React/native entity recreation, schema, backend command or gameplay formula change.

Profiles: CURIOUS uses separate approach/stop radii and finite slow steps; TIMID avoids nearby Companion then idles/wanders; PLAYFUL mixes sparse wander/burst/approach; AGGRESSIVE approaches but cannot initiate battle; SLEEPY starts paused and mostly pauses; STATIC TRICKSTER always pauses, EDGE TRICKSTER shifts vertically on its current safe side; PASSIVE mostly idles with short slow wander. Missing Companion yields safe idle/wander. Companion is a read-only reference: production proximity does not issue Companion reactions; explicit/debug interaction contracts remain.

Use bounded2–4 second decision intervals, at most one decision per due tick, no catch-up. Pause/suspension never draws RNG; resume waits a fresh bounded interval. Complete finite motion before a new random decision; current proximity can stop an approach without rerolling. Existing World tick owns scheduling. No new thread, timer, polling, framework or pathfinding.

Movement adapter owns absolute targets, profile constraints and cached cursor/window safety. Preserve GROUND/JUMP, confine FLYING to its upper band, EDGE to the current safe side, STATIC to no movement. FLOATING may translate horizontally through the existing interpolation while retaining vertical bobbing so CURIOUS/TIMID can act without replacing its profile. Add safe-start/safe-step wrappers around the existing controller, sharing existing unobstructed checks for all production profiles. Unknown windows deny motion. No OS calls in the decision layer.

Battle ACTIVE/request, terminal encounter, menu/items/evolution interaction, mouse-down or Companion drag suspend/cancel ambient movement. Only an authoritative still-ACTIVE encounter may resume; terminal never resumes even if reconciliation arrives later. Decision layer has no backend/Companion mutation APIs.

Alternatives rejected: direct position writes or per-tick random choices bypass movement safety and create jitter; behavior trees/new engines are unnecessary. Existing behavior-independent movement regressions will retain bounds/profile/identity assertions while timing expectations adapt to intentional pauses. Add deterministic actual World traces for seven representative species plus all15 regression, suspension/locks and safety tests. Architecture acceptance and merge remain HUMAN_REVIEW_REQUIRED. Visible native focus/input and visual comfort remain MANUAL_REQUIRED; no auto merge.
