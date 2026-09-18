package dev.luma.game;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import static dev.luma.game.EvolutionDtos.*;

@Service
public class EvolutionService {
    private static final long LOCAL_PLAYER = 1;
    private final GameRepository game;
    private final EvolutionRepository repository;
    public EvolutionService(GameRepository game, EvolutionRepository repository) {
        this.game=game; this.repository=repository;
    }
    private Status status(GameDtos.Companion c) {
        var next=EvolutionRules.next(c);
        if (next.isEmpty()) return new Status(c.evolutionStage()==5 ? State.MAX_STAGE : State.LOCKED,
            c.species(),c.evolutionStage(),c.evolutionName(),null,null,null);
        var rule=next.get();
        String name=repository.nextName(c.species(),rule.toStage());
        return new Status(rule.eligible(c) ? State.AVAILABLE : State.LOCKED,
            c.species(),c.evolutionStage(),c.evolutionName(),rule.toStage(),name,
            new Requirements(new Requirement(rule.requiredLevel(),c.level(),c.level()>=rule.requiredLevel()),
                new Requirement(rule.requiredBond(),c.bond(),c.bond()>=rule.requiredBond())));
    }
    @Transactional
    public Status status() {
        game.lockPlayer(LOCAL_PLAYER);
        return status(repository.lockActive(LOCAL_PLAYER));
    }
    @Transactional
    public Result evolve() {
        var player=game.lockPlayer(LOCAL_PLAYER);
        var current=repository.lockActive(LOCAL_PLAYER);
        if (repository.completedFirstEvolution(current))
            return new Result("ALREADY_EVOLVED",status(current),new GameDtos.Bootstrap(player,current));
        var before=status(current); // Verifies the next master before mutation.
        if (before.status()==State.MAX_STAGE) throw new GameFault(409,"MAX_STAGE");
        if (before.status()!=State.AVAILABLE) throw new GameFault(409,"NOT_ELIGIBLE");
        var rule=EvolutionRules.next(current).orElseThrow();
        repository.evolve(current,rule);
        var updated=game.activeCompanion(LOCAL_PLAYER);
        return new Result("EVOLVED",status(updated),new GameDtos.Bootstrap(player,updated));
    }
}
