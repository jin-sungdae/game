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
    private static final Map<Key, Rule> APPROVED = Map.ofEntries(
        Map.entry(new Key("MOA", 1), new Rule("MOA", 1, 2, 3, 5)),
        Map.entry(new Key("MOA", 2), new Rule("MOA", 2, 3, 6, 12)),
        Map.entry(new Key("MOA", 3), new Rule("MOA", 3, 4, 30, 40)),
        Map.entry(new Key("MOA", 4), new Rule("MOA", 4, 5, 60, 80)),
        Map.entry(new Key("RUU", 1), new Rule("RUU", 1, 2, 3, 5)),
        Map.entry(new Key("RUU", 2), new Rule("RUU", 2, 3, 6, 12)),
        Map.entry(new Key("RUU", 3), new Rule("RUU", 3, 4, 30, 40)),
        Map.entry(new Key("RUU", 4), new Rule("RUU", 4, 5, 60, 80)),
        Map.entry(new Key("NOX", 1), new Rule("NOX", 1, 2, 3, 5)),
        Map.entry(new Key("NOX", 2), new Rule("NOX", 2, 3, 6, 12)),
        Map.entry(new Key("NOX", 3), new Rule("NOX", 3, 4, 30, 40)),
        Map.entry(new Key("NOX", 4), new Rule("NOX", 4, 5, 60, 80)));
    public static Optional<Rule> next(GameDtos.Companion c) {
        return Optional.ofNullable(APPROVED.get(new Key(c.species(), c.evolutionStage())));
    }
}
