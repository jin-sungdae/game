package dev.luma.game;

public final class EvolutionDtos {
    private EvolutionDtos() {}
    public enum State { LOCKED, AVAILABLE, MAX_STAGE }
    public record Requirement(int required, int current, boolean met) {}
    public record Requirements(Requirement level, Requirement bond) {}
    public record Status(State status, String species, int currentStage, String currentName,
                         Integer nextStage, String nextName, Requirements requirements) {}
    public record Result(String result, Status evolution, GameDtos.Bootstrap bootstrap) {}
}
