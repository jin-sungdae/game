# MOA REACT v1 — production asset pilot

Six supplied `react_01..06.png` are copied byte-for-byte to canonical `react/react_00..05.png`. [Source manifest](source-manifest.json) and [asset validation](asset-validation.json) retain hashes,256×256 RGBA/transparent checks,RIGHT source, bottom-center registration,center-X0px,bottom0px and06==01. No artwork transformation. MOA Stage1 REACT alone opts into `PRODUCTION_PILOT`; approved IDLE/MOVE remain production, PIP remains NOT_SUPPLIED.

The existing canonical manifest already defines6×80ms,480ms,non-looping. Generated static metadata therefore needs **no duplicate source or regeneration diff**. `PilotAssets` only adds the per-state opt-in. Renderer, resolver, shared clock, idle scheduler, native movement/gesture code, CSP and runtime inventory have no change. Base/Breath/Blink/MOVE hashes are preserved in [preserved contracts](preserved-contracts.json). No new engine, API, fetch, timer or polling loop.

## Trigger and authority

Real mouse-down uses the existing `drag` action. Native release classifier decides click versus drag. A valid click sets native REACTING and independently requests server interaction. First eligible click grants Bond+1; cooldown click grants+0 yet still acknowledges visually. Backend reward authority is unchanged.

REACT is one-shot:01→02→03→04→05→06, then current velocity selects MOVE or IDLE. Native REACTING lasts1.2s as before; visual clip lasts480ms. Same REACTING observations do not extend a queue. A new valid native gesture passes through DRAGGING, cancels the old visual reaction, and restarts one bounded480ms window on REACTING re-entry. Higher-priority Battle/Evolution/suppression or drag cancels REACT. IDLE resumes Breath with a fresh3–7s Blink schedule; reduced motion pins neutral frame0 under existing policy. Missing/invalid REACT uses MOA own-base and does not disable IDLE/MOVE.

**Existing native limitation:** mouse-down immediately starts Dragging and cancels MovementController. Therefore actual moving-click is MOVE→DRAGGING→REACT→IDLE. Positive-velocity REACT→MOVE passes resolver tests, but is **NOT_AVAILABLE in the existing actual mouse path**. This pilot preserves native policy instead of silently redesigning gestures. Actual MOVE→REACT→MOVE is not claimed PASS. A future behavior change requires a separately reviewed proposal.

## Actual production app

[Four short actual review clips](review/README.md) are committed, approximately130–145KB each, at1× speed. Same release binary, unchanged CSP, existing native QA/world seed20; no HTML mock, state injection or API-trigger-only acceptance. Binary/CSP hashes are in [bundle verification](bundle-verification.json). Capture was made from implementation source before its commit; the binary hash and preserved source hashes bind that run. Later documentation/tests do not alter the production bundle.

| Check | Observed result |
|---|---|
| Native trigger / Bond | PASS: RIGHT moving-click Bond+1; subsequent stationary click Bond+0 with REACT. |
| Frame order | PASS: five complete01→06 reactions across three recordings; repeated clicks intentionally interrupt earlier reactions. |
| Duration | Complete reactions478.257,489.009,475.432,480.096,490.774ms; candidate contract480ms.20ms AX sampling and delivery jitter are measurement limits. |
| IDLE→REACT→IDLE | PASS on LEFT and RIGHT. Brief own-base during native mouse-down/DRAGGING is existing suppression, not missing REACT frames. |
| MOVE→REACT→MOVE | NOT_AVAILABLE: existing native click cancels movement; actual exitIDLE. Velocity-dependent return is automated-only. |
| Repeated clicks | PASS in RIGHT recording:01→03 interrupted, next click starts01→06; no unbounded queue. |
| Drag | PASS: actual native drag has no REACT; early fast pointer-placement trials also classified as drag and are retained, not counted as successful stationary clicks. |
| Facing | LEFT/RIGHT observed and retained through each reaction; source RIGHT uses existing horizontal flip. |
| Center/bottom | Source0px; within each actual REACT visible bounds0pt and panel displacement0pt. Panel96×104pt; image82×82pt. |
| Clipping | No character silhouette touches captured panel edge in sampled REACT frames. Existing Bond toast can overlap character. |
| Facing excursion | Clean LEFT center94px and RIGHT97px on2× capture → historical1.5pt; unchanged, not fixed. Clean LEFT sequence covers01..03 of an interrupted repeat; full LEFT clip includes Bond toast, so its union center must not be used as character center. |
| World continuity | REACT interval panel coordinates stable. The whole native gesture is not asserted motion-free: existing Dragging can move the panel and always cancels walking. |
| Static metadata/network | Manifest fetch0, XHR0, CSP violations0. Observed7/8 fetch attempts are existing Tauri IPC startup and mouse actions, not HTTP manifest loads. |
| Focus / Single Instance | PASS actual TextEdit marker and140 foreground samples; three secondary launches create no extra World/panels, activation/key-window counters0. |

Full [LEFT](production-left.json), [RIGHT](production-right.json), [stationary follow-up](production-left-stationary.json) and [measurement summary](playback-summary.json) preserve unsuccessful attempts and sampling limitations. Raw PTS/PNGs, AX trace, native app logs and full recordings remain in `/Users/jinseongdae/Documents/LUMA QA/moa-react-v1`, `moa-react-v1-right`, and `moa-react-v1-left-stationary`. Native sessions used isolated saves/databases and were stopped afterward.

## Regression / remaining human review

`npm run validate:alpha:release`: initial full18-check run **AUTOMATED_READY / MANUAL_QA_REQUIRED**; [report](release-result.json) explicitly records the dirty pre-commit source. Final clean-HEAD rerun and GitHub CI links are added to the PR after committing. The gate includes frontend, animation/content,44 asset tests, validators, presentation, policies, Rust/fmt/clippy/Tao/native link and Java/PostgreSQL persistence/failure integration. Added tests cover opt-in,invalid/missing REACT,own-base isolation,nonloop frame order,480ms completion,current velocity,repeated policy,priority,Reduced Motion and Blink rescheduling. Dedicated actual GUI Battle/Evolution and OS Reduced Motion toggles are NOT_RUN; deterministic regression covers their contracts.

**MANUAL_VISUAL_REVIEW:** reaction readability,strength,480ms naturalness and click acknowledgement. No aesthetic PASS or final timing approval. Known issues retained:1.5pt facing excursion, native gesture cancellation and mouse-down base suppression. Historical IDLE/MOVE evidence is untouched. Draft PR, no merge.
