# Alpha Monster Gameplay Activation — Batch 2 v0.1

## Proposal before implementation

Base origin/main 1822e58 includes Advanced Spawn #27 and production asset delivery #28. Existing strict-alpha validates all 15 PNGs (0 errors, 0 missing). This isolated feature/alpha-monster-activation-batch2 worktree owns V7 only, adding PEBB/PUFF/TIKKI/MIMI/WISP masters with content-matching names, profiles, levels1–3 and rarity-default weights. Previous migrations/masters and Batch3 content remain unchanged.

Reuse Monster Content, Asset Registry, Spawn runtime, MovementController and server selection/combat/inventory/collection. Extend exact approved asset loading for these five; permit UNCOMMON alongside COMMON in the existing server capture formula. COMMON0.35/UNCOMMON0.25 plus existing HP term, Charm+0.10 and clamps remain server-owned. Preserve STATIC/EDGE for MIMI, FLOATING/FREE_AREA for PUFF/WISP, GROUND for PEBB/TIKKI; do not replace profiles. Seven COMMON weight100 and three UNCOMMON weight50 total850. No desktop probability calculation.

Activation requires per-species asset/master/World/server acceptance, including same-ID restart without CREATE, movement, battle, potion/charm capture, collection and cooldown. Implement tests with production definitions and commit readiness only after isolated PostgreSQL + Spring + actual Desktop World vertical slices pass. No new engine, schema columns, production art, dependencies or native focus changes.

Alternatives rejected: flag-only activation bypasses integration evidence; replacing STATIC with GROUND changes MIMI's contract; client capture/selection violates server authority. Existing adapters and additive tests suffice. Gameplay activation acceptance and merge remain HUMAN_REVIEW_REQUIRED; no auto merge. Native visible focus/input/visual acceptance remains MANUAL_REQUIRED even after automated World/native compilation checks.
