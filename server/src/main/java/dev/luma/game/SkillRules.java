package dev.luma.game;

import static dev.luma.game.SkillDefinitions.*;

/** Pure definition checks and arithmetic; never executes or persists a battle action. */
public final class SkillRules {
    private SkillRules() {}
    public enum Availability {
        AVAILABLE, UNKNOWN_SKILL, UNSUPPORTED_VERSION, DISABLED, LOCKED, UNSUPPORTED_EFFECT
    }

    public static boolean unlocked(Definition skill, String species, int stage, int level) {
        return skill != null && skill.speciesCode().equals(species)
            && stage >= skill.unlockStage() && stage <= 5 && level >= skill.unlockLevel();
    }

    /** AVAILABLE means this contract supports the definition, not gameplay activation. */
    public static Availability availability(Definition skill, String species, int stage, int level) {
        if (skill == null) return Availability.UNKNOWN_SKILL;
        if (skill.version() != SUPPORTED_VERSION) return Availability.UNSUPPORTED_VERSION;
        if (!skill.enabled()) return Availability.DISABLED;
        if (!unlocked(skill, species, stage, level)) return Availability.LOCKED;
        if (skill.kind() != Kind.ACTIVE || skill.target() != Target.ENEMY
            || !"DIRECT_DAMAGE".equals(skill.effectType())) return Availability.UNSUPPORTED_EFFECT;
        return Availability.AVAILABLE;
    }

    public static Availability candidateAvailability(SkillCatalog.Entry entry,String species,int stage,int level) {
        if(entry==null)return Availability.UNKNOWN_SKILL;
        var skill=entry.definition();
        if(skill.version()!=SUPPORTED_VERSION)return Availability.UNSUPPORTED_VERSION;
        if(!skill.enabled())return Availability.DISABLED;
        if(!unlocked(skill,species,stage,level))return Availability.LOCKED;
        return Availability.AVAILABLE;
    }
    /** Arithmetic only: callers must separately check availability before any future execution. */
    public static int power(Definition skill, int level) {
        if (skill == null || skill.version() != SUPPORTED_VERSION || level < 1)
            throw new IllegalArgumentException("Invalid skill power input");
        long growthLevels = Math.max(0L, (long) level - skill.unlockLevel());
        long power = skill.basePower() + growthLevels * skill.powerPerLevel();
        return (int) Math.min(skill.maxPower(), power);
    }
}
