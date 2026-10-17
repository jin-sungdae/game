package dev.luma.game;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

/** Real HTTP and PostgreSQL; restarted contexts share no in-memory battle identity. */
class BattleParticipantIdentityTest {
    final TestRestTemplate http=new TestRestTemplate();
    ConfigurableApplicationContext start() {
        String db=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!db.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?"))throw new IllegalStateException("Test DB required");
        return new SpringApplicationBuilder(GameApplication.class).run("--server.port=0",
            "--spring.datasource.url="+db,"--spring.datasource.username="+System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"),
            "--spring.datasource.password="+System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD",""));
    }
    String url(ConfigurableApplicationContext app,String path) {
        return "http://127.0.0.1:"+app.getEnvironment().getProperty("local.server.port")+"/api/v1"+path;
    }
    void clean(JdbcTemplate db) {
        for(String table:List.of("t_battle_item_effect","t_reward","t_collection","t_battle","t_encounter"))db.update("DELETE FROM game."+table);
        db.update("DELETE FROM game.t_player_companion WHERE species_id IN (SELECT species_id FROM game.m_species WHERE code IN ('RUU','NOX'))");
        CompanionBondIntegrationTest.clean(db);
    }
    BattleDtos.Battle battle(ConfigurableApplicationContext app) {
        var e=http.postForObject(url(app,"/encounters"),null,GameDtos.Encounter.class);
        var b=http.postForObject(url(app,"/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);
        assertEquals(e.monster().code(),b.monsterCode());return b;
    }
    BattleDtos.Battle get(ConfigurableApplicationContext app,UUID id) {
        return http.getForObject(url(app,"/battles/"+id),BattleDtos.Battle.class);
    }
    void ignore(ConfigurableApplicationContext app,BattleDtos.Battle b) {
        assertEquals(200,http.postForEntity(url(app,"/encounters/"+b.encounterId()+"/ignore"),null,String.class).getStatusCode().value());
    }
    long activateFixture(JdbcTemplate db,String species) {
        db.update("UPDATE game.t_player_companion SET active=false");
        return db.queryForObject("""
            INSERT INTO game.t_player_companion(player_id,species_id,evolution_stage,active)
            SELECT 1,species_id,1,true FROM game.m_species WHERE code=? RETURNING player_companion_id
            """,Long.class,species);
    }
    @Test void identityIsAdditiveAndNeverClaimsAnUnstoredSnapshot() {
        try(var app=start()) {
            var db=app.getBean(JdbcTemplate.class);clean(db);
            try {
                db.update("UPDATE game.m_monster SET use_yn=(code='PIP')");
                var b=battle(app);
                long actor=db.queryForObject("SELECT player_companion_id FROM game.t_battle WHERE battle_id=?",Long.class,b.battleId());
                assertEquals(new BattleDtos.Participant(actor,"MOA"),b.participant());
                assertEquals("PIP",b.monsterCode());
                JsonNode json=http.getForObject(url(app,"/battles/"+b.battleId()),JsonNode.class);
                var fields=new HashSet<String>();json.fieldNames().forEachRemaining(fields::add);
                assertEquals(Set.of("battleId","encounterId","turn","status","encounterStatus","companion","monster","events","reward","presentationEvents","participant","monsterCode"),fields);
                assertEquals(Set.of("hp","maxHp"),fieldNames(json.get("companion")));
                assertEquals(Set.of("hp","maxHp"),fieldNames(json.get("monster")));
                assertEquals(Set.of("playerCompanionId","species"),fieldNames(json.get("participant")));
                var attacked=http.postForObject(url(app,"/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);
                assertEquals(b.participant(),attacked.participant());
                var captured=http.postForObject(url(app,"/battles/"+b.battleId()+"/capture"),null,BattleDtos.Capture.class);
                assertEquals(b.participant(),captured.battle().participant());
                assertEquals(captured.monster().code(),captured.battle().monsterCode());
            } finally {clean(db);}
        }
    }
    Set<String> fieldNames(JsonNode node) {var names=new HashSet<String>();node.fieldNames().forEachRemaining(names::add);return names;}
    @Test void evolutionDoesNotInventHistoricalFieldsAndNewBattleKeepsActor() {
        try(var app=start()) {
            var db=app.getBean(JdbcTemplate.class);clean(db);
            try {
                var before=battle(app);ignore(app,before);
                db.update("UPDATE game.t_player_companion SET level=3,exp=300,bond=5 WHERE player_companion_id=?",before.participant().playerCompanionId());
                assertEquals(200,http.postForEntity(url(app,"/companions/active/evolve"),null,String.class).getStatusCode().value());
                assertEquals(2,db.queryForObject("SELECT evolution_stage FROM game.t_player_companion WHERE player_companion_id=?",Integer.class,before.participant().playerCompanionId()));
                var after=battle(app);
                assertNotEquals(before.battleId(),after.battleId());
                assertEquals(before.participant(),after.participant());
                assertEquals(before.participant(),get(app,before.battleId()).participant());
            } finally {clean(db);}
        }
    }
    @Test void persistedParticipantSurvivesActiveChangeAndHttpServerRestart() {
        UUID original;BattleDtos.Participant actor;String monster;
        try(var app=start()) {
            var db=app.getBean(JdbcTemplate.class);clean(db);
            try {
                db.update("UPDATE game.m_monster SET use_yn=(code='PIP')");
                var b=battle(app);original=b.battleId();actor=b.participant();monster=b.monsterCode();
                long ruu=activateFixture(db,"RUU"); // Fixture only: no switching endpoint is introduced.
                assertEquals(actor,get(app,original).participant());
                var attacked=http.postForObject(url(app,"/battles/"+original+"/attack"),null,BattleDtos.Battle.class);
                assertEquals(actor,attacked.participant());
                while(attacked.status().equals("ACTIVE"))attacked=http.postForObject(url(app,"/battles/"+original+"/attack"),null,BattleDtos.Battle.class);
                assertEquals("VICTORY",attacked.status());
                assertTrue(db.queryForObject("SELECT exp FROM game.t_player_companion WHERE player_companion_id=?",Long.class,actor.playerCompanionId())>0);
                assertEquals(0L,db.queryForObject("SELECT exp FROM game.t_player_companion WHERE player_companion_id=?",Long.class,ruu));
                ignore(app,b);
                db.update("UPDATE game.m_monster SET use_yn=(code='MELLO')");
                var other=battle(app);assertEquals(new BattleDtos.Participant(ruu,"RUU"),other.participant());ignore(app,other);
                long nox=activateFixture(db,"NOX");
                var last=battle(app);assertEquals(new BattleDtos.Participant(nox,"NOX"),last.participant());ignore(app,last);
            } catch(Throwable failure) {clean(db);throw failure;}
        }
        try(var app=start()) {
            var db=app.getBean(JdbcTemplate.class);
            try {
                var restored=get(app,original);
                assertEquals(actor,restored.participant());assertEquals(monster,restored.monsterCode());
                assertEquals("VICTORY",restored.status());
                assertEquals("ESCAPED",restored.encounterStatus());
            } finally {clean(db);}
        }
    }
}
