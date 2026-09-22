# Advanced Monster Spawn Conditions v0.1

## Design before implementation

Extend the existing Rust Spawn Director/runtime, content adapter and MovementController without replacing them. Add one injectable desktop calendar-clock boundary: NIGHT is local time >=22:00 or <06:00, independent of server UTC encounter leases and monotonic scheduling. Evaluate conditions only when attempting placement. An already visible encounter keeps its authoritative lease through dawn; a restart/new placement outside NIGHT uses existing Resolve and bounded backoff, never a replacement POST while authority is held.

Map EDGE content to safe left/right placement; reuse the existing controller for vertical edge motion and FREE_2D/FLOATING. Keep rarity as validated server/content metadata, never a desktop probability or placement rule. SPECIAL rarity never implies SPECIAL_EVENT. Use a test-only provider/asset fixture through the same World path while all production Batch3 flags and PNGs remain unchanged.

Alternatives rejected: server time for desktop-local conditions, enabling Batch3 to test, new movement engine, and changing combat/capture probabilities. Human review required before merge.
