package dev.luma.game;

import java.util.Objects;
import java.util.UUID;

/** All expectations are frozen with commandId for the lifetime of one user intent. */
public record EvolutionCommandRequest(UUID commandId, long expectedCompanionId,
                                      int expectedStage, long expectedSelectionRevision) {
    public EvolutionCommandRequest {
        Objects.requireNonNull(commandId, "commandId");
        if (expectedCompanionId <= 0 || expectedStage < 1 || expectedStage > 5
                || expectedSelectionRevision < 0)
            throw new IllegalArgumentException("Invalid evolution command expectations");
    }
}
