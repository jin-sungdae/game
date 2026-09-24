# macOS Native GUI QA Automation v1

This is real GUI evidence, not a conversion of unit-test results into GUI passes. Baseline: main `60d72fcc00d84a487a2253a74d40fd76be2d04ed` (release hardening #43). No production source, focus/window behavior, gameplay, balance, asset or dependency changes.

## Environment and actual app

macOS26.5 (25F71), active console/WindowServer. Native probe reports AX trust, CGEvent post permission and Screen Recording available; Apple Events to TextEdit/System Events succeeded. `osascript`, `screencapture`, `open`, `pgrep`, `ps`, `launchctl`, clang/AppKit/ApplicationServices were available. No packages installed.

One actual display:2056×1329pt, scale2, origin0,0; initial visibleFrame `{{0,70},{2056,1220}}`. Multi-monitor/negative-origin hardware was absent: ENVIRONMENT_UNAVAILABLE, not a simulated PASS.

A release-mode `.app` was built with the normal production entrypoint using `npm run tauri -- build --bundles app --config '{"bundle":{"active":true}}'` and copied to `/tmp/luma-gui-qa-20260924/LUMA Spike.app`. Identifier `dev.luma.spike`; executable `Contents/MacOS/luma-spike`; original actual PID **71218**. Ad-hoc signing, not notarized/distribution-certified. The existing read-only `LUMA_FOCUS_AUDIT=1` observer recorded activation/key-window notifications. `LUMA_VISUAL_AUDIT=1` recorded presentation diagnostics; no smoke driver or modified production behavior was used for the release process.

The existing test-only `LiveValidationServer` (BATCH1 deterministic RNG) ran against a new PostgreSQL16 `luma_gui_qa_test` on55494, server18144. It is absent from production bootJar. MOA/Stage1/Lv1/EXP0/Bond0/Gold0 was confirmed before real mouse tests. For evolution-only GUI acceptance, this disposable save was explicitly advanced to Lv3/EXP300/Bond5 and then Lv6/EXP1500/Bond12. No production DB or rule was changed; these are **isolated eligibility fixtures**, not organic progression evidence.

## Automation methods and evidence

`scripts/gui_qa/native.m`: AXUIElement tree/press, CGWindow owner/position/size/layer, NSWorkspace frontmost/focused AX element, CGEvent Unicode character typing with physical Return, real mouseDown/dragged/mouseUp. `session.py`: per-window PNGs with PID/window ID/timestamp, TextEdit markers and focus traces. `soak.py`: actual elapsed time with15-second samples (thus includes0/5/10/15/20/25/30-minute neighborhoods). `lifecycle.py`: bounded repetition of the existing Debug Spawn/Despawn PIP menu. `report.py`: explicit classifications and counts; tests prove absent GUI events and missing/lost input cannot become GUI_AUTO_PASS.

Evidence directory: **`/tmp/luma-gui-qa-20260924/`**. Large PNGs, full AX/text/process logs and database files are not committed. `gui-qa-result.json` includes headSha, compiledAppHeadSha, OS, bundle ID/path, permissions, per-test evidence/notes and separate counts. A harness commit can differ from compiledAppHeadSha because no production files changed; the report retains both rather than misattributing the build.

## Observed GUI results and boundaries

| Test | Classification | Actual evidence |
|---|---|---|
| App launch / native panels | GUI_AUTO_PASS | PID71218, real release World initialized;3 panels created, visible count varies1–3; layer3, AXSystemDialog, canBecomeKey/Main=false. Window PNG captured. |
| Single instance | GUI_AUTO_PASS | Secondary PID71512 exited0; no panel/World log; original PID/window ownership remained. No separate backend initialization. |
| TextEdit typing / Companion | GUI_AUTO_PASS | Real CGEvent markers, exact document comparison, AXTextArea and frontmost trace; no LUMA activation/key-window events. |
| PIP spawn focus | GUI_AUTO_PASS, debug scope | Existing native Debug Spawn PIP menu, actual production renderer/window and moving PIP; physical Return retest exact and focus stable. Not a server-authoritative placement PASS. |
| Evolution focus | GUI_AUTO_PASS | Actual GUI EVOLVE clicks during typing for both transitions; exact marker contents, frontmost TextEdit, focused text area and no LUMA key-window event. |
| Real click | GUI_AUTO_PASS | Real stationary click→native classifier→worker→server; Bond0→1. API was observed, not used to trigger the interaction. |
| Real drag / classifier | GUI_AUTO_PASS | Real down/30 drag steps/up; horizontal position changed180pt; Bond stayed1; Idle/Looking/Walking resumed. |
| MOA / MOKORI / NEBLA | GUI_AUTO_PASS | Named AXImage and actual window PNGs. NEBLA production image visibly present, no diagnostic placeholder. |
| Evolution visuals | GUI_AUTO_PASS for identity/asset transition | Captures around .10/.45/.85/1.25/1.8/2.3s after actual EVOLVE click; old/final asset timeline visible. Aesthetic quality not auto-certified. |
| All15 Monster sweep | ENVIRONMENT_UNAVAILABLE | PIP debug image observed; other14 not displayed. Ordinary normal windows cover the safe placement region; production fail-closed retained. No unit/simulation substitute. |
| Movement profiles | MANUAL_VISUAL_REVIEW | Actual PIP GROUND trace and Companion motion collected. Other6 Monster profiles unobserved. |
| RARE/SPECIAL arrival / duration | ENVIRONMENT_UNAVAILABLE | No actual rarity arrival;400/750/1000ms duration not claimed measured. |
| Battle GUI | ENVIRONMENT_UNAVAILABLE | Authoritative Monster placement did not succeed; no fabricated battle screenshot/PASS. |
| Reduced Motion | MANUAL_VISUAL_REVIEW | Native settings UI OFF→ON→original OFF, probe confirmed; actual Companion reaction captured. Rarity animation comparison unavailable. |
| Dock/Menu Bar | MANUAL_VISUAL_REVIEW | Settings UI bottom→left→right→bottom; preference restored. Actual coordinates/screenshots collected. visibleFrame retained left inset during later observations, so complete dynamic geometry acceptance is not claimed. |
| Multi/negative monitors | ENVIRONMENT_UNAVAILABLE | No such actual monitor topology. |

### Input mismatch retained

The first Debug PIP typing trial retained TextEdit focus but exact text comparison failed: one Unicode-posted newline was displaced. Evidence remains in `existing-debug-pip-typing.json`, its focus trace and `debug-pip-actual-marker.txt`. No LUMA activation/key-window event occurred. QA helper now sends a real Return keycode36 and waits250ms for the last posted event before reading. The repeated actual PIP spawn trial (`physical_return_pip-*`) passed exactly. This is a QA-input protocol correction, not a proven production focus defect; the original mismatch was not erased. Native helper compile syntax was also corrected once. Automatic repair budget used:2 of3; no production defect repair.

### Environment/approval constraints

Real CGWindow geometry showed a full-screen normal window covering the placement area. An attempted broad temporary hide was rejected by automatic approval review because it would disrupt unrelated work apps; partial earlier changes were rolled back to the recorded originally-visible list. Further broad hiding was not performed without approval. A full-desktop screenshot was separately rejected because it could include unrelated private content. The narrower alternative—LUMA-owned window captures and the existing Debug PIP menu—was used. These are automation-scope approvals, **not missing AX/Screen Recording permissions**. Approval to clear the actual QA desktop is still needed for the remaining authoritative15-species sweep.

## Permissions and reproduction

Run the probe from the same host that will automate GUI:

```sh
clang -fobjc-arc -framework AppKit -framework ApplicationServices scripts/gui_qa/native.m -o /tmp/luma-native-gui-qa
/tmp/luma-native-gui-qa probe
```

If any permission is false, authorize the **launching application** (Codex `com.openai.codex`, or Terminal when run there) under System Settings→Privacy & Security→Accessibility and Screen & System Audio Recording, and approve its Apple Events access to TextEdit/System Events when macOS requests it. The helper executable is `/tmp/luma-native-gui-qa` (or the output directory's `native-qa`); identify the actual requesting host in the OS prompt. Do not grant arbitrary binaries or silently change TCC. Current run required no new permission grant.

A repeatable basic real GUI smoke owns a new DB/server and records actual app evidence:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home \
PG_BIN=/opt/homebrew/opt/postgresql@16/bin \
python3 scripts/gui_qa/run.py --bundle '/absolute/path/LUMA Spike.app' --output /tmp/luma-gui-new --keep-running
python3 scripts/gui_qa/soak.py /tmp/luma-gui-new --seconds 1800
python3 scripts/gui_qa/lifecycle.py /tmp/luma-gui-new --cycles 10
python3 scripts/gui_qa/stop.py /tmp/luma-gui-new
```

Quit any other LUMA primary first. The smoke does not hide user apps, alter display settings or change progression. It leaves a new scratch TextEdit document; close only that document after preserving its marker evidence. Run lifecycle concurrently with soak if desired, preserving the same app PID. The full certification report additionally requires the named evolution/restart artifacts; running the smoke alone is not full certification. `python3 scripts/gui_qa/report.py /tmp/luma-gui-qa-20260924` regenerates this run's report. GUI typing can affect the focused application: run deliberately on an idle desktop with the dedicated TextEdit document. Never run input unattended against an unknown foreground application.

## Regression and release disposition

`npm run validate:alpha:release` passed both before GUI work (`/tmp/luma-gui-pre-gate`) and after the GUI helper/input changes (`/tmp/luma-gui-post-gate`). Existing frontend/server/Rust/assets/Tao checks remain unchanged. Added report-classification unit tests verify report policy only; they do not certify GUI behavior. Hosted CI remains regression evidence, never desktop acceptance.

No confirmed production defect was fixed. No false all15/rarity/Battle/monitor PASS is claimed. Remaining review: input protocol first-trial mismatch, detailed clipping/facing and visual comfort, dynamic Dock visibleFrame behavior, authoritative Monster sweep and arrival timings. Full native release acceptance is incomplete even when automated regression passes. No automatic merge.

## Completed restart, soak and harness replay

Actual same-PID observation completed **1800.004 seconds**,120 samples. PID71218 remained alive; RSS106752→95520KB (peak106752KB), threads31→23, maximum observed owned windows2. Ten existing Debug PIP spawn/despawn cycles ran during the observation. This supports this bounded workload only, not all15 authoritative lifecycle coverage or a universal leak guarantee.

Actual app Quit and old-PID absence were verified, then Spring71175→74520 and app71218→74529 were restarted against the same isolated PostgreSQL save. All observed bootstrap, inventory, collection, dex and evolution responses matched exactly. NEBLA AXImage and new window screenshot were recorded. Gold/inventory/collection remained the fixture's zero/empty values; nonzero inventory restoration is not claimed.

A second fresh isolated run using the committed `run.py` completed real release app launch,97 TextEdit focus samples with exact marker retention, and the real click path. Its artifacts are `/tmp/luma-gui-qa-replay-smoke`. Both QA app/server/database runs were shut down; owned process/listener absence was verified. Dock preference is restored to bottom and Reduce Motion to OFF. Scratch TextEdit documents remain for inspection.

Final recorded GUI summary: **14 GUI_AUTO_PASS,0 unresolved FAIL,0 PERMISSION_REQUIRED,4 ENVIRONMENT_UNAVAILABLE,4 MANUAL_VISUAL_REVIEW**,46 original-session window screenshots (plus the separate replay). Original failed typing trial remains documented above; counts use its explicit successful retest. Focus traces are `*-focus.jsonl`; resource trace is `resource-trace.jsonl`; machine report is `gui-qa-result.json`. CPU settled from27.3% at initial startup to0.6% at the final sample; open files62→65 (range61–65); recorded requests0→673. No runaway trend or crash was observed in this workload.
