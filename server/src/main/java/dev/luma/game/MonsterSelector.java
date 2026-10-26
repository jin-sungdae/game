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
    /** Existing approved Alpha content retains its original weight and level distribution.
     * Other already-authorized content is intersected with the active growth band.
     * Production authorization remains the repository/content gate, never this selector.
     */
    public Selection select(List<Monster> monsters, int companionLevel) {
        var tier = MonsterTier.forLevel(companionLevel);
        var eligible = new java.util.ArrayList<Monster>();
        for (var m : monsters) {
            if (m.weight() < 0 || m.minLevel() < 1 || m.maxLevel() < m.minLevel() || m.maxLevel() > 100)
                throw new GameUnavailable("Invalid tier encounter master configuration");
            if (MonsterContent.find(m.code()).map(MonsterContent.Definition::alphaCandidate).orElse(false)) {
                eligible.add(m);
                continue;
            }
            int min = Math.max(m.minLevel(), tier.minLevel());
            int max = Math.min(m.maxLevel(), tier.maxLevel());
            if (min <= max) eligible.add(new Monster(m.id(), m.code(), m.name(), m.rarity(),
                m.movementProfile(), min, max, m.weight()));
        }
        return select(eligible);
    }
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
