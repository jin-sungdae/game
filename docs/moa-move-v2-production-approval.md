# MOA Stage1 MOVE v2 — Alpha Pilot Production approval

The user approved the existing anatomy-guided MOVE v2 artwork and timing for Alpha Pilot Production. This approval promotes only the MOVE readiness marker from PRODUCTION_PILOT to PRODUCTION; supplied artwork and execution behavior are unchanged.

| Animation | Final status / approved timing |
|---|---|
| MOA Stage1 IDLE | PRODUCTION: Breath1800ms; Blink90ms/frame; randomized3–7s interval |
| MOA Stage1 MOVE | PRODUCTION:8frames,80ms/frame,640ms/cycle at existing1× rate |
| MOA Stage1 REACT | NOT_SUPPLIED / MOA own-base fallback |
| PIP animation | NOT_SUPPLIED / existing own-base fallback |

The existing bounded velocity-linked playback rate remains active.640ms describes the1× cycle, not a replacement for that rate contract. Source-facing RIGHT, existing horizontal flip, shared clock, static registry, CSP and MovementController ownership remain unchanged.

Historical facing reversal visible-silhouette excursion of approximately1.5pt is an accepted **Known Visual Issue**, explicitly not a blocker for this MOVE artwork. The approval is scoped to Alpha Pilot; future artwork/timing polish remains possible through review.

V1/V2 capture reports and anatomy measurements are preserved. Their candidate/visual-review labels describe their capture-time status and are superseded by this explicit user approval, not rewritten into retroactive automated visual PASS.

- [V1 evidence](evidence/moa-move-v1/README.md)
- [Anatomy evidence](evidence/moa-move-anatomy/README.md)
- [V2 evidence](evidence/moa-move-v2/README.md)
- [Four original short production clips](evidence/moa-move-v2/review/README.md)

Final clean-HEAD release gate and GitHub CI are recorded in PR #47. Ready for Review follows successful verification; approval does not authorize automatic merge.
