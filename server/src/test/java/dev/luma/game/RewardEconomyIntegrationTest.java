package dev.luma.game;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.luma.game.command.CommandReceiptExecutor;
import dev.luma.game.economy.*;
import static dev.luma.game.economy.RewardEntitlement.*;
import java.time.LocalDate;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.*;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.UnexpectedRollbackException;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(properties={"luma.economy.rewards-enabled=true","spring.datasource.hikari.maximum-pool-size=2"})
@DirtiesContext(classMode=DirtiesContext.ClassMode.AFTER_CLASS)
class RewardEconomyIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate db;
    @Autowired RewardEconomy economy;
    @Autowired GameRepository repo;
    @Autowired CommandReceiptExecutor commands;
    @Autowired ObjectMapper json;
    @Autowired PlatformTransactionManager manager;
    private final List<Long> players=new ArrayList<>();
    long player;
    @BeforeEach void setup(){player=player();}
    long player(){
        long id=db.queryForObject("INSERT INTO game.t_player(player_name) VALUES (?) RETURNING player_id",
            Long.class,"economy-"+UUID.randomUUID());
        players.add(id);return id;
    }
    @AfterEach void cleanup(){
        // Test-only disposable database. Runtime API and SQL deny history UPDATE/DELETE.
        db.execute("TRUNCATE game.t_economy_reward_ledger,game.t_reward_entitlement_item,game.t_reward_entitlement");
        for(long id:players){
            db.update("DELETE FROM game.t_command_receipt WHERE player_id=?",id);
            db.update("DELETE FROM game.t_inventory WHERE player_id=?",id);
            db.update("DELETE FROM game.t_player WHERE player_id=?",id);
        }
    }
    Key weekly(){return Key.weekly(player,LocalDate.of(2026,10,12),"SLOT_1");}
    Terms terms(){return new Terms("TEST_V1",7,Map.of("SMALL_POTION",2));}
    long gold(){return db.queryForObject("SELECT gold FROM game.t_player WHERE player_id=?",Long.class,player);}
    int count(String table){return db.queryForObject("SELECT count(*) FROM game."+table+" WHERE player_id=?",Integer.class,player);}
    int quantity(){return db.queryForObject("SELECT COALESCE(sum(quantity),0) FROM game.t_inventory WHERE player_id=?",Integer.class,player);}

    @Test void duplicateEntitlementAndChangedPolicyReturnOriginalTerms(){
        var first=economy.entitle(weekly(),terms());
        assertEquals(first,economy.entitle(weekly(),terms()));
        assertEquals(first,economy.entitle(weekly(),new Terms("TEST_V2",999,Map.of())));
        assertEquals(0,gold());assertEquals(0,count("t_economy_reward_ledger"));
        assertEquals(1,count("t_reward_entitlement"));
        assertTrue(economy.claim(player,first.id(),UUID.randomUUID()).granted());
        assertFalse(economy.claim(player,economy.entitle(weekly(),new Terms("TEST_V3",123,Map.of())).id(),UUID.randomUUID()).granted());
        assertEquals(7,gold());assertEquals(2,quantity());
    }
    @Test void domainIdentitySeparatesSlotWeekCampaignTypeMilestoneAndPlayer(){
        var keys=List.of(weekly(),Key.weekly(player,LocalDate.of(2026,10,12),"SLOT_2"),
            Key.weekly(player,LocalDate.of(2026,10,19),"SLOT_1"),
            Key.collection(player,"ALPHA",Type.COLLECTION_DISCOVERY,5),
            Key.collection(player,"ALPHA",Type.COLLECTION_CAPTURE,5),
            Key.collection(player,"ALPHA",Type.COLLECTION_CAPTURE,10),
            Key.collection(player,"BETA",Type.COLLECTION_CAPTURE,5));
        var ids=new HashSet<UUID>();
        for(var key:keys)ids.add(economy.entitle(key,terms()).id());
        assertEquals(keys.size(),ids.size());
        long other=player();
        var distinct=economy.entitle(Key.weekly(other,weekly().weekStart(),"SLOT_1"),terms());
        assertFalse(ids.contains(distinct.id()));
        assertThrows(GameFault.class,()->economy.claim(player,distinct.id(),UUID.randomUUID()));
        assertEquals(0,gold());assertEquals(0,count("t_command_receipt"));
    }
    @Test void concurrentEntitlementCreationHasOneIdentity() throws Exception {
        try(var pool=Executors.newFixedThreadPool(6)){
            var gate=new CountDownLatch(1);var futures=new ArrayList<Future<UUID>>();
            for(int i=0;i<12;i++)futures.add(pool.submit(()->{gate.await();return economy.entitle(weekly(),terms()).id();}));
            gate.countDown();var ids=new HashSet<UUID>();
            for(var f:futures)ids.add(f.get(15,TimeUnit.SECONDS));
            assertEquals(1,ids.size());assertEquals(1,count("t_reward_entitlement"));
        }
    }
    @Test void differentCommandsConcurrentClaimPayExactlyOnce() throws Exception {
        var right=economy.entitle(weekly(),terms());
        try(var pool=Executors.newFixedThreadPool(6)){
            var gate=new CountDownLatch(1);var futures=new ArrayList<Future<Claim>>();
            for(int i=0;i<12;i++)futures.add(pool.submit(()->{gate.await();return economy.claim(player,right.id(),UUID.randomUUID());}));
            gate.countDown();int granted=0;
            for(var f:futures)if(f.get(15,TimeUnit.SECONDS).granted())granted++;
            assertEquals(1,granted);
        }
        assertEquals(7,gold());assertEquals(2,quantity());
        assertEquals(1,count("t_economy_reward_ledger"));assertEquals(12,count("t_command_receipt"));
    }
    @Test void sameCommandConcurrentReplayAndWrongTargetAreSafe() throws Exception {
        var right=economy.entitle(weekly(),terms());var command=UUID.randomUUID();
        try(var pool=Executors.newFixedThreadPool(4)){
            var gate=new CountDownLatch(1);var futures=new ArrayList<Future<Claim>>();
            for(int i=0;i<8;i++)futures.add(pool.submit(()->{gate.await();return economy.claim(player,right.id(),command);}));
            gate.countDown();for(var f:futures)assertTrue(f.get(15,TimeUnit.SECONDS).granted());
        }
        assertEquals(7,gold());assertEquals(2,quantity());assertEquals(1,count("t_command_receipt"));
        var other=economy.entitle(Key.collection(player,"ALPHA",Type.COLLECTION_CAPTURE,1),terms());
        assertEquals("COMMAND_ID_REUSED",assertThrows(GameFault.class,()->economy.claim(player,other.id(),command)).getMessage());
    }
    @Test void inventoryFailureRollsBackGoldLedgerReceiptAndRetryWorks(){
        var right=economy.entitle(weekly(),terms());var command=UUID.randomUUID();
        db.update("INSERT INTO game.t_inventory(player_id,item_id,quantity) SELECT ?,item_id,99 FROM game.m_item WHERE item_code='SMALL_POTION'",player);
        assertThrows(GameFault.class,()->economy.claim(player,right.id(),command));
        assertEquals(0,gold());assertEquals(99,quantity());
        assertEquals(0,count("t_economy_reward_ledger"));assertEquals(0,count("t_command_receipt"));
        db.update("UPDATE game.t_inventory SET quantity=97 WHERE player_id=?",player);
        assertTrue(economy.claim(player,right.id(),command).granted());
        assertEquals(7,gold());assertEquals(99,quantity());
    }
    @Test void lateItemFailureRollsBackEarlierItemAndGold(){
        var right=economy.entitle(weekly(),new Terms("TEST_V1",7,Map.of("BOND_BERRY",1,"SMALL_POTION",2)));
        db.update("INSERT INTO game.t_inventory(player_id,item_id,quantity) SELECT ?,item_id,99 FROM game.m_item WHERE item_code='SMALL_POTION'",player);
        assertThrows(GameFault.class,()->economy.claim(player,right.id(),UUID.randomUUID()));
        assertEquals(0,gold());assertEquals(99,quantity());assertEquals(0,count("t_economy_reward_ledger"));
        assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_inventory WHERE player_id=?",Integer.class,player));
    }
    @Test void outerRollbackAndCaughtFailureCannotPartiallyCommit(){
        var right=economy.entitle(weekly(),terms());
        var tx=new TransactionTemplate(manager);
        tx.executeWithoutResult(s->{economy.claim(player,right.id(),UUID.randomUUID());s.setRollbackOnly();});
        assertEquals(0,gold());assertEquals(0,quantity());assertEquals(0,count("t_economy_reward_ledger"));
        assertEquals(0,count("t_command_receipt"));
        assertThrows(UnexpectedRollbackException.class,()->tx.executeWithoutResult(s->{
            try {economy.claim(player,UUID.randomUUID(),UUID.randomUUID());}catch(GameFault ignored){}
            db.update("UPDATE game.t_player SET gold=10 WHERE player_id=?",player);
        }));
        assertEquals(0,gold());
    }
    @Test void entitlementCreationRollbackLeavesNoPartialSnapshot(){
        assertThrows(GameFault.class,()->economy.entitle(weekly(),new Terms("TEST_V1",7,Map.of("UNKNOWN_ITEM",1))));
        assertEquals(0,count("t_reward_entitlement"));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_reward_entitlement_item",Integer.class));
    }
    @Test void goldOverflowRollsBackEverything(){
        var right=economy.entitle(weekly(),terms());
        db.update("UPDATE game.t_player SET gold=? WHERE player_id=?",Long.MAX_VALUE,player);
        assertThrows(org.springframework.dao.DataAccessException.class,()->economy.claim(player,right.id(),UUID.randomUUID()));
        assertEquals(Long.MAX_VALUE,gold());assertEquals(0,quantity());
        assertEquals(0,count("t_economy_reward_ledger"));assertEquals(0,count("t_command_receipt"));
    }
    @Test void databaseEnforcesSemanticUniquenessOwnershipAndHistory(){
        var right=economy.entitle(weekly(),terms());
        assertThrows(DataIntegrityViolationException.class,()->db.update("""
            INSERT INTO game.t_reward_entitlement
            SELECT ?,player_id,reward_type,week_start,reward_slot,campaign_id,milestone,policy_version,gold,created_at
            FROM game.t_reward_entitlement WHERE entitlement_id=?
            """,UUID.randomUUID(),right.id()));
        long other=player();
        assertThrows(DataIntegrityViolationException.class,()->db.update(
            "INSERT INTO game.t_economy_reward_ledger(entitlement_id,player_id,command_id) VALUES (?,?,?)",right.id(),other,UUID.randomUUID()));
        economy.claim(player,right.id(),UUID.randomUUID());
        for(String table:List.of("t_reward_entitlement","t_reward_entitlement_item","t_economy_reward_ledger")){
            assertThrows(DataIntegrityViolationException.class,()->db.update("DELETE FROM game."+table+" WHERE entitlement_id=?",right.id()));
        }
        assertThrows(DataIntegrityViolationException.class,()->db.update("UPDATE game.t_reward_entitlement SET policy_version='TEST_V2' WHERE entitlement_id=?",right.id()));
        assertEquals(7,gold());
    }
    @Test void disabledFoundationCannotMintOrClaim(){
        var disabled=new RewardEconomy(db,repo,commands,json,false);
        assertEquals("ECONOMY_REWARDS_DISABLED",assertThrows(GameFault.class,()->disabled.entitle(weekly(),terms())).getMessage());
        assertThrows(GameFault.class,()->disabled.claim(player,UUID.randomUUID(),UUID.randomUUID()));
        assertEquals(0,count("t_reward_entitlement"));assertEquals(0,gold());
    }
}
