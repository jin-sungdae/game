package dev.luma.game;

import java.time.Instant;
import java.time.OffsetDateTime;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CompanionInteractionService {
    public static final long COOLDOWN_SECONDS=300;
    public static final int BOND_GAIN=1;
    public enum Outcome { AWARDED, COOLDOWN }
    public record Result(Outcome outcome,int bondDelta,Instant serverTime,Instant nextAvailableAt,
                         GameDtos.Bootstrap bootstrap,EvolutionDtos.Status evolution) {}
    private final GameRepository game;
    private final EvolutionRepository companions;
    private final EvolutionService evolution;
    private final JdbcTemplate db;
    public CompanionInteractionService(GameRepository game,EvolutionRepository companions,EvolutionService evolution,JdbcTemplate db) {
        this.game=game;this.companions=companions;this.evolution=evolution;this.db=db;
    }
    @Transactional
    public Result interact() {
        var player=game.lockPlayer(1);
        var before=companions.lockActive(1);
        // Read DB wall time after obtaining locks: queued requests must observe committed cooldown.
        var now=game.now();
        var last=db.queryForObject("SELECT last_bond_interaction_at FROM game.t_player_companion WHERE player_companion_id=?",
            (r,n)->r.getObject(1,OffsetDateTime.class),before.playerCompanionId());
        boolean available=last==null || !now.isBefore(last.toInstant().plusSeconds(COOLDOWN_SECONDS));
        if(available) {
            if(before.bond()>Integer.MAX_VALUE-BOND_GAIN) throw new GameFault(409,"BOND_LIMIT_REACHED");
            db.update("UPDATE game.t_player_companion SET bond=bond+?,last_bond_interaction_at=?,updated_at=clock_timestamp() WHERE player_companion_id=?",
                BOND_GAIN,OffsetDateTime.ofInstant(now,java.time.ZoneOffset.UTC),before.playerCompanionId());
        }
        var after=game.activeCompanion(1);
        var next=(available?now:last.toInstant()).plusSeconds(COOLDOWN_SECONDS);
        return new Result(available?Outcome.AWARDED:Outcome.COOLDOWN,available?BOND_GAIN:0,now,next,
            new GameDtos.Bootstrap(player,after),evolution.status(after));
    }
}
