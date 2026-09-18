package dev.luma.game;

import java.time.Instant;
import java.util.UUID;

public final class GameDtos {
    private GameDtos() {}
    public record Player(long playerId, String name, long gold) {}
    public record Companion(long playerCompanionId, String species, int evolutionStage,
                            String evolutionName, int level, long exp, int bond) {}
    public record Bootstrap(Player player, Companion activeCompanion) {}
    public record Monster(String code, String name, int level, String rarity, String movementProfile) {}
    public record Encounter(UUID encounterId, Monster monster, Instant spawnedAt, Instant expiresAt) {}
}
