package dev.luma.game;
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
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class DiscoveryIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate db;
    @Autowired DiscoveryService service;
    @Autowired BattleService battles;
    @org.springframework.test.context.bean.override.mockito.MockitoBean RandomSource random;
    @Autowired GameRepository repo;
    @Autowired PlatformTransactionManager manager;
    @Autowired TestRestTemplate http;
    @LocalServerPort int port;
    String url(String path){return "http://127.0.0.1:"+port+"/api/v1"+path;}
    @BeforeEach @AfterEach void clean(){
        db.update("DELETE FROM game.t_reward");db.update("DELETE FROM game.t_battle");
        db.update("DELETE FROM game.t_encounter");db.update("DELETE FROM game.t_monster_discovery");db.update("DELETE FROM game.t_collection");
        db.update("UPDATE game.m_monster SET use_yn=true");
    }
    UUID encounter(String code){
        var id=UUID.randomUUID();
        // Resolved encounter fixtures allow concurrent acknowledgement of earlier placements.
        db.update("""
            INSERT INTO game.t_encounter(encounter_id,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at,resolved_at,created_at,updated_at)
            SELECT ?,1,monster_id,1,rarity,'EXPIRED',clock_timestamp()-interval '61 seconds',clock_timestamp()-interval '1 second',clock_timestamp(),clock_timestamp(),clock_timestamp()
            FROM game.m_monster WHERE code=?
            """,id,code);return id;
    }
    DiscoveryService.Entry entry(String code){int no=MonsterContent.find(code).orElseThrow().dexNo();return service.dex().stream().filter(e->e.dexNo()==no).findFirst().orElseThrow();}
    @Test void firstRediscoveryIdempotencyAndTimestamps(){
        var id=encounter("WISP");assertEquals("UNDISCOVERED",entry("WISP").state());
        var first=service.discover("WISP",id);assertEquals(1,first.encounterCount());assertEquals("DISCOVERED",first.state());
        assertEquals(first,service.discover("WISP",id));
        var second=service.discover("WISP",encounter("WISP"));assertEquals(2,second.encounterCount());
        assertEquals(first.firstDiscoveredAt(),second.firstDiscoveredAt());assertTrue(second.lastSeenAt().isAfter(first.lastSeenAt()));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_collection",Integer.class));
    }
    @Test void concurrentDistinctAndDuplicateAcknowledgements() throws Exception {
        var ids=new ArrayList<UUID>();for(int i=0;i<8;i++)ids.add(encounter("WISP"));
        try(var pool=Executors.newFixedThreadPool(8)){
            var gate=new CountDownLatch(1);var futures=new ArrayList<Future<?>>();
            for(var id:ids)for(int duplicate=0;duplicate<2;duplicate++)futures.add(pool.submit(()->{gate.await();return service.discover("WISP",id);}));
            gate.countDown();for(var f:futures)f.get(15,TimeUnit.SECONDS);
        }
        assertEquals(8,entry("WISP").encounterCount());assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_monster_discovery",Integer.class));
        assertEquals(8,db.queryForObject("SELECT count(*) FROM game.t_monster_discovery_receipt",Integer.class));
    }
    void captured(String code){new TransactionTemplate(manager).execute(s->{repo.lockPlayer(1);db.update("""
        INSERT INTO game.t_collection(player_id,monster_id,capture_count,first_captured_at,last_captured_at)
        SELECT 1,monster_id,1,clock_timestamp(),clock_timestamp() FROM game.m_monster WHERE code=?
        ON CONFLICT(player_id,monster_id) DO UPDATE SET capture_count=game.t_collection.capture_count+1,last_captured_at=EXCLUDED.last_captured_at
        """,code);return null;});}
    @Test void historicalCaptureAndDiscoveryRaceNeverDowngrade() throws Exception {
        captured("PIP");assertEquals("CAPTURED",entry("PIP").state());assertEquals(0,entry("PIP").encounterCount());
        var id=encounter("WISP");
        db.update("UPDATE game.t_encounter SET status='ACTIVE',spawned_at=clock_timestamp(),expires_at=clock_timestamp()+interval '60 seconds',resolved_at=NULL WHERE encounter_id=?",id);
        var battle=battles.start(id);
        try(var pool=Executors.newFixedThreadPool(2)){
            var gate=new CountDownLatch(1);
            var a=pool.submit(()->{gate.await();return service.discover("WISP",id);});
            var b=pool.submit(()->{gate.await();return battles.capture(battle.battleId());});gate.countDown();a.get(10,TimeUnit.SECONDS);assertTrue(b.get(10,TimeUnit.SECONDS).success());
        }
        assertEquals("CAPTURED",entry("WISP").state());assertEquals("CAPTURED",service.discover("WISP",id).state());
    }
    @Test void transactionRollbackIncludesReceiptAndAggregate(){
        var id=encounter("PIP");new TransactionTemplate(manager).execute(s->{service.discover("PIP",id);s.setRollbackOnly();return null;});
        assertEquals("UNDISCOVERED",entry("PIP").state());assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_monster_discovery_receipt",Integer.class));
        assertEquals(1,service.discover("PIP",id).encounterCount());
    }
    @Test void allFifteenIdentitiesAndReconstructedService(){
        var alpha=MonsterContent.definitions().stream().filter(MonsterContent.Definition::alphaCandidate).toList();assertEquals(15,alpha.size());
        for(var d:alpha){var row=service.discover(d.monsterCode(),encounter(d.monsterCode()));assertEquals(d.assetIdentity(),row.assetIdentity());assertEquals("/assets/monsters/"+d.assetIdentity()+"/base.png",row.baseAsset());}
        assertEquals(service.dex(),new DiscoveryService(db,new GameRepository(db)).dex());
    }
    @Test void maskingAndUntrustedCommands(){
        var json=http.getForObject(url("/dex"),String.class);assertFalse(json.contains("monsterName"));assertFalse(json.contains("assetIdentity"));assertFalse(json.contains("baseAsset"));assertFalse(json.contains("monsterCode"));
        var id=encounter("PIP");
        for(var code:List.of("UNKNOWN","WISP"))assertTrue(http.postForEntity(url("/monsters/"+code+"/discoveries"),Map.of("encounterId",id),String.class).getStatusCode().is4xxClientError());
        for(var field:List.of("playerId","monsterId","rarity","count","timestamp"))assertEquals(400,http.postForEntity(url("/monsters/PIP/discoveries"),Map.of("encounterId",id,field,"injected"),String.class).getStatusCode().value());
        db.update("UPDATE game.m_monster SET use_yn=false WHERE code='PIP'");assertThrows(GameFault.class,()->service.discover("PIP",id));
        db.update("UPDATE game.m_monster SET use_yn=true WHERE code='PIP'");
        var row=http.postForObject(url("/monsters/PIP/discoveries"),Map.of("encounterId",id),DiscoveryService.Entry.class);assertEquals("DISCOVERED",row.state());
    }
}
