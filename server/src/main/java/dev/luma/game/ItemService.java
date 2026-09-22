package dev.luma.game;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.*;
import java.time.OffsetDateTime;

@Service
@Transactional
public class ItemService {
    private final JdbcTemplate db;
    private final GameRepository game;
    private final EvolutionRepository companions;
    public ItemService(JdbcTemplate db,GameRepository game,EvolutionRepository companions) {this.db=db;this.game=game;this.companions=companions;}
    record Item(long id,String code,String type,long price,int maxStack,boolean enabled) {}
    record Battle(UUID id,int hp,int maxHp,String status,String encounterStatus) {}
    private Item item(String code) {
        var item=db.query("SELECT item_id,item_code,item_type,price,max_stack,use_yn FROM game.m_item WHERE item_code=? FOR SHARE",
            (r,n)->new Item(r.getLong(1),r.getString(2),r.getString(3),r.getLong(4),r.getInt(5),r.getBoolean(6)),code)
            .stream().findFirst().orElseThrow(()->new GameFault(404,"ITEM_NOT_FOUND"));
        if(!item.enabled) throw new GameFault(409,"ITEM_DISABLED");
        return item;
    }
    private int inventory(Item i) {
        return db.query("SELECT quantity FROM game.t_inventory WHERE player_id=1 AND item_id=? FOR UPDATE",(r,n)->r.getInt(1),i.id)
            .stream().findFirst().orElse(0);
    }
    private Battle battle(UUID id) {
        if(id==null) throw new GameFault(400,"ITEM_NOT_USABLE");
        var ids=db.query("SELECT e.encounter_id FROM game.t_battle b JOIN game.t_encounter e USING(encounter_id) WHERE b.battle_id=? AND e.player_id=1",(r,n)->r.getObject(1,UUID.class),id);
        if(ids.isEmpty()) throw new GameFault(404,"BATTLE_NOT_FOUND");
        String encounter=db.queryForObject("SELECT status FROM game.t_encounter WHERE encounter_id=? FOR UPDATE",String.class,ids.getFirst());
        return db.query("SELECT battle_id,companion_hp,companion_max_hp,status FROM game.t_battle WHERE battle_id=? FOR UPDATE",
            (r,n)->new Battle(r.getObject(1,UUID.class),r.getInt(2),r.getInt(3),r.getString(4),encounter),id).getFirst();
    }
    public List<ItemDtos.ShopItem> shop() {
        game.lockPlayer(1);
        return db.query("""
            SELECT m.item_code,m.item_name,m.item_type,m.price,COALESCE(i.quantity,0),m.max_stack
            FROM game.m_item m LEFT JOIN game.t_inventory i ON i.item_id=m.item_id AND i.player_id=1
            WHERE m.use_yn ORDER BY m.item_code
            """,(r,n)->new ItemDtos.ShopItem(r.getString(1),r.getString(2),r.getString(3),r.getLong(4),r.getInt(5),r.getInt(6)));
    }
    public List<ItemDtos.Owned> inventory() {
        game.lockPlayer(1);
        return db.query("""
            SELECT m.item_code,m.item_name,m.item_type,i.quantity FROM game.t_inventory i JOIN game.m_item m USING(item_id)
            WHERE i.player_id=1 ORDER BY m.item_code
            """,(r,n)->new ItemDtos.Owned(r.getString(1),r.getString(2),r.getString(3),r.getInt(4)));
    }
    public ItemDtos.Purchase purchase(ItemDtos.PurchaseRequest request) {
        var player=game.lockPlayer(1);
        if(request==null || request.itemCode()==null || request.quantity()==null) throw new GameFault(400,"INVALID_QUANTITY");
        var item=item(request.itemCode());int owned=inventory(item);
        long total=ItemRules.total(item.price,request.quantity());
        if(player.gold()<total) throw new GameFault(409,"INSUFFICIENT_GOLD");
        long next=(long)owned+request.quantity();
        if(next>item.maxStack) throw new GameFault(409,"MAX_STACK_EXCEEDED");
        db.update("UPDATE game.t_player SET gold=gold-?,updated_at=clock_timestamp() WHERE player_id=1",total);
        db.update("""
            INSERT INTO game.t_inventory(player_id,item_id,quantity) VALUES(1,?,?)
            ON CONFLICT(player_id,item_id) DO UPDATE SET quantity=EXCLUDED.quantity,updated_at=clock_timestamp()
            """,item.id,(int)next);
        var id=UUID.randomUUID();
        db.update("INSERT INTO game.t_item_purchase(purchase_id,player_id,item_id,quantity,unit_price,total_price) VALUES(?,1,?,?,?,?)",
            id,item.id,request.quantity(),item.price,total);
        return new ItemDtos.Purchase(id,item.code,request.quantity(),item.price,total,player.gold()-total,(int)next);
    }
    public ItemDtos.Use use(String code,UUID battleId) {
        game.lockPlayer(1);
        Battle b=null;GameDtos.Companion companion=null;
        if("BOND_BERRY".equals(code)) {
            if(battleId!=null) throw new GameFault(400,"ITEM_NOT_USABLE");
            boolean active=Boolean.TRUE.equals(db.queryForObject("""
                SELECT EXISTS(SELECT 1 FROM game.t_battle b JOIN game.t_encounter e USING(encounter_id)
                WHERE e.player_id=1 AND b.status='ACTIVE')
                """,Boolean.class));
            if(active) throw new GameFault(409,"ITEM_NOT_USABLE");
            companion=companions.lockActive(1);
        } else if(List.of("SMALL_POTION","CAPTURE_CHARM").contains(code)) {
            b=battle(battleId);
            if(!b.status.equals("ACTIVE") || !b.encounterStatus.equals("ACTIVE")) throw new GameFault(409,"INVALID_BATTLE_STATE");
        }
        var item=item(code);int owned=inventory(item);
        if(owned<=0) throw new GameFault(409,"ITEM_NOT_OWNED");
        Integer heal=null,hp=null,max=null,before=null,after=null;Boolean armed=null;Double bonus=null;
        switch(code) {
            case "SMALL_POTION" -> {
                if(b.hp==b.maxHp) throw new GameFault(409,"FULL_HP");
                heal=Math.min(ItemRules.POTION_HEAL,b.maxHp-b.hp);hp=b.hp+heal;max=b.maxHp;
                db.update("UPDATE game.t_battle SET companion_hp=?,updated_at=clock_timestamp() WHERE battle_id=?",hp,b.id);
            }
            case "BOND_BERRY" -> {
                before=companion.bond();
                if(before>Integer.MAX_VALUE-ItemRules.BERRY_BOND) throw new GameFault(409,"ITEM_NOT_USABLE");
                after=before+ItemRules.BERRY_BOND;
                db.update("UPDATE game.t_player_companion SET bond=?,updated_at=clock_timestamp() WHERE player_companion_id=?",after,companion.playerCompanionId());
            }
            case "CAPTURE_CHARM" -> {
                int changed=db.update("""
                    INSERT INTO game.t_battle_item_effect(battle_id,effect_type,value) VALUES(?,'CAPTURE_BONUS',?)
                    ON CONFLICT(battle_id,effect_type) DO UPDATE SET value=EXCLUDED.value,consumed_at=NULL,created_at=clock_timestamp()
                    WHERE game.t_battle_item_effect.consumed_at IS NOT NULL
                    """,b.id,ItemRules.CHARM_BONUS);
                if(changed!=1) throw new GameFault(409,"EFFECT_ALREADY_ACTIVE");
                armed=true;bonus=ItemRules.CHARM_BONUS;
            }
            default -> throw new GameFault(409,"ITEM_NOT_USABLE");
        }
        db.update("UPDATE game.t_inventory SET quantity=quantity-1,updated_at=clock_timestamp() WHERE player_id=1 AND item_id=?",item.id);
        return new ItemDtos.Use(code,owned-1,heal,hp,max,before,after,armed,bonus,battleId);
    }
    public List<ItemDtos.Effect> effects(UUID id) {
        game.lockPlayer(1);battle(id); // Ownership and a consistent snapshot, also for terminal battles.
        return db.query("SELECT battle_id,effect_type,value,consumed_at FROM game.t_battle_item_effect WHERE battle_id=? ORDER BY effect_type",
            (r,n)->{var consumed=r.getObject(4,OffsetDateTime.class);return new ItemDtos.Effect(r.getObject(1,UUID.class),r.getString(2),r.getDouble(3),consumed==null,consumed==null?null:consumed.toInstant());},id);
    }
}
