package dev.luma.game;

import org.junit.jupiter.api.Test;
import java.util.Set;
import static dev.luma.game.GrowthMigrationPreflight.*;
import static org.junit.jupiter.api.Assertions.*;

class GrowthMigrationPreflightTest {
    @Test void everyThresholdAndAdjacentExp() {
        long cumulative = 0;
        for (int level = 1; level <= 100; level++) {
            assertEquals(cumulative, GrowthCurveB.threshold(level), "threshold " + level);
            assertEquals(level, GrowthCurveB.level(cumulative));
            assertEquals(level, GrowthCurveB.level(cumulative + 1));
            if (level == 1) assertThrows(IllegalArgumentException.class, () -> GrowthCurveB.level(-1));
            else assertEquals(level - 1, GrowthCurveB.level(cumulative - 1));
            cumulative += level <= 5 ? 100L * level : level <= 19 ? 600 : level <= 49 ? 800 : level <= 74 ? 1000 : 1200;
        }
        assertEquals(88900, GrowthCurveB.threshold(100));
        assertThrows(IllegalArgumentException.class, () -> GrowthCurveB.threshold(0));
        assertThrows(IllegalArgumentException.class, () -> GrowthCurveB.threshold(101));
        assertThrows(IllegalArgumentException.class, () -> GrowthCurveB.threshold(Integer.MAX_VALUE));
    }

    @Test void everyLegacyExpThroughNewCapPreservesIdentityAndNeverLowersLevel() {
        assertEquals(20, CombatRules.MAX_LEVEL);
        assertEquals(GrowthPolicyVersion.ALPHA_GROWTH_V1, SOURCE_POLICY);
        for (long exp = 0; exp <= 88901; exp++) {
            int old = CombatRules.level(exp);
            var input = new Snapshot(42, old, exp);
            var result = preview(input, 60);
            assertEquals(Set.of(Status.NORMAL), result.conversionStatus());
            assertEquals(42, result.playerCompanionId());
            assertEquals(old, result.oldLevel());
            assertEquals(exp, result.oldExp());
            assertEquals(Integer.valueOf(old), result.expectedOldLevel());
            assertTrue(result.newLevel() >= old);
            assertEquals(Long.valueOf(GrowthCurveB.threshold(result.newLevel())), result.newThreshold());
            assertEquals(GrowthPolicyVersion.GROWTH_B_V2, result.growthPolicyVersion());
            assertEquals(new Snapshot(42, old, exp), input);
        }
        for (int level = 1; level <= 20; level++) {
            assertEquals(50L * level * (level - 1), CombatRules.levelThreshold(level));
            assertEquals(level, CombatRules.level(CombatRules.levelThreshold(level)));
        }
        assertEquals(20, CombatRules.level(88900));
    }

    @Test void legacyCapMapsTo31AndCandidateCapDoesNotDiscardExp() {
        assertEquals(Integer.valueOf(31), preview(new Snapshot(1, 20, 19000), 60).newLevel());
        for (long exp : new long[] {88900, 88901, 100000, Long.MAX_VALUE}) {
            var result = preview(new Snapshot(1, 20, exp), 0);
            assertEquals(Integer.valueOf(100), result.newLevel());
            assertEquals(Long.valueOf(88900), result.newThreshold());
            assertEquals(exp, result.oldExp());
        }
    }

    @Test void corruptInputsAreReportedWithoutRepairOrConversion() {
        assertInvalid(new Snapshot(1, 1, -1), 0, Set.of(Status.NEGATIVE_EXP));
        assertInvalid(new Snapshot(1, 1, Long.MIN_VALUE), 0, Set.of(Status.NEGATIVE_EXP));
        for (int level : new int[] {Integer.MIN_VALUE, 0, 21, 100, Integer.MAX_VALUE})
            assertInvalid(new Snapshot(1, level, 19000), 0, Set.of(Status.LEVEL_OUT_OF_RANGE));
        assertInvalid(new Snapshot(1, 20, 0), 0, Set.of(Status.LEVEL_EXP_MISMATCH));
        assertInvalid(new Snapshot(1, 1, 19000), 0, Set.of(Status.LEVEL_EXP_MISMATCH));
        assertInvalid(new Snapshot(1, 0, -1), 0, Set.of(Status.LEVEL_OUT_OF_RANGE, Status.NEGATIVE_EXP));
        assertInvalid(new Snapshot(1, 1, Long.MAX_VALUE), 1,
            Set.of(Status.LEVEL_EXP_MISMATCH, Status.OVERFLOW_RISK));
        assertNull(preview(new Snapshot(1, 1, -1), 0).expectedOldLevel());
        assertEquals(Integer.valueOf(20), preview(new Snapshot(1, 0, 19000), 0).expectedOldLevel());
    }

    @Test void overflowHeadroomBoundaryIsExplicitAndDoesNotApplyReward() {
        long safe = Long.MAX_VALUE - 60;
        var result = preview(new Snapshot(1, 20, safe), 60);
        assertEquals(Set.of(Status.NORMAL), result.conversionStatus());
        assertEquals(safe, result.oldExp());
        assertInvalid(new Snapshot(1, 20, safe + 1), 60, Set.of(Status.OVERFLOW_RISK));
        assertInvalid(new Snapshot(1, 20, Long.MAX_VALUE), 1, Set.of(Status.OVERFLOW_RISK));
        assertEquals(Set.of(Status.NORMAL), preview(new Snapshot(1, 1, 0), Long.MAX_VALUE).conversionStatus());
        assertInvalid(new Snapshot(1, 1, 1), Long.MAX_VALUE, Set.of(Status.OVERFLOW_RISK));
        assertThrows(IllegalArgumentException.class, () -> preview(new Snapshot(1, 1, 0), -1));
        assertThrows(NullPointerException.class, () -> preview(null, 0));
        assertThrows(UnsupportedOperationException.class, () -> result.conversionStatus().clear());
    }

    private static void assertInvalid(Snapshot input, long gain, Set<Status> expected) {
        var result = preview(input, gain);
        assertEquals(expected, result.conversionStatus());
        assertEquals(input.level(), result.oldLevel());
        assertEquals(input.exp(), result.oldExp());
        assertNull(result.newLevel());
        assertNull(result.newThreshold());
    }
}
