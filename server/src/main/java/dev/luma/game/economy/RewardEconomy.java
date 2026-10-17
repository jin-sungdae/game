package dev.luma.game.economy;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.luma.game.GameFault;
import dev.luma.game.GameRepository;
import dev.luma.game.command.*;
import java.sql.Date;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import static dev.luma.game.economy.RewardEntitlement.*;

/**
 * Dormant trusted server API. No controller, scheduler or gameplay caller.
 * Eligibility, player identity and terms must come from a future server domain policy.
 * Command receipts protect transport retries; entitlement keys protect semantic retries.
 * All writes use the existing datasource/player lock and REQUIRED transaction.
 */
@Service
public class RewardEconomy {
    private final JdbcTemplate db;
    private final GameRepository game;
    private final CommandReceiptExecutor commands;
    private final ObjectMapper json;
    private final boolean enabled;

    public RewardEconomy(JdbcTemplate db, GameRepository game, CommandReceiptExecutor commands,
            ObjectMapper json, @Value("${luma.economy.rewards-enabled:false}") boolean enabled) {
        this.db=db; this.game=game; this.commands=commands; this.json=json; this.enabled=enabled;
    }

    private void requireEnabled() {
        if (!enabled) throw new GameFault(409, "ECONOMY_REWARDS_DISABLED");
    }

    /** Idempotent first-write-wins snapshot, including when policy version changes. */
    @Transactional(isolation=Isolation.READ_COMMITTED)
    public RewardEntitlement entitle(Key key, Terms terms) {
        requireEnabled();
        Objects.requireNonNull(key); Objects.requireNonNull(terms);
        game.lockPlayer(key.playerId());
        var ids=db.queryForList("""
            SELECT entitlement_id FROM game.t_reward_entitlement
            WHERE player_id=? AND reward_type=? AND week_start IS NOT DISTINCT FROM ?
              AND reward_slot IS NOT DISTINCT FROM ? AND campaign_id IS NOT DISTINCT FROM ?
              AND milestone IS NOT DISTINCT FROM ?
            """, UUID.class, key.playerId(), key.type().name(),
            key.weekStart()==null?null:Date.valueOf(key.weekStart()), key.rewardSlot(), key.campaignId(), key.milestone());
        if (!ids.isEmpty()) return read(key.playerId(), ids.getFirst());
        UUID id=UUID.randomUUID();
        db.update("""
            INSERT INTO game.t_reward_entitlement
            (entitlement_id,player_id,reward_type,week_start,reward_slot,campaign_id,milestone,policy_version,gold)
            VALUES (?,?,?,?,?,?,?,?,?)
            """, id,key.playerId(),key.type().name(),key.weekStart()==null?null:Date.valueOf(key.weekStart()),
            key.rewardSlot(),key.campaignId(),key.milestone(),terms.policyVersion(),terms.gold());
        for (var entry:new TreeMap<>(terms.items()).entrySet()) {
            var item=item(entry.getKey());
            if (entry.getValue()>item.maxStack()) throw new GameFault(409,"MAX_STACK_EXCEEDED");
            db.update("INSERT INTO game.t_reward_entitlement_item(entitlement_id,item_id,quantity) VALUES (?,?,?)",
                id,item.id(),entry.getValue());
        }
        return read(key.playerId(),id);
    }

    /** Same command replays its original result; a different command returns granted=false. */
    public Claim claim(long playerId, UUID entitlementId, UUID commandId) {
        requireEnabled();
        Objects.requireNonNull(entitlementId);
        var request=new CommandRequest(playerId,commandId,"ECONOMY_REWARD_CLAIM",entitlementId.toString(),"{}");
        var response=commands.execute(request,()-> {
            var entitlement=read(playerId,entitlementId);
            boolean paid=Boolean.TRUE.equals(db.queryForObject(
                "SELECT EXISTS(SELECT 1 FROM game.t_economy_reward_ledger WHERE entitlement_id=?)",
                Boolean.class,entitlementId));
            if (!paid) {
                db.update("INSERT INTO game.t_economy_reward_ledger(entitlement_id,player_id,command_id) VALUES (?,?,?)",
                    entitlementId,playerId,commandId);
                db.update("UPDATE game.t_player SET gold=gold+?,updated_at=clock_timestamp() WHERE player_id=?",
                    entitlement.terms().gold(),playerId);
                for (var entry:new TreeMap<>(entitlement.terms().items()).entrySet())
                    grantItem(playerId,entry.getKey(),entry.getValue());
            }
            try {
                return new CommandResponse(200,json.writeValueAsString(new Claim(entitlementId,!paid,entitlement.terms())),1);
            } catch (JsonProcessingException ex) {
                throw new IllegalStateException("Cannot serialize reward receipt",ex);
            }
        });
        try {return json.readValue(response.body(),Claim.class);}
        catch (JsonProcessingException ex) {throw new IllegalStateException("Invalid persisted reward receipt",ex);}
    }

    private RewardEntitlement read(long playerId, UUID id) {
        var rows=db.query("""
            SELECT reward_type,week_start,reward_slot,campaign_id,milestone,policy_version,gold
            FROM game.t_reward_entitlement WHERE player_id=? AND entitlement_id=?
            """,(r,n)-> {
                var date=r.getDate(2);
                var key=new Key(playerId,Type.valueOf(r.getString(1)),date==null?null:date.toLocalDate(),
                    r.getString(3),r.getString(4),r.getObject(5,Long.class));
                return new RewardEntitlement(id,key,new Terms(r.getString(6),r.getLong(7),items(id)));
            },playerId,id);
        return rows.stream().findFirst().orElseThrow(()->new GameFault(404,"REWARD_ENTITLEMENT_NOT_FOUND"));
    }

    private Map<String,Integer> items(UUID id) {
        var items=new TreeMap<String,Integer>();
        db.query("""
            SELECT m.item_code,i.quantity FROM game.t_reward_entitlement_item i
            JOIN game.m_item m USING(item_id) WHERE i.entitlement_id=?
            """,r->{items.put(r.getString(1),r.getInt(2));},id);
        return items;
    }

    private record Item(long id,int maxStack) {}
    private Item item(String code) {
        return db.query("SELECT item_id,max_stack FROM game.m_item WHERE item_code=? AND use_yn FOR SHARE",
            (r,n)->new Item(r.getLong(1),r.getInt(2)),code).stream().findFirst()
            .orElseThrow(()->new GameFault(409,"REWARD_ITEM_UNAVAILABLE"));
    }

    private void grantItem(long player,String code,int quantity) {
        var item=item(code);
        if (quantity>item.maxStack()) throw new GameFault(409,"MAX_STACK_EXCEEDED");
        int changed=db.update("""
            INSERT INTO game.t_inventory(player_id,item_id,quantity) VALUES (?,?,?)
            ON CONFLICT(player_id,item_id) DO UPDATE
              SET quantity=game.t_inventory.quantity+EXCLUDED.quantity,updated_at=clock_timestamp()
              WHERE game.t_inventory.quantity::bigint+EXCLUDED.quantity<=?
            """,player,item.id(),quantity,item.maxStack());
        if (changed!=1) throw new GameFault(409,"MAX_STACK_EXCEEDED");
    }
}
