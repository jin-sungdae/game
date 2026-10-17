package dev.luma.game;

import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

/** Read-only snapshot validation. No bean, database access, UPDATE or gameplay integration.
 * The source contract is ALPHA_GROWTH_V1 (levels 1..20), never inferred as B from EXP.
 * Other companion fields and evolution history are outside this projection and untouched.
 */
public final class GrowthMigrationPreflight {
    public static final GrowthPolicyVersion SOURCE_POLICY = GrowthPolicyVersion.ALPHA_GROWTH_V1;
    private GrowthMigrationPreflight() {}

    public enum Status { NORMAL, LEVEL_EXP_MISMATCH, NEGATIVE_EXP, LEVEL_OUT_OF_RANGE, OVERFLOW_RISK }

    /** Deliberately permits invalid level/EXP values for auditing corrupted or imported data. */
    public record Snapshot(long playerCompanionId, int level, long exp) {}

    /** growthPolicyVersion names the preview target, not an assignment to stored data.
     * Invalid snapshots retain their original values and have no proposed level/threshold.
     * expectedOldLevel is null only when negative EXP makes it undefined.
     */
    public record Preview(long playerCompanionId, int oldLevel, long oldExp,
                          Integer expectedOldLevel, Integer newLevel, Long newThreshold,
                          GrowthPolicyVersion growthPolicyVersion, Set<Status> conversionStatus) {
        public Preview { conversionStatus = Set.copyOf(conversionStatus); }
    }

    /** anticipatedExpGain is the nonnegative reward headroom to audit, not EXP to apply.
     * Zero audits conversion alone; callers must supply their reward bound for overflow safety.
     * Multiple faults are reported together. NORMAL is exclusive of all faults.
     */
    public static Preview preview(Snapshot snapshot, long anticipatedExpGain) {
        Objects.requireNonNull(snapshot, "snapshot");
        if (anticipatedExpGain < 0) throw new IllegalArgumentException("EXP gain must be nonnegative");
        var issues = EnumSet.noneOf(Status.class);
        boolean validLevel = snapshot.level() >= 1 && snapshot.level() <= 20;
        if (!validLevel) issues.add(Status.LEVEL_OUT_OF_RANGE);
        Integer expected = null;
        if (snapshot.exp() < 0) {
            issues.add(Status.NEGATIVE_EXP);
        } else {
            expected = alphaLevel(snapshot.exp());
            if (validLevel && snapshot.level() != expected) issues.add(Status.LEVEL_EXP_MISMATCH);
            if (snapshot.exp() > Long.MAX_VALUE - anticipatedExpGain) issues.add(Status.OVERFLOW_RISK);
        }
        Integer next = null;
        Long threshold = null;
        if (issues.isEmpty()) {
            next = GrowthCurveB.level(snapshot.exp());
            if (next < snapshot.level()) throw new IllegalStateException("Conversion would reduce level");
            threshold = GrowthCurveB.threshold(next);
            issues.add(Status.NORMAL);
        }
        return new Preview(snapshot.playerCompanionId(), snapshot.level(), snapshot.exp(), expected,
            next, threshold, GrowthPolicyVersion.GROWTH_B_V2, issues);
    }

    // Frozen source-policy calculation: changing live CombatRules must not reinterpret old saves.
    private static int alphaLevel(long exp) {
        int level = 1;
        while (level < 20 && exp >= 50L * (level + 1) * level) level++;
        return level;
    }
}
