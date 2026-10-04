# Native GUI QA Environment v1

This is QA infrastructure, not production placement or animation logic. PR #53
stays independently GUI_ENVIRONMENT_BLOCKED. No user windows are moved, resized,
closed or activated. No Mission Control automation, fake renderer, debug entity,
placement injection, threshold adjustment or production asset/timing changes.

## Environment contract

`environment_probe.m` reads primary NSScreen (the same `screens.firstObject` as
production), visible frame, display ID/scale, on-screen layer-zero window bounds,
Dock candidates and cursor. LUMA-owned windows/processes are reported separately.
Window titles, document names and other applications' AX contents are not read or
saved. Current Space ID is `UNAVAILABLE_PUBLIC_API`: a fingerprint is geometry,
not a reliable Space identity. Identical-geometry Space changes cannot be detected.

`environment.py` checks complete metadata, permission availability, native window
capacity, cold-start safe-area reservations, panel size, 100pt cursor exclusion,
obstacle and Dock overlap. Its finite candidate search is a conservative eligibility
estimate, NOT production's 16 seeded candidates. It can reject usable narrow gaps.
It never passes coordinates to production. READY does not guarantee spawn, movement
or recording; native placement remains authoritative. Production policy source
hashes are checked first; a delta blocks until the QA model is reviewed explicitly.

READY requires at least one sampled safe candidate and 3 seconds of identical
geometry fingerprints. The read-only gate samples every 250ms; it cannot prove
that nothing changed between samples. Cursor clearance is rechecked each sample.
Unknown metadata/permission, existing LUMA, insufficient space or geometry changes
produce `GUI_ENVIRONMENT_BLOCKED` (exit 2), with zero user-window changes. No retries
that manipulate the desktop are attempted. Later external geometry changes abort
capture; partial files remain evidence and are never reported as successful capture.

## Manual empty-Space procedure

1. Build the unchanged release bundle and server bootJar; set Java21 `JAVA_HOME`
   and PostgreSQL16 `PG_BIN`. Grant AX and Screen Recording manually if needed.
2. Start the command below, then manually select an empty Desktop during the 5s
   countdown. Do not return to a different application's Space until capture ends.
   Applications assigned to all Desktops can still obstruct this environment.
3. The first gate checks eligibility before any app/server launch. After isolated
   server preparation, a second 5s countdown and 3s gate run immediately before
   release launch. Geometry is checked again at launch and throughout recording.
4. If blocked, inspect `preflight.json`; prepare the environment manually and use a
   NEW output directory. The harness never changes Desktop settings for you.

```sh
python3 scripts/gui_qa/launch_environment.py \
  --bundle '/absolute/path/LUMA Spike.app' \
  --profile scripts/gui_qa/profiles/moa.json \
  --output '/absolute/path/new-qa-run' --seconds 20
```

Preflight only (no server/app started):

```sh
python3 scripts/gui_qa/environment.py \
  --profile scripts/gui_qa/profiles/moa.json --output '/absolute/path/new-preflight'
```

For a Monster profile, `--encounter-code PIP` seeds encounter weights only inside
this invocation's new local database, then calls the real server POST /encounters
before release launch. The response code must match. No DB defaults/content
activation are changed; app restart reconciliation must still perform real native
placement. A missing native panel is a capture failure, never replaced with debug.

## Recording, trace and analysis

The existing ScreenCaptureKit `record_window.swift` records only the LUMA native
window by PID/name. Actual presentation timestamps and PNG captures are preserved;
no synthetic renderer or guessed 60fps playback is generated. `frames-character`
reads the production AX image label and its panel/canvas geometry for any label.

`trace.jsonl` version 1 includes timestamp, entity ID/type, world position, vx/vy,
speed, movement state, animation state/frame, native facing, renderer flip, panel,
canvas and display ID. Unsupported native fields are null with missing-field
provenance. In particular MOA/PIP labels on current main do NOT expose native world,
velocity or facing every sample. Rounded panel movement is not relabeled native
velocity. No production instrumentation is added to fill those gaps.

The independent `common_analyzer.py` consumes profile state/frame counts, loop flags,
optional speed/excursion expectations, source bounds/canvas, source facing, pixel mask
and maximum trace/capture skew. Profile `panelSize` must describe the actual native
panel. `sourceBounds` uses exclusive right/bottom pixel bounds. Required states
must be observed before frame-order PASS. Profiles describe expectations only and
never change runtime timing. The MOA profile provides an initial smoke configuration.

```sh
python3 scripts/gui_qa/common_analyzer.py '/path/run/trace.jsonl' \
  --profile scripts/gui_qa/profiles/moa.json \
  --frames '/path/run/frames' --output '/path/run/analysis.json'
```

Pixel analysis requires Pillow in the operator's QA Python environment; no production
dependency was added. It aligns the nearest AX observation within a bounded skew,
crops to measured canvas, removes world displacement via panel-local measurements,
and groups drift by animation state/facing. It reports frame order/gaps, observed
cycle medians, center-X/Y and bottom drift, panel/canvas sizes, LEFT/RIGHT mirror
offset, facing and configured state/velocity agreement. Missing observations remain
NOT_VERIFIED. Threshold masks are not alpha-exact framebuffer geometry: edge contact
is REVIEW_REQUIRED, not proof of clipping; identity/art quality remain manual.

## Ownership and evidence

Cleanup verifies PID start-time/command identity before stopping only the created
release app/server, and stops only its own new PGDATA. Recorder/trace children are
terminated and waited. Identity uncertainty fails cleanup, never kills a replacement
process. Database/save and evidence are retained for inspection. There is no user
window restoration because the harness performs no user window mutation.

Raw environment geometry, AX trace and logs stay outside Git; share only reviewed
aggregates or intentionally selected LUMA-only recording. Synthetic READY/BLOCKED
unit tests are AUTOMATED evidence, not actual native spawn evidence. CI compiles the
native observer/recorder but does not claim a hosted interactive desktop PASS.

Alternatives considered: automatic Mission Control is unreliable on this host;
separate user/session requires provisioning; a second display does not override
production primary-screen selection; QA-owned windows cannot remove user obstacles.
Manual preparation + fail-closed observation is the smallest reusable approach.
