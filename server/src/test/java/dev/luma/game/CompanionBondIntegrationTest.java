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
import java.time.OffsetDateTime;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class CompanionBondIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired TestRestTemplate http;@Autowired JdbcTemplate db;@LocalServerPort int port;
 @MockitoBean RandomSource random;
 String url(String path){return "http://127.0.0.1:"+port+"/api/v1"+path;}
 @BeforeEach void reset(){clean(db);when(random.nextLong(anyLong())).thenReturn(0L);}
 @AfterEach void cleanup(){clean(db);}
 static void clean(JdbcTemplate db){
  for(String table:List.of("t_battle_item_effect","t_item_purchase","t_inventory","t_companion_evolution_history","t_reward","t_collection","t_battle","t_encounter"))db.update("DELETE FROM game."+table);
  db.update("UPDATE game.t_player SET gold=0");
  db.update("UPDATE game.t_player_companion SET evolution_stage=1,level=1,exp=0,bond=0,active=true,last_bond_interaction_at=NULL");
  db.update("UPDATE game.m_monster SET use_yn=true");
 }
 GameDtos.Bootstrap bootstrap(){return http.getForObject(url("/game/bootstrap"),GameDtos.Bootstrap.class);}
 CompanionInteractionService.Result interact(){return http.postForObject(url("/companions/active/interact"),null,CompanionInteractionService.Result.class);}
 EvolutionDtos.Status status(){return http.getForObject(url("/companions/active/evolution"),EvolutionDtos.Status.class);}
 EvolutionDtos.Result evolve(){return http.postForObject(url("/companions/active/evolve"),null,EvolutionDtos.Result.class);}
 void expireCooldown(){db.update("UPDATE game.t_player_companion SET last_bond_interaction_at=clock_timestamp()-interval '300 seconds'");}
 OffsetDateTime stamp(){return db.queryForObject("SELECT last_bond_interaction_at FROM game.t_player_companion WHERE active",OffsetDateTime.class);}
 BattleDtos.Battle win(){
  var e=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);
  var b=http.postForObject(url("/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);
  while(b.status().equals("ACTIVE"))b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);
  assertEquals("VICTORY",b.status());
  http.postForEntity(url("/encounters/"+e.encounterId()+"/ignore"),null,String.class);return b;
 }
 ItemDtos.Use berry(){return http.postForObject(url("/inventory/items/BOND_BERRY/use"),null,ItemDtos.Use.class);}
 void buy(int quantity){assertEquals(200,http.postForEntity(url("/shop/purchases"),new ItemDtos.PurchaseRequest("BOND_BERRY",quantity),String.class).getStatusCode().value());}
 @Test void firstCooldownOneMinuteAndExpiryUseDbTime(){
  var a=interact();assertEquals(CompanionInteractionService.Outcome.AWARDED,a.outcome());assertEquals(1,a.bondDelta());
  assertEquals(300,java.time.Duration.between(a.serverTime(),a.nextAvailableAt()).toSeconds());
  var original=stamp();var b=interact();assertEquals(CompanionInteractionService.Outcome.COOLDOWN,b.outcome());assertEquals(0,b.bondDelta());assertEquals(original,stamp());
  db.update("UPDATE game.t_player_companion SET last_bond_interaction_at=clock_timestamp()-interval '60 seconds'");
  assertEquals(CompanionInteractionService.Outcome.COOLDOWN,interact().outcome());
  expireCooldown();assertEquals(CompanionInteractionService.Outcome.AWARDED,interact().outcome());assertEquals(2,bootstrap().activeCompanion().bond());
 }
 @Test void concurrentHttpInteractionsAwardExactlyOnce() throws Exception {
  try(var pool=Executors.newFixedThreadPool(12)){
   var gate=new CountDownLatch(1);var tasks=new ArrayList<Future<CompanionInteractionService.Result>>();
   for(int i=0;i<12;i++)tasks.add(pool.submit(()->{gate.await();return interact();}));gate.countDown();
   int awarded=0;var times=new HashSet<java.time.Instant>();
   for(var task:tasks){var r=task.get(15,TimeUnit.SECONDS);awarded+=r.bondDelta();times.add(r.nextAvailableAt());}
   assertEquals(1,awarded);assertEquals(1,times.size());assertEquals(1,bootstrap().activeCompanion().bond());
  }
 }
 @Test void clientFieldsCannotBypassCooldown(){
  for(String body:List.of("{\"bond\":99}","{\"timestamp\":\"2099-01-01\"}","{}"))
   assertEquals(400,http.postForEntity(url("/companions/active/interact"),body,String.class).getStatusCode().value());
  assertEquals(400,http.postForEntity(url("/companions/active/interact?cooldown=0"),null,String.class).getStatusCode().value());
  assertEquals(0,bootstrap().activeCompanion().bond());assertNull(stamp());
 }
 @Test void berryIsIndependentAndOneOwnedItemCannotBeConsumedTwiceConcurrently() throws Exception {
  for(int i=0;i<3;i++)win(); // real Gold30; Battle grants zero Bond
  interact();var timestamp=stamp();buy(1);
  try(var pool=Executors.newFixedThreadPool(2)){
   var gate=new CountDownLatch(1);var tasks=new ArrayList<Future<Integer>>();
   for(int i=0;i<2;i++)tasks.add(pool.submit(()->{gate.await();return http.postForEntity(url("/inventory/items/BOND_BERRY/use"),null,String.class).getStatusCode().value();}));gate.countDown();
   var codes=new ArrayList<Integer>();for(var task:tasks)codes.add(task.get(10,TimeUnit.SECONDS));
   assertEquals(1,Collections.frequency(codes,200));assertEquals(1,Collections.frequency(codes,409));
  }
  assertEquals(2,bootstrap().activeCompanion().bond());assertEquals(timestamp,stamp());assertEquals(CompanionInteractionService.Outcome.COOLDOWN,interact().outcome());
  assertEquals(0,db.queryForObject("SELECT quantity FROM game.t_inventory",Integer.class));
 }
 @Test void naturalBattleThenInteractionReachesBothStagesAndBerryResolvesEleven(){
  for(int i=0;i<75;i++){var b=win();assertEquals(0,b.reward().bond());assertEquals(20,b.reward().exp());}
  assertEquals(1500,bootstrap().activeCompanion().exp());assertEquals(0,bootstrap().activeCompanion().bond());assertEquals(EvolutionDtos.State.LOCKED,status().status());
  // Only the test clock fixture advances. EXP/Bond/stage are changed exclusively via production commands.
  for(int i=1;i<=11;i++){
   if(i>1)expireCooldown();var r=interact();assertEquals(i,r.bootstrap().activeCompanion().bond());
   if(i==4)assertEquals(EvolutionDtos.State.LOCKED,status().status());
   if(i==5){assertEquals(EvolutionDtos.State.AVAILABLE,r.evolution().status());assertEquals(2,evolve().bootstrap().activeCompanion().evolutionStage());}
   if(i==8 || i==11)assertEquals(EvolutionDtos.State.LOCKED,status().status());
  }
  buy(1);var timestamp=stamp();assertEquals(12,berry().bondAfter());assertEquals(timestamp,stamp());
  assertEquals(EvolutionDtos.State.AVAILABLE,status().status());assertEquals(3,evolve().bootstrap().activeCompanion().evolutionStage());
  assertEquals(720,bootstrap().player().gold());assertEquals(1500,bootstrap().activeCompanion().exp());
 }
 @Test void interactionAloneReachesBondButNotLevelGate(){
  for(int i=0;i<12;i++){if(i>0)expireCooldown();interact();}
  var c=bootstrap().activeCompanion();assertEquals(1,c.level());assertEquals(0,c.exp());assertEquals(12,c.bond());assertEquals(EvolutionDtos.State.LOCKED,status().status());
 }
 @Test void existingHighBondAndNeblaNeverRecomputedByBattleOrBootstrap(){
  for(int bond:new int[]{5,12,30,75}){
   db.update("UPDATE game.t_player_companion SET evolution_stage=3,level=6,exp=1500,bond=?",bond);
   var b=win();var c=bootstrap().activeCompanion();assertEquals(0,b.reward().bond());assertEquals(bond,c.bond());assertEquals(3,c.evolutionStage());assertEquals(1520,c.exp());
  }
 }
 @Test void overflowDoesNotConsumeCooldown(){
  db.update("UPDATE game.t_player_companion SET bond=2147483647");
  assertEquals(409,http.postForEntity(url("/companions/active/interact"),null,String.class).getStatusCode().value());
  assertNull(stamp());assertEquals(Integer.MAX_VALUE,bootstrap().activeCompanion().bond());
 }
}
