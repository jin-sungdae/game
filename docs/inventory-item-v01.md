# Inventory / Item / Gold Spending v0.1

## Integration design (before implementation)

Extend the existing server-authoritative JDBC economy. Add V5 tables for item master, inventory, price-snapshot purchase history and one persisted charm effect per battle. Existing migrations and combat base formula stay unchanged. Existing compact nonactivating interaction panel gains Shop/Inventory routes; no new windows or dependencies.

All mutations lock LOCAL_PLAYER first, then owned encounter/battle (when applicable), active companion (berry), item/inventory/effect rows. The player lock serializes empty-inventory insertion and existing battle/capture/reward/evolution operations. Constraints independently protect nonnegative quantities and unique identities. Transactions roll back all inventory mutations on errors. Capture reads/consumes one effect inside its existing transaction after validity/RNG checks.

Charm policy: at most one armed effect; consumed effect can be rearmed by a **new explicit use command** in an ACTIVE battle. A unique battle/effect row stores current armed/consumed state. No additive stacking. Desktop never retries mutation POST automatically. Repeated purchase/use POSTs are distinct explicit commands, not transport-idempotent requests; uncertain results require a read refresh before another command.

Alternative rejected: local HP/bond/charm changes or a local boolean could diverge on retries/restart. A new RPG window/engine is unnecessary. Domain ItemRules owns values (heal30, bond1, charm0.10), controllers accept identifiers/context only, server DTOs carry actual applied values.

## Validation

Pending implementation. Use a fresh isolated PostgreSQL, never the user's local gameplay database. Automated DTO/World/presentation tests and native compile are distinct from physical focus/visual acceptance. No inaccessible UI check is labelled PASS.
