package dev.luma.game;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static dev.luma.game.SkillDefinitions.*;
import static dev.luma.game.SkillRules.Availability.*;

class SkillRulesTest {
    // Synthetic content only; no names, magnitudes or unlocks are approved for production.
    Definition fixture(int version, boolean enabled, Kind kind, Target target, String effect) {
        return new Definition("TEST_ONLY", version, "MOA", kind, 2, 3, target, effect, 10, 2, 20, 1, enabled);
    }
    Definition fixture() { return fixture(1, true, Kind.ACTIVE, Target.ENEMY, "DIRECT_DAMAGE"); }

    @Test void speciesMismatch() {
        for (String species : new String[]{"RUU", "NOX", "moa", "UNKNOWN", null}) {
            assertFalse(SkillRules.unlocked(fixture(), species, 2, 3));
            assertEquals(LOCKED, SkillRules.availability(fixture(), species, 2, 3));
        }
    }
    @Test void stageBoundary() {
        assertFalse(SkillRules.unlocked(fixture(), "MOA", 1, 3));
        assertTrue(SkillRules.unlocked(fixture(), "MOA", 2, 3));
        assertTrue(SkillRules.unlocked(fixture(), "MOA", 3, 3));
        assertFalse(SkillRules.unlocked(fixture(), "MOA", 6, 3));
    }
    @Test void levelBoundary() {
        assertEquals(LOCKED, SkillRules.availability(fixture(), "MOA", 2, 2));
        assertEquals(AVAILABLE, SkillRules.availability(fixture(), "MOA", 2, 3));
        assertEquals(AVAILABLE, SkillRules.availability(fixture(), "MOA", 2, 4));
    }
    @Test void disabledSkill() {
        assertEquals(DISABLED, SkillRules.availability(fixture(1, false, Kind.ACTIVE, Target.ENEMY, "DIRECT_DAMAGE"), "MOA", 2, 3));
    }
    @Test void unknownSkillAndEmptyProductionCatalog() {
        assertTrue(SkillDefinitions.all().isEmpty());
        for (String code : new String[]{"UNKNOWN", "TEST_ONLY", null}) {
            assertTrue(SkillDefinitions.find(code).isEmpty());
            assertEquals(UNKNOWN_SKILL, SkillRules.availability(SkillDefinitions.find(code).orElse(null), "MOA", 2, 3));
        }
        assertThrows(UnsupportedOperationException.class, () -> SkillDefinitions.all().add(fixture()));
    }
    @Test void invalidVersion() {
        assertThrows(IllegalArgumentException.class, () -> fixture(0, true, Kind.ACTIVE, Target.ENEMY, "DIRECT_DAMAGE"));
        assertThrows(IllegalArgumentException.class, () -> fixture(-1, true, Kind.ACTIVE, Target.ENEMY, "DIRECT_DAMAGE"));
        var future = fixture(2, true, Kind.ACTIVE, Target.ENEMY, "DIRECT_DAMAGE");
        assertEquals(UNSUPPORTED_VERSION, SkillRules.availability(future, "MOA", 2, 3));
        assertThrows(IllegalArgumentException.class, () -> SkillRules.power(future, 3));
    }
    @Test void unsupportedEffectAndCombination() {
        assertEquals(UNSUPPORTED_EFFECT, SkillRules.availability(fixture(1, true, Kind.ACTIVE, Target.ENEMY, "POISON"), "MOA", 2, 3));
        assertEquals(UNSUPPORTED_EFFECT, SkillRules.availability(fixture(1, true, Kind.PASSIVE, Target.ENEMY, "DIRECT_DAMAGE"), "MOA", 2, 3));
        assertEquals(UNSUPPORTED_EFFECT, SkillRules.availability(fixture(1, true, Kind.ACTIVE, Target.SELF, "DIRECT_DAMAGE"), "MOA", 2, 3));
    }
    @Test void powerScalingAndCap() {
        assertEquals(10, SkillRules.power(fixture(), 1));
        assertEquals(10, SkillRules.power(fixture(), 3));
        assertEquals(12, SkillRules.power(fixture(), 4));
        assertEquals(18, SkillRules.power(fixture(), 7));
        assertEquals(20, SkillRules.power(fixture(), 8));
        assertEquals(20, SkillRules.power(fixture(), 20));
    }
    @Test void powerOverflowIsCappedWithoutWrapping() {
        var huge = new Definition("TEST_HUGE", 1, "MOA", Kind.ACTIVE, 1, 1, Target.ENEMY,
            "DIRECT_DAMAGE", Integer.MAX_VALUE, Integer.MAX_VALUE, Integer.MAX_VALUE, 0, true);
        assertEquals(Integer.MAX_VALUE, SkillRules.power(huge, Integer.MAX_VALUE));
    }
    @Test void invalidPowerInput() {
        assertThrows(IllegalArgumentException.class, () -> SkillRules.power(fixture(), 0));
        assertThrows(IllegalArgumentException.class, () -> SkillRules.power(fixture(), -1));
        assertThrows(IllegalArgumentException.class, () -> SkillRules.power(null, 3));
    }
    @Test void invalidDefinitionBounds() {
        for (int[] values : new int[][]{{0,1,0,0,0,0}, {6,1,0,0,0,0}, {1,0,0,0,0,0},
            {1,1,-1,0,0,0}, {1,1,0,-1,0,0}, {1,1,2,0,1,0}, {1,1,0,0,0,-1}}) {
            assertThrows(IllegalArgumentException.class, () -> new Definition("TEST", 1, "MOA", Kind.ACTIVE,
                values[0], values[1], Target.ENEMY, "DIRECT_DAMAGE", values[2], values[3], values[4], values[5], true));
        }
    }
}
