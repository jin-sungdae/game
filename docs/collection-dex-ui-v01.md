# Collection Dex UI v0.1

## Architecture decision before implementation

Base: latest origin/main dfe8345. Reuse the existing nonactivating interaction NSPanel and its compact fixed bounds for a scrollable 30-slot Dex. Add DEX entries in the Companion and Encounter surfaces; do not create another native window. Generic Monster Content and Spawn Director files remain untouched.

Use the existing Collection GET and Monster Dex registry plus its dexEntry projection. A dedicated presentation snapshot distinguishes unloaded, loading, empty success and failed refresh; server Collection records alone authorize capture/count/timestamp. Existing server Encounter responses provide session-only discovery evidence; no persistent discovery API exists. Captured always implies discovered. No speculative desktop capture decisions, DB migration or registry enablement.

Alternative: a new Dex NSPanel would add native lifecycle/focus risk without improving this small scope. Persistent discovery needs a future server contract and is deferred. Architecture and actual desktop focus/visual acceptance require human review; no automatic merge.
