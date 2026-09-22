# MOKORI Production Base Asset Delivery v0.1

Approved `mokori_base.png` is copied byte-for-byte to `public/assets/creatures/moa/stage02/base.png`.
SHA-256: `ba03365bea48efc2e05170e470b2facfa15ac8c78440dfb16c97c1b162b4fdc4` (source and destination equal).
No redraw, crop, resize, recolor, background removal, game code, dependencies, migrations, panel dimensions or architecture changes.

## Asset and size measurement

PNG 256×256, 8-bit RGBA, non-interlaced. Public AppKit NSBitmapImageRep read-only alpha measurement (nonzero-alpha bounds, exclusive right/bottom):

| Asset | Alpha bounds px | Visible extent at 82pt canvas | Fully transparent pixels |
|---|---|---|---|
| MOA Stage1 | (14,30)–(244,248) | 73.671875 × 69.828125 pt | 36,501 |
| MOKORI Stage2 | (15,37)–(241,252) | 72.390625 × 68.8671875 pt | 33,893 |

These are **computed asset extents at the current renderer scale**, not screenshot/DOM measurements. MOKORI has 8.98% more nonzero-alpha pixels but its outer extent is 1.74% narrower /1.38% shorter. Thus a larger visual silhouette is not proven; perceived growth remains manual acceptance. Matching MOA's outer width alone would require about 83.45pt canvas, but this is not a recommended unvalidated change. Keep the current 82pt canvas and 96×104pt native panel; review actual art before any sizing change.

Canvas bottom-center remains (128,256) → (41,82); horizontal flip does not move it. MOKORI's visible bottom lies 1.28125pt above canvas ground (4 transparent source rows), compared with MOA 2.5625pt. Static alpha bounds fit the existing panel. Animated combinations/actual WKWebView clipping remain MANUAL_REQUIRED. Source art faces RIGHT; LEFT uses the existing runtime flip.

## Integration unchanged

Registry resolves species `moa`, stage2, name MOKORI to stage02/base.png. Stage1 continues stage01/base.png. Existing resolution priority is animation → same-stage base → diagnostic fallback; stage1 is never substituted for stage2. Stage2 animation clips remain intentionally absent.

Server EVOLVED acknowledgment triggers the existing GLOW → REVEAL timeline; no optimistic stage update. The same Rust entity/world position and three pre-existing panels remain. Base polish receives species `moa` for both stages, so IDLE/WALK/LOOK/SIT/SLEEP/REACT already apply without a code change. Movement and combat remain unchanged (no stage bonus).

## Validation — 2026-09-22

### AUTOMATED PASS

- Asset format/alpha/transparent pixels, source/destination hash and stage2 recognition: PASS. `validate:assets -- --allow-missing --strict-base`: 0 errors; 24 missing clips + RUU/NOX bases intentionally pending. MOA/PIP strict gate retained.
- npm build; animation28 + base8; presentation gameplay4 + polish18 + evolution5; asset16; policy9; Tao exact three-file integrity: PASS.
- Rust73 PASS, existing five live tests excluded by default; cargo clippy and formatting pass. Existing vendor warnings unchanged.
- Real PostgreSQL17 server52 tests PASS, including evolution15 and prior37 tests.
- Fresh isolated container `luma-mokori-delivery-test` on55441 and Spring Boot18083, separate from the user's55440/18082 environment: LOCKED → fixture Lv3/EXP321/Bond5/Gold73 → AVAILABLE → explicit evolve → MOKORI Stage2, preserved world position, retry ALREADY_EVOLVED. Existing live battle/capture/reward and gameplay visual sequences pass at Stage2.
- Actual Spring Boot restart from test fixture process to production jar, same DB; fresh Rust World restores MOKORI Stage2. No user DB reset/mutation.

### PLATFORM PASS

macOS native compile/link/debug bundle including delivered PNG: PASS. Existing opt-in 10-second native smoke boots Stage2, exercises PIP lifecycle/interaction and exits normally. First run audit: activation0/keyWindow0 at exit (10.33s). Native app restarted after Spring Boot restart and stage2 bootstrap checked again. These logs do not prove actual image pixels on screen.

### MANUAL_REQUIRED / ENVIRONMENT_BLOCKED

Native screenshot/mouse inspection remains blocked by the previously reported `access_programs` organization permission. That unavailable tool was not called again; no new permission/system setting/workaround was introduced.

MANUAL_REQUIRED: visible production MOKORI PNG, perceived growth, actual GLOW→REVEAL, facing during movement, GROUND/JUMP/FREE_2D/drag visuals, animated clipping, base polish feel, native restart image display, continuous typing while clicking/dragging. Resolver/World/static bounds are automated PASS; do not equate them with visual acceptance.

## Known risks

MOKORI's outer alpha extent is slightly smaller despite more filled area. Full animation frame assets are not supplied. Pixel-perfect live PNG display and animated clipping have not been inspected in this restricted environment. Native dimensions and Never Steal Focus architecture are unchanged. PR must remain unmerged, READY_FOR_HUMAN_REVIEW after CI.
