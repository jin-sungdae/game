# Production MOA eye-region measurement only

Source: production `public/assets/creatures/moa/stage01/base.png`, 256×256; SHA256 `3e2f8a31d71bda3005a0a78eb31ac1ac84a146add959034fdcea3f5c1b765743`.

LEFT/RIGHT mean screen/image left/right in the original source-facing-RIGHT PNG, not anatomical left/right. Top-left origin, x rightward, y downward. Maximum coordinates are inclusive. Width=x_max-x_min+1. Centers are midpoint of pixel-index extrema; they are not intensity centroids. In pixel-edge coordinates the centers would be +0.5 on each axis.

Pixels were losslessly decoded. Within broad face ROIs, use alpha>=128, max(RGB)<230 and R-G<35 to exclude cream skin and red nose. Select the largest four-connected component. Bounding rectangles include enclosed highlights. Strict dark bounds use max(RGB)<110 on the same component. Source opacity is commonly253, so requiring255 would incorrectly discard the eyes.

There is no authored semantic eye mask in this PNG. Antialias pixels mix eye and fur, so an objectively unique subpixel boundary or exact separate sclera segmentation cannot be claimed. Measured colored-eye bounds (including enclosed highlights) are LEFT x192..211,y138..163 and RIGHT x230..236,y138..157. RGB<110 dark bounds are LEFT x192..210,y138..162 and RIGHT x231..236,y138..156.

The reported full-eye rectangles conservatively add ONE pixel for bright exterior antialias/white rim: LEFT x191..212,y137..164 (22×28), RIGHT x229..237,y137..158 (9×22). These are coverage rectangles derived from measured pixels, not a claim that every boundary pixel is eye tissue. `eye-box-overlay.png` draws those boxes and center points only, over a copied source. Magenta=LEFT, blue=RIGHT. `eye-box-overlay-4x.png` is a nearest-neighbor debug enlargement; neither is a production asset.

Proposed minimum practical blink work regions add ONE further pixel: LEFT x190..213,y136..165 (24×30), RIGHT x228..238,y136..159 (11×24). These are proposed work ROIs, not rectangular paint masks or guaranteed anatomical minima. Especially near the far/right eye, protect the nose, face outline and original alpha; do not fill the entire box. Exact eye-local edits should respect the silhouette/edge mask rather than erase neighboring nose pixels.

`measurement.json` includes exact threshold definitions, counts, per-row component extents and all rectangles. `measure.py` reproduces measurement and the debug overlay. No production/blink image, runtime, timing or repository file was modified. No new artwork was generated.

Published to PR #46 after confirming the measurement had previously existed only in the local QA folder. This evidence does not change or approve Blink v2 artwork; visual acceptance remains FAIL.

[Debug overlay](eye-box-overlay-4x.png) · [Measured coordinates and per-row extents](measurement.json)
