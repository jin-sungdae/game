package dev.luma.game;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class GameRepository {
    private final JdbcTemplate jdbc;
    public GameRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    public GameDtos.Player lockPlayer(long playerId) {
        var rows = jdbc.query("SELECT player_id,player_name,gold FROM game.t_player WHERE player_id=? FOR UPDATE",
            (r,n)->new GameDtos.Player(r.getLong(1),r.getString(2),r.getLong(3)), playerId);
        if (rows.size()!=1) throw new GameUnavailable("Local player missing");
        return rows.getFirst();
    }
    public GameDtos.Companion activeCompanion(long playerId) {
        var rows = jdbc.query("""
            SELECT c.player_companion_id,s.code,c.evolution_stage,e.name,c.level,c.exp,c.bond
            FROM game.t_player_companion c JOIN game.m_species s USING(species_id)
            JOIN game.m_species_evolution e USING(species_id,evolution_stage)
            WHERE c.player_id=? AND c.active
            """,(r,n)->new GameDtos.Companion(r.getLong(1),r.getString(2),r.getInt(3),r.getString(4),r.getInt(5),r.getLong(6),r.getInt(7)),playerId);
        if(rows.size()!=1) throw new GameUnavailable("Exactly one active companion required");
        return rows.getFirst();
    }
    public Instant now() { return jdbc.queryForObject("SELECT clock_timestamp()",OffsetDateTime.class).toInstant(); }
    public void expire(long playerId, Instant now) {
        var time=OffsetDateTime.ofInstant(now,java.time.ZoneOffset.UTC);
        jdbc.update("""
            UPDATE game.t_encounter e SET status=CASE WHEN EXISTS
              (SELECT 1 FROM game.t_battle b WHERE b.encounter_id=e.encounter_id AND b.status='VICTORY') THEN 'DEFEATED' ELSE 'EXPIRED' END,
              resolved_at=?,updated_at=? WHERE player_id=? AND status='ACTIVE' AND expires_at<=?
              AND NOT EXISTS (SELECT 1 FROM game.t_battle b WHERE b.encounter_id=e.encounter_id AND b.status='ACTIVE')
            """,time,time,playerId,time);
    }
    public Optional<GameDtos.Encounter> active(long playerId) {
        var rows=jdbc.query("""
            SELECT e.encounter_id,m.code,m.name,e.monster_level,e.rarity,m.movement_profile,e.spawned_at,e.expires_at,b.battle_id,COALESCE(b.status='ACTIVE',false)
            FROM game.t_encounter e JOIN game.m_monster m USING(monster_id) LEFT JOIN game.t_battle b ON b.encounter_id=e.encounter_id
            WHERE e.player_id=? AND e.status='ACTIVE'
            """,(r,n)->new GameDtos.Encounter(r.getObject(1,UUID.class),
                new GameDtos.Monster(r.getString(2),r.getString(3),r.getInt(4),r.getString(5),r.getString(6)),
                r.getObject(7,OffsetDateTime.class).toInstant(),r.getObject(8,OffsetDateTime.class).toInstant(),r.getObject(9,UUID.class),r.getBoolean(10)),playerId);
        if(rows.size()>1) throw new GameUnavailable("Multiple active encounters");
        return rows.stream().findFirst();
    }
    public List<MonsterSelector.Monster> monsters() {
        return jdbc.query("SELECT monster_id,code,name,rarity,movement_profile,min_level,max_level,encounter_weight FROM game.m_monster WHERE use_yn AND encounter_weight>0 ORDER BY monster_id",
            (r,n)->new MonsterSelector.Monster(r.getLong(1),r.getString(2),r.getString(3),r.getString(4),r.getString(5),r.getInt(6),r.getInt(7),r.getInt(8)));
    }
    public GameDtos.Encounter create(long playerId, MonsterSelector.Selection selection, Instant now) {
        var m=selection.monster(); var id=UUID.randomUUID(); var expires=now.plusSeconds(60);
        jdbc.update("""
            INSERT INTO game.t_encounter(encounter_id,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at,created_at,updated_at)
            VALUES (?,?,?,?,?,'ACTIVE',?,?,?,?)
            """,id,playerId,m.id(),selection.level(),m.rarity(),
            OffsetDateTime.ofInstant(now,java.time.ZoneOffset.UTC),OffsetDateTime.ofInstant(expires,java.time.ZoneOffset.UTC),
            OffsetDateTime.ofInstant(now,java.time.ZoneOffset.UTC),OffsetDateTime.ofInstant(now,java.time.ZoneOffset.UTC));
        return new GameDtos.Encounter(id,new GameDtos.Monster(m.code(),m.name(),selection.level(),m.rarity(),m.movementProfile()),now,expires,null,false);
    }
}
