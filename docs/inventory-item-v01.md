# Inventory / Item / Gold Spending v0.1

## Economy loop and integration decision

Battle rewards provide Gold → Shop purchases inventory → Potion restores active battle HP / Charm improves the next capture / Berry increases companion Bond → server evolution eligibility refreshes. All effects and money come from PostgreSQL-backed server commands, never desktop calculations.

The design was recorded in the draft PR before implementation. Extend existing Spring JDBC services and the bounded Rust worker; reuse the existing compact nonactivating interaction panel. Rejected alternatives: client-only HP/bond/charm state, optimistic Gold deduction, a separate RPG window, a new engine/dependency. Existing combat base formula, CompanionState, movement, art, animation timing, safe area, single instance, NSPanel/Tao/focus remain unchanged.

## Additive V5 schema

`V5__inventory_items.sql` adds:

- `game.m_item`: identity PK, unique item_code, name/type, positive price/max_stack, use_yn, timestamps.
- `game.t_inventory`: identity PK, player/item FKs, unique(player,item), quantity≥0 and timestamps. Domain enforces current master max_stack.
- `game.t_item_purchase`: UUID PK, player/item FKs, quantity, unit_price and total_price snapshots, creation time; numeric CHECK verifies multiplication without bigint overflow.
- `game.t_battle_item_effect`: battle FK, effect_type/value, consumed_at/created_at; primary key(battle,effect_type), value and time checks. Reference lookup indexes cover history/inventory.

V1–V4 are unchanged. No Collection/evolution data is repurposed.

| Code | Name / type | Price | Max stack | Effect |
|---|---|---:|---:|---|
| SMALL_POTION | Small Potion / BATTLE_CONSUMABLE |20|99|ACTIVE battle: heal min(30, missingHP), fullHP rejects |
| BOND_BERRY | Bond Berry / COMPANION_CONSUMABLE |30|99|Outside ACTIVE battle: active companion Bond+1 |
| CAPTURE_CHARM | Capture Charm / BATTLE_CONSUMABLE |40|99|ACTIVE battle: arm +0.10 absolute probability for next Capture |

`ItemRules` owns effect magnitudes and checked price multiplication. Potion is not an attack/turn and adds no counterattack. Berry does not auto-evolve. Inventory consumption and effects share one transaction.

## Transactions / locking / retry

All game mutations lock LOCAL_PLAYER first, sharing the existing battle/reward/evolution lock. Purchase then reads item `FOR SHARE`, inventory `FOR UPDATE`, checks quantity/overflow/Gold/stack, updates Gold and inventory, inserts price-snapshot history and commits. Player locking serializes the absent inventory-row case before UPSERT. All ItemService exceptions roll back the transaction.

Battle item use: player → owned encounter → battle → item → inventory → effect. Berry: player → active companion FOR UPDATE → item → inventory. All validations precede writes; constraint failure after HP/Gold changes rolls the entire transaction back. No JVM mutex is used.

Capture retains its player → encounter → battle order, then locks the unconsumed effect. It computes `baseChance` with the unchanged CombatRules formula, adds persisted bonus, clamps to [0.05,0.95], validates RNG, marks the effect consumed and resolves capture in the same transaction. Failure consumes the bonus too; the next valid capture has zero bonus unless a **new explicit** Charm use rearms it. A second use while armed returns EFFECT_ALREADY_ACTIVE without consuming inventory. One row per battle/type prevents stacking. A terminal battle cannot use another item; an unused terminal-battle charm is not refunded and cannot affect another battle.

Desktop never automatically retries mutation POST. Purchase/use requests intentionally represent distinct commands, not an idempotency-key protocol. Two affordable purchase commands may both succeed. If a response is lost, use GET/Refresh to reconcile before another explicit command. Charm arm/consume state and terminal battle state are queryable. Enabling automatic retries later requires request IDs/receipts first.

## APIs

| Method | Path | Contract |
|---|---|---|
|GET|`/api/v1/shop/items`|enabled items, itemCode/name/type, price, ownedQuantity, maxStack; itemCode order |
|POST|`/api/v1/shop/purchases`|`{itemCode,quantity}` only → purchaseId, unitPrice/totalPrice, goldAfter, remainingQuantity |
|GET|`/api/v1/inventory`|owned rows including depleted quantity0; deterministic itemCode order |
|POST|`/api/v1/inventory/items/{itemCode}/use`|Potion/Charm `{battleId}`; Berry no body or `{battleId:null}` |
|GET|`/api/v1/battles/{id}/item-effects`|owned battle effects including armed/value/consumedAt, including terminal battles |

Use result contains actual `healedAmount/currentHp/maxHp`, `bondBefore/bondAfter`, or `armed/bonus`, plus remainingQuantity and context. Capture keeps `chance` as final probability and adds `baseChance/itemBonus/finalChance`.

Errors: ITEM_NOT_FOUND/BATTLE_NOT_FOUND404; invalid quantity, overflow, forbidden client fields/context400; ITEM_DISABLED, INSUFFICIENT_GOLD, MAX_STACK_EXCEEDED, ITEM_NOT_OWNED, ITEM_NOT_USABLE, FULL_HP, INVALID_BATTLE_STATE, EFFECT_ALREADY_ACTIVE409. DB failures use existing sanitized GAME_UNAVAILABLE503; SQL/stack traces are not returned.

## Desktop/UI

