# Monster Dex Foundation v0.1

## Architecture proposal before implementation

Base: origin/main c482fec. Isolated branch: feature/monster-dex-foundation-v01.

Add a validated Monster content registry alongside the existing Monster asset registry, independent of Companion definitions. Thirty provisional design slots describe identity, rarity, archetype, existing movement wire names, behavior, spawn metadata, capture direction and asset identity. Only PIP remains enabled. No runtime selector or formula changes.

Reason: the current one-entry asset map cannot describe future content or undiscovered Dex presentation. Keep server-owned gameplay values authoritative; client content is a design/presentation contract, never a source of encounter or capture decisions.

Alternatives: database columns/seeds are deferred to avoid parallel Flyway conflicts; merging Monster and Companion registries is rejected because the domains have different lifecycles; a new movement/AI engine is outside scope. Reuse existing MovementProfile values without routing content into movement execution.

Human review is required for this architecture proposal and eventual merge. Implementation is explicitly requested by the user; no automatic architecture approval or merge is performed.
