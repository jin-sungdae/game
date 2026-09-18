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

## Implemented behavior

- MOA idle: 2.6s anchored breathing, scaleX .997–1, scaleY 1–1.012.
- MOA walk: .48s cadence, 1.5pt bob, ±.5° tilt, tiny squash/stretch.
- Look: 3.2s, .3° tilt/1.003 scaleY; sit: .975–.98 scaleY/3.6s.
- Sleep: 4.6s breathing and static in-canvas Zz; react: one .32s/2pt hop.
- PIP idle: 1.9s mostly still with a short ≤.8° twitch; roam: .34s/1.8pt bob.
- Dragging/despawning/unknown states stay still. Unknown species do not acquire
  MOA behavior. PIP defeat remains driven only by server VICTORY.
- Capture ring/pulse/success and despawn remain the existing authoritative pipeline.
- During gameplay impulses base animation yields to the existing outer effect;
  afterward it restarts from neutral. Ordinary same-state snapshots do not restart it.
- `prefers-reduced-motion: reduce` removes all base movement. Existing gameplay
  reduced-motion rules suppress hit shake. Static sleep text remains available.

## Automated checks

Build PASS; animation 27 + base 7 PASS; existing gameplay 4 + polish 18 PASS;
asset validator 16 PASS; strict production-base gate PASS; policy 9 PASS;
Rust 66 PASS (4 opt-in live tests not part of the default suite); clippy/fmt and
Tao integrity PASS. Native/CI/server final evidence is recorded on the PR.

Tests cover mappings, source priority, state/snapshot stability, separate facing
and gameplay nodes, capture/defeat authority, reduced motion and bounded cadence.
Wrapper/no-remount assertions are source-contract tests, not a simulated React DOM
reconciliation benchmark. Physical naturalness/focus remains MANUAL_REQUIRED.

## Performance / known limits

No new JS tick, RAF, interval, dependency, window or game state. Transform-only CSS
animations reuse the existing sprite; sleep adds one small span. CPU/RSS impact is
not numerically benchmarked. Composite layers can cost GPU memory/energy while idle;
no permanent will-change is used. Art is still a single whole-body image, not a
skeletal/ear deformation or frame animation. Production PNG hashes are unchanged.
Native dimensions remain 96×104, base canvas 82pt, PIP effective 65.6pt. During
ordinary motion the supplied bottom transparent padding accommodates tiny tilts;
future art with different padding needs a new clipping review. Gameplay defeat's
existing tilt/scale behavior is preserved, not redesigned.
