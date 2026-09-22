# Spawn × Encounter Integration v0.1

## Proposal before implementation

Base main 6ba7593; separate worktree, branch feature/spawn-encounter-integration-v01.

Connect existing Director opportunity to the bounded backend worker, with explicit completion events. The worker retains all HTTP; AppKit/World only evaluate monotonic schedules and placement. No server selection fields are sent. Keep the current 120–300s seeded cooldown and budget1. Startup reconciliation precedes any POST; failures use5/10/30s backoff and reconcile before retrying uncertain POST.

A server-owned encounter occupies budget even without a visible entity. Content-ready metadata resolves code/profile/asset identity after server selection. Placement uses the cached DesktopSafeArea/cursor/window samples. Retry the same encounter locally with a bounded schedule; unsupported metadata/zone/condition or exhausted placement invokes the existing server Ignore resolution, reconciling before each retry. Offline resolution retains authority and retries at bounded backoff, never creates replacement encounters. Local expiry hides the visual but only authoritative terminal/empty reconciliation releases the budget.

Discovery requires successful visible placement, not a received DTO. Keep debug PIP separate from authority/discovery/scheduling; a production encounter replaces a debug visual in the existing single panel. Generalize production identity and reuse MovementController. No new native windows/architecture, polling, timer, migration, balance/formula, Inventory/Shop/Evolution/schema or PNG changes.

Alternatives rejected: local monster selection violates server authority; repeatedly POSTing after placement failure duplicates opportunities; local-only discard leaves server ACTIVE; new worker/engine duplicates existing foundations. Existing passive backend reconciliation stays on its current5s worker cycle, with explicit spawn commands carrying independent acknowledgements/backoff.

Architecture/protocol review is HUMAN_REVIEW_REQUIRED. User authorizes implementation; do not merge automatically. Live acceptance uses isolated PostgreSQL/Spring and World with fake monotonic time, never reduced production cooldown. Physical macOS mouse/focus remains a separate manual boundary.
