package dev.luma.game;

import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.dao.DataIntegrityViolationException;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static dev.luma.game.EvolutionDtos.*;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class EvolutionIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r) { GameIntegrationTest.database(r); }
    @Autowired TestRestTemplate http; @Autowired JdbcTemplate db; @LocalServerPort int port;
    String url(String p) { return "http://127.0.0.1:"+port+"/api/v1"+p; }
    @BeforeEach @AfterEach void clean() {
        db.update("DELETE FROM game.t_companion_evolution_history");
        db.update("DELETE FROM game.t_reward"); db.update("DELETE FROM game.t_collection");
        db.update("DELETE FROM game.t_battle"); db.update("DELETE FROM game.t_encounter");
        db.update("UPDATE game.t_player_companion SET evolution_stage=1,level=1,exp=0,bond=0,active=true");
        db.update("UPDATE game.t_player SET gold=0");
        db.update("INSERT INTO game.m_species_evolution(species_id,evolution_stage,name) SELECT species_id,2,'MOKORI' FROM game.m_species WHERE code='MOA' ON CONFLICT DO NOTHING");
    }
    void progress(int level,int bond) { db.update("UPDATE game.t_player_companion SET level=?,bond=?,exp=321",level,bond); db.update("UPDATE game.t_player SET gold=73"); }
    Status status() { return http.getForObject(url("/companions/active/evolution"),Status.class); }
    Result evolve() { return http.postForObject(url("/companions/active/evolve"),null,Result.class); }
    GameDtos.Bootstrap bootstrap() { return http.getForObject(url("/game/bootstrap"),GameDtos.Bootstrap.class); }
    int histories() { return db.queryForObject("SELECT count(*) FROM game.t_companion_evolution_history",Integer.class); }
    void locked(int level,int bond,boolean levelMet,boolean bondMet) {
        progress(level,bond); var s=status(); assertEquals(State.LOCKED,s.status());
        assertEquals(levelMet,s.requirements().level().met()); assertEquals(bondMet,s.requirements().bond().met());
        var r=http.postForEntity(url("/companions/active/evolve"),null,Map.class);
        assertEquals(409,r.getStatusCode().value()); assertEquals("NOT_ELIGIBLE",r.getBody().get("code"));
        assertEquals(1,bootstrap().activeCompanion().evolutionStage()); assertEquals(0,histories());
    }
    @Test void lockedByLevel() { locked(2,5,false,true); }
    @Test void lockedByBond() { locked(3,4,true,false); }
    @Test void lockedByBoth() { locked(1,0,false,false); }
    @Test void availableDoesNotAutoEvolve() {
        progress(3,5); var s=status(); assertEquals(State.AVAILABLE,s.status());
        assertEquals("MOKORI",s.nextName()); assertEquals(2,s.nextStage());
        assertEquals(3,s.requirements().level().required()); assertEquals(5,s.requirements().bond().required());
        assertEquals(1,bootstrap().activeCompanion().evolutionStage()); assertEquals(0,histories());
    }
    @Test void successPreservesProgressionAndRecordsAudit() {
        progress(3,5); var before=bootstrap(); var r=evolve(); assertEquals("EVOLVED",r.result());
        var c=r.bootstrap().activeCompanion(); assertEquals(2,c.evolutionStage()); assertEquals("MOKORI",c.evolutionName());
        assertEquals(before.player(),r.bootstrap().player()); assertEquals(before.activeCompanion().level(),c.level());
        assertEquals(before.activeCompanion().bond(),c.bond()); assertEquals(before.activeCompanion().exp(),c.exp());
        assertEquals(before.activeCompanion().playerCompanionId(),c.playerCompanionId());
        assertEquals(r.bootstrap(),bootstrap()); assertEquals(1,histories());
        var row=db.queryForMap("SELECT from_stage,to_stage,level_at_evolution,bond_at_evolution,evolved_at FROM game.t_companion_evolution_history");
        assertEquals(1,row.get("from_stage")); assertEquals(2,row.get("to_stage"));
        assertEquals(3,row.get("level_at_evolution")); assertEquals(5,row.get("bond_at_evolution")); assertNotNull(row.get("evolved_at"));
    }
    @Test void repeatedRequestsNeverReachStageThree() {
        progress(5,100); evolve();
        for(int i=0;i<5;i++) { var r=evolve(); assertEquals("ALREADY_EVOLVED",r.result()); assertEquals(2,r.bootstrap().activeCompanion().evolutionStage()); }
        assertEquals(1,histories()); assertEquals(State.LOCKED,status().status()); assertEquals(3,status().nextStage());
    }
    @Test void simultaneousEvolveExactlyOnce() throws Exception {
        progress(3,5); var pool=Executors.newFixedThreadPool(4); var gate=new CountDownLatch(1);
        try {
            List<Future<Result>> futures=new ArrayList<>();
            for(int i=0;i<4;i++) futures.add(pool.submit(()->{gate.await();return evolve();}));
            gate.countDown(); List<String> outcomes=new ArrayList<>();
            for(var f:futures) {var r=f.get(20,TimeUnit.SECONDS);outcomes.add(r.result());assertEquals(2,r.bootstrap().activeCompanion().evolutionStage());}
            assertEquals(1,Collections.frequency(outcomes,"EVOLVED")); assertEquals(3,Collections.frequency(outcomes,"ALREADY_EVOLVED"));
            assertEquals(1,histories());
        } finally { pool.shutdownNow(); }
    }
    @Test void invalidActiveCompanion() {
        db.update("UPDATE game.t_player_companion SET active=false");
        assertEquals(503,http.getForEntity(url("/companions/active/evolution"),String.class).getStatusCode().value());
        assertEquals(503,http.postForEntity(url("/companions/active/evolve"),null,String.class).getStatusCode().value());
    }
    @Test void missingMasterCannotMutate() {
        progress(3,5); db.update("DELETE FROM game.m_species_evolution WHERE evolution_stage=2 AND species_id=(SELECT species_id FROM game.m_species WHERE code='MOA')");
        assertEquals(503,http.postForEntity(url("/companions/active/evolve"),null,String.class).getStatusCode().value());
        assertEquals(1,bootstrap().activeCompanion().evolutionStage()); assertEquals(0,histories());
    }
    @Test void maximumStageFoundation() {
        db.update("UPDATE game.t_player_companion SET evolution_stage=5"); assertEquals(State.MAX_STAGE,status().status());
        var r=http.postForEntity(url("/companions/active/evolve"),null,Map.class);
        assertEquals(409,r.getStatusCode().value()); assertEquals("MAX_STAGE",r.getBody().get("code")); assertEquals(0,histories());
    }
    @Test void stageTwoWithoutHistoryIsNotAnEnabledTransition() {
        progress(5,100); db.update("UPDATE game.t_player_companion SET evolution_stage=2");
        assertEquals(409,http.postForEntity(url("/companions/active/evolve"),null,String.class).getStatusCode().value());
        assertEquals(2,bootstrap().activeCompanion().evolutionStage()); assertEquals(0,histories());
    }
    @Test void clientFieldsAreRejected() {
        progress(3,5);
        assertEquals(400,http.postForEntity(url("/companions/active/evolve"),Map.of("nextStage",5),String.class).getStatusCode().value());
        assertEquals(400,http.postForEntity(url("/companions/active/evolve?level=99"),null,String.class).getStatusCode().value());
        assertEquals(0,histories());
    }
    @Test void historyConstraintAndWholeTransactionRollback() {
        progress(3,5); evolve();
        assertThrows(DataIntegrityViolationException.class,()->db.update("INSERT INTO game.t_companion_evolution_history(player_companion_id,species_id,from_stage,to_stage,level_at_evolution,bond_at_evolution) SELECT player_companion_id,species_id,1,2,3,5 FROM game.t_player_companion"));
        // Corrupt test fixture only: an existing audit row must make a new stage update roll back.
        db.update("UPDATE game.t_player_companion SET evolution_stage=1");
        assertEquals(503,http.postForEntity(url("/companions/active/evolve"),null,String.class).getStatusCode().value());
        assertEquals(1,bootstrap().activeCompanion().evolutionStage()); assertEquals(1,histories());
    }
    @Test void newServiceInstanceReadsPersistedState() {
        progress(3,5); evolve();
        var fresh=new EvolutionService(new GameRepository(db),new EvolutionRepository(db));
        assertEquals("MOKORI",fresh.status().currentName()); assertEquals(2,fresh.status().currentStage());
    }
    @Test void battleAfterEvolutionUsesExistingLevelFormula() {
        progress(3,5); evolve();
        var e=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);
        var b=http.postForObject(url("/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);
        assertEquals(CombatRules.companionHp(),b.companion().maxHp());
        var a=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);
        assertEquals(1,a.turn()); assertEquals(2,bootstrap().activeCompanion().evolutionStage()); assertEquals(1,histories());
    }

    @Test void stageThreeBoundariesHistoryConcurrencyAndProgress() throws Exception {
        progress(3,5);evolve();
        for(var pair:List.of(new int[]{5,12},new int[]{6,11})) {progress(pair[0],pair[1]);assertEquals(State.LOCKED,status().status());assertEquals(2,bootstrap().activeCompanion().evolutionStage());}
        progress(6,12);var before=bootstrap();assertEquals(State.AVAILABLE,status().status());assertEquals("NEBLA",status().nextName());
        try(var pool=Executors.newFixedThreadPool(4)) {
            var gate=new CountDownLatch(1);var futures=new ArrayList<Future<Result>>();
            for(int i=0;i<4;i++)futures.add(pool.submit(()->{gate.await();return evolve();}));gate.countDown();
            var outcomes=new ArrayList<String>();
            for(var f:futures){var r=f.get(20,TimeUnit.SECONDS);outcomes.add(r.result());assertEquals(3,r.bootstrap().activeCompanion().evolutionStage());}
            assertEquals(1,Collections.frequency(outcomes,"EVOLVED"));assertEquals(3,Collections.frequency(outcomes,"ALREADY_EVOLVED"));
        }
        var after=bootstrap();assertEquals("NEBLA",after.activeCompanion().evolutionName());
        assertEquals(before.player(),after.player());assertEquals(before.activeCompanion().level(),after.activeCompanion().level());
        assertEquals(before.activeCompanion().exp(),after.activeCompanion().exp());assertEquals(before.activeCompanion().bond(),after.activeCompanion().bond());
        assertEquals(List.of(2,3),db.queryForList("SELECT to_stage FROM game.t_companion_evolution_history ORDER BY evolution_history_id",Integer.class));
        assertEquals("ALREADY_EVOLVED",evolve().result());assertEquals(2,histories());assertNull(status().nextStage());
        var fresh=new EvolutionService(new GameRepository(db),new EvolutionRepository(db));assertEquals("NEBLA",fresh.status().currentName());
    }
    @Test void stageThreeHistoryFailureRollsBackStageUpdate() {
        progress(3,5);evolve();progress(6,12);evolve();
        db.update("UPDATE game.t_player_companion SET evolution_stage=2");
        assertEquals(503,http.postForEntity(url("/companions/active/evolve"),null,String.class).getStatusCode().value());
        assertEquals(2,bootstrap().activeCompanion().evolutionStage());assertEquals(2,histories());
    }
}
