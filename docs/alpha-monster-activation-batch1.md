# Alpha Monster Gameplay Activation — Batch 1

## Proposal before implementation

Base origin/main b81ce45. Independent feature/alpha-monster-activation-batch1 worktree. Retain the existing ContentProvider, Spawn Runtime, World, MovementController, server MonsterSelector and Battle/Capture/Inventory formulas. Add only the four approved master rows in V6; existing migrations and PIP master remain unchanged. Reuse COMMON weight100, capture base0.35, level1–3. Five equal weights imply20% each at selection boundaries.

Gate activation on the supplied assets and per-species server/Desktop World vertical slices. Preserve MELLO/BUBU BOTTOM/JUMP, MOSSY LOWER_CORNER/GROUND and CHIRP TOP/FLYING. Keep all other content disabled. Fail closed on unavailable assets, identity/content mismatch, unsupported movement and unsafe placement. Preserve native96×104 panels, visible scale, source RIGHT and bottom-center anchor. No new engine, schema column, formula or production PNG edits.

Alternatives rejected: only toggling enabled skips master/placement/movement validation; replacing MOSSY zone or grounding CHIRP changes approved content; client selection/capture calculations violate server authority. Existing runtime adapters and additive tests are sufficient. Review of gameplay activation and architecture remains HUMAN_REVIEW_REQUIRED; no auto merge.

Verification will use a new isolated loopback PostgreSQL *_test database and test-only deterministic Spring server plus compiled Desktop World, never the user's DB. Native visible NSPanel focus/input acceptance remains a separate manual boundary.
