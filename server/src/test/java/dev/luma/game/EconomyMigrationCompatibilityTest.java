package dev.luma.game;

import java.util.*;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.test.context.*;
import org.springframework.test.annotation.DirtiesContext;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(properties="spring.datasource.hikari.maximum-pool-size=2")
@DirtiesContext(classMode=DirtiesContext.ClassMode.AFTER_CLASS)
class EconomyMigrationCompatibilityTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate existing;
    @Test void upgradeFromV11PreservesEveryExistingTableRow() {
        String original=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!original.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?"))throw new IllegalStateException("Test DB required");
        String name="economy_"+UUID.randomUUID().toString().replace("-","")+"_test";
        String url=original.substring(0,original.lastIndexOf('/')+1)+name;
        String user=System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma");
        String password=System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD","");
        existing.execute("CREATE DATABASE "+name);
        try {
            Flyway.configure().dataSource(url,user,password).schemas("game").defaultSchema("game").target("11").load().migrate();
            var db=new JdbcTemplate(new DriverManagerDataSource(url,user,password));
            db.update("UPDATE game.t_player SET gold=137 WHERE player_id=1");
            db.update("INSERT INTO game.t_inventory(player_id,item_id,quantity) SELECT 1,item_id,3 FROM game.m_item WHERE item_code='SMALL_POTION'");
            var tables=db.queryForList("SELECT tablename FROM pg_tables WHERE schemaname='game' AND tablename<>'flyway_schema_history' ORDER BY tablename",String.class);
            var existingStages=db.queryForList("SELECT species_id,evolution_stage,name FROM game.m_species_evolution ORDER BY species_id,evolution_stage");
            tables.remove("m_species_evolution");
            var before=snapshot(db,tables);
            var checksums=db.queryForList("SELECT version,checksum FROM game.flyway_schema_history ORDER BY installed_rank");
            Flyway.configure().dataSource(url,user,password).schemas("game").defaultSchema("game").load().migrate();
            assertEquals(before,snapshot(db,tables));
                assertEquals(0,db.queryForObject("SELECT active_selection_revision FROM game.t_player WHERE player_id=1",Long.class));
            for(var stage:existingStages)assertEquals(stage,db.queryForMap("SELECT species_id,evolution_stage,name FROM game.m_species_evolution WHERE species_id=? AND evolution_stage=?",stage.get("species_id"),stage.get("evolution_stage")));
            assertEquals(15,db.queryForObject("SELECT count(*) FROM game.m_species_evolution",Integer.class));
            assertEquals(checksums,db.queryForList("SELECT version,checksum FROM game.flyway_schema_history WHERE version IS NULL OR version::int<=11 ORDER BY installed_rank"));
            assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_reward_entitlement",Integer.class));
            assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_economy_reward_ledger",Integer.class));
        } finally {existing.execute("DROP DATABASE "+name+" WITH (FORCE)");}
    }
    Map<String,String> snapshot(JdbcTemplate db,List<String> tables) {
        var result=new LinkedHashMap<String,String>();
        for(String table:tables){
            if(!table.matches("[a-z_]+"))throw new IllegalArgumentException("Invalid table");
            String projection=table.equals("t_player_companion")?"to_jsonb(t)-'growth_policy_version'":table.equals("t_player")?"to_jsonb(t)-'active_selection_revision'":"to_jsonb(t)";
            result.put(table,db.queryForObject("SELECT md5(COALESCE(jsonb_agg("+projection+" ORDER BY ("+projection+")::text)::text,'[]')) FROM game."+table+" t",String.class));
        }
        return result;
    }
}
