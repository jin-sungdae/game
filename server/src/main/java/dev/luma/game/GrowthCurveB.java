package dev.luma.game;

/** Approved growth policy GROWTH_B_V2. CombatRules retains frozen Alpha battle formulas. */
public final class GrowthCurveB {
    public static final int MAX_LEVEL = 100;
    private GrowthCurveB() {}

    public static long threshold(int level) {
        if (level < 1 || level > MAX_LEVEL) throw new IllegalArgumentException("Level must be 1..100");
        if (level <= 6) return 50L * level * (level - 1);
        if (level <= 20) return 1500L + 600L * (level - 6);
        if (level <= 50) return 9900L + 800L * (level - 20);
        if (level <= 75) return 33900L + 1000L * (level - 50);
        return 58900L + 1200L * (level - 75);
    }

    public static int level(long exp) {
        if (exp < 0) throw new IllegalArgumentException("EXP must be nonnegative");
        int level = 1;
        while (level < MAX_LEVEL && exp >= threshold(level + 1)) level++;
        return level;
    }
}
