package dev.luma.game;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Dormant server-only contract: no controller, scheduler, or calls from Alpha Game/BattleService.
 * Future command handlers must invoke completion in the same transaction as battle persistence.
 * Command receipt infrastructure owns command replay; encounter PK owns semantic reward replay.
 * Local player authority follows the existing server. No client-supplied player, points or time.
 */
@Service
@Transactional
public class CollectionEncounterFoundation {
    private static final long PLAYER = 1;
    private final JdbcTemplate db;
    private final GameRepository game;
    private final MonsterSelector selector;
    private final boolean enabled;
    private final int intervalSeconds;

    public CollectionEncounterFoundation(JdbcTemplate db, GameRepository game, MonsterSelector selector,
            @Value("${luma.collection-foundation.enabled:false}") boolean enabled,
            @Value("${luma.collection-foundation.interval-seconds:240}") int intervalSeconds) {
        if (intervalSeconds < 1 || intervalSeconds > 86400) throw new IllegalArgumentException("Invalid issuance interval");
        this.db=db; this.game=game; this.selector=selector; this.enabled=enabled; this.intervalSeconds=intervalSeconds;
    }
    private void lock() {
        if (!enabled) throw new GameFault(409,"COLLECTION_FOUNDATION_DISABLED");
        game.lockPlayer(PLAYER);
    }
    public record Progress(long earned, long committed, long available) {}
    public record Issuance(GameDtos.Encounter encounter, Instant nextAvailableAt, boolean issued) {}
    public record Reservation(UUID reservationId, String targetMonster, int observationCost,
                              String status, String consumptionState, UUID encounterId) {}

