# PR #5 correction: DesktopSafeArea

**Status: MANUAL_REQUIRED / NOT MERGE READY.** The user reproduced MOA hidden behind the visible Dock on the original PR #5 build. The previous `visibleFrame` geometry PASS did **not** establish safe desktop UX. The historical logs are retained, not promoted to a visual PASS.

## Public API investigation

AppKit `NSScreen.visibleFrame` excludes OS-reported reserved space, but on this Mac the primary screen returns `(0,0,2056,1290)` while an actual Dock overlay can appear at the bottom. AppKit offers no documented occupied-Dock-body rectangle API found in this investigation.

Public `CGWindowListCopyWindowInfo` can expose bounds/PID/layer metadata without asking for Accessibility or screen recording permission. We identify the Dock PID using `NSRunningApplication` and bundle ID `com.apple.dock`, then select `CGWindowLevelForKey(kCGDockWindowLevelKey)`. We do not read window titles, capture images, request permissions, use private APIs or read/write undocumented Dock settings.

On this Mac the Dock-level candidate is **the full primary screen**, `(0,0,2056,1329)`, rather than the Dock body. Dock also owns desktop/background windows, which are filtered by window level. A full-screen proxy is ambiguous and is rejected. Merely observing that rectangle must not produce a claim that we measured the actual Dock height.

