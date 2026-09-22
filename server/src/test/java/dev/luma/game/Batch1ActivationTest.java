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

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class Batch1ActivationTest {
 static final List<String> CODES=List.of("PIP","MELLO","MOSSY","CHIRP","BUBU");
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired JdbcTemplate db; @Autowired GameRepository repository; @Autowired TestRestTemplate http; @LocalServerPort int port;
 @MockitoBean RandomSource random;
 String url(String p){return "http://127.0.0.1:"+port+"/api/v1"+p;}
 @BeforeEach void reset(){clean();db.update("UPDATE game.t_player SET gold=10000");when(random.nextLong(anyLong())).thenReturn(0L);}
 @AfterEach void clean(){
  for(String table:List.of("t_battle_item_effect","t_item_purchase","t_inventory","t_companion_evolution_history","t_reward","t_collection","t_battle","t_encounter")) db.update("DELETE FROM game."+table);
  db.update("UPDATE game.m_monster SET use_yn=true");
  db.update("UPDATE game.t_player SET gold=0");
  db.update("UPDATE game.t_player_companion SET evolution_stage=1,level=1,exp=0,bond=0,active=true");
 }
 GameDtos.Encounter create(String code){
  when(random.nextLong(anyLong())).thenAnswer(c->(Long)c.getArgument(0)==500?CODES.indexOf(code)*100L:0L);
  var e=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);assertEquals(code,e.monster().code());return e;
 }
 BattleDtos.Battle start(GameDtos.Encounter e){return http.postForObject(url("/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);}
 @Test void exactMastersAndEqualWeightedSelectionIncludingSeededReplay(){
  var masters=repository.monsters();assertEquals(CODES,masters.stream().map(MonsterSelector.Monster::code).toList());
  for(var m:masters){assertEquals(100,m.weight());assertEquals(1,m.minLevel());assertEquals(3,m.maxLevel());assertTrue(MonsterContent.eligible(m));}
  int[] counts=new int[5];
  for(int point=0;point<500;point++){
   final int selected=point;var selector=new MonsterSelector(bound->bound==500?selected:0);
   var result=selector.select(masters);counts[CODES.indexOf(result.monster().code())]++;assertEquals(1,result.level());
  }
  assertArrayEquals(new int[]{100,100,100,100,100},counts);
  var rng=new Random(42);var selector=new MonsterSelector(rng::nextLong);var seen=new HashSet<String>();
  for(int i=0;i<1000;i++)seen.add(selector.select(masters).monster().code());assertEquals(new HashSet<>(CODES),seen);
 }
 @ParameterizedTest @ValueSource(strings={"PIP","MELLO","MOSSY","CHIRP","BUBU"})
 void capturePersistenceCharmPotionAndRestart(String code){
  var e=create(code); var restored=http.getForObject(url("/encounters/active"),GameDtos.Encounter.class);
  assertEquals(e.encounterId(),restored.encounterId());assertEquals(code,restored.monster().code());
  assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_encounter",Integer.class));
  var b=start(e);assertEquals(30,b.monster().hp());assertEquals(100,b.companion().hp());
  b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);
  assertEquals(18,b.monster().hp());assertEquals(95,b.companion().hp());
  for(String item:List.of("SMALL_POTION","CAPTURE_CHARM"))http.postForObject(url("/shop/purchases"),new ItemDtos.PurchaseRequest(item,1),ItemDtos.Purchase.class);
  var potion=http.postForObject(url("/inventory/items/SMALL_POTION/use"),new ItemDtos.UseRequest(b.battleId()),ItemDtos.Use.class);
  assertEquals(5,potion.healedAmount());assertEquals(100,potion.currentHp());
  http.postForObject(url("/inventory/items/CAPTURE_CHARM/use"),new ItemDtos.UseRequest(b.battleId()),ItemDtos.Use.class);
  var c=http.postForObject(url("/battles/"+b.battleId()+"/capture"),null,BattleDtos.Capture.class);
  assertTrue(c.success());assertEquals(.55,c.baseChance(),1e-9);assertEquals(.1,c.itemBonus(),1e-9);assertEquals(.65,c.finalChance(),1e-9);
  assertEquals(code,c.collection().monsterCode());assertEquals(1,c.collection().captureCount());assertNotNull(c.collection().firstCapturedAt());
  assertEquals(204,http.getForEntity(url("/encounters/active"),String.class).getStatusCode().value());
  var second=start(create(code));var again=http.postForObject(url("/battles/"+second.battleId()+"/capture"),null,BattleDtos.Capture.class);
  assertTrue(again.success());assertEquals(.35,again.baseChance(),1e-9);assertEquals(2,again.collection().captureCount());
  assertEquals(c.collection().firstCapturedAt(),again.collection().firstCapturedAt());
  var collection=http.getForObject(url("/collection"),BattleDtos.Collected[].class);
  assertEquals(1,collection.length);assertEquals(code,collection[0].monsterCode());assertEquals(2,collection[0].captureCount());
 }
 @ParameterizedTest @ValueSource(strings={"PIP","MELLO","MOSSY","CHIRP","BUBU"})
 void victoryDefeatAndMismatchGates(String code){
  var b=start(create(code));while(b.status().equals("ACTIVE"))b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);
  assertEquals("VICTORY",b.status());assertEquals(10,b.reward().gold());assertEquals(20,b.reward().exp());
  http.postForObject(url("/encounters/"+b.encounterId()+"/ignore"),null,String.class);
  b=start(create(code));db.update("UPDATE game.t_battle SET companion_hp=1 WHERE battle_id=?",b.battleId());
  b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);assertEquals("DEFEAT",b.status());
  db.update("UPDATE game.m_monster SET use_yn=false WHERE code=?",code);assertFalse(repository.monsters().stream().anyMatch(m->m.code().equals(code)));
  db.update("UPDATE game.m_monster SET use_yn=true,encounter_weight=99 WHERE code=?",code);
  try{assertThrows(GameUnavailable.class,()->repository.monsters());}finally{db.update("UPDATE game.m_monster SET encounter_weight=100 WHERE code=?",code);}
 }
}
