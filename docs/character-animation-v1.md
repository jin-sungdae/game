# Character Animation System v1 — MOA/PIP Pilot

## Proposed scope and alternatives (before implementation)

Behavior/gameplay → AnimationStateResolver → IDLE/MOVE/REACT → CharacterAnimator → CharacterRenderer. MovementController retains all position, velocity and safe-area authority. The renderer only observes successive native position snapshots to measure speed; it never writes world coordinates.

Reuse the existing frame-sequence manifest/AssetIO architecture, registry-derived own-character roots and browser image cache. Decode each complete clip before use. A shared lifecycle-managed requestAnimationFrame clock replaces per-character animation clocks for the pilot. Keep React entity identity stable across state/frame changes and same-encounter reconciliation.

Alternative: a new sprite-sheet framework would add another asset format and validator path; per-character timers would fragment lifecycle ownership. Neither is needed. Existing frame sequences are the smaller extension. Only MOA Stage1 and PIP opt in; other stages/species retain their base path.

Animation transforms live inside facing and existing spawn/gameplay/evolution wrappers. Special presentation suppresses pilot animation; REACT then MOVE then IDLE follow. Missing/unprovided/invalid animation falls back to the same character production base, then existing diagnostic fallback. Production PNGs are immutable in this PR; no animation artwork supplied/generated.

This explicitly requested presentation-layer addition requires human architectural review before merge. Implementation and validation evidence will be appended; no automatic merge.
