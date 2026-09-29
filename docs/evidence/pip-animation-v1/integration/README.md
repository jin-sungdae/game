# PR49 final integrated production GUI QA

Latest main `c7aadd874ebcd423daa8d24dbe25539c8452d7b8` includes merged PR50. Merge commit `cf3f8c482fd94d695cf72c1486465bb3a82cd538` preserves the PIP animation pilot and uses that exact native facing runtime. One add/add conflict in the QA window helper retained main's optional window-index support and backward-compatible calls. No production conflict, workaround, force push, asset or timing change.

## Actual review clips

- [PIP IDLE —6s](review/idle.mp4)
- [PIP RIGHT MOVE —4s](review/right.mp4)
- [PIP LEFT MOVE —4s](review/left.mp4)
- [IDLE→RIGHT MOVE→IDLE→LEFT MOVE→IDLE —16s](review/transitions.mp4)

These are actual release `.app` native window captures, not HTML previews. Full50.01s recording and405 original native screenshots remain at `/Users/jinseongdae/Documents/LUMA QA/pip-facing-integration-v1/run2/`; only short clips are committed. Median observed interval128.22ms (~7.8fps);60fps MP4 encoding repeats timestamped samples, not invented intermediate frames. Display enlargement does not alter production assets or playback speed.

Real server PIP encounter and normal placement are established by [encounter](encounter.json) and [native log](app.log). The Spawning→Roaming/IDLE records precede the first recorded MOVE; a complete arrival-fade recording is not claimed. Later recorded transitions include the requested IDLE/right/idle/left/idle sequence.

## Measurements

| Check | Result |
|---|---|
| PIP IDLE4 / MOVE8 frame order | PASS, all frame indices observed, zero AX order gaps |
| RIGHT / LEFT facing | PASS,249 stable moving pixel samples, zero native/renderer/direction mismatches |
| Reversal | PASS, repeated RIGHT↔LEFT with native sign updates |
| IDLE→MOVE / MOVE→IDLE |10 transitions each |
| IDLE cycle median |1803.47ms; unchanged1800ms candidate |
| MOVE cycle median |1282.67ms; samples1072.94–1324.38ms at ambient speed |
| Same-facing center drift |0pt for IDLE/MOVE in both directions |
| Same-facing bottom drift |0pt for all four state/direction groups |
| Total center/bottom excursion |0pt /0pt in this animation capture |
| Panel / canvas |96×104pt panel; rounded AX image66×66pt (nominal65.6pt) |
| Scale / anchor |No canvas-size or panel-y changes observed |
| World continuity |No speed-bound violations; maximum rounded native step3pt, y step0pt |
| Clipping / blank / base fallback |None observed |
| Mouse REACT |NOT_APPLICABLE; production click remains ENGAGED/Battle |
| Focus / Single Instance |PASS native audit,3 secondary launches without extra world/panels or focus activation |

MOVE640ms remains the1× candidate. Existing0.5–2× velocity-linked playback explains slower ambient cycles; no speed/timing was tuned for QA. REACT6×80ms non-looping480ms remains PRODUCTION_PILOT and deterministic asset/state-level coverage; no invented production trigger.

[Integrated analysis](integration-analysis.json), [facing CSV](facing-trace.csv), [raw AX trace](pip-trace.jsonl), [capture timestamps](capture-timestamps.json). CSV includes wall timestamp, estimated native time, signed panel vx, position, native facing, pixel-observed direction/flip and actual AX animation state/frame. Native log timestamps are aligned to wall time with mean positional residual0.314pt; raw native facing is held between existing change logs. ±150ms around flips is excluded from strict paired comparisons. No runtime instrumentation or DOM transform override was added. Pixel direction was visually corroborated in both orientations.

Drift uses visible RGB>40 against the captured background at2× scale, consistent with prior evidence; it is not an alpha-exact framebuffer claim. Actual AX frame labels establish order at higher frequency than screenshots. No blank observed does not rule out unobserved sub-capture intervals.

## Safe placement and preservation

First attempt without window changes failed normal placement. An empty-Desktop inspection alternative timed out. Only the fullscreen ChatGPT window blocking the primary ground band was temporarily shortened; no other app/window was changed or quit. [Restoration](window-restoration.json) verifies exact original x/y/width/height/fullscreen with `restoreMatchesOriginal:true`. Owned QA app/server/PostgreSQL were stopped afterward. Historical earlier Excel restoration limitations remain preserved in their original evidence, not rewritten as this run's result.

[Hashes](preservation.json) verify unchanged PIP/MOA assets, pilot metadata, generated static registry, Shared Clock, Renderer and production CSP. Native behavior/movement files are byte-identical to latest main. The recorded executable was built from the merge commit; subsequent changes are QA/evidence only. Full final clean-HEAD release report and CI are posted on PR49.

## Approval boundary

**TECHNICALLY_READY_FOR_VISUAL_REVIEW:** PIP IDLE/MOVE can be considered for production promotion by a human. They remain **PRODUCTION_PILOT**, as does REACT. Breathing naturalness, walking/sliding impression, body motion and timing remain **MANUAL_VISUAL_REVIEW**. The earlier RIGHT-travel/LEFT-facing defect is resolved by merged PR50, not a remaining issue or an asset workaround. MOA's historical1.5pt reversal silhouette issue is unchanged and remains separately documented. Draft retained; no merge or automatic visual approval.
