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
    private static final Map<Key, Rule> APPROVED = approved();
    private static Map<Key, Rule> approved() {
        var rules = new java.util.HashMap<Key, Rule>();
        int[] levels = {3,6,30,60}, bonds = {5,12,40,80};
        for (String species : new String[]{"MOA","RUU","NOX"})
            for (int stage=1;stage<=4;stage++)
                rules.put(new Key(species,stage),new Rule(species,stage,stage+1,levels[stage-1],bonds[stage-1]));
        return Map.copyOf(rules);
    }
    public static Optional<Rule> next(GameDtos.Companion c) {
        return Optional.ofNullable(APPROVED.get(new Key(c.species(), c.evolutionStage())));
    }
}
