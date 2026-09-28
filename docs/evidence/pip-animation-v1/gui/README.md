# PR49 actual server PIP GUI QA — 2026-09-28

Production release bundle from `9267e46aaaf6a599bd5b3f9c04adc27cc9f346c6`, unchanged assets/runtime/CSP. This follow-up changes only QA tools and evidence. No debug PIP, placement bypass, threshold change, alternate renderer or flipped source artwork.

## Actual recordings (original playback speed)

- [Production PIP, 39.20 seconds](review/production-pip.mp4)
- [LEFT MOVE with adjacent IDLE, 5 seconds](review/left.mp4)
- [RIGHT MOVE with adjacent IDLE, 5 seconds](review/right.mp4)
- [IDLE, 7 seconds](review/idle.mp4)

ScreenCaptureKit captured the actual 96×104pt PIP NSPanel at 192×208 pixels; the review video is 3× nearest-neighbor display enlargement only, with original PTS timing. No source PNG was resized. Window-only recording does not show world travel against the desktop: native position trace supplies that measurement. Total videos <1MB, consistent with existing small review clips; no repository numeric video cap was found. Raw PNGs, AX events and server logs remain at `/Users/jinseongdae/Documents/LUMA QA/pip-animation-v1-gui-run2/` (not /tmp). The first arrival fade predates recorder startup; spawn success is evidenced by the server encounter and native placement log, not a claimed complete spawn-fade video.

## Observations

| Check | Result | Evidence / limit |
|---|---|---|
| Actual PIP spawn | PASS | Server encounter `8c572ca1-2ca7-41eb-b7f0-c7ba413bc952`, native placement `(316,200)`; fresh isolated QA DB only |
| IDLE actual GUI | PASS | All 01→04 frames, repeated; median1799.21ms |
| MOVE actual GUI | PASS | All 01→08 observed, complete ordered cycles during stable motion |
| RIGHT travel | PASS travel / KNOWN_ISSUE facing | Expected+1 RIGHT, actual−1 LEFT |
| LEFT travel | PASS | Expected−1 LEFT, actual−1 LEFT |
| Center / bottom drift | PASS | Both0pt in36.02s ambient interval |
| Clipping | PASS | No observed pixel touches captured panel boundary |
| Panel / canvas | PASS |96×104pt panel; rounded AX image66×66pt (nominal transformed65.6pt) |
| Ambient base fallback | PASS | None; all ambient IDLE/MOVE samples animation |
| Focus / Single Instance | PASS | Zero recorded activation/key events;3 secondary launches exit0 without extra world/panels, foreground stays outside LUMA |
| Safe placement restoration | PASS | Only ChatGPT and one Kakao window temporarily shortened; exact geometry/fullscreen restored; both processes alive |
| Mouse REACT | NOT_APPLICABLE | Real click enters ENGAGED, battle/capture UI; suppressed animation/base is expected, not failed load |

MOVE samples include approximately1067ms ShortBurst cycles and1279–1291ms low-speed cycles. Overall observed median1286.10ms;640ms remains the1× candidate, not actual low-speed timing. One2269ms frame1-to-frame1 interval crosses a rate/direction change and observation gaps. Three frame-label skips occur near the last movement transition, with AX gaps up to379ms; this is **not proof of lossless delivery of every frame**. Stable earlier cycles show the full order. Raw trace preserves these gaps instead of silently declaring every transition PASS.

## Facing root cause — existing runtime defect, unchanged

`src-tauri/src/behaviors.rs` creates server monsters with `facing:-1` and assigns ambient controller x/y at lines417–426 without deriving facing from velocity. The later boundary clamp alone flips facing; ordinary RIGHT travel does not. That file is byte-identical to main and the previous PR HEAD. `CharacterRenderer` correctly applies unchanged `directionScale(-1) = scaleX(-1)` to source-facing RIGHT art. The video visibly faces LEFT during both directions. This is not a PIP asset inversion.

Impact: server-owned monsters using this common ambient movement branch can retain stale facing, including PIP; not a newly introduced per-PIP animation defect. Debug movement's facing-driven branch and Companion movement are separate. No runtime repair or source-art flip is included.

[facing-trace.csv](facing-trace.csv) records timestamp, signed panel velocity, direction, animation state/frame, native facing, renderer flip and expected facing. Native facing is held between existing state-change log records, not newly sampled instrumentation. Renderer flip is inferred from that unchanged mapping and corroborated by pixels, not an injected DOM probe. Rounded CGWindow position differences are noisy velocity estimates, not exact physics velocity. See [native log](app.log), [raw AX samples](frame-trace.jsonl), [analysis](pip-analysis.json).

## Boundaries and restoration

Pixel drift uses nonblack RGB max>40 against ScreenCaptureKit black background at2× scale. It is a visible silhouette measure, not alpha-exact framebuffer geometry. Battle/engagement squash is outside the ambient interval; including it would mix different production effects into registration measurements.

Window snapshots: [ChatGPT](window-chatgpt.json), [Kakao](window-kakao.json), both `restoreMatchesOriginal:true`. No user app quit. Owned QA app/server/PostgreSQL stopped and listeners62350/62351 absent. Original failed safe-placement attempt and first capture script's absent `Close panel` failure remain in their local session directories; capture now closes that panel only if present.

Existing MOA assets, PIP assets, movement/interaction/evolution, Static Registry, Shared Clock and CSP are unchanged; [preservation hashes](preservation.json). Full release regressions are rerun after GUI QA on the final committed HEAD and linked in the PR. Manual typing focus scenario and a new multi-display sweep were not run in this follow-up; the actual native focus/single-instance observation above is the bounded GUI claim.

**MANUAL_VISUAL_REVIEW:** PIP idle naturalness, foot/body motion, sliding impression and REACT readability. Facing is a KNOWN_ISSUE. Draft retained; no visual production approval or merge.
