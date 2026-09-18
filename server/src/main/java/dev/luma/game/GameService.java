package dev.luma.game;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.Optional;

@Service
public class GameService {
    private static final long LOCAL_PLAYER=1;
    private final GameRepository repository;
    private final MonsterSelector selector;
    public GameService(GameRepository repository,MonsterSelector selector) {this.repository=repository;this.selector=selector;}
    @Transactional
    public GameDtos.Bootstrap bootstrap() {
        return new GameDtos.Bootstrap(repository.lockPlayer(LOCAL_PLAYER),repository.activeCompanion(LOCAL_PLAYER));
    }
    @Transactional
    public GameDtos.Encounter createEncounter() {
        repository.lockPlayer(LOCAL_PLAYER); // Serialize this player's requests before observing DB time.
        repository.activeCompanion(LOCAL_PLAYER);
        var now=repository.now();
        repository.expire(LOCAL_PLAYER,now);
        return repository.active(LOCAL_PLAYER).orElseGet(()->repository.create(LOCAL_PLAYER,selector.select(repository.monsters()),now));
    }
    @Transactional
    public Optional<GameDtos.Encounter> activeEncounter() {
        repository.lockPlayer(LOCAL_PLAYER);
        repository.expire(LOCAL_PLAYER,repository.now());
        return repository.active(LOCAL_PLAYER);
    }
}
