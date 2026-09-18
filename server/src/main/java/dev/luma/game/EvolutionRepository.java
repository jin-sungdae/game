package dev.luma.game;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class EvolutionRepository {
    private final JdbcTemplate jdbc;
    public EvolutionRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    public GameDtos.Companion lockActive(long player) {
        var rows = jdbc.query("""
            SELECT c.player_companion_id,s.code,c.evolution_stage,e.name,c.level,c.exp,c.bond
            FROM game.t_player_companion c JOIN game.m_species s USING(species_id)
            JOIN game.m_species_evolution e USING(species_id,evolution_stage)
            WHERE c.player_id=? AND c.active FOR UPDATE OF c
            """, (r,n) -> new GameDtos.Companion(r.getLong(1),r.getString(2),r.getInt(3),r.getString(4),
                r.getInt(5),r.getLong(6),r.getInt(7)), player);
        if (rows.size()!=1) throw new GameUnavailable("Exactly one active companion required");
        return rows.getFirst();
    }
    public String nextName(String species, int stage) {
        var rows = jdbc.query("""
            SELECT e.name FROM game.m_species_evolution e JOIN game.m_species s USING(species_id)
            WHERE s.code=? AND e.evolution_stage=?
            """, (r,n)->r.getString(1), species, stage);
        if (rows.size()!=1) throw new GameUnavailable("Evolution master missing");
        return rows.getFirst();
    }
    public boolean completedFirstEvolution(GameDtos.Companion c) {
        return "MOA".equals(c.species()) && c.evolutionStage()==2 && Boolean.TRUE.equals(jdbc.queryForObject("""
            SELECT EXISTS(SELECT 1 FROM game.t_companion_evolution_history h
            JOIN game.m_species s USING(species_id)
            WHERE h.player_companion_id=? AND s.code=? AND from_stage=1 AND to_stage=2)
            """, Boolean.class, c.playerCompanionId(), c.species()));
    }
    public void evolve(GameDtos.Companion c, EvolutionRules.Rule rule) {
        int updated = jdbc.update("""
            UPDATE game.t_player_companion SET evolution_stage=?,updated_at=clock_timestamp()
            WHERE player_companion_id=? AND evolution_stage=?
            """, rule.toStage(), c.playerCompanionId(), rule.fromStage());
        if (updated!=1) throw new GameUnavailable("Evolution state changed");
        jdbc.update("""
            INSERT INTO game.t_companion_evolution_history
            (player_companion_id,species_id,from_stage,to_stage,level_at_evolution,bond_at_evolution)
            SELECT player_companion_id,species_id,?,?,?,? FROM game.t_player_companion
            WHERE player_companion_id=?
            """, rule.fromStage(),rule.toStage(),c.level(),c.bond(),c.playerCompanionId());
    }
}
