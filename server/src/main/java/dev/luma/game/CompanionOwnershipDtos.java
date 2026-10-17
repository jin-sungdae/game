package dev.luma.game;

import java.util.List;

public final class CompanionOwnershipDtos {
    private CompanionOwnershipDtos() {}
    public record Owned(long playerCompanionId, String species, int evolutionStage,
                        String evolutionName, int level, long exp, int bond, boolean active) {}
    public record Ownership(List<Owned> companions, long activeCompanionId) {
        public Ownership { companions = List.copyOf(companions); }
    }
}
