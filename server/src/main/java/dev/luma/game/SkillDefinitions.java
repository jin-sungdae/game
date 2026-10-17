package dev.luma.game;

import java.util.List;
import java.util.Optional;

/** Server-only contract. No production skill content has been approved. */
public final class SkillDefinitions {
    private SkillDefinitions() {}
    public static final int SUPPORTED_VERSION = 1;
    public enum Kind { ACTIVE, PASSIVE }
    public enum Target { ENEMY, SELF }

    public record Definition(String code, int version, String speciesCode, Kind kind,
                             int unlockStage, int unlockLevel, Target target, String effectType,
                             int basePower, int powerPerLevel, int maxPower, int cooldownTurns,
                             boolean enabled) {
        public Definition {
            if (code == null || code.isBlank() || speciesCode == null || speciesCode.isBlank()
                || kind == null || target == null || effectType == null || effectType.isBlank()
                || version < 1 || unlockStage < 1 || unlockStage > 5 || unlockLevel < 1
                || basePower < 0 || powerPerLevel < 0 || maxPower < basePower || cooldownTurns < 0)
                throw new IllegalArgumentException("Invalid skill definition");
        }
    }

    public static List<Definition> reviewCandidates() { return SkillCatalog.all().stream().map(SkillCatalog.Entry::definition).toList(); }
    public static List<Definition> all() { return List.of(); }
    public static Optional<Definition> find(String code) {
        return all().stream().filter(skill -> skill.code().equals(code)).findFirst();
    }
}