Companion ✦ opens the existing interaction entry containing Inventory/Shop. Battle has ITEM. Shop shows authoritative Gold, names/prices/owned counts and BUY (one per click). Contextual inventory shows Berry outside battle, Potion/Charm during battle; Shop round trips retain active-battle filtering. Existing 240×300 interaction surface scrolls if needed; no new panel/key window.

Rust `backend/items.rs` owns DTO validation, supported command mapping, busy guards and actual-value feedback. Main handler blocks simultaneous item/battle/evolution commands. Worker sends explicit purchase/use once, then refreshes inventory/effects/bootstrap/evolution. Network failures release busy and instruct Refresh; no optimistic HP/Bond/Gold changes. The JSX renders provided values only. Potion shows actual HP gain, Berry before→after Bond, Charm Ready, Capture base/bonus/final percentages. React has no new timers or domain formulas.

## Validation evidence — 2026-09-22

### AUTOMATED PASS

- **84 server tests** on fresh PostgreSQL17: existing52 + Item32. Shop/all purchases/history snapshots, validation/overflow/Gold/stack, concurrent purchase and use, potion exact/clamped/fullHP, berry evolution/battle exclusion/overflow, charm arm/duplicate/success/failure/rearm/concurrent captures/use races, bootstrap updates and rollback after deliberately injected DB constraints all pass. Initial failure RNG fixture incorrectly affected encounter selection; constrained it to the capture RNG bound and reran the complete suite.
- **85 Rust tests**, seven opt-in live tests excluded by default; fmt and clippy `--no-deps -- -D warnings` PASS. Existing upstream Tao warnings unchanged.
- Frontend: animation28 + base8; gameplay4 + polish18 + evolution5 + item model8 + **React static-render5** PASS. Static rendering tests execute actual ItemInteraction with mocked Tauri invoke: no render-triggered mutations, server prices/Gold, filtered inventory, guards, feedback. They are not native mouse/focus tests.
- Asset16 + policy9, strict MOA/PIP asset gate including supplied MOKORI base, Tao exact three-file integrity and npm build PASS. Empty animation clips/RUU/NOX bases remain intentionally pending.

### Live vertical slices

Fresh `luma-inventory-test`, loopback PostgreSQL55442 + Spring Boot18084, never the user's55440/18082 DB/server:

1. Ten ordinary deterministic battles earn100G → purchase Potion20G → new battle damage → Potion actual healing and inventory decrement → Charm40G → arm → capture bonus0.10 consumed → Berry30G → authoritative bootstrap. Rust World applies server values and preserves position. Final slice Gold10, HP100, Bond11.
2. Separate isolated fixture Lv3/Bond4/Gold100 → purchase Berry → actual bounded Backend worker UseItem command → ItemUsed/Items/Bootstrap/Evolution/ItemsFinished events → Bond5, AVAILABLE, still Stage1 (no automatic evolution).
3. Existing live evolution explicitly reaches MOKORI Stage2. Existing encounter, battle/capture/reward, gameplay visual and failure/defeat slices pass. All seven opt-in test functions run in their appropriate success/failure fixtures.
4. Arm Charm via HTTP, stop test server process19653, restart process with same PostgreSQL and test-only failure RNG. GET effect remains armed with0.10. Capture reports base0.35 + item0.10 = final0.45; failure marks it consumed; next Capture bonus0.0. Inventory and MOKORI bootstrap survive restart. The first ad-hoc HTTP probe omitted JSON content type (415); corrected the probe, no product change.

### PLATFORM PASS

Local macOS native compile/link/debug bundle PASS. Existing native10-second smoke: transparent nonactivating panels, PIP lifecycle, normal cleanup; exit audit activation0/keyWindow0 (10.31s). This is not an interactive focus guarantee.

### MANUAL_REQUIRED / ENVIRONMENT_BLOCKED

Actual Shop/Inventory appearance/scrolling, physical BUY/USE/click/drag, healing/charm feedback feel, and continuous typing/application/key focus remain MANUAL_REQUIRED. Previously unavailable `access_programs` inspection remains ENVIRONMENT_BLOCKED; it was not retried. No settings, permissions, native architecture or tests were weakened to bypass it.

## Known risks and review boundary

- No automatic mutation retry / idempotency keys. Repeated explicit affordable purchases are distinct; refresh after uncertain transport results.
- Read refreshes are separate serialized HTTP snapshots, not one cross-endpoint database snapshot. Server mutation responses are authoritative; another client may change state between reads.
- One effect row retains current lifecycle, not a full item-use audit. Purchase history retains immutable price snapshots.
- Inventory refresh adds bounded local HTTP reads while the compact panel is open; same five-second worker, no new UI tick/window. CPU/RSS delta not measured.
- Physical UI/focus acceptance remains manual. Architecture/additive migration require human review; PR stays open, never auto-merged.
- Local sync repeatedly generated duplicate node_modules type directories; npm ci restored dependencies without code/config/version workarounds. Untracked user `* 2` files are excluded and preserved.

## Final result

Shop, Purchase, Gold Transaction, Inventory, Potion, Bond Berry, Capture Charm, Capture Integration, Evolution Integration, Concurrency, Rollback, Live Vertical Slice and Regression: AUTOMATED PASS. Desktop UI: static rendering/DTO/worker PASS, physical UI MANUAL_REQUIRED. GitHub CI result is recorded on the PR for the final commit. READY_FOR_HUMAN_REVIEW only after CI passes.
