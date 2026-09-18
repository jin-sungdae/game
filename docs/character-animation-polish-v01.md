# Character Animation Polish v0.1

## Integration decision before implementation

Keep frame AnimationController, asset resolver, PNGs, world/native geometry, and
server/gameplay logic unchanged. Add only a stable CSS motion wrapper inside the
existing BaseSprite renderer. Frame and diagnostic branches never receive it.

Layer order: native world position → existing gameplay pose/impulse → existing
PIP size wrapper → base motion → sprite facing flip. Every transform has its own
node and bottom-center origin. No new RAF, interval, entity state, or window.

Alternative: animate the image's existing transform or add a JS controller.
Rejected because that collides with facing or duplicates the existing engine.
Preserve the current 82pt canvas/96×104pt panel. Motion uses small scale/bob/tilt,
not world-coordinate changes. Gameplay attack/hit/capture and authoritative PIP
victory suspend/reset base motion, giving the existing effects full space and
preventing compounded transforms from overflowing tight bounds. Same-state world
snapshots keep the same node/class; no keys or controller remounts are added.

MOA idle/walk/look/sit/sleep/react and PIP idle/roaming use explicit presentation
mapping from existing states. Dragging/despawning are still. Sleep uses a small
static Z indicator within the existing canvas. Reduced motion disables base
animation and retains that indicator without changing world movement.

Acceptance results and native observations will be recorded after implementation.
Aesthetic naturalness and physical mouse/typing focus remain MANUAL_REQUIRED.
No automatic merge.
