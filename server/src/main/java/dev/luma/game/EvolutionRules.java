package dev.luma.game;

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
    private static final Rule MOA_TO_MOKORI = new Rule("MOA", 1, 2, 3, 5);
    public static Optional<Rule> next(GameDtos.Companion c) {
        return MOA_TO_MOKORI.species().equals(c.species()) && c.evolutionStage() == MOA_TO_MOKORI.fromStage()
            ? Optional.of(MOA_TO_MOKORI) : Optional.empty();
    }
}
