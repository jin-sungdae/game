# Companion Bond Progression v0.2

## Implementation design (recorded before implementation)

Base: origin/main dc22de9, including PR #40. User-authorized separation: Battle EXP unchanged, Battle Bond0; explicit companion interaction Bond+1 per300 seconds; Berry+1 unchanged. Evolution thresholds3/5 and6/12 unchanged. Existing Bond/stage/history must never be reset or recomputed.

Current production sources inspected directly: BattleService.reward increments Bond1 with EXP/Gold; ItemService.use/BERRY_BOND increments1 and consumes inventory; Capture/Evolution/Discovery/bootstrap do not add Bond; CompanionController's classified click only triggers local Reacting. No persistent interaction reward/cooldown exists.

Minimal command: bodyless POST /api/v1/companions/active/interact. Reject client amount/timestamp/query fields. Server transaction locks existing player then active companion, reads PostgreSQL clock after lock, awards1 if last successful interaction is null or at least300 seconds old. Cooldown returns HTTP200 COOLDOWN with delta0. Both outcomes return authoritative bootstrap/evolution status and nextAvailableAt. No JVM mutex. No automatic client replay after uncertain POST failure.

Schema inspection: t_player_companion.updated_at is shared by battle, Berry and evolution; using it would incorrectly reset or bypass the relationship cooldown. No existing interaction history timestamp exists. Add V10 nullable last_bond_interaction_at only. Existing rows remain unchanged (null means first valid interaction available). Alternative separate history table is unnecessary for one per-companion cooldown. Existing migrations untouched; no destructive/backfill migration.

Desktop keeps the existing native click-vs-drag classifier and bounded backend worker. Only a completed click requests the command; ambient reactions/drag/hover do not. Bond changes only from acknowledged server bootstrap. Show a short in-panel Bond +1 message on success, silently handle cooldown, no new window/modal/focus activation. Server remains authoritative even for direct API callers; physical-human proof/auth is out of this local-backend scope.

PR #40 analysis is historical v0.1 evidence; preserve its reported data while clearly separating its historical assumptions from the new production analysis. Add current deterministic A/B/C/D/E pacing analysis and regression evidence here.

## Validation plan

Battle EXP/Gold/Personality/Capture unchanged; battle Bond0; interaction first/cooldown/expiry/concurrency/restart; Berry inventory/independence; natural battle-only vs relationship progression; old high Bond/NEBLA preservation; level6 Bond8/11 locked,12 available. Full Java/PostgreSQL, Rust, Desktop/content/assets/presentation, clippy/Tao and latest HEAD CI. Native focus/mouse/typing manual checks separately NOT_RUN until performed. No automatic merge.
