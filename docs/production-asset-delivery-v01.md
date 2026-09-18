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

Runtime and final CI evidence pending. Do not treat unobserved animation, mouse,
or focus scenarios as PASS. No automatic merge.
