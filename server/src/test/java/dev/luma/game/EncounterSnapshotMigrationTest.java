package dev.luma.game;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import java.sql.DriverManager;
import java.util.UUID;
import static org.junit.jupiter.api.Assertions.*;

class EncounterSnapshotMigrationTest {
    @Test void v18UpgradePreservesFutureBattleVersionAndRemainsClosedAfterRestart() throws Exception {
        String source=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!source.matches("jdbc:postgresql://[^/]+/[^/?]+_test"))throw new IllegalStateException("Dedicated test DB required");
        String user=System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"),password=System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD","");
        String name="luma_encounter_"+UUID.randomUUID().toString().replace("-","")+"_test";
        String url=source.substring(0,source.lastIndexOf('/')+1)+name;
        try(var admin=DriverManager.getConnection(source,user,password);var statement=admin.createStatement()) {
            statement.execute("CREATE DATABASE "+name);
            try {
                Flyway.configure().dataSource(url,user,password).schemas("game").defaultSchema("game").target("18").load().migrate();
                var db=new JdbcTemplate(new DriverManagerDataSource(url,user,password));
                UUID encounter=UUID.randomUUID(),battle=UUID.randomUUID();
                db.update("INSERT INTO game.t_encounter(encounter_id,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at) SELECT ?,1,monster_id,2,'COMMON','ACTIVE',clock_timestamp(),clock_timestamp()+interval '60 seconds' FROM game.m_monster WHERE code='PIP'",encounter);
                db.update("""
                    INSERT INTO game.t_battle(battle_id,encounter_id,player_companion_id,monster_id,
                    companion_hp,companion_max_hp,monster_hp,monster_max_hp,companion_attack,monster_attack,status,rules_version)
                    SELECT ?,?,c.player_companion_id,m.monster_id,73,100,16,40,12,7,'ACTIVE','EXPANDED_V2'
                    FROM game.t_player_companion c CROSS JOIN game.m_monster m WHERE c.active AND m.code='PIP'
                    """,battle,encounter);
                String before=db.queryForObject("SELECT to_jsonb(b)::text FROM game.t_battle b WHERE battle_id=?",String.class,battle);
                Flyway.configure().dataSource(url,user,password).schemas("game").defaultSchema("game").load().migrate();
                for(int restart=0;restart<2;restart++) {
                    try(var app=new BattleRulesMigrationRestartTest().start(url,user,password)) {
                        assertEquals(before,db.queryForObject("SELECT to_jsonb(b)::text FROM game.t_battle b WHERE battle_id=?",String.class,battle));
                        assertEquals("EXPANDED_V2",db.queryForObject("SELECT rules_version FROM game.t_encounter WHERE encounter_id=?",String.class,encounter));
                        assertNull(db.queryForObject("SELECT spawn_tier FROM game.t_encounter WHERE encounter_id=?",Integer.class,encounter));
                        assertEquals(2,db.queryForObject("SELECT monster_level FROM game.t_encounter WHERE encounter_id=?",Integer.class,encounter));
                        assertThrows(GameUnavailable.class,()->app.getBean(GameService.class).activeEncounter());
                        assertThrows(GameUnavailable.class,()->app.getBean(BattleService.class).start(encounter));
                    }
                }
            } finally {statement.execute("DROP DATABASE "+name);}
        }
    }
}
