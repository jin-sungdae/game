# MOA MOVE v1 evidence

## Delivery and production boundary

The supplied eight PNGs are byte-identical to the ZIP (`asset-validation.json`, `source-manifest.json`). Recomputed center-X and bottom drift are 0px. `unchanged-contracts.json` is verified again by `verification.json`: base/Breath/Blink, canonical/generated registry, shared clock, renderer, MovementController, behavior module, CSP and runtime inventory are unchanged from main 74a886d. MOA MOVE alone opts into PRODUCTION_PILOT; approved IDLE stays production, REACT/PIP remain unsupplied.

The normal production app was built with the existing CSP, without a timing override or alternate renderer. `LUMA_QA_WORLD_SEED=165945` uses the existing World constructor RNG to make autonomous choices reproducible; default launches still use the time seed. No state/position injection, behavior-weight change, shortened waits or movement-speed change. The seed parser is unit-tested. The build preceded relocation of the compile-time-only Rust test module to the file end; runtime code/assets match cdfaee7. This conventional placement restores full production-source scanning; no policy/baseline change was made.

## Actual GUI measurements

ScreenCaptureKit recorded 315.00 seconds and 1,099 complete window buffers. AX/native panel trace measured **22.356 seconds of actual MOVE**, in seven walks, with LEFT and RIGHT observed. See `production-analysis.json` for every segment, frame observation, cycle and raw exception. Six direct IDLE→MOVE transitions, seven MOVE→IDLE transitions and resumed Blink were observed; the other entry interrupts Blink as intended.

| Check | Evidence/result |
|---|---|
| Ordered playback | PASS: complete 01→08→01 loops in actual renderer; five of seven walk traces contain no skipped AX frame observations. Three gaps are preserved, not silently filled. |
| Timing | Candidate 80ms/frame, 640ms at 1× unchanged. Observed cycle median **640.929ms**. Single-cycle observations 606.776–707.034ms; one 1273.611ms frame-1 interval spans a missing AX observation. |
| Same-facing center drift | PASS: **0pt LEFT**, **0pt RIGHT** in stable MOVE capture pixels. |
| Bottom drift | PASS: **0pt** both directions and across captured states. |
| Facing reversal | Both directions PASS; visible silhouette centers 94px LEFT / 97px RIGHT on 2× capture → **1.5pt excursion**, unchanged historical limitation. Zero-excursion acceptance is **FAIL**, not waived. |
| Panel / image canvas | 96×104pt / 82×82pt, constant. No scale jump. |
| Clipping / blank | PASS in captured renderer buffers; no base fallback samples during IDLE/BLINK/MOVE. |
| World ownership | PASS code/tests: native MovementController alone moves the panel; unchanged renderer/animator never assigns position. Native trace limitations below prevent claiming perfect per-tick continuity from these samples. |
| Focus | PASS native audit and bounded real TextEdit marker delivery. `focus-input.json`: 210 observations, TextEdit retained foreground, 175pt native travel. |
| Single Instance | PASS three real secondary launches; no second World/panels, no LUMA foreground activation. |
| Network / CSP | PASS zero manifest fetch, XHR and CSP violations. The two startup fetch attempts are existing Tauri IPC listen/snapshot calls. |
| Fallback / Reduced Motion / priority | PASS automated tests; missing MOVE clip uses own base; IDLE/Blink retained; existing frame-0 reduced-motion rule and Battle/Interaction/Evolution priority unchanged. |

### Observation limits, retained without threshold changes

AX polling and ScreenCaptureKit are independently scheduled. AX gaps were 7→1, 8→2 and 4→6; captured pixels confirm an intermediate base-shaped frame in the second gap, while the other gaps do not establish that every frame was presented. Ordered cycles are proven; **zero dropped display frames throughout the recording is NOT_VERIFIED**. Gait smoothness must be reviewed in the actual recording, not inferred from unit tests.

Raw CGWindow positions include a 2110pt transient during TextEdit activation while IDLE; AX-local Y and image size remain fixed. Association with macOS window/Space transition is an inference from timing, not a new artwork displacement. During MOVE, sampled CGWindow steps reach 7pt, since delivery/AX sampling can coalesce native ticks. `stepsExceedingNativeDtCap` is a diagnostic list, not proof that one native tick exceeded its limit. These raw values and the 1.5pt facing excursion are retained. **Strict all-sample world-position continuity is NOT_VERIFIED**; no threshold was relaxed or movement logic changed to hide it.

Two high-rate typing attempts stopped at the existing foreground guard (exit4), so those attempts are not PASS. The later bounded marker-delivery check and native single-instance/focus audit passed. Actual Battle/Evolution UI scenarios were not replayed in this recording; their automated regression and suppression tests passed.

## Human-accessible recordings

All media and raw traces are durable local files, not `/tmp`:

`/Users/jinseongdae/Documents/LUMA QA/moa-move-v1-seeded/`

- `production-move.mp4`: full 315-second production recording.
- `move-01-left.mp4` … `move-07-left.mp4`: each actual walk with available surrounding IDLE; `move-03-right.mp4` is RIGHT.
- `review-clips.json`: exact full-recording offsets and durations.
- `playback-frames/frames.json`, PNG buffers, `frame-trace.jsonl`, `runtime-trace.jsonl`, `session/app.log`: raw timestamps, panel geometry and state/network evidence.
- `verification.json` in this PR contains every MP4 SHA256 and byte size.

The first uncontrolled autonomous attempt (only 2.303 seconds MOVE in about 930 seconds) remains at `/Users/jinseongdae/Documents/LUMA QA/moa-move-v1/`; it is not used to claim the 20-second acceptance.

Preview images below are copied actual production captures, not mock/source previews:

![Actual LEFT MOVE](actual-move-left.png)
![Actual RIGHT MOVE](actual-move-right.png)

## Regression and visual gate

Full `npm run validate:alpha:release` passed **AUTOMATED_READY / MANUAL_QA_REQUIRED**: frontend, animation/content, presentation, 42 asset tests, validators/strict Alpha, policies, Tao, Rust tests/fmt/clippy, native harnesses, Java/PostgreSQL fresh/persistence/failure regression. `release-result.json` records the exact run binding and dirty-tree flag. First pending-clip-count failure (25→24) and test-placement scanner failure are retained in local logs; neither baseline nor policies were loosened.

**MANUAL_VISUAL_REVIEW**: walking impression, foot motion, sticker sliding, body bob strength and 640ms naturalness. Assets and timing remain pilot candidates, not visually approved defaults. PR remains Draft; no merge.
