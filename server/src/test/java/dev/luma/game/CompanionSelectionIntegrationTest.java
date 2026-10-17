package dev.luma.game;

import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class CompanionSelectionIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r) { GameIntegrationTest.database(r); }
    @Autowired JdbcTemplate db; @Autowired TestRestTemplate http;
    @Autowired CompanionSelectionService selections; @Autowired EvolutionCommandService evolution;
    @Autowired PlatformTransactionManager transactions;
    @LocalServerPort int port;
    long moa,ruu;
    String url(String path) { return "http://127.0.0.1:"+port+"/api/v1"+path; }
    @BeforeEach void setup() {
        clean(); moa=selections.snapshot().activeCompanionId();
        CompanionOwnershipIntegrationTest.add(db,1,"RUU");
        ruu=db.queryForObject("SELECT player_companion_id FROM game.t_player_companion WHERE player_id=1 AND NOT active",Long.class);
        db.update("UPDATE game.t_player_companion SET level=6,exp=1500,bond=12 WHERE player_id=1");
    }
    @AfterEach void clean() {
        db.update("DELETE FROM game.t_command_receipt");
        for(String table:List.of("t_battle_item_effect","t_reward","t_battle","t_encounter","t_companion_evolution_history")) db.update("DELETE FROM game."+table);
        db.update("DELETE FROM game.t_player_companion WHERE species_id IN (SELECT species_id FROM game.m_species WHERE code IN ('RUU','NOX'))");
        db.update("UPDATE game.t_player SET active_selection_revision=0");
        CompanionBondIntegrationTest.clean(db);
    }
    CompanionSelectionService.Request request(UUID id,long target,long revision) {return new CompanionSelectionService.Request(id,target,revision);}
    void select(long target,long revision) {assertEquals(200,selections.select(request(UUID.randomUUID(),target,revision)).status());}
    void fault(String code,Runnable action) {var e=assertThrows(GameFault.class,action::run);assertEquals(code,e.code);}
    @Test void replayNoopAndChangedPayloadPreserveRevisionAndIdentity() {
        var r=request(UUID.randomUUID(),ruu,0);var first=selections.select(r);
        assertEquals(new CompanionSelectionService.Snapshot(ruu,1),selections.snapshot());
        select(ruu,1);assertEquals(1,selections.snapshot().activeSelectionRevision());
        select(moa,1);assertEquals(first,selections.select(r));
        assertEquals(new CompanionSelectionService.Snapshot(moa,2),selections.snapshot());
        fault("COMMAND_ID_REUSED",()->selections.select(request(r.commandId(),moa,0)));
    }
    @Test void realAbaRejectsOldEvolutionAndCommittedEvolutionReplaysBeforeRevisionCheck() {
        var old=new EvolutionCommandRequest(UUID.randomUUID(),moa,1,0);
        select(ruu,0);select(moa,1);
        fault("STALE_SELECTION",()->evolution.execute(old));
        var legacy=http.postForEntity(url("/companions/active/evolve"),null,String.class);
        assertEquals(409,legacy.getStatusCode().value());assertTrue(legacy.getBody().contains("EVOLUTION_COMMAND_REQUIRED"));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_companion_evolution_history",Integer.class));
        var current=new EvolutionCommandRequest(UUID.randomUUID(),moa,1,2);var result=evolution.execute(current);
        select(ruu,2);select(moa,3);
        assertEquals(result,evolution.execute(current));
        assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_companion_evolution_history",Integer.class));
        fault("STALE_STAGE",()->evolution.execute(new EvolutionCommandRequest(UUID.randomUUID(),moa,1,4)));
    }
    @Test void transactionRollbackRestoresSelectionRevisionAndReceipt() {
        var before=db.queryForList("SELECT * FROM game.t_player_companion ORDER BY player_companion_id");
        new TransactionTemplate(transactions).executeWithoutResult(tx->{select(ruu,0);tx.setRollbackOnly();});
        assertEquals(before,db.queryForList("SELECT * FROM game.t_player_companion ORDER BY player_companion_id"));
        assertEquals(new CompanionSelectionService.Snapshot(moa,0),selections.snapshot());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
    }
    @Test void concurrentSameCommandCommitsOneSelection() throws Exception {
        var r=request(UUID.randomUUID(),ruu,0);
        try(var pool=Executors.newFixedThreadPool(4)) {
            var gate=new CountDownLatch(1);var futures=new ArrayList<Future<String>>();
            for(int i=0;i<4;i++)futures.add(pool.submit(()->{gate.await();return selections.select(r).body();}));
            gate.countDown();var bodies=new HashSet<String>();for(var f:futures)bodies.add(f.get(20,TimeUnit.SECONDS));
            assertEquals(1,bodies.size());
        }
        assertEquals(1,selections.snapshot().activeSelectionRevision());
        assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
    }
    @Test void concurrentDifferentCommandsHaveOneWinner() throws Exception {
        try(var pool=Executors.newFixedThreadPool(4)) {
            var gate=new CountDownLatch(1);var futures=new ArrayList<Future<String>>();
            for(int i=0;i<4;i++)futures.add(pool.submit(()->{
                gate.await();try {select(ruu,0);return "OK";} catch(GameFault e){return e.code;}
            }));
            gate.countDown();int winners=0;
            for(var f:futures){var value=f.get(20,TimeUnit.SECONDS);if(value.equals("OK"))winners++;else assertEquals("STALE_SELECTION",value);}
            assertEquals(1,winners);
        }
        assertEquals(1,selections.snapshot().activeSelectionRevision());
        assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
    }
    @Test void revisionOverflowRollsBackBothActiveFlags() {
        db.update("UPDATE game.t_player SET active_selection_revision=? WHERE player_id=1",Long.MAX_VALUE);
        assertThrows(org.springframework.dao.DataAccessException.class,()->select(ruu,Long.MAX_VALUE));
        assertEquals(new CompanionSelectionService.Snapshot(moa,Long.MAX_VALUE),selections.snapshot());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
    }
    @Test void selectionPreservesGrowthCooldownGoldAndHistory() {
        var before=db.queryForList("SELECT player_companion_id,species_id,evolution_stage,level,exp,bond,last_bond_interaction_at FROM game.t_player_companion ORDER BY player_companion_id");
        var gold=db.queryForObject("SELECT gold FROM game.t_player WHERE player_id=1",Long.class);
        select(ruu,0);select(moa,1);
        assertEquals(before,db.queryForList("SELECT player_companion_id,species_id,evolution_stage,level,exp,bond,last_bond_interaction_at FROM game.t_player_companion ORDER BY player_companion_id"));
        assertEquals(gold,db.queryForObject("SELECT gold FROM game.t_player WHERE player_id=1",Long.class));
    }
    @Test void ongoingBattleBlocksChangeWithoutTouchingSnapshot() {
        var encounter=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);
        var battle=http.postForObject(url("/encounters/"+encounter.encounterId()+"/battle"),null,BattleDtos.Battle.class);
        var before=db.queryForList("SELECT * FROM game.t_battle");
        fault("BATTLE_IN_PROGRESS",()->select(ruu,0));
        assertEquals(before,db.queryForList("SELECT * FROM game.t_battle"));
        assertEquals(new CompanionSelectionService.Snapshot(moa,0),selections.snapshot());
        // Reselecting the same companion is not a switch, even during battle.
        select(moa,0);
        http.postForEntity(url("/encounters/"+encounter.encounterId()+"/ignore"),null,String.class);
        select(ruu,0);
        assertEquals(moa,db.queryForObject("SELECT player_companion_id FROM game.t_battle WHERE battle_id=?",Long.class,battle.battleId()));
    }
    @Test void foreignOrMissingCompanionCannotBeSelectedAndStrictHttpContract() {
        fault("COMPANION_NOT_OWNED",()->select(Long.MAX_VALUE,0));
        var good="{\"commandId\":\""+UUID.randomUUID()+"\",\"companionId\":"+ruu+",\"expectedSelectionRevision\":0}";
        for(String bad:List.of("{}","null",good+" {}",good.replace("Revision\":0","Revision\":0.0"),good.replace("}",",\"extra\":true}")))
            assertEquals(400,http.postForEntity(url("/companions/selection"),bad,String.class).getStatusCode().value());
        assertEquals(200,http.postForEntity(url("/companions/selection"),good,String.class).getStatusCode().value());
        assertEquals(selections.snapshot(),http.getForObject(url("/companions/selection"),CompanionSelectionService.Snapshot.class));
    }
}
