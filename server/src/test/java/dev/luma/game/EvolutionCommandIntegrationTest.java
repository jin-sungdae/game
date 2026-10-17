package dev.luma.game;

import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** PostgreSQL integration with a TEST-ONLY revision provider, not a Switching implementation. */
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class EvolutionCommandIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r) { GameIntegrationTest.database(r); }
    @Autowired TestRestTemplate http;
    @Autowired JdbcTemplate db;
    @Autowired EvolutionCommandService commands;
    @Autowired PlatformTransactionManager transactions;
    @Autowired org.springframework.context.ApplicationContext context;
    @LocalServerPort int port;
    @MockitoBean EvolutionSelectionRevision selection;
    long companion;

    @BeforeEach void reset() {
        clean(); when(selection.current(1)).thenReturn(0L);
        companion=db.queryForObject("SELECT player_companion_id FROM game.t_player_companion WHERE player_id=1 AND active",Long.class);
        db.update("UPDATE game.t_player_companion SET level=6,exp=1500,bond=12 WHERE player_companion_id=?",companion);
        db.update("UPDATE game.t_player SET gold=73 WHERE player_id=1");
    }
    @AfterEach void clean() {
        db.update("DELETE FROM game.t_command_receipt");
        CompanionBondIntegrationTest.clean(db);
        db.update("UPDATE game.t_player_companion SET species_id=(SELECT species_id FROM game.m_species WHERE code='MOA') WHERE player_id=1");
    }
    EvolutionCommandRequest request(UUID id,int stage) { return new EvolutionCommandRequest(id,companion,stage,0); }
    ResponseEntity<String> post(Object body) { return http.postForEntity("http://127.0.0.1:"+port+"/api/v1/companions/active/evolve",body,String.class); }
    int count(String table) { return db.queryForObject("SELECT count(*) FROM game."+table,Integer.class); }
    int stage() { return db.queryForObject("SELECT evolution_stage FROM game.t_player_companion WHERE player_companion_id=?",Integer.class,companion); }
    void error(ResponseEntity<String> response,int status,String code) {
        assertEquals(status,response.getStatusCode().value()); assertTrue(response.getBody().contains("\"code\":\""+code+"\""),response.getBody());
    }
    void untouched() { assertEquals(1,stage()); assertEquals(0,count("t_companion_evolution_history")); assertEquals(0,count("t_command_receipt")); }

    @Test void replayIsExactEvenAfterAnotherCommandAdvancesStage() {
        var request=request(UUID.randomUUID(),1); var first=post(request);
        assertEquals(200,first.getStatusCode().value()); assertEquals("1",first.getHeaders().getFirst("X-Luma-Response-Schema-Version"));
        assertEquals(first.getBody(),post(request).getBody()); assertEquals(2,stage());
        assertEquals(200,post(request(UUID.randomUUID(),2)).getStatusCode().value());
        clearInvocations(selection); var replay=post(request);
        assertEquals(first.getBody(),replay.getBody()); assertEquals(first.getStatusCode(),replay.getStatusCode());
        assertEquals("1",replay.getHeaders().getFirst("X-Luma-Response-Schema-Version")); verifyNoInteractions(selection);
        assertEquals(3,stage()); assertEquals(2,count("t_companion_evolution_history")); assertEquals(2,count("t_command_receipt"));
        assertEquals(1500,db.queryForObject("SELECT exp FROM game.t_player_companion WHERE player_companion_id=?",Long.class,companion));
        assertEquals(12,db.queryForObject("SELECT bond FROM game.t_player_companion WHERE player_companion_id=?",Integer.class,companion));
        assertEquals(73,db.queryForObject("SELECT gold FROM game.t_player WHERE player_id=1",Long.class));
    }
    @Test void reusedIdentityRejectsEveryChangedExpectationBeforeStateValidation() {
        UUID id=UUID.randomUUID(); assertEquals(200,post(request(id,1)).getStatusCode().value());
        for(var changed:List.of(request(id,2),new EvolutionCommandRequest(id,companion+1,1,0),new EvolutionCommandRequest(id,companion,1,1)))
            error(post(changed),409,"COMMAND_ID_REUSED");
        assertEquals(2,stage()); assertEquals(1,count("t_command_receipt")); assertEquals(1,count("t_companion_evolution_history"));
    }
    @Test void newIdentityCannotRepeatOldStage() {
        assertEquals(200,post(request(UUID.randomUUID(),1)).getStatusCode().value());
        error(post(request(UUID.randomUUID(),1)),409,"STALE_STAGE");
        assertEquals(2,stage()); assertEquals(1,count("t_command_receipt"));
    }
    @Test void expectationChecksPrecedeRulesAndDoNotSaveReceipts() {
        error(post(new EvolutionCommandRequest(UUID.randomUUID(),companion+1,1,0)),409,"COMPANION_MISMATCH");
        verifyNoInteractions(selection);
        error(post(new EvolutionCommandRequest(UUID.randomUUID(),companion,1,1)),409,"STALE_SELECTION");
        error(post(request(UUID.randomUUID(),2)),409,"STALE_STAGE"); untouched();
    }
    @Test void changedRevisionRejectsSameCompanionFixtureOnly() {
        // Models the expected contract after A->B->A. No actual Switching/schema integration exists yet.
        when(selection.current(1)).thenReturn(2L);
        error(post(request(UUID.randomUUID(),1)),409,"STALE_SELECTION"); untouched();
    }
    @Test void simultaneousSameIdentityMutatesOnce() throws Exception { concurrent(false); }
    @Test void simultaneousDifferentIdentitiesRejectLosersAsStale() throws Exception { concurrent(true); }
    void concurrent(boolean different) throws Exception {
        try(var pool=Executors.newFixedThreadPool(4)) {
            var gate=new CountDownLatch(1); UUID id=UUID.randomUUID(); var futures=new ArrayList<Future<ResponseEntity<String>>>();
            for(int i=0;i<4;i++) { var request=request(different?UUID.randomUUID():id,1); futures.add(pool.submit(()->{gate.await();return post(request);})); }
            gate.countDown(); var bodies=new HashSet<String>(); int success=0;
            for(var f:futures) { var response=f.get(20,TimeUnit.SECONDS); if(response.getStatusCode().value()==200){success++;bodies.add(response.getBody());}else error(response,409,"STALE_STAGE"); }
            assertEquals(different?1:4,success); assertEquals(1,bodies.size());
        }
        assertEquals(2,stage()); assertEquals(1,count("t_companion_evolution_history")); assertEquals(1,count("t_command_receipt"));
    }
    @Test void historyFailureRollsBackStageAndDoesNotSaveReceipt() {
        assertEquals(200,post(request(UUID.randomUUID(),1)).getStatusCode().value());
        db.update("UPDATE game.t_player_companion SET evolution_stage=1 WHERE player_companion_id=?",companion);
        UUID failed=UUID.randomUUID(); error(post(request(failed,1)),503,"GAME_UNAVAILABLE");
        assertEquals(1,stage()); assertEquals(1,count("t_companion_evolution_history")); assertEquals(1,count("t_command_receipt"));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt WHERE command_id=?",Integer.class,failed));
    }
    @Test void finalReceiptInsertFailureRollsBackStageHistoryAndInjectedReceipt() {
        UUID id=UUID.randomUUID();
        when(selection.current(1)).thenAnswer(call->{
            // Deliberate SQL fault fixture: reserve this key inside the SAME transaction before mutation.
            db.update("INSERT INTO game.t_command_receipt(player_id,command_id,command_type,target_id,request_fingerprint,response_status,response_body,response_schema_version) VALUES(1,?,'EVOLUTION',? ,?,200,'{}',1)",id,Long.toString(companion),"0".repeat(64));
            return 0L;
        });
        error(post(request(id,1)),503,"GAME_UNAVAILABLE"); untouched();
    }
    @Test void callerRollbackIncludesAllThreeWrites() {
        new TransactionTemplate(transactions).executeWithoutResult(tx->{
            assertEquals(200,commands.execute(request(UUID.randomUUID(),1)).status());
            assertEquals(2,stage()); assertEquals(1,count("t_companion_evolution_history")); assertEquals(1,count("t_command_receipt"));
            tx.setRollbackOnly();
        }); untouched();
    }
    @Test void serializationFailureAfterMutationRollsBackAllWrites() throws Exception {
        var mapper=spy(context.getBean(com.fasterxml.jackson.databind.ObjectMapper.class).copy());
        doReturn(mapper).when(mapper).copy();
        doThrow(new com.fasterxml.jackson.core.JsonProcessingException("deliberate result encoding failure") {})
            .when(mapper).writeValueAsString(isA(EvolutionDtos.Result.class));
        var adapter=new EvolutionCommandService(context.getBean(dev.luma.game.command.CommandReceiptExecutor.class),
            context.getBean(EvolutionRepository.class),context.getBean(EvolutionService.class),
            context.getBeanProvider(EvolutionSelectionRevision.class),mapper);
        assertThrows(GameUnavailable.class,()->adapter.execute(request(UUID.randomUUID(),1)));
        untouched();
    }
    @Test void approvedThresholdsAndUnapprovedSpeciesStayUnchanged() {
        for(int[] pair:List.of(new int[]{2,5},new int[]{3,4})) {
            db.update("UPDATE game.t_player_companion SET level=?,exp=?,bond=? WHERE player_companion_id=?",pair[0],GrowthCurveB.threshold(pair[0]),pair[1],companion);
            error(post(request(UUID.randomUUID(),1)),409,"NOT_ELIGIBLE"); untouched();
        }
        db.update("UPDATE game.t_player_companion SET level=3,exp=300,bond=5 WHERE player_companion_id=?",companion);
        assertEquals(200,post(request(UUID.randomUUID(),1)).getStatusCode().value());
        for(int[] pair:List.of(new int[]{5,12},new int[]{6,11})) {
            db.update("UPDATE game.t_player_companion SET level=?,exp=?,bond=? WHERE player_companion_id=?",pair[0],GrowthCurveB.threshold(pair[0]),pair[1],companion);
            // Existing service preserves ALREADY_EVOLVED, so this is a saved no-op result, not an extra evolution.
            var response=post(request(UUID.randomUUID(),2)); assertEquals(200,response.getStatusCode().value()); assertTrue(response.getBody().contains("ALREADY_EVOLVED"));
            assertEquals(2,stage()); assertEquals(1,count("t_companion_evolution_history"));
        }
        db.update("UPDATE game.t_player_companion SET level=6,exp=1500,bond=12 WHERE player_companion_id=?",companion);
        assertEquals(200,post(request(UUID.randomUUID(),2)).getStatusCode().value()); assertEquals(3,stage());
        clean();
        for(String species:List.of("RUU","NOX")) {
            db.update("UPDATE game.t_player_companion SET species_id=(SELECT species_id FROM game.m_species WHERE code=?),level=100,exp=88900,bond=100 WHERE player_companion_id=?",species,companion);
            error(post(request(UUID.randomUUID(),1)),409,"NOT_ELIGIBLE"); untouched();
        }
    }
}
