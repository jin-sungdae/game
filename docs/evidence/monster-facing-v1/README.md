# Monster facing actual production evidence

[Implementation/ownership](../../monster-facing-runtime-v1.md) · [Analysis](analysis.json) · [Per-capture facing trace](facing-trace.csv) · [Native log](app.log) · [Preservation hashes](preservation.json)

## Review clips (original elapsed time)

- [LEFT 1](review/left-1.mp4)
- [RIGHT 1](review/right-1.mp4)
- [LEFT 2](review/left-2.mp4)
- [RIGHT 2](review/right-2.mp4)
- [Full PIP,49.82s](review/pip-production.mp4)
- [MOA control,49.83s](review/moa-control.mp4)
- [PIP LEFT pixel sample](review/pip-left.png) / [PIP RIGHT pixel sample](review/pip-right.png)

Actual `screencapture -l <native window>` frames, no HTML mock.130 samples per character, median384ms interval. Clips are display-enlarged only; production PNGs are untouched. ScreenCaptureKit helpers stalled in two earlier attempts, so native per-window capture was used. Failed attempts/raw logs retained locally; no screen-recording permission or production security setting changed. Full raw recordings live at `/Users/jinseongdae/Documents/LUMA QA/monster-facing-v1/run3/`.

| Measurement | Result |
|---|---|
| Actual encounter | Real server PIP; see encounter.json; normal safe placement |
| Stable moving samples |85, no native/renderer/direction mismatch |
| Direction sequence | RIGHT→LEFT→RIGHT→LEFT→RIGHT (requested four-direction subsequence present) |
| PIP center excursion |0pt |
| PIP bottom raster excursion |0.5pt, bounds202/203 physical px; panel y fixed |
| MOA center reversal excursion |1.5pt, unchanged historical magnitude |
| MOA bottom excursion |0pt |
| Clipping |None observed |
| Panel |96×104pt, canvas capture192×208px |
| Renderer |Source RIGHT, native−1 flips LEFT; native+1 displays RIGHT; unchanged |
| Focus / Single Instance |PASS,3 secondary launches, no activation/key/window duplication |

Native log monotonic time was fitted to existing AppKit wall timestamp and rounded CGWindow x (mean residual0.354pt). CSV explicitly separates native last-log x from capture-time panel x; velocity is derived from rounded panel displacement, not direct physics telemetry. Native facing is held between existing change records. Screen pixel direction is independently classified by the head/ears' upper centroid and visually checked in both linked samples. ±150ms around facing changes is excluded from strict paired assertions, not silently treated as passing.

Silhouette uses visible RGB>40 in actual window pixels below y60, preserving the historical MOA measurement convention. Pixel bounds are not an alpha-exact framebuffer contract. Frame timestamps and raw AX traces are included for independent review. PIP displays base because PR49 animations are not in main; no missing-asset regression or PIP animation approval is inferred.

Window restoration: [summary](window-restoration-summary.json). Kakao exact PASS; four Excel target windows disappeared during QA, so original-window restoration NOT_VERIFIABLE. Remaining three windows are original unadjusted geometry; app was not quit and no850px temporary size remains. Original failed restore snapshots are retained.

Final clean-HEAD release report and CI link are posted on the PR; GUI was built from the two production-source hashes in preservation.json before committing evidence. `session.json.headSha` identifies the base checkout, not an assertion that the recorded executable lacks this fix.
