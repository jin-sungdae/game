package dev.luma.game;

/** Approved growth bands; never grants content readiness or assigns concept identities. */
public record MonsterTier(int number, int minLevel, int maxLevel) {
    public static MonsterTier forLevel(int level) {
        if (level < 1 || level > 100) throw new GameUnavailable("Companion level outside approved growth range");
        if (level < 20) return new MonsterTier(1, 1, 19);
        if (level < 40) return new MonsterTier(2, 20, 39);
        if (level < 60) return new MonsterTier(3, 40, 59);
        if (level < 80) return new MonsterTier(4, 60, 79);
        return new MonsterTier(5, 80, 100);
    }
}
