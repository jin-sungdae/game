# MIMI Alpha Production STATIC Profile

Human-approved Alpha Pilot default: MIMI IDLE is PRODUCTION, with five frames and a 2500ms cycle. MOVE and PEEK are NOT_APPLICABLE. Supplied artwork and timing are unchanged.

The reusable STATIC contract is **No World Movement + Persistent IDLE Presentation + Optional Domain-triggered Secondary Animation**. MovementController retains world coordinates and facing. The existing shared clock, static registry, lifecycle, reduced-motion policy and own-base fallback remain unchanged.

MIMI has no reliable secondary-animation domain signal. PEEK assets remain available for deterministic asset/state coverage only; no production trigger, random timer, setInterval or synthetic movement is introduced. Spawn/rarity and encounter/battle/capture/despawn take precedence over IDLE.

## Deferred visual QA

Acceptance is AUTOMATED_ACCEPTED with GUI_VISUAL_QA_DEFERRED. The observed GUI_ENVIRONMENT_BLOCKED / NO_SAFE_CANDIDATE result is neither a production defect nor a GUI PASS.

Actual MIMI, actual IDLE cycle, world/panel stability, renderer center-X/center-Y/bottom drift and clipping remain NOT_VERIFIED and deferred to Monster Visual Regression Sweep when the common native harness observes READY. Source registration measurements do not establish renderer stability. Historical evidence is preserved in [acceptance.json](evidence/mimi-static-v1/acceptance.json).
