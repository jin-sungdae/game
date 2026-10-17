package dev.luma.game.economy;

import java.time.Duration;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Pure, dormant decision contract. Does not issue encounters or own another budget table.
 * Persistence/issuance belongs to CollectionEncounterFoundation (PR #71):
 * t_collection_issuance_budget(player_id,next_available_at).
 * Its adapter must lock player, sample DB time, expire/re-read ACTIVE, load persisted
 * next_available_at as nextEligibleAt, then create AND debit in the SAME transaction.
 * NATURAL and OBSERVATION_RESERVATION share one player key; commandId is NOT a budget key.
 * ACTIVE is returned before cooldown and consumes nothing; restart loads the same snapshot.
 * No adapter is wired here; existing GameService behavior remains authoritative.
 */
@Component
public final class EncounterIssuancePolicy {
    public enum Mode { DISABLED, SHARED_PLAYER_BUDGET }
    public enum Source { NATURAL, OBSERVATION_RESERVATION }
    public enum Action { LEGACY_UNCHANGED, REUSE_ACTIVE, WAIT, ELIGIBLE }
    public record Snapshot(long playerId, Instant nextEligibleAt, UUID activeEncounterId) {
        public Snapshot {if(playerId<=0) throw new IllegalArgumentException("Invalid player");}
    }
    public record Decision(Action action, UUID activeEncounterId, Instant nextEligibleAt) {}
    private final Mode mode;
    private final long intervalSeconds;

    public EncounterIssuancePolicy(
            @Value("${luma.economy.encounter-issuance.mode:DISABLED}") Mode mode,
            @Value("${luma.economy.encounter-issuance.interval-seconds:0}") long intervalSeconds) {
        this.mode=Objects.requireNonNull(mode);
        if (intervalSeconds<0 || intervalSeconds>86400 || (mode!=Mode.DISABLED && intervalSeconds==0))
            throw new IllegalArgumentException("Enabled policy requires an explicit positive interval");
        this.intervalSeconds=intervalSeconds;
    }

    public Mode mode() {return mode;}
    public long budgetOwner(Snapshot snapshot, Source source) {
        Objects.requireNonNull(source);
        return snapshot.playerId();
    }
    public Decision evaluate(Snapshot snapshot, Source source, Instant databaseNow) {
        Objects.requireNonNull(snapshot); Objects.requireNonNull(source); Objects.requireNonNull(databaseNow);
        if (mode==Mode.DISABLED) return new Decision(Action.LEGACY_UNCHANGED,null,null);
        if (snapshot.activeEncounterId()!=null)
            return new Decision(Action.REUSE_ACTIVE,snapshot.activeEncounterId(),snapshot.nextEligibleAt());
        if (snapshot.nextEligibleAt()!=null && databaseNow.isBefore(snapshot.nextEligibleAt()))
            return new Decision(Action.WAIT,null,snapshot.nextEligibleAt());
        return new Decision(Action.ELIGIBLE,null,snapshot.nextEligibleAt());
    }
    /** Candidate interval has no default. Only call after actual issuance inside the owner transaction. */
    public Instant deadlineAfterIssuance(Instant databaseNow) {
        if (mode==Mode.DISABLED) throw new IllegalStateException("Issuance policy disabled");
        return databaseNow.plus(Duration.ofSeconds(intervalSeconds));
    }
}
