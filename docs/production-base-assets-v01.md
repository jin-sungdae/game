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

Actual production artwork: NOT_SUPPLIED. Automated results are recorded below.
Physical typing/click/drag focus and delivered-art appearance: MANUAL_REQUIRED.

## Production delivery

Place approved art at:
- `public/assets/creatures/moa/stage01/base.png`
- `public/assets/monsters/pip/base.png`

`companionBase(species, stage)` resolves beside the existing registered manifest
(including future registered species/stages); unknown identities fall back without IO.
`resolveMonster(code)` uses independent `monsters.json`; PIP is its sole entry.

Run `npm run validate:assets -- --allow-missing` while animation clips are absent.
Run `npm run validate:assets -- --allow-missing --strict-base` to require both base
deliveries. Omit `--allow-missing` to also enforce all 102 animation frames.
Optional RUU/NOX bases are validated when present but are not required deliveries.
Base checks never bypass frame checks: a partially supplied clip still fails.
Incorrect `base.PNG` / `base.jpg` names fail even in optional mode.

Runtime validates 256×256 and browser image decoding through the existing Image
IO (no fetch/blob CSP expansion). Delivery validation enforces PNG signature,
8-bit RGBA, chunks/CRC/decompression. A decodable non-PNG renamed base.png is
rejected by the delivery gate, not by browser Image decoding. Alpha channel
presence is checked; artist-provided transparent pixels and foot placement still
require visual review. Assets are trusted local bundled files, not remote uploads.
Success and failure promises are cached per URL for the WebView lifetime; no
polling or retry timer. A final DOM image error also poisons that base cache.
Restart/reload after replacing files. Existing clip controller/timing is unchanged.

## Manual acceptance after delivery

- Confirm animation wins when a complete clip exists; remove clip and reload to
  confirm base, remove base and reload to confirm diagnostic fallback.
- Check RIGHT/LEFT, full canvas bottom-center alignment for MOA and PIP, different
  apparent size, GROUND/JUMP/FREE_2D and drag/release at all safe-area edges.
- Check attack/hit/damage/capture/defeat/reward and reduced-motion presentation.
- Keep typing in VS Code/Chrome/IntelliJ during launch, clicks and dragging;
  confirm foreground/key focus never moves. This physical test is MANUAL_REQUIRED.

## Performance and risks

At most one extra base fetch + decode per registered URL per WebView lifetime;
no new interval, RAF, native window or backend request. Decoded base memory is
roughly 256 KiB per RGBA canvas plus browser overhead; no measured CPU/RSS claim.
Base rendering uses at most 82pt (PIP 65.6pt), deliberately below the requested
110–130pt target to fit existing panels. Actual opaque art can appear smaller.
Outer gameplay effects intentionally move/scale around the common bottom anchor;
world/native coordinates remain unchanged. No production or placeholder PNG added.

## Automated regression results (2026-09-18)

- Frontend production build: PASS.
- Animation: 27 existing + 7 base integration tests PASS (priority, registry,
  cached failures, dimensions, facing/anchor/scale, wrapper/reduced-motion contract).
- Gameplay presentation: 4 PASS.
- Asset validator: 12 existing + 4 base tests PASS. Existing binary parser
  fixtures remain test-only; no new PNG fixtures/artwork were generated.
- Optional asset gate: PASS, 0 errors, 18 clips + 4 bases NOT_SUPPLIED.
- Strict base gate: expected rejection, 2 missing required bases (MOA/PIP).
- Rust: 66 PASS, 4 live-server tests ignored/NOT_RUN in this task.
  Includes movement, drag, safe area, gameplay state and single-instance coverage.
- Cargo clippy/fmt: PASS (18 existing vendor Tao warnings, vendor untouched).
- Policy: 9 PASS. Tao integrity: PASS, exactly the existing 3-file patch.
- Java server: 37 tests, 0 failures/errors (25 Battle, 9 Game, 3 selection),
  isolated PostgreSQL database. No server/schema/native/engine changes.
- Physical macOS focus, base-art appearance: MANUAL_REQUIRED, not claimed PASS.
- CI: recorded on the PR against its final head; no automatic merge.
