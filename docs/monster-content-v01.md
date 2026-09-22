# Monster Content Integration v0.1

## Architecture proposal before implementation

Base main dfe8345; isolated worktree /private/tmp/luma-monster-content-v01, branch feature/monster-content-v01.

Preserve PR #19's 30-slot MonsterDefinition and stable Dex numbers, independent of Companion. Replace the approved 15 Alpha slots with confirmed identities/tags; retain the other 15 provisional slots. Add contentReady without weakening enabled/production metadata validation. PIP stays production; 14 approved identities remain disabled and asset-unready.

Authority: server Domain rarity defaults own capture references and encounter weights. Desktop receives checked static projections, never computes rarity economics. Package the same Dex content with the server; the server joins enabled DB masters to production-ready content, failing closed for missing/unready content and inconsistent production master metadata. m_monster continues owning DB identity, level range and operator use_yn; no new master rows or invented levels are needed. Existing PIP capture formula retains its HP term and obtains the same 0.35 base from the Domain default.

No migration is necessary: content-only definitions do not need runtime DB IDs until a separately reviewed Spawn × Encounter integration and asset delivery. Alternatives of seeding 14 disabled rows or widening m_monster are deferred to avoid invented combat levels and parallel Flyway conflicts. V1–V5 remain byte-for-byte unchanged. No Inventory/Shop UI, Spawn Director implementation, native focus or Companion changes.

Approved Alpha adds FIRE/MOON/NIGHT archetypes and LOWER_CORNER metadata. Existing Spawn Director does not support LOWER_CORNER yet; it remains disabled and is not connected here. PIP's approved NEAR_DOCK tag uses its existing supported zone; the director remains disabled by default. Contract tests must reflect the new approved metadata rather than the old provisional Alpha coverage.

Unspecified balance defaults are conservative initial configuration for human review, not finalized balance: COMMON 100/0.35, UNCOMMON 50/0.25, RARE 20/0.15, EPIC 5/0.10, SPECIAL 1/0.05 (weight/base capture). PIP visualScale stays0.8; other new Alpha definitions use neutral1.0 pending assets. Metadata scales are not a renderer/panel size change.

Architecture and balance remain HUMAN_REVIEW_REQUIRED; user authorizes implementation, not automatic merge.
