package dev.luma.game;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class ProgressionIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired TestRestTemplate http;@Autowired JdbcTemplate db;@LocalServerPort int port;
 @MockitoBean RandomSource random;
 String url(String p){return "http://127.0.0.1:"+port+"/api/v1"+p;}
 @BeforeEach void reset(){clean();when(random.nextLong(anyLong())).thenReturn(0L);}
 @AfterEach void clean(){
  db.update("DELETE FROM game.t_battle_item_effect");db.update("DELETE FROM game.t_item_purchase");db.update("DELETE FROM game.t_inventory");
  db.update("DELETE FROM game.t_companion_evolution_history");db.update("DELETE FROM game.t_reward");db.update("DELETE FROM game.t_collection");db.update("DELETE FROM game.t_battle");db.update("DELETE FROM game.t_encounter");
  db.update("UPDATE game.t_player SET gold=0");db.update("UPDATE game.t_player_companion SET evolution_stage=1,exp=0,level=1,bond=0,active=true");
 }
 GameDtos.Bootstrap bootstrap(){return http.getForObject(url("/game/bootstrap"),GameDtos.Bootstrap.class);}
 EvolutionDtos.Status status(){return http.getForObject(url("/companions/active/evolution"),EvolutionDtos.Status.class);}
 EvolutionDtos.Result evolve(){return http.postForObject(url("/companions/active/evolve"),null,EvolutionDtos.Result.class);}
 BattleDtos.Battle start(){var e=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);return http.postForObject(url("/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);}
 BattleDtos.Battle attack(UUID id){return http.postForObject(url("/battles/"+id+"/attack"),null,BattleDtos.Battle.class);}
 BattleDtos.Battle win(){var b=start();while(b.status().equals("ACTIVE"))b=attack(b.battleId());assertEquals("VICTORY",b.status());return b;}
 void resolve(BattleDtos.Battle b){assertEquals(200,http.postForEntity(url("/encounters/"+b.encounterId()+"/ignore"),null,String.class).getStatusCode().value());}
 @Test void naturalSeventyFiveBattlesReachSixButDoNotUnlockBondGate(){
  for(int i=1;i<=75;i++){
   var b=win();assertEquals(20,b.reward().exp());assertEquals(0,b.reward().bond());resolve(b);
   var c=bootstrap().activeCompanion();assertEquals(i*20L,c.exp());assertEquals(0,c.bond());
   if(i==15)assertEquals(EvolutionDtos.State.LOCKED,status().status());
   if(i==50)assertEquals(5,c.level());
  }
  assertEquals(6,bootstrap().activeCompanion().level());assertEquals(1,bootstrap().activeCompanion().evolutionStage());
  assertEquals(EvolutionDtos.State.LOCKED,status().status());
  assertEquals(750,bootstrap().player().gold());
  assertEquals(75,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
 }
 @Test void battleCrossesSixBerryUnlocksAndSevenRemainsReachable(){
  db.update("UPDATE game.t_player_companion SET evolution_stage=2,level=5,exp=1480,bond=11");db.update("UPDATE game.t_player SET gold=100");
  var b=win();resolve(b);var c=bootstrap().activeCompanion();assertEquals(6,c.level());assertEquals(1500,c.exp());assertEquals(11,c.bond());
  assertEquals(EvolutionDtos.State.LOCKED,status().status());
  http.postForObject(url("/shop/purchases"),new ItemDtos.PurchaseRequest("BOND_BERRY",1),ItemDtos.Purchase.class);
  var berry=http.postForObject(url("/inventory/items/BOND_BERRY/use"),null,ItemDtos.Use.class);assertEquals(12,berry.bondAfter());
  assertEquals(EvolutionDtos.State.AVAILABLE,status().status());assertEquals("NEBLA",evolve().bootstrap().activeCompanion().evolutionName());
  for(int i=0;i<30;i++){b=win();resolve(b);}
  assertEquals(7,bootstrap().activeCompanion().level());assertEquals(2100,bootstrap().activeCompanion().exp());assertEquals(3,bootstrap().activeCompanion().evolutionStage());
 }
 @Test void simultaneousWinningAttacksNeverDuplicateOrLoseReward() throws Exception {
  db.update("UPDATE game.t_player_companion SET level=5,exp=1480,bond=10");var b=start();attack(b.battleId());
  try(var pool=Executors.newFixedThreadPool(4)){
   var gate=new CountDownLatch(1);var tasks=new ArrayList<Future<Integer>>();
   for(int i=0;i<4;i++)tasks.add(pool.submit(()->{gate.await();return http.postForEntity(url("/battles/"+b.battleId()+"/attack"),null,String.class).getStatusCode().value();}));gate.countDown();
   var results=new ArrayList<Integer>();for(var task:tasks)results.add(task.get(10,TimeUnit.SECONDS));assertEquals(1,Collections.frequency(results,200));assertEquals(3,Collections.frequency(results,409));
  }
  assertEquals(1500,bootstrap().activeCompanion().exp());assertEquals(6,bootstrap().activeCompanion().level());assertEquals(10,bootstrap().activeCompanion().bond());
  assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
 }
 @Test void legacyCappedExpReconcilesOnNextRewardWithLevelUpEvent(){
  db.update("UPDATE game.t_player_companion SET level=5,exp=3000,bond=10");
  var b=win();assertEquals(3020,bootstrap().activeCompanion().exp());assertEquals(8,bootstrap().activeCompanion().level());
  assertTrue(b.events().contains("LEVEL_UP"));assertEquals(20,b.reward().exp());
 }
 @Test void maxLevelKeepsExpAndOverflowRollsBackWholeReward(){
  db.update("UPDATE game.t_player_companion SET level=20,exp=?",Long.MAX_VALUE-20);
  var b=win();resolve(b);assertEquals(Long.MAX_VALUE,bootstrap().activeCompanion().exp());assertEquals(20,bootstrap().activeCompanion().level());
  var before=bootstrap();b=start();var response=http.postForEntity(url("/battles/"+b.battleId()+"/attack"),null,String.class);
  assertTrue(response.getStatusCode().is5xxServerError());assertEquals(before,bootstrap());
  assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
  var unchanged=http.getForObject(url("/battles/"+b.battleId()),BattleDtos.Battle.class);assertEquals(0,unchanged.turn());assertEquals("ACTIVE",unchanged.status());
 }
}
