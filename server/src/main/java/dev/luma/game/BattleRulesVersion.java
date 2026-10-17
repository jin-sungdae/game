package dev.luma.game;

/** Persisted battle contract. Reserved versions are never executable fallbacks. */
public enum BattleRulesVersion {
    ALPHA_V1,
    EXPANDED_V2;

    public static void requireSupported(String version) {
        // Runtime failure rolls back even BattleService's noRollbackFor=GameFault:
        // lazy encounter expiry must not commit when a stored version is unsupported.
        if (!ALPHA_V1.name().equals(version))
            throw new GameUnavailable("Unsupported battle rules version");
    }
}
