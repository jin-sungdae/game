# Production Base Asset Runtime Integration v0.1

## Integration decision (before implementation)

Keep AnimationController, manifests, native panel sizes and gameplay wrappers unchanged.
Resolve an optional companion base.png beside its registered manifest; resolve PIP through
an independent monster registry. A cached, validated base loader is separate from clip
loading. Render a valid animation first, then base, then existing diagnostic CSS.
A failed base load stays failed for this WebView lifetime; reload after delivering assets.

Alternative: enlarge native panels to reach 110–130pt. Rejected for this integration:
current panels are 96×104pt and changing them affects geometry/hit regions. Use an 82pt
square base canvas, bounded by measured content, inside the existing 6pt horizontal
padding. Attack extent: 82/2 × 1.04 + 5 = 47.64pt < 48pt half-panel.
PIP inherits the existing outer 0.8 scale (65.6pt), not a second scale.
Canvas bottom-center stays at the panel bottom-center; no sprite labels displace it.
No assumption about opaque-pixel feet is possible before production art is supplied.

Base contract: base.png, 256×256, 8-bit RGBA PNG, transparent background,
bottom-center canvas anchor, source RIGHT. The base renderer adds no timer/movement.
Existing outer gameplay transforms deliberately provide temporary visual displacement.
Reduced motion continues to use the existing gameplay policy.

Validation will retain the full 34-frame contract and add optional base checks plus
an explicit strict base delivery gate. No production/placeholder PNGs are added.

## Verification

Implementation and checks pending. Actual production artwork: NOT_SUPPLIED.
Physical typing/click/drag focus and delivered-art appearance: MANUAL_REQUIRED.
