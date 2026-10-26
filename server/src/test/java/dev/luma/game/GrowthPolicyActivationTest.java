package dev.luma.game;

import java.sql.DriverManager;
import java.util.*;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import static org.junit.jupiter.api.Assertions.*;

class GrowthPolicyActivationTest {
    interface Work { void run(String url,String user,String password,JdbcTemplate db) throws Exception; }
    void database(Work work) throws Exception {
        String source=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!source.matches("jdbc:postgresql://[^/]+/[^/?]+_test"))throw new IllegalStateException("Dedicated test DB required");
        String user=System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"),password=System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD","");
        String name="growth_"+UUID.randomUUID().toString().replace("-","")+"_test";
        String url=source.substring(0,source.lastIndexOf('/')+1)+name;
        try(var admin=DriverManager.getConnection(source,user,password);var statement=admin.createStatement()) {
            statement.execute("CREATE DATABASE "+name);
            try {work.run(url,user,password,new JdbcTemplate(new DriverManagerDataSource(url,user,password)));}
            finally {statement.execute("DROP DATABASE "+name+" WITH (FORCE)");}
        }
    }
    void migrate(String url,String user,String password,String target) {
        var config=Flyway.configure().dataSource(url,user,password).schemas("game").defaultSchema("game");
        if(target!=null)config.target(target);
        config.load().migrate();
    }
    ConfigurableApplicationContext start(String url,String user,String password) {
        return new SpringApplicationBuilder(GameApplication.class).run("--server.port=0","--spring.datasource.url="+url,
            "--spring.datasource.username="+user,"--spring.datasource.password="+password);
    }
    String unchanged(JdbcTemplate db,String table) {
        String projection=table.equals("t_player_companion")?"to_jsonb(t)-'level'-'growth_policy_version'":"to_jsonb(t)";
        return db.queryForObject("SELECT COALESCE(jsonb_agg("+projection+" ORDER BY ("+projection+")::text),'[]'::jsonb)::text FROM game."+table+" t",String.class);
    }
    @Test void migrationRehearsalPreservesExpHistoryBattleAndRestartState() throws Exception {
        database((url,user,password,db)->{
            migrate(url,user,password,"15");
            db.update("UPDATE game.t_player_companion SET level=20,exp=88900,bond=80,evolution_stage=2,last_bond_interaction_at=clock_timestamp()");
            db.update("UPDATE game.t_player SET gold=147");
            db.update("INSERT INTO game.t_companion_evolution_history(player_companion_id,species_id,from_stage,to_stage,level_at_evolution,bond_at_evolution) SELECT player_companion_id,species_id,1,2,3,5 FROM game.t_player_companion");
            UUID encounter=UUID.randomUUID(),battle=UUID.randomUUID();
            db.update("INSERT INTO game.t_encounter(encounter_id,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at) SELECT ?,1,monster_id,1,'COMMON','ACTIVE',clock_timestamp(),clock_timestamp()+interval '60 seconds' FROM game.m_monster WHERE code='PIP'",encounter);
            db.update("INSERT INTO game.t_battle(battle_id,encounter_id,player_companion_id,monster_id,companion_hp,companion_max_hp,monster_hp,monster_max_hp,companion_attack,monster_attack,status,rules_version) SELECT ?,?,c.player_companion_id,m.monster_id,73,100,30,30,50,5,'ACTIVE','ALPHA_V1' FROM game.t_player_companion c CROSS JOIN game.m_monster m WHERE c.active AND m.code='PIP'",battle,encounter);
            var tables=List.of("t_player_companion","t_player","t_companion_evolution_history","t_battle","t_battle_skill_state","t_reward","t_collection","t_inventory");
            var before=new LinkedHashMap<String,String>();for(String table:tables)before.put(table,unchanged(db,table));
            migrate(url,user,password,null);
            for(String table:tables)assertEquals(before.get(table),unchanged(db,table),table);
            assertEquals(100,db.queryForObject("SELECT level FROM game.t_player_companion WHERE active",Integer.class));
            assertEquals("GROWTH_B_V2",db.queryForObject("SELECT growth_policy_version FROM game.t_player_companion WHERE active",String.class));
            for(int level=1;level<=100;level++) {
                long exp=GrowthCurveB.threshold(level);
                assertEquals(level,db.queryForObject("SELECT game.growth_b_level_v2(?)",Integer.class,exp));
                if(level>1)assertEquals(level-1,db.queryForObject("SELECT game.growth_b_level_v2(?)",Integer.class,exp-1));
            }
            assertEquals(100,db.queryForObject("SELECT game.growth_b_level_v2(?)",Integer.class,Long.MAX_VALUE));
            assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("UPDATE game.t_player_companion SET level=?",CombatRules.level(88900)));
            assertEquals(100,db.queryForObject("SELECT level FROM game.t_player_companion WHERE active",Integer.class));
            for(int restart=0;restart<2;restart++)try(var app=start(url,user,password)) {
                assertEquals(88900,app.getBean(GameService.class).bootstrap().activeCompanion().exp());
                assertEquals(100,app.getBean(GameService.class).bootstrap().activeCompanion().level());
                var current=app.getBean(BattleService.class).get(battle);
                assertEquals(73,current.companion().hp());assertEquals(0,current.turn());assertTrue(current.skills().isEmpty());
                assertThrows(GameFault.class,()->app.getBean(SkillCommandService.class).execute(battle,new SkillCommandService.Request(UUID.randomUUID(),"MOA_S1",0)));
                for(String table:tables)assertEquals(before.get(table),unchanged(db,table),table);
            }
        });
    }
    @Test void invalidLegacySaveAbortsWithoutPartialMigrationOrRepair() throws Exception {
        database((url,user,password,db)->{
            migrate(url,user,password,"15");
            db.update("UPDATE game.t_player_companion SET level=6,exp=0,bond=7");
            String before=unchanged(db,"t_player_companion");
            assertThrows(org.flywaydb.core.api.FlywayException.class,()->migrate(url,user,password,null));
            assertEquals(before,unchanged(db,"t_player_companion"));
            assertEquals(6,db.queryForObject("SELECT level FROM game.t_player_companion WHERE active",Integer.class));
            assertEquals(0,db.queryForObject("SELECT count(*) FROM information_schema.columns WHERE table_schema='game' AND table_name='t_player_companion' AND column_name='growth_policy_version'",Integer.class));
            assertEquals(0,db.queryForObject("SELECT count(*) FROM game.flyway_schema_history WHERE version='16'",Integer.class));
        });
    }
    @Test void rewardCrossesLevel100OnceAndBattleSkillSnapshotStaysAtStart() throws Exception {
        database((url,user,password,db)->{
            migrate(url,user,password,null);
            try(var app=start(url,user,password)) {
                db.update("UPDATE game.t_player_companion SET level=99,exp=88890");
                var game=app.getBean(GameService.class);var battles=app.getBean(BattleService.class);var states=app.getBean(SkillStateStore.class);
                UUID encounter=UUID.randomUUID();
                db.update("INSERT INTO game.t_encounter(encounter_id,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at) SELECT ?,1,monster_id,1,'COMMON','ACTIVE',clock_timestamp(),clock_timestamp()+interval '60 seconds' FROM game.m_monster WHERE code='PIP'",encounter);
                var battle=battles.start(encounter);
                assertEquals(99,states.load(battle.battleId()).level);assertEquals(1,states.load(battle.battleId()).stage);
                var won=battles.attack(battle.battleId());assertEquals("VICTORY",won.status());
                assertEquals(88910,game.bootstrap().activeCompanion().exp());assertEquals(100,game.bootstrap().activeCompanion().level());
                assertTrue(won.events().contains("LEVEL_UP"));assertEquals(99,states.load(battle.battleId()).level);
                assertThrows(GameFault.class,()->battles.attack(battle.battleId()));
                assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
                assertEquals(88910,game.bootstrap().activeCompanion().exp());
            }
        });
    }
}
