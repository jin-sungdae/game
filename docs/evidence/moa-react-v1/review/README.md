# Actual production renderer review

> Current status: the user has approved REACT v1 as Alpha Pilot Production, including MOVE → native walking cancel → REACT → IDLE. See [production approval](../../../moa-react-v1-production-approval.md). Candidate/Draft labels below are preserved historical capture-time status, superseded by that approval.
All clips are real ScreenCaptureKit recordings of the unchanged-CSP release `.app`. Playback is **1×**, not a mock or re-created sprite preview. Each short clip is4.5s, approximately130–145KB; original capture PTS determines the intermediate video timing. File hashes/source offsets are in [recordings.json](../recordings.json). No full90s recording is committed.

- [LEFT: IDLE → click → REACT → IDLE](idle-react-left.mp4)
- [RIGHT: actual autonomous MOVE → click → REACT → IDLE](moving-click-right.mp4)
- [RIGHT: cooldown Bond +0 with REACT acknowledgement](cooldown-react-right.mp4)
- [RIGHT: repeated click interrupts and restarts REACT](repeated-click-right.mp4)

The moving-click clip intentionally says **IDLE** on exit: existing native mouse-down begins Dragging and cancels movement. This pilot does not change native gesture policy. The positive-velocity REACT→MOVE branch is tested in the existing resolver, not falsely claimed as an actual GUI path.

The capture follows the entity window; absolute movement is measured in accompanying native panel traces. Bond toast is an existing overlay, not part of REACT artwork. Mouse-down can briefly show own-base because existing DRAGGING has higher priority than animation.

**MANUAL_VISUAL_REVIEW:** reaction readability, strength,480ms naturalness and whether the click feels acknowledged. Artwork and timing are candidates, not visual production approval.