Sources: [Apple CGWindowListCopyWindowInfo](https://developer.apple.com/documentation/coregraphics/cgwindowlistcopywindowinfo(_:_:)), [Apple window metadata permission explanation](https://developer.apple.com/videos/play/wwdc2019/701/), [NSScreen.visibleFrame](https://developer.apple.com/documentation/appkit/nsscreen/visibleframe).

## Pipeline and configuration

`ScreenFrame → OSVisibleFrame + Dock candidates → DesktopSafeArea → existing bottom-center/full-bounds clamp → NSPanel`.

`src-tauri/src/desktop.rs` is the single configuration source (`DesktopSafeAreaConfig`, `CONFIG`):

| Setting | Initial value (logical points unless noted) |
|---|---:|
| ground_margin | 8 |
| side_margin | 8 |
| top_margin | 8 |
| fallback_bottom_inset | 192 |
| fallback_side_inset | 192 |
| menu_gap | 6 (unchanged) |
| dock_poll_seconds | 1 second |
| edge_tolerance | 24 |
| max_edge_fraction | 0.35 |
| minimum_aspect | 2 |

The 192pt fallback deliberately reserves substantially more than the former cosmetic 8pt gap: room for a normal single-row Dock plus visual/magnification allowance. It is an initial conservative placement budget, **not** a measured Dock height or a universal maximum. If the user's Dock is taller/wider, central configuration must be increased. The geometry report alone cannot certify that unknown Dock content fits this budget.

A missing/hidden/full-screen Dock candidate cannot safely reveal orientation. We conservatively reserve **all three possible edges**, even when one edge is currently detected, to protect against auto-hide and changes of occupied edge. This sacrifices horizontal/vertical working space rather than guessing bottom orientation. For a usable edge-shaped candidate, the reservation on that specific bottom/left/right edge is increased to include its full depth. OS visible-frame reservations are merged with maximums, not added twice.

`SafeAreaTracker` retains per-display-ID high-water insets for the lifetime of the process. Dock hiding, metadata loss, smaller bounds and moving to another edge never reduce them. Moving a display to negative coordinates translates its safe area while preserving its reservation; a different display ID has separate history. Growing a Dock beyond the retained reserve can move ground upward once when observed, but hiding it never moves ground back downward. Restart clears this history to configured fallback/current observations. A monitor too small for safe bounds and entity is handled by the existing hide-instead-of-overflow rule.

## Candidate handling and coordinates

Quartz global window bounds use top-left/downward coordinates. Convert to AppKit points via `appKitY = primary.frame.maxY - quartzY - height`, without Retina multiplication. Only intersections with the current primary screen matter. Bounds must have positive finite size, be edge-shaped (aspect ≥2, depth ≤35% of the corresponding screen dimension), and meet one of bottom/left/right within 24pt. These tunable shape thresholds reject full-screen proxy/background windows; they are heuristics, not Apple guarantees. Ambiguous candidates fall back to the configured reserve.

The existing primary screen policy remains. Metadata is queried at most once per second, not on every 33ms behavior tick. The existing main-thread tick consumes cached safe bounds. No new timer/thread/hook was added. OS display or Dock geometry changes may take up to one polling interval to be reflected; the pre-reserved fallback and retained insets protect normal auto-hide reveals during that interval. Abrupt oversized/unreported Dock changes remain a manual validation risk.

## Preserved behavior and scope

Bottom-center anchor, full bounds clamp, native frame integer projection and MOA/PIP common ground remain. Drag uses the final safe area and release returns to its ground. State transitions, personality, weights, animation, assets, PIP lifecycle, World movement behavior, Tao patch, Tauri version and native NSPanel architecture are not changed. This correction only changes the area supplied to existing placement logic and the diagnostic distinction between OS bounds and LUMA safety policy. No Single Instance feature is added.

## Tests and validation

All previous 23 tests remain. Seven additional tests cover:

- full-screen visibleFrame with a detected bottom Dock overlay;
- actual bottom/left/right occupied-edge reservations;
- no Dock metadata/full-screen proxy fallback;
- hide, smaller Dock and metadata loss without dropping ground;
- per-monitor history, negative origin and monitor change;
- different entity heights/common ground/drag-down bounds;
- actual World/controller drag-down → release IDLE/common ground.

Native logs now include `screenFrame`, `visibleFrame`, `dockWindowCandidates`, `detectedDockBounds`, `fallbackSafeInsets`, `retainedSafeInsets`, `finalLumaSafeArea`, `computedGroundLine`, entity world position and actual panel frame. When detection is unavailable, `detectedDockIntersectionArea=null` and `dockBoundsStatus=FALLBACK_UNVERIFIED`; an empty detected list is **not** treated as zero physical overlap. `visualVerification=MANUAL_REQUIRED` remains explicit.

The earlier `reservedIntersectionArea` field now describes exclusion from **LUMA safe area**, not proof of no physical Dock overlap. Real final evidence and artifact hash are recorded under `docs/evidence/desktop-safe-area/`. No screenshot obtained through unsupported capture APIs is used to pretend visual certification.

## User recheck (required before merge)

1. Run the updated debug bundle with the Dock visibly shown. Confirm the displayed entities belong to this build (old instances were stopped only for testing).
2. Spawn PIP using MOA right-click. Both whole bodies and their labels must sit above the Dock, on the same line.
3. Drag MOA down toward Dock and release; it must remain above Dock and return to the common ground.
4. Show/hide Dock repeatedly: ground must not follow it downward/upward repeatedly.
5. Immediately type in the previously active editor after each mouse action. Focus must remain there.
6. If convenient, repeat with Dock left/right and screen arrangement changes. This agent did not alter Dock settings.

Record PASS/FAIL from the actual screen. Automated safe-rectangle tests, fallback coordinates or CI green alone do not complete these acceptance criteria. **Keep PR #5 unmerged until the user decides.**

## Latest automated result (2026-09-17)

- Existing 23 + new 7 Rust tests = **30/30 PASS**; app fmt/clippy, npm build/debug bundle, Tao integrity and foundation tests PASS.
- Final debug smoke PID 2288: 17 samples inside **LUMA safe bounds**, projected/actual frames equal, all ground Y=200. Activation/key window 0, normal exit. Before/exit foreground Codex; no continuous external foreground observer.
- screen=(0,0,2056,1329), visible=(0,0,2056,1290), Dock candidate=(0,0,2056,1329) rejected as proxy, detected bounds=[], physical overlap **NOT_VERIFIED**.
- Fallback bottom/left/right=192; retained top=39 from OS. Final LUMA safe area=(192,192,1672,1098).
- Representative MOA panel=(1584,200,96,104), PIP panel=(1758,200,96,104).
- A separate final bundle was left running for user Dock-visible, mouse/drag/typing recheck. Dock CUA inspection timed out; no screenshot-based PASS is claimed.
- [Raw runtime log](evidence/desktop-safe-area/runtime.log) and [artifact/validation summary](evidence/desktop-safe-area/summary.json).
