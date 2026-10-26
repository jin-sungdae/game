package dev.luma.game;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/** Reads the durable revision under the executor's player lock. */
@Component
public class DatabaseSelectionRevision implements EvolutionSelectionRevision {
    private final JdbcTemplate db;
    public DatabaseSelectionRevision(JdbcTemplate db) { this.db=db; }
    @Override public long current(long playerId) {
        return db.queryForObject("SELECT active_selection_revision FROM game.t_player WHERE player_id=?",Long.class,playerId);
    }
}
