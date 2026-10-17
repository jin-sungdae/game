package dev.luma.game;

import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class CompanionOwnershipRepository {
    private final JdbcTemplate jdbc;
    public CompanionOwnershipRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    public List<CompanionOwnershipDtos.Owned> owned(long playerId) {
        return jdbc.query("""
            SELECT c.player_companion_id,s.code,c.evolution_stage,e.name,c.level,c.exp,c.bond,c.active
            FROM game.t_player_companion c JOIN game.m_species s USING(species_id)
            JOIN game.m_species_evolution e USING(species_id,evolution_stage)
            WHERE c.player_id=? ORDER BY c.player_companion_id
            """, (r,n)->new CompanionOwnershipDtos.Owned(r.getLong(1),r.getString(2),r.getInt(3),
                r.getString(4),r.getInt(5),r.getLong(6),r.getInt(7),r.getBoolean(8)),playerId);
    }
}
