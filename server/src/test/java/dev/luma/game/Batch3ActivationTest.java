package dev.luma.game;

import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Final production selection through real HTTP and migrated masters, in a disposable *_test DB. */
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class Batch3ActivationTest {
 static final List<String> CODES=List.of("SHADE","EMBER","LUNET","NOVA","NOCT");
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired JdbcTemplate db; @Autowired GameRepository repository; @Autowired TestRestTemplate http;
 @LocalServerPort int port; @MockitoBean RandomSource random;
 String url(String p){return "http://127.0.0.1:"+port+"/api/v1"+p;}
 @BeforeEach void reset(){clean();db.update("UPDATE game.t_player SET gold=10000");when(random.nextLong(anyLong())).thenReturn(0L);}
 @AfterEach void clean(){
  for(String table:List.of("t_battle_item_effect","t_item_purchase","t_inventory","t_companion_evolution_history","t_reward","t_collection","t_battle","t_encounter"))db.update("DELETE FROM game."+table);
  db.update("UPDATE game.m_monster SET use_yn=true");
  db.update("UPDATE game.t_player SET gold=0");
  db.update("UPDATE game.t_player_companion SET evolution_stage=1,level=1,exp=0,bond=0,active=true");
 }
 GameDtos.Encounter fixture(String code){
  var masters=repository.monsters();
  long total=masters.stream().mapToLong(MonsterSelector.Monster::weight).sum();
  long point=0;for(var m:masters){if(m.code().equals(code))break;point+=m.weight();}
  final long selected=point;
  when(random.nextLong(total)).thenReturn(selected);
  var e=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);
  assertEquals(code,e.monster().code());return e;
 }
 BattleDtos.Battle start(GameDtos.Encounter e){return http.postForObject(url("/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);}
 @ParameterizedTest @ValueSource(strings={"SHADE","EMBER","LUNET","NOVA","NOCT"})
 void rarityBattleCaptureCharmPersistenceAndRestore(String code)throws Exception{
  var d=MonsterContent.find(code).orElseThrow();
  double base=switch(d.rarity()){case "UNCOMMON"->.25;case "RARE"->.15;case "SPECIAL"->.05;default->throw new AssertionError();};
  int weight=switch(d.rarity()){case "UNCOMMON"->50;case "RARE"->20;case "SPECIAL"->1;default->throw new AssertionError();};
  assertEquals(weight,d.encounterWeight());assertEquals(base,d.baseCaptureRate());
  assertEquals(weight,MonsterContent.rarity(d.rarity()).encounterWeight());
  for(int hp:new int[]{30,15,0})assertEquals(base+(1-hp/30.0)*.5,CombatRules.captureChance(hp,30,d.rarity()),1e-9);
  var e=fixture(code);
  var restored=http.getForObject(url("/encounters/active"),GameDtos.Encounter.class);
  assertEquals(e.encounterId(),restored.encounterId());assertEquals(code,restored.monster().code());
  assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_encounter",Integer.class));
  var b=start(e);assertEquals(30,b.monster().hp());
  b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);
  assertEquals(18,b.monster().hp());assertEquals(95,b.companion().hp());
  http.postForObject(url("/shop/purchases"),new ItemDtos.PurchaseRequest("CAPTURE_CHARM",1),ItemDtos.Purchase.class);
  http.postForObject(url("/inventory/items/CAPTURE_CHARM/use"),new ItemDtos.UseRequest(b.battleId()),ItemDtos.Use.class);
  var c=http.postForObject(url("/battles/"+b.battleId()+"/capture"),null,BattleDtos.Capture.class);
  assertTrue(c.success());assertEquals(base+.2,c.baseChance(),1e-9);assertEquals(.10,c.itemBonus(),1e-9);assertEquals(base+.3,c.finalChance(),1e-9);
  assertEquals(code,c.collection().monsterCode());assertEquals(1,c.collection().captureCount());
  assertNotNull(c.collection().firstCapturedAt());assertEquals(204,http.getForEntity(url("/encounters/active"),String.class).getStatusCode().value());
  var next=fixture(code);
  var again=start(next);var second=http.postForObject(url("/battles/"+again.battleId()+"/capture"),null,BattleDtos.Capture.class);
  assertEquals(base,second.baseChance(),1e-9);assertEquals(0,second.itemBonus());assertEquals(2,second.collection().captureCount());assertEquals(c.collection().firstCapturedAt(),second.collection().firstCapturedAt());
 }

 @ParameterizedTest @ValueSource(strings={"SHADE","EMBER","LUNET","NOVA","NOCT"})
 void victoryDefeatAndFailedCapture(String code){
  var e=fixture(code);var b=start(e);
  when(random.nextLong(1_000_000)).thenReturn(999999L);
  var failed=http.postForObject(url("/battles/"+b.battleId()+"/capture"),null,BattleDtos.Capture.class);
  assertFalse(failed.success());assertNull(failed.collection());assertEquals(95,failed.battle().companion().hp());
  while(b.status().equals("ACTIVE"))b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);
  assertEquals("VICTORY",b.status());assertEquals(10,b.reward().gold());
  http.postForObject(url("/encounters/"+e.encounterId()+"/ignore"),null,String.class);
  b=start(fixture(code));
  db.update("UPDATE game.t_battle SET companion_hp=1 WHERE battle_id=?",b.battleId());
  b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);assertEquals("DEFEAT",b.status());
 }
 @Test void finalFifteenProductionMastersAndEveryWeightedBoundary(){
  var codes=List.of("PIP","MELLO","MOSSY","CHIRP","BUBU","PEBB","PUFF","TIKKI","MIMI","WISP","SHADE","EMBER","LUNET","NOVA","NOCT");
  var masters=repository.monsters();assertEquals(codes,masters.stream().map(MonsterSelector.Monster::code).toList());
  assertEquals(961,masters.stream().mapToInt(MonsterSelector.Monster::weight).sum());
  assertEquals(15,db.queryForObject("SELECT count(*) FROM game.m_monster WHERE use_yn",Integer.class));
  assertEquals(List.of(7L,4L,3L,1L),List.of("COMMON","UNCOMMON","RARE","SPECIAL").stream().map(r->masters.stream().filter(m->m.rarity().equals(r)).count()).toList());
  for(var m:masters){
   var d=MonsterContent.find(m.code()).orElseThrow();
   assertTrue(d.enabled());assertTrue(d.contentReady());assertEquals("PRODUCTION",d.productionStatus());
   assertEquals(d.displayName(),m.name());assertEquals(d.rarity(),m.rarity());assertEquals(d.movementProfile(),m.movementProfile());
   assertEquals(d.encounterWeight(),m.weight());assertEquals(1,m.minLevel());assertEquals(3,m.maxLevel());assertTrue(MonsterContent.eligible(m));
  }
  for(int level:List.of(1,3)){
   int[] counts=new int[15];
   for(int point=0;point<961;point++){
    final int selected=point;var result=new MonsterSelector(bound->bound==961?selected:level-1).select(masters);
    counts[codes.indexOf(result.monster().code())]++;assertEquals(level,result.level());
   }
   assertArrayEquals(new int[]{100,100,100,100,100,100,100,50,50,50,50,20,20,20,1},counts);
  }
  assertEquals("NIGHT",MonsterContent.find("NOCT").orElseThrow().spawnCondition());
 }
 @ParameterizedTest @ValueSource(strings={"SHADE","EMBER","LUNET","NOVA","NOCT"})
 void mismatchedMasterFailsClosedAndDisabledRowsAreExcluded(String code){
  var d=MonsterContent.find(code).orElseThrow();
  db.update("UPDATE game.m_monster SET use_yn=false WHERE code=?",code);
  assertEquals(14,repository.monsters().size());assertTrue(repository.monsters().stream().noneMatch(m->m.code().equals(code)));
  db.update("UPDATE game.m_monster SET use_yn=true WHERE code=?",code);
  for(String assignment:List.of("name='Wrong'","rarity='EPIC'","movement_profile='GROUND'","encounter_weight=99","min_level=2","max_level=4")){
   db.update("UPDATE game.m_monster SET "+assignment+" WHERE code=?",code);
   try{assertThrows(GameUnavailable.class,()->repository.monsters());}
   finally{db.update("UPDATE game.m_monster SET name=?,rarity=?,movement_profile=?,encounter_weight=?,min_level=1,max_level=3 WHERE code=?",d.displayName(),d.rarity(),d.movementProfile(),d.encounterWeight(),code);}
  }
 }
 @Test void invalidCaptureInputFailsClosed(){
  assertThrows(GameFault.class,()->CombatRules.captureChance(30,30,null));
  for(String rarity:List.of("UNKNOWN","","common"))assertThrows(GameFault.class,()->CombatRules.captureChance(30,30,rarity));
  for(int[] hp:List.of(new int[]{-1,30},new int[]{31,30},new int[]{0,0}))assertThrows(GameFault.class,()->CombatRules.captureChance(hp[0],hp[1],"RARE"));
 }
}
