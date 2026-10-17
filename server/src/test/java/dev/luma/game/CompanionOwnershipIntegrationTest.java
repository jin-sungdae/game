package dev.luma.game;

import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class CompanionOwnershipIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r) { GameIntegrationTest.database(r); }
    @Autowired TestRestTemplate http;
    @Autowired JdbcTemplate db;
    @LocalServerPort int port;
    String url(String path) { return "http://127.0.0.1:"+port+"/api/v1"+path; }
    static void clean(JdbcTemplate db) {
        db.update("DELETE FROM game.t_player_companion WHERE player_id=92001 OR species_id IN (SELECT species_id FROM game.m_species WHERE code IN ('RUU','NOX'))");
        db.update("DELETE FROM game.t_player WHERE player_id=92001");
        CompanionBondIntegrationTest.clean(db);
    }
    @BeforeEach @AfterEach void clean() { clean(db); }
    static void add(JdbcTemplate db,long player,String species) {
        db.update("""
            INSERT INTO game.t_player_companion(player_id,species_id,evolution_stage,level,exp,bond,active)
            SELECT ?,species_id,1,2,123,7,false FROM game.m_species WHERE code=?
            """,player,species);
    }
    CompanionOwnershipDtos.Ownership read() {
        var response=http.getForEntity(url("/companions"),CompanionOwnershipDtos.Ownership.class);
        assertEquals(200,response.getStatusCode().value());return response.getBody();
    }
    @Test void moaMatchesBootstrapAndStableIdentity() {
        var b=http.getForObject(url("/game/bootstrap"),GameDtos.Bootstrap.class).activeCompanion();
        var r=read();assertEquals(1,r.companions().size());var c=r.companions().getFirst();
        assertEquals(b.playerCompanionId(),r.activeCompanionId());assertTrue(c.active());
        assertEquals(b,new GameDtos.Companion(c.playerCompanionId(),c.species(),c.evolutionStage(),c.evolutionName(),c.level(),c.exp(),c.bond()));
        assertEquals(r,read());
    }
    @Test void threeSpeciesWithExactlyOneActiveAndPlayerIsolation() {
        add(db,1,"RUU");add(db,1,"NOX");
        db.update("INSERT INTO game.t_player(player_id,player_name) VALUES(92001,'OWNERSHIP_TEST')");
        add(db,92001,"RUU");
        var r=read();assertEquals(List.of("MOA","RUU","NOX"),r.companions().stream().map(CompanionOwnershipDtos.Owned::species).toList());
        assertEquals(1,r.companions().stream().filter(CompanionOwnershipDtos.Owned::active).count());
        assertEquals(r.activeCompanionId(),r.companions().getFirst().playerCompanionId());
        long foreign=db.queryForObject("SELECT player_companion_id FROM game.t_player_companion WHERE player_id=92001",Long.class);
        assertTrue(r.companions().stream().noneMatch(c->c.playerCompanionId()==foreign));
        for(var c:r.companions().subList(1,3)) {assertFalse(c.active());assertEquals(123,c.exp());assertEquals(7,c.bond());}
        assertEquals(400,http.getForEntity(url("/companions?playerId=92001"),String.class).getStatusCode().value());
    }
    @Test void activeIdentityComesFromStoredFlagNotSpeciesOrListPosition() {
        add(db,1,"RUU");
        db.update("UPDATE game.t_player_companion SET active=false WHERE player_id=1");
        db.update("UPDATE game.t_player_companion SET active=true WHERE player_id=1 AND species_id=(SELECT species_id FROM game.m_species WHERE code='RUU')");
        var r=read();var active=r.companions().stream().filter(CompanionOwnershipDtos.Owned::active).findFirst().orElseThrow();
        assertEquals("RUU",active.species());assertEquals(active.playerCompanionId(),r.activeCompanionId());
        assertEquals(r.activeCompanionId(),http.getForObject(url("/game/bootstrap"),GameDtos.Bootstrap.class).activeCompanion().playerCompanionId());
    }
    @Test void noActiveFailsClosedWithoutRepair() {
        db.update("UPDATE game.t_player_companion SET active=false WHERE player_id=1");
        assertEquals(503,http.getForEntity(url("/companions"),String.class).getStatusCode().value());
        assertEquals(503,http.getForEntity(url("/game/bootstrap"),String.class).getStatusCode().value());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_player_companion WHERE active",Integer.class));
    }
    @Test void readsPreserveAllCompanionColumnsAndEvolutionHistory() {
        db.update("UPDATE game.t_player_companion SET evolution_stage=2,level=3,exp=321,bond=8,last_bond_interaction_at=clock_timestamp() WHERE player_id=1");
        db.update("""
            INSERT INTO game.t_companion_evolution_history(player_companion_id,species_id,from_stage,to_stage,level_at_evolution,bond_at_evolution)
            SELECT player_companion_id,species_id,1,2,3,5 FROM game.t_player_companion WHERE player_id=1
            """);
        var before=db.queryForList("SELECT * FROM game.t_player_companion ORDER BY player_companion_id");
        var history=db.queryForList("SELECT * FROM game.t_companion_evolution_history");
        var result=read();assertEquals("MOKORI",result.companions().getFirst().evolutionName());read();
        assertEquals(before,db.queryForList("SELECT * FROM game.t_player_companion ORDER BY player_companion_id"));
        assertEquals(history,db.queryForList("SELECT * FROM game.t_companion_evolution_history"));
    }
    @Test void databaseRejectsSecondActive() {
        add(db,1,"RUU");
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("UPDATE game.t_player_companion SET active=true WHERE player_id=1 AND species_id=(SELECT species_id FROM game.m_species WHERE code='RUU')"));
        assertEquals(1,read().companions().stream().filter(CompanionOwnershipDtos.Owned::active).count());
    }
}
