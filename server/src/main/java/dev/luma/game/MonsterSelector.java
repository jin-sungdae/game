package dev.luma.game;

import org.springframework.stereotype.Component;
import java.util.List;

@Component
public class MonsterSelector {
    public record Monster(long id, String code, String name, String rarity, String movementProfile,
                          int minLevel, int maxLevel, int weight) {}
    public record Selection(Monster monster, int level) {}
    private final RandomSource random;
    public MonsterSelector(RandomSource random) { this.random = random; }
    public Selection select(List<Monster> monsters) {
        long total = monsters.stream().mapToLong(Monster::weight).sum();
        if (total <= 0 || monsters.stream().anyMatch(m -> m.weight() < 0 || m.minLevel() < 1 || m.maxLevel() < m.minLevel()))
            throw new GameUnavailable("No valid encounter master configuration");
        long point = random.nextLong(total);
        if (point < 0 || point >= total) throw new GameUnavailable("Invalid random source");
        for (var monster : monsters) {
            if (point < monster.weight()) {
                long range = (long) monster.maxLevel() - monster.minLevel() + 1;
                long offset = random.nextLong(range);
                if (offset < 0 || offset >= range) throw new GameUnavailable("Invalid random source");
                return new Selection(monster, Math.toIntExact(monster.minLevel() + offset));
            }
            point -= monster.weight();
        }
        throw new GameUnavailable("No selectable monster");
    }
}
