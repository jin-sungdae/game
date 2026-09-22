package dev.luma.game;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.*;
import java.time.OffsetDateTime;

@Service
@Transactional(noRollbackFor=GameFault.class)
public class BattleService {
    private final JdbcTemplate db;
    private final GameRepository game;
    private final RandomSource random;
    public BattleService(JdbcTemplate db,GameRepository game,RandomSource random) {this.db=db;this.game=game;this.random=random;}
    record Encounter(UUID id,long monsterId,int level,String rarity,String status,String code,String name) {}
    record Row(UUID id,UUID encounter,long companionId,int hp,int maxHp,int monsterHp,int monsterMax,int attack,int counter,int turn,String status) {}
    private void playerLock() {game.lockPlayer(1);game.expire(1,game.now());}
    private Encounter encounter(UUID id) {
        return db.query("""
            SELECT e.encounter_id,e.monster_id,e.monster_level,e.rarity,e.status,m.code,m.name
            FROM game.t_encounter e JOIN game.m_monster m USING(monster_id)
            WHERE e.encounter_id=? AND e.player_id=1 FOR UPDATE OF e
            """,(r,n)->new Encounter(r.getObject(1,UUID.class),r.getLong(2),r.getInt(3),r.getString(4),r.getString(5),r.getString(6),r.getString(7)),id)
            .stream().findFirst().orElseThrow(()->new GameFault(404,"ENCOUNTER_NOT_FOUND"));
    }
    private Row row(UUID id) {
        return db.query("SELECT * FROM game.t_battle WHERE battle_id=? FOR UPDATE",(r,n)->new Row(
            r.getObject("battle_id",UUID.class),r.getObject("encounter_id",UUID.class),r.getLong("player_companion_id"),
            r.getInt("companion_hp"),r.getInt("companion_max_hp"),r.getInt("monster_hp"),r.getInt("monster_max_hp"),
            r.getInt("companion_attack"),r.getInt("monster_attack"),r.getInt("turn_no"),r.getString("status")),id)
            .stream().findFirst().orElseThrow(()->new GameFault(404,"BATTLE_NOT_FOUND"));
    }
    private Encounter lockBattleEncounter(UUID battleId) {
        playerLock();
        var ids=db.query("SELECT encounter_id FROM game.t_battle WHERE battle_id=?",(r,n)->r.getObject(1,UUID.class),battleId);
        if(ids.isEmpty()) throw new GameFault(404,"BATTLE_NOT_FOUND");
        return encounter(ids.getFirst());
    }
    private void active(Encounter e) {
        if(!e.status.equals("ACTIVE")) throw new GameFault(409,e.status.equals("EXPIRED")?"ENCOUNTER_EXPIRED":"INVALID_STATE");
    }
    private BattleDtos.Battle dto(Row b,List<String> events) {return dto(b,events,List.of());}
    private BattleDtos.Battle dto(Row b,List<String> events,List<BattleDtos.PresentationEvent> presentation) {
        var rewards=db.query("SELECT gold_reward,exp_reward,bond_reward FROM game.t_reward WHERE encounter_id=?",
            (r,n)->new BattleDtos.Reward(r.getLong(1),r.getLong(2),r.getInt(3)),b.encounter);
        String status=db.queryForObject("SELECT status FROM game.t_encounter WHERE encounter_id=?",String.class,b.encounter);
        return new BattleDtos.Battle(b.id,b.encounter,b.turn,b.status,status,new BattleDtos.Hp(b.hp,b.maxHp),
            new BattleDtos.Hp(b.monsterHp,b.monsterMax),events,rewards.isEmpty()?null:rewards.getFirst(),presentation);
    }
    public BattleDtos.Battle start(UUID id) {
        playerLock();var e=encounter(id);
        var ids=db.query("SELECT battle_id FROM game.t_battle WHERE encounter_id=?",(r,n)->r.getObject(1,UUID.class),id);
        if(!ids.isEmpty()) return dto(row(ids.getFirst()),List.of());
        active(e);var c=game.activeCompanion(1);var battle=UUID.randomUUID();
        db.update("""
            INSERT INTO game.t_battle(battle_id,encounter_id,player_companion_id,monster_id,companion_hp,companion_max_hp,
             monster_hp,monster_max_hp,companion_attack,monster_attack,status) VALUES(?,?,?,?,?,?,?,?,?,?,'ACTIVE')
            """,battle,id,c.playerCompanionId(),e.monsterId,CombatRules.companionHp(),CombatRules.companionHp(),
            CombatRules.monsterHp(e.level),CombatRules.monsterHp(e.level),CombatRules.companionAttack(c.level()),CombatRules.monsterAttack(e.level));
        return dto(row(battle),List.of());
    }
    public BattleDtos.Battle get(UUID id) {lockBattleEncounter(id);return dto(row(id),List.of());}
    private void save(Row b,int hp,int monsterHp,String status) {
        db.update("""
            UPDATE game.t_battle SET companion_hp=?,monster_hp=?,turn_no=turn_no+1,status=?,
            ended_at=CASE WHEN ?='ACTIVE' THEN NULL ELSE COALESCE(ended_at,clock_timestamp()) END,updated_at=clock_timestamp() WHERE battle_id=?
            """,hp,monsterHp,status,status,b.id);
    }
    private void resolve(UUID id,String status) {
        db.update("UPDATE game.t_encounter SET status=?,resolved_at=clock_timestamp(),updated_at=clock_timestamp() WHERE encounter_id=?",status,id);
    }
    private void reward(Row b,Encounter e,List<String> events) {
        db.update("INSERT INTO game.t_reward(reward_id,encounter_id,player_id,gold_reward,exp_reward,bond_reward) VALUES(?,?,1,?,?,1)",UUID.randomUUID(),e.id,CombatRules.gold(e.level),CombatRules.exp(e.level));
        db.update("UPDATE game.t_player SET gold=gold+?,updated_at=clock_timestamp() WHERE player_id=1",CombatRules.gold(e.level));
        long oldExp=db.queryForObject("SELECT exp FROM game.t_player_companion WHERE player_companion_id=?",Long.class,b.companionId);
        long exp=Math.addExact(oldExp,CombatRules.exp(e.level));int level=CombatRules.level(exp);
        db.update("UPDATE game.t_player_companion SET exp=?,level=?,bond=bond+1,updated_at=clock_timestamp() WHERE player_companion_id=?",exp,level,b.companionId);
        events.add("REWARD");if(level>CombatRules.level(oldExp)) events.add("LEVEL_UP");
    }
    private int counter(Row b,Encounter e,List<String> events) {
        var personality=MonsterContent.find(e.code).map(MonsterContent.Definition::battlePersonality)
            .orElseThrow(()->new GameUnavailable("Missing battle personality"));
        if(BattleDecision.choose(personality,b.turn,random)==BattleDecision.Action.WAIT) {
            events.add("MONSTER_WAIT");return b.hp;
        }
        events.add("MONSTER_ATTACK");return Math.max(0,b.hp-b.counter);
    }
    public BattleDtos.Battle attack(UUID id) {
        var e=lockBattleEncounter(id);var b=row(id);
        if(!b.status.equals("ACTIVE")) throw new GameFault(409,"BATTLE_ALREADY_TERMINAL");active(e);
        int monster=Math.max(0,b.monsterHp-b.attack),hp=b.hp;String status="ACTIVE";var events=new ArrayList<String>();events.add("PLAYER_ATTACK");
        if(monster==0) {
            status="VICTORY";events.add("VICTORY");reward(b,e,events);
            db.update("UPDATE game.t_encounter SET expires_at=clock_timestamp()+interval '60 seconds',updated_at=clock_timestamp() WHERE encounter_id=?",e.id);
        } else {hp=counter(b,e,events);if(hp==0) {status="DEFEAT";events.add("DEFEAT");resolve(e.id,"PLAYER_DEFEATED");}}
        save(b,hp,monster,status);
        var presentation=new ArrayList<BattleDtos.PresentationEvent>();
        presentation.add(new BattleDtos.PresentationEvent("PLAYER_ATTACK",b.monsterHp-monster));
        if(events.contains("MONSTER_ATTACK")) presentation.add(new BattleDtos.PresentationEvent("MONSTER_ATTACK",b.hp-hp));
        return dto(row(id),events,presentation);
    }
    public BattleDtos.Capture capture(UUID id) {
        var e=lockBattleEncounter(id);var b=row(id);
        if(!e.status.equals("ACTIVE")) throw new GameFault(409,"CAPTURE_ALREADY_RESOLVED");
        if(!List.of("ACTIVE","VICTORY").contains(b.status)) throw new GameFault(409,"BATTLE_ALREADY_TERMINAL");
        double baseChance=CombatRules.captureChance(b.monsterHp,b.monsterMax,e.rarity);
        var bonuses=db.query("SELECT value FROM game.t_battle_item_effect WHERE battle_id=? AND effect_type='CAPTURE_BONUS' AND consumed_at IS NULL FOR UPDATE",(r,n)->r.getDouble(1),id);
        double itemBonus=bonuses.isEmpty()?0:bonuses.getFirst();
        double chance=ItemRules.captureChance(baseChance,itemBonus);
        long roll=random.nextLong(1_000_000);if(roll<0||roll>=1_000_000) throw new GameUnavailable("Invalid random source");
        if(itemBonus>0) db.update("UPDATE game.t_battle_item_effect SET consumed_at=clock_timestamp() WHERE battle_id=? AND effect_type='CAPTURE_BONUS' AND consumed_at IS NULL",id);
        boolean success=roll<Math.round(chance*1_000_000);var events=new ArrayList<String>();
        BattleDtos.Collected collection=null;
        if(success) {
            db.update("""
                INSERT INTO game.t_collection(player_id,monster_id,first_captured_at,last_captured_at,capture_count)
                VALUES(1,?,clock_timestamp(),clock_timestamp(),1) ON CONFLICT(player_id,monster_id)
                DO UPDATE SET capture_count=game.t_collection.capture_count+1,last_captured_at=clock_timestamp(),updated_at=clock_timestamp()
                """,e.monsterId);
            resolve(e.id,"CAPTURED");save(b,b.hp,b.monsterHp,b.status.equals("VICTORY")?"VICTORY":"CAPTURED");
            collection=collection().stream().filter(c->c.monsterCode().equals(e.code)).findFirst().orElseThrow();
        } else if(b.status.equals("VICTORY")) {resolve(e.id,"DEFEATED");}
        else {
            int hp=counter(b,e,events);
            if(hp==0) {events.add("DEFEAT");resolve(e.id,"PLAYER_DEFEATED");}
            save(b,hp,b.monsterHp,hp==0?"DEFEAT":"ACTIVE");
        }
        var current=row(id);
        var presentation=events.contains("MONSTER_ATTACK")?List.of(new BattleDtos.PresentationEvent("MONSTER_ATTACK",b.hp-current.hp)):List.<BattleDtos.PresentationEvent>of();
        var result=dto(current,events,presentation);
        return new BattleDtos.Capture(id,e.id,success,chance,new BattleDtos.Monster(e.code,e.name),result.status(),result.encounterStatus(),collection,result,baseChance,itemBonus,chance);
    }
    public BattleDtos.Resolution ignore(UUID id) {
        playerLock();var e=encounter(id);active(e);resolve(id,"ESCAPED");
        db.update("UPDATE game.t_battle SET status='ESCAPED',ended_at=clock_timestamp(),updated_at=clock_timestamp() WHERE encounter_id=? AND status='ACTIVE'",id);
        return new BattleDtos.Resolution(id,"ESCAPED");
    }
    @Transactional(readOnly=true)
    public List<BattleDtos.Collected> collection() {
        return db.query("""
            SELECT m.code,m.name,c.capture_count,c.first_captured_at,c.last_captured_at FROM game.t_collection c
            JOIN game.m_monster m USING(monster_id) WHERE c.player_id=1 ORDER BY c.first_captured_at,m.code
            """,(r,n)->new BattleDtos.Collected(r.getString(1),r.getString(2),r.getLong(3),r.getObject(4,OffsetDateTime.class).toInstant(),r.getObject(5,OffsetDateTime.class).toInstant()));
    }
}
