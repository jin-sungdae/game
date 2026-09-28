# MOA Stage1 REACT v1 — Alpha Pilot Production approval

The user approved the registered REACT v1 artwork and6-frame,80ms/frame,480ms,non-looping playback as the Alpha Pilot Production default. This finalization changes only REACT readiness from PRODUCTION_PILOT to PRODUCTION and its corresponding assertions. No asset bytes, timing, renderer, native gesture/movement architecture, CSP, static metadata or shared clock are changed.

| Animation | Final status / approved default |
|---|---|
| MOA Stage1 IDLE | PRODUCTION: Breath1800ms; Blink90ms/frame; randomized3–7s interval |
| MOA Stage1 MOVE | PRODUCTION:8frames,80ms/frame,640ms/cycle at1× |
| MOA Stage1 REACT | PRODUCTION:6frames,80ms/frame,480ms,non-looping |
| PIP animation | NOT_SUPPLIED; existing own-base fallback |

## Known Interaction Behavior — accepted, not a blocker

Clicking a moving Companion transfers control to the existing native mouse-down/drag owner and cancels walking. The actual path is **MOVE → mouse interaction → walking cancel → REACT → IDLE**. This is explicitly accepted for the current Alpha Desktop Companion interaction contract. It may be reconsidered during future interaction polish; this PR does not redesign native Drag/Click or preserve movement through clicks.

A repeated valid click restarts REACT through the existing native state transition; no unbounded queue is created. A click during Bond cooldown still gives visual REACT while the server grants Bond+0. The server remains reward-authoritative. Real drag is excluded from click REACT. Mouse-down DRAGGING suppression can briefly use MOA own-base, as recorded in the existing evidence.

Existing priority, velocity-dependent resolver completion, Reduced Motion, own-base fallback, IDLE Breath/Blink rescheduling and MOVE behavior remain unchanged. Historical approximately1.5pt facing reversal excursion remains a Known Visual Issue.

## Evidence and verification

- [Actual native mouse / release-app recordings and measurements](evidence/moa-react-v1/README.md)
- [Four short production renderer clips](evidence/moa-react-v1/review/README.md)
- [Source byte hashes and registration](evidence/moa-react-v1/asset-validation.json)

Historical candidate, missing-MOVE-return and manual visual-review labels describe what was known at capture time. They are retained rather than rewritten into retroactive automated visual approval. The user now approves the artwork/timing and accepts the native interaction behavior. Future visual polish remains possible.

Final clean-HEAD `npm run validate:alpha:release` and GitHub CI are recorded in PR #48 after this commit. Real click, drag exclusion, Bond and IDLE/MOVE recordings from the pilot remain evidence for unchanged execution behavior; finalization does not claim a new GUI recording. Ready for Review follows passing verification. Automatic merge is not authorized.
