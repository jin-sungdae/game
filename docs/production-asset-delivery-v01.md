# Production Base Asset Delivery v0.1

Base: main `0991cd9` (PR #13 merged). No runtime/design/native changes.
Approved original PNGs copied byte-for-byte, without resizing/repainting/removing background.

| Asset | Destination | SHA-256 |
|---|---|---|
| MOA | public/assets/creatures/moa/stage01/base.png | 3e2f8a31d71bda3005a0a78eb31ac1ac84a146add959034fdcea3f5c1b765743 |
| PIP | public/assets/monsters/pip/base.png | f0e63d1349854c4539f07e402eecd70a7cfcfc789442d9243b5e20e4304487dd |

Both files: 256×256, 8-bit RGBA, non-interlaced PNG. Strict base gate PASS.
102 animation frames remain NOT_SUPPLIED; existing base fallback is used.

## Measurement

Read-only PNG filter decoding measured all pixels with alpha > 0, with exclusive
right/bottom bounds. No image output or transformation was performed.

| Metric | MOA | PIP |
|---|---:|---:|
| Alpha bounds in 256px source | (14,30)–(244,248) | (12,41)–(244,248) |
| Fully transparent pixels | 36501 | 34379 |
| Partial alpha pixels | 28340 | 30409 |
| Configured canvas at current layout (logical pt) | 82×82 | 65.6×65.6 |
| Calculated visible bounds (logical pt) | 73.671875×69.828125 | 59.45×53.04375 |
| Transparent space below visible body (pt) | 2.5625 | 2.05 |
| Native panel contract (pt) | 96×104 | 96×104 |

The canvas anchor is bottom-center; opaque feet are above it by the supplied
transparent padding. PIP uses the existing 0.8 gameplay wrapper scale once.
These are source-alpha/layout calculations, not a claim of measured WKWebView DOM
rectangles. Native panel and visual observations are recorded below after execution.
No scale/panel change is made. The current art is substantially smaller than the
original 110–130pt aspiration because the 96pt panel is retained. Keep 82pt for
this delivery; any larger target needs a separate panel/hit-area review.

## Regression fixture adjustment

Existing missing-base tests copied all production assets into their temporary
fixture. Delivering real bases invalidated four missing-file assumptions (including
case-insensitive base.PNG on macOS). Exclude base.png only from that temporary
fixture copy; preserve production files and all validator/runtime behavior.

## Validation

Automated: strict-base gate PASS; frontend build PASS; animation 27 + base 7,
presentation 4, asset validator 16, policy 9, Rust 66 PASS; clippy/fmt and Tao
integrity PASS (18 pre-existing Tao warnings). Java/PostgreSQL 37 tests + bootJar
PASS after Gradle clean removed a duplicated generated `GameApplication 2.class`.
No application source workaround. Isolated test DB only; no production DB changes.

Local macOS: the delivered MOA was visibly rendered as an image in the actual
`tauri://localhost/index.html?entity=moa` WKWebView (AX image MOA), facing LEFT.
Captured panel image was 96×104; no stationary MOA sprite clipping observed.
CUA drag recorded DRAGGING → IDLE and world position (1632,200) → (1618.97,200),
with native frame (1571,200,96,104), groundY=200, reserved intersection=0.
NSPanel remained transparent/nonactivating by configuration; alpha data is verified.

The native UI tool exposed only the MOA window, not PIP/interaction windows.
PIP rendered rectangle, runtime RIGHT view, moving JUMP/FREE_2D foot placement,
and the actual attack/hit/damage/capture/defeat/reward pixels are NOT_VERIFIED,
MANUAL_REQUIRED. Automated movement/presentation tests do not replace those checks.
Native panel bounds are measured; visible sprite dimensions above are calculated
from alpha bounds and existing transforms, not DOM getBoundingClientRect results.

Focus audit during tool-driven drag: activation=1, keyWindows=0 (PID 77851,
182.38-second run, normal cleanup). Never Steal Focus is NOT requalified as PASS.
The notification coincides with CUA drag; tool-versus-native causality is unresolved.
No focus/native patch is attempted in this asset-only delivery. HUMAN_REVIEW_REQUIRED.

CI and additional live smoke evidence are linked on the PR against its head.
No automatic merge. Final visual acceptance remains with the user.
