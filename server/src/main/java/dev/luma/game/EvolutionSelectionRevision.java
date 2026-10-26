package dev.luma.game;

/** Switching-owned integration point. Implemented by DatabaseSelectionRevision.
 * The provider reads game.t_player.active_selection_revision in the current
 * transaction, after the executor has locked that player FOR UPDATE.
 * Switching owns the schema, existing-player revision 0, and atomic increments
 * on actual selection changes only (not reselecting the same companion).
 * Do not substitute a constant, process-local counter, or companion ID for this value.
 */
@FunctionalInterface
public interface EvolutionSelectionRevision {
    long current(long playerId);
}