    public Progress progress() { lock(); return balance(); }
    private Progress balance() {
        long earned=db.queryForObject("SELECT COALESCE(sum(points),0) FROM game.t_observation_receipt WHERE player_id=?",Long.class,PLAYER);
        long committed=db.queryForObject("SELECT COALESCE(sum(observation_cost),0) FROM game.t_collection_reservation WHERE player_id=? AND consumption_state IN ('HELD','CONSUMED')",Long.class,PLAYER);
        return new Progress(earned,committed,earned-committed);
    }
    /** Persisted outcomes only. No backfill/scheduler is installed by this foundation. */
    public boolean recordCompletion(UUID encounterId) {
        lock();
        var reasons=db.query("""
            SELECT CASE WHEN e.status='CAPTURED' THEN 'CAPTURED' ELSE 'VICTORY' END
            FROM game.t_encounter e JOIN game.t_battle b USING(encounter_id)
            WHERE e.encounter_id=? AND e.player_id=?
              AND ((e.status='CAPTURED' AND b.status IN ('CAPTURED','VICTORY'))
                OR (b.status='VICTORY' AND e.status IN ('ACTIVE','DEFEATED')))
              AND NOT EXISTS (SELECT 1 FROM game.t_collection_reservation r WHERE r.encounter_id=e.encounter_id)
            FOR UPDATE OF e,b
            """,(r,n)->r.getString(1),encounterId,PLAYER);
        if (reasons.isEmpty()) return false;
        return db.update("""
            INSERT INTO game.t_observation_receipt(encounter_id,player_id,reason)
            VALUES (?,?,?) ON CONFLICT(encounter_id) DO NOTHING
            """,encounterId,PLAYER,reasons.getFirst())==1;
    }
    private Instant next() {
        var rows=db.query("SELECT next_available_at FROM game.t_collection_issuance_budget WHERE player_id=?",
            (r,n)->r.getObject(1,OffsetDateTime.class).toInstant(),PLAYER);
        return rows.isEmpty()?null:rows.getFirst();
    }
    private void debitBudget(Instant now) {
        db.update("""
            INSERT INTO game.t_collection_issuance_budget(player_id,next_available_at) VALUES (?,?)
            ON CONFLICT(player_id) DO UPDATE SET next_available_at=EXCLUDED.next_available_at
            """,PLAYER,OffsetDateTime.ofInstant(now.plusSeconds(intervalSeconds),java.time.ZoneOffset.UTC));
    }
    /** Opt-in future natural path; existing Alpha createEncounter does NOT call this method.
     * DB time is sampled after player lock. Existing ACTIVE encounters neither debit nor reroll.
     * Terminal/ignore/restart cannot reset the persisted issuance deadline.
     */
    public Issuance issueNatural() {
        lock(); game.activeCompanion(PLAYER);
        var now=game.now(); game.expire(PLAYER,now);
        var active=game.active(PLAYER); var next=next();
        if (active.isPresent()) return new Issuance(active.get(),next,false);
        if (next!=null && now.isBefore(next)) return new Issuance(null,next,false);
        var encounter=game.create(PLAYER,selector.select(game.monsters()),now);
        debitBudget(now);
        return new Issuance(encounter,next(),true);
    }
    private Reservation reservation(UUID id) {
        return db.query("""
            SELECT r.reservation_id,m.code,r.observation_cost,r.status,r.consumption_state,r.encounter_id
            FROM game.t_collection_reservation r JOIN game.m_monster m ON m.monster_id=r.target_monster_id
            WHERE r.reservation_id=? AND r.player_id=? FOR UPDATE OF r
            """,(r,n)->new Reservation(r.getObject(1,UUID.class),r.getString(2),r.getInt(3),
                r.getString(4),r.getString(5),r.getObject(6,UUID.class)),id,PLAYER)
            .stream().findFirst().orElseThrow(()->new GameFault(404,"RESERVATION_NOT_FOUND"));
    }
    /** Cost is a future SERVER policy input, never an HTTP request field.
     * ID is stable across retries; mismatched terms fail closed. Only approved content is accepted.
     */
    public Reservation reserve(UUID id, String target, int cost) {
        lock();
        if(id==null || target==null || cost<1) throw new GameFault(400,"INVALID_RESERVATION");
        if(Boolean.TRUE.equals(db.queryForObject("SELECT EXISTS(SELECT 1 FROM game.t_collection_reservation WHERE reservation_id=?)",Boolean.class,id))) {
            var old=reservation(id);
            if(!old.targetMonster().equals(target) || old.observationCost()!=cost) throw new GameFault(409,"RESERVATION_CONFLICT");
            return old;
        }
        var monster=game.monsters().stream().filter(m->m.code().equals(target)).findFirst()
            .orElseThrow(()->new GameFault(409,"INELIGIBLE_TARGET"));
        if(balance().available()<cost) throw new GameFault(409,"INSUFFICIENT_OBSERVATION");
        db.update("""
            INSERT INTO game.t_collection_reservation(reservation_id,player_id,target_monster_id,observation_cost,status,consumption_state)
            VALUES (?,?,?,?,'PENDING','HELD')
            """,id,PLAYER,monster.id(),cost);
        return reservation(id);
    }
    public Reservation cancel(UUID id) {
        lock(); var row=reservation(id);
        if(row.status().equals("ISSUED")) throw new GameFault(409,"RESERVATION_ALREADY_CONSUMED");
        db.update("UPDATE game.t_collection_reservation SET status='CANCELLED',consumption_state='RELEASED' WHERE reservation_id=? AND status='PENDING'",id);
        return reservation(id);
    }
    /**
     * Minimal future consumption contract, intentionally no reserved spawn implementation.
     * Binding accepts only a new matching encounter created by the caller's SAME transaction:
     * PostgreSQL xmin guards against attaching an existing Alpha or replayed encounter.
     * Future issuance must also respect time/target policy before creating that encounter.
     */
    public Reservation consume(UUID id, UUID encounterId) {
        lock(); var row=reservation(id);
        if(row.status().equals("ISSUED")) {
            if(!row.encounterId().equals(encounterId)) throw new GameFault(409,"RESERVATION_CONFLICT");
            return row;
        }
        if(!row.status().equals("PENDING")) throw new GameFault(409,"RESERVATION_NOT_PENDING");
        var now=game.now();var next=next();
        if(next!=null && now.isBefore(next)) throw new GameFault(409,"ISSUANCE_COOLDOWN");
        var valid=db.queryForObject("""
            SELECT EXISTS(
              SELECT 1 FROM game.t_encounter e JOIN game.m_monster m USING(monster_id)
              WHERE e.encounter_id=? AND e.player_id=? AND m.code=? AND e.status='ACTIVE'
                AND e.expires_at>? AND e.xmin::text=pg_current_xact_id()::xid::text
                AND NOT EXISTS (SELECT 1 FROM game.t_observation_receipt o WHERE o.encounter_id=e.encounter_id)
            )
            """,Boolean.class,encounterId,PLAYER,row.targetMonster(),OffsetDateTime.ofInstant(now,java.time.ZoneOffset.UTC));
        if(!Boolean.TRUE.equals(valid)) throw new GameFault(409,"INVALID_RESERVED_ENCOUNTER");
        db.update("""
            UPDATE game.t_collection_reservation SET status='ISSUED',consumption_state='CONSUMED',encounter_id=?,consumed_at=clock_timestamp()
            WHERE reservation_id=? AND status='PENDING'
            """,encounterId,id);
        debitBudget(now);
        return reservation(id);
    }
}
