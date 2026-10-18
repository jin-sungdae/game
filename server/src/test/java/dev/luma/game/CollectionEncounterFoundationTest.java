package dev.luma.game;

import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;

@SpringBootTest(properties="luma.collection-foundation.enabled=true")
class CollectionEncounterFoundationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate db;
    @Autowired GameRepository repo;
    @Autowired GameService game;
    @Autowired BattleService battles;
    @Autowired MonsterSelector selector;
    @Autowired CollectionEncounterFoundation foundation;
    @Autowired PlatformTransactionManager manager;
    @MockitoBean RandomSource random;
    static void clean(JdbcTemplate db) {
        db.update("DELETE FROM game.t_collection_reservation");
        db.update("DELETE FROM game.t_observation_receipt");
        db.update("DELETE FROM game.t_collection_issuance_budget");
        CompanionBondIntegrationTest.clean(db);
    }
    @BeforeEach void setup(){clean(db);when(random.nextLong(anyLong())).thenReturn(0L);}
    @AfterEach void cleanup(){clean(db);}
    UUID win() {
        var e=game.createEncounter();var b=battles.start(e.encounterId());
        while(b.status().equals("ACTIVE")) b=battles.attack(b.battleId());
        assertEquals("VICTORY",b.status());return e.encounterId();
    }
    UUID battle(UUID encounter){return db.queryForObject("SELECT battle_id FROM game.t_battle WHERE encounter_id=?",UUID.class,encounter);}
    void award() {var e=win();assertTrue(foundation.recordCompletion(e));battles.ignore(e);}
    @Test void victoryThenCaptureAndCompletionReplayPayExactlyOnce() {
        var id=win();assertTrue(foundation.recordCompletion(id));
        assertTrue(battles.capture(battle(id)).success());
        for(int i=0;i<5;i++) assertFalse(foundation.recordCompletion(id));
        assertThrows(GameFault.class,()->battles.capture(battle(id)));
        assertEquals(new CollectionEncounterFoundation.Progress(1,0,1),foundation.progress());
        assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_observation_receipt",Integer.class));
    }
    @Test void captureWithoutVictoryPaysAndFailedCaptureDoesNot() {
        var e=game.createEncounter();var b=battles.start(e.encounterId());
        when(random.nextLong(anyLong())).thenAnswer(i->(long)i.getArgument(0)-1);
        assertFalse(battles.capture(b.battleId()).success());
        assertFalse(foundation.recordCompletion(e.encounterId()));
        when(random.nextLong(anyLong())).thenReturn(0L);
        assertTrue(battles.capture(b.battleId()).success());
        assertTrue(foundation.recordCompletion(e.encounterId()));
        assertFalse(foundation.recordCompletion(e.encounterId()));
        assertEquals(1,foundation.progress().available());
    }
    @Test void ignoreExpiredActiveAndUnknownDoNotPay() {
        var ignored=game.createEncounter();assertFalse(foundation.recordCompletion(ignored.encounterId()));
        battles.ignore(ignored.encounterId());assertFalse(foundation.recordCompletion(ignored.encounterId()));
        var expired=game.createEncounter();
        db.update("UPDATE game.t_encounter SET spawned_at=clock_timestamp()-interval '61 seconds',expires_at=clock_timestamp()-interval '1 second' WHERE encounter_id=?",expired.encounterId());
        game.activeEncounter();assertFalse(foundation.recordCompletion(expired.encounterId()));
        assertFalse(foundation.recordCompletion(UUID.randomUUID()));
        assertEquals(0,foundation.progress().earned());
    }
    @Test void failedPostVictoryCaptureStillHasOneVictoryCredit() {
        var id=win();when(random.nextLong(anyLong())).thenReturn(999999L);
        assertFalse(battles.capture(battle(id)).success());
        assertTrue(foundation.recordCompletion(id));assertFalse(foundation.recordCompletion(id));
        assertEquals(1,foundation.progress().earned());
    }
    @Test void concurrentCompletionIsOneReceipt() throws Exception {
        var id=win();
        try(var pool=Executors.newFixedThreadPool(8)){
            var start=new CountDownLatch(1);var tasks=new ArrayList<Future<Boolean>>();
            for(int i=0;i<16;i++)tasks.add(pool.submit(()->{start.await();return foundation.recordCompletion(id);}));
            start.countDown();int paid=0;for(var t:tasks)if(t.get(15,TimeUnit.SECONDS))paid++;
            assertEquals(1,paid);
        }
        assertEquals(1,foundation.progress().earned());
    }
    @Test void completionRollsBackWithWinningCommand() {
        new TransactionTemplate(manager).execute(s->{var id=win();assertTrue(foundation.recordCompletion(id));s.setRollbackOnly();return null;});
        assertEquals(0,foundation.progress().earned());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_encounter",Integer.class));
    }
    @Test void defaultDisabledAndExistingAlphaPathRemainUnchanged() {
        var disabled=new CollectionEncounterFoundation(db,repo,selector,false,240);
        assertThrows(GameFault.class,disabled::issueNatural);
        assertThrows(GameFault.class,()->disabled.recordCompletion(UUID.randomUUID()));
        assertThrows(GameFault.class,()->disabled.reserve(UUID.randomUUID(),"PIP",1));
        assertThrows(GameFault.class,()->disabled.consume(UUID.randomUUID(),UUID.randomUUID()));
        assertEquals(15,repo.monsters().size());assertEquals(961,repo.monsters().stream().mapToInt(MonsterSelector.Monster::weight).sum());
        var first=game.createEncounter();battles.ignore(first.encounterId());
        assertNotEquals(first.encounterId(),game.createEncounter().encounterId());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_collection_issuance_budget",Integer.class));
        assertEquals(0,foundation.progress().earned());
    }
    @Test void budgetReusesActiveAndSurvivesIgnoreAndConcurrentIssuance() throws Exception {
        try(var pool=Executors.newFixedThreadPool(6)){
            var start=new CountDownLatch(1);var tasks=new ArrayList<Future<CollectionEncounterFoundation.Issuance>>();
            for(int i=0;i<12;i++)tasks.add(pool.submit(()->{start.await();return foundation.issueNatural();}));
            start.countDown();var ids=new HashSet<UUID>();int issued=0;
            for(var t:tasks){var result=t.get(15,TimeUnit.SECONDS);ids.add(result.encounter().encounterId());if(result.issued())issued++;}
            assertEquals(1,ids.size());assertEquals(1,issued);
            var before=foundation.issueNatural();battles.ignore(ids.iterator().next());
            var blocked=foundation.issueNatural();assertNull(blocked.encounter());assertFalse(blocked.issued());assertEquals(before.nextAvailableAt(),blocked.nextAvailableAt());
        }
        db.update("UPDATE game.t_collection_issuance_budget SET next_available_at=clock_timestamp()-interval '1 second'");
        assertTrue(foundation.issueNatural().issued());
    }
    @Test void insufficientBalanceAndConcurrentReservationCannotOverspend() throws Exception {
        assertThrows(GameFault.class,()->foundation.reserve(UUID.randomUUID(),"PIP",1));award();
        try(var pool=Executors.newFixedThreadPool(4)){
            var start=new CountDownLatch(1);var tasks=new ArrayList<Future<Boolean>>();
            for(int i=0;i<4;i++)tasks.add(pool.submit(()->{start.await();try{foundation.reserve(UUID.randomUUID(),"PIP",1);return true;}catch(GameFault e){return false;}}));
            start.countDown();int accepted=0;for(var t:tasks)if(t.get(15,TimeUnit.SECONDS))accepted++;
            assertEquals(1,accepted);
        }
        assertEquals(0,foundation.progress().available());
    }
    @Test void reservationReplayCancelAndProvisionalRejection() {
        award();var id=UUID.randomUUID();var row=foundation.reserve(id,"PIP",1);
        assertEquals(row,foundation.reserve(id,"PIP",1));assertEquals(0,foundation.progress().available());
        assertThrows(GameFault.class,()->foundation.reserve(id,"NOCT",1));
        assertEquals("RELEASED",foundation.cancel(id).consumptionState());
        assertEquals(1,foundation.progress().available());foundation.cancel(id);assertEquals(1,foundation.progress().available());
        assertEquals("CANCELLED",foundation.reserve(id,"PIP",1).status());
        assertThrows(GameFault.class,()->foundation.reserve(UUID.randomUUID(),"MONSTER_022",1));
    }
    UUID newPip() {return repo.create(1,new MonsterSelector.Selection(repo.monsters().getFirst(),1),repo.now(),repo.activeCompanion(1).level()).encounterId();}
    @Test void consumptionBindsFreshEncounterAtomicallyAndDoesNotFarmObservation() {
        award();var id=UUID.randomUUID();foundation.reserve(id,"PIP",1);
        var eid=new TransactionTemplate(manager).execute(s->{repo.lockPlayer(1);var e=newPip();foundation.consume(id,e);return e;});
        assertEquals(eid,foundation.consume(id,eid).encounterId());
        assertEquals(0,foundation.progress().available());
        assertThrows(GameFault.class,()->foundation.consume(id,UUID.randomUUID()));
        assertThrows(GameFault.class,()->foundation.cancel(id));
        var b=battles.start(eid);assertTrue(battles.capture(b.battleId()).success());
        assertFalse(foundation.recordCompletion(eid));assertEquals(1,foundation.progress().earned());
        assertNull(foundation.issueNatural().encounter());
    }
    @Test void consumeRollbackDoesNotSpendOrLeaveEncounterAndRejectsOldAlphaEncounter() {
        award();var id=UUID.randomUUID();foundation.reserve(id,"PIP",1);
        new TransactionTemplate(manager).execute(s->{repo.lockPlayer(1);foundation.consume(id,newPip());s.setRollbackOnly();return null;});
        assertEquals("PENDING",foundation.reserve(id,"PIP",1).status());
        assertTrue(game.activeEncounter().isEmpty());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_collection_issuance_budget",Integer.class));
        var old=game.createEncounter();assertThrows(GameFault.class,()->foundation.consume(id,old.encounterId()));
        assertEquals("PENDING",foundation.reserve(id,"PIP",1).status());
    }
    @Test void databaseRejectsDuplicateReceiptAndInvalidReservationState() {
        var id=win();foundation.recordCompletion(id);
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("INSERT INTO game.t_observation_receipt(encounter_id,player_id,reason) VALUES (?,1,'VICTORY')",id));
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("""
            INSERT INTO game.t_collection_reservation(reservation_id,player_id,target_monster_id,observation_cost,status,consumption_state)
            SELECT ?,1,monster_id,1,'ISSUED','HELD' FROM game.m_monster WHERE code='PIP'
            """,UUID.randomUUID()));
    }
}
