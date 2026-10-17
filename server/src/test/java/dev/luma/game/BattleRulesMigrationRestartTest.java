package dev.luma.game;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import java.sql.DriverManager;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

/** Real V10 -> latest migration and two Spring lifetimes in a disposable database. */
class BattleRulesMigrationRestartTest {
    Map<String,String> snapshot(JdbcTemplate db) {
        var state=new LinkedHashMap<String,String>();
        for(String t:List.of("t_battle","t_encounter","t_reward","t_player","t_player_companion")) {
            String value=t.equals("t_battle")?"to_jsonb(t)-'rules_version'":"to_jsonb(t)";
            state.put(t,db.queryForObject("SELECT COALESCE(jsonb_agg("+value+" ORDER BY ("+value+")::text),'[]'::jsonb)::text FROM game."+t+" t",String.class));
        }
        return state;
    }
    ConfigurableApplicationContext start(String url,String user,String password) {
        return new SpringApplicationBuilder(GameApplication.class).run("--server.port=0",
            "--spring.datasource.url="+url,"--spring.datasource.username="+user,"--spring.datasource.password="+password);
    }
    @ParameterizedTest @ValueSource(strings={"ACTIVE","VICTORY"})
    void migrationAndRestartPreserveStoredBattleAndCaptureWindow(String status) throws Exception {
        String source=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!source.matches("jdbc:postgresql://[^/]+/[^/?]+_test"))
            throw new IllegalStateException("Dedicated test database URL required");
        String user=System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma");
        String password=System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD","");
        String name="luma_rules_"+UUID.randomUUID().toString().replace("-","")+"_test";
        String url=source.substring(0,source.lastIndexOf('/')+1)+name;
        try(var admin=DriverManager.getConnection(source,user,password);var statement=admin.createStatement()) {
            statement.execute("CREATE DATABASE "+name);
            try {
                var config=Flyway.configure().dataSource(url,user,password).schemas("game").defaultSchema("game");
                config.target("10").load().migrate();
                var db=new JdbcTemplate(new DriverManagerDataSource(url,user,password));
                UUID encounter=UUID.randomUUID(),battle=UUID.randomUUID();
                db.update("INSERT INTO game.t_encounter(encounter_id,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at) SELECT ?,1,monster_id,2,'COMMON','ACTIVE',clock_timestamp(),clock_timestamp()+interval '60 seconds' FROM game.m_monster WHERE code='PIP'",encounter);
                db.update("INSERT INTO game.t_battle(battle_id,encounter_id,player_companion_id,monster_id,companion_hp,companion_max_hp,monster_hp,monster_max_hp,companion_attack,monster_attack,turn_no,status,ended_at) SELECT ?,?,c.player_companion_id,m.monster_id,73,100,?,40,12,7,3,?,CASE WHEN ?='ACTIVE' THEN NULL ELSE clock_timestamp() END FROM game.t_player_companion c CROSS JOIN game.m_monster m WHERE c.active AND m.code='PIP'",battle,encounter,status.equals("ACTIVE")?16:0,status,status);
                if(status.equals("VICTORY"))
                    db.update("INSERT INTO game.t_reward(reward_id,encounter_id,player_id,gold_reward,exp_reward,bond_reward) VALUES(?,?,1,20,40,0)",UUID.randomUUID(),encounter);
                var before=snapshot(db);
                Flyway.configure().dataSource(url,user,password).schemas("game").defaultSchema("game").load().migrate();
                assertEquals(before,snapshot(db));
                assertEquals("ALPHA_V1",db.queryForObject("SELECT rules_version FROM game.t_battle WHERE battle_id=?",String.class,battle));
                for(int restart=0;restart<2;restart++) {
                    try(var app=start(url,user,password)) {
                        var result=app.getBean(BattleService.class).get(battle);
                        assertEquals(status,result.status());assertEquals("ACTIVE",result.encounterStatus());
                        assertEquals(73,result.companion().hp());assertEquals(3,result.turn());
                        assertEquals(status.equals("ACTIVE")?16:0,result.monster().hp());
                        assertEquals(before,snapshot(db));
                        assertEquals("ALPHA_V1",db.queryForObject("SELECT rules_version FROM game.t_battle WHERE battle_id=?",String.class,battle));
                        if(restart==1) {
                            if(status.equals("ACTIVE")) {
                                var next=app.getBean(BattleService.class).attack(battle);
                                assertEquals(4,next.monster().hp());assertEquals(4,next.turn());
                            } else {
                                var captured=app.getBean(BattleService.class).capture(battle);
                                assertEquals(.85,captured.chance(),1e-12);
                                assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
                            }
                        }
                    }
                }
            } finally {
                statement.execute("DROP DATABASE "+name);
            }
        }
    }
}
