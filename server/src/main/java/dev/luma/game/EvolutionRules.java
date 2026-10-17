package dev.luma.game;

import java.util.Map;
import java.util.Optional;

/** The approved transitions, independent of transport and persistence. */
public final class EvolutionRules {
    private EvolutionRules() {}
    public record Rule(String species, int fromStage, int toStage, int requiredLevel, int requiredBond) {
        boolean eligible(GameDtos.Companion c) {
            return species.equals(c.species()) && fromStage == c.evolutionStage()
                && c.level() >= requiredLevel && c.bond() >= requiredBond;
        }
    }
    private record Key(String species, int fromStage) {}
    private static final Map<Key, Rule> APPROVED = Map.of(
        new Key("MOA", 1), new Rule("MOA", 1, 2, 3, 5),
        new Key("MOA", 2), new Rule("MOA", 2, 3, 6, 12));
    public static Optional<Rule> next(GameDtos.Companion c) {
        return Optional.ofNullable(APPROVED.get(new Key(c.species(), c.evolutionStage())));
    }
}
