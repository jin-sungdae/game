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
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/** Disabled rows in a disposable *_test database only, never production seeding. */
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class Batch3PreparationTest {
 static final List<String> CODES=List.of("SHADE","EMBER","LUNET","NOVA","NOCT");
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired JdbcTemplate db; @Autowired GameRepository repository; @Autowired TestRestTemplate http;
 @LocalServerPort int port; @MockitoBean RandomSource random;
 String url(String p){return "http://127.0.0.1:"+port+"/api/v1"+p;}
 @BeforeEach void reset(){clean();db.update("UPDATE game.t_player SET gold=10000");when(random.nextLong(anyLong())).thenReturn(0L);}
 @AfterEach void clean(){
  for(String table:List.of("t_battle_item_effect","t_item_purchase","t_inventory","t_companion_evolution_history","t_reward","t_collection","t_battle","t_encounter"))db.update("DELETE FROM game."+table);
  for(String code:CODES)db.update("DELETE FROM game.m_monster WHERE code=?",code);
  db.update("UPDATE game.t_player SET gold=0");
  db.update("UPDATE game.t_player_companion SET evolution_stage=1,level=1,exp=0,bond=0,active=true");
 }
 GameDtos.Encounter fixture(String code){
  var d=MonsterContent.find(code).orElseThrow();
  assertFalse(d.enabled());assertFalse(d.contentReady());assertEquals("PROVISIONAL",d.productionStatus());
  db.update("INSERT INTO game.m_monster(code,name,rarity,movement_profile,min_level,max_level,encounter_weight,use_yn) VALUES (?,?,?,?,1,3,?,false)",code,d.displayName(),d.rarity(),d.movementProfile(),d.encounterWeight());
  long id=db.queryForObject("SELECT monster_id FROM game.m_monster WHERE code=?",Long.class,code);
  var master=new MonsterSelector.Monster(id,code,d.displayName(),d.rarity(),d.movementProfile(),1,3,d.encounterWeight());
  assertFalse(MonsterContent.eligible(master));
  assertTrue(repository.monsters().stream().noneMatch(m->CODES.contains(m.code())));
  // Explicit fixture bypass of selection, never a production candidate/readiness switch.
  return repository.create(1,new MonsterSelector.Selection(master,1),repository.now());
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
  // Fresh encounter references the same disabled test master, proving repeat count and first timestamp.
  var m=new MonsterSelector.Monster(db.queryForObject("SELECT monster_id FROM game.m_monster WHERE code=?",Long.class,code),code,code,d.rarity(),d.movementProfile(),1,3,weight);
  var next=repository.create(1,new MonsterSelector.Selection(m,1),repository.now());
  var again=start(next);var second=http.postForObject(url("/battles/"+again.battleId()+"/capture"),null,BattleDtos.Capture.class);
  assertEquals(base,second.baseChance(),1e-9);assertEquals(0,second.itemBonus());assertEquals(2,second.collection().captureCount());assertEquals(c.collection().firstCapturedAt(),second.collection().firstCapturedAt());
  if("1".equals(System.getenv("LUMA_BATCH3_LIVE"))){
   repository.create(1,new MonsterSelector.Selection(m,1),repository.now());
   var root=Path.of(System.getProperty("user.dir")).getParent();
   var pb=new ProcessBuilder("cargo","test","--locked","--manifest-path",root.resolve("src-tauri/Cargo.toml").toString(),"live_batch3_fixture","--","--ignored","--nocapture").directory(root.toFile()).inheritIO();
   pb.environment().put("LUMA_GAME_SERVER_URL","http://127.0.0.1:"+port);pb.environment().put("LUMA_BATCH3_CODE",code);
   var process=pb.start();if(!process.waitFor(240,TimeUnit.SECONDS)){process.destroyForcibly();fail("Desktop fixture timeout");}assertEquals(0,process.exitValue());
  }
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
  var d=MonsterContent.find(code).orElseThrow();long id=db.queryForObject("SELECT monster_id FROM game.m_monster WHERE code=?",Long.class,code);
  b=start(repository.create(1,new MonsterSelector.Selection(new MonsterSelector.Monster(id,code,code,d.rarity(),d.movementProfile(),1,3,d.encounterWeight()),1),repository.now()));
  db.update("UPDATE game.t_battle SET companion_hp=1 WHERE battle_id=?",b.battleId());
  b=http.postForObject(url("/battles/"+b.battleId()+"/attack"),null,BattleDtos.Battle.class);assertEquals("DEFEAT",b.status());
 }
 @Test void invalidCaptureInputFailsClosed(){
  assertThrows(GameFault.class,()->CombatRules.captureChance(30,30,null));
  for(String rarity:List.of("UNKNOWN","","common"))assertThrows(GameFault.class,()->CombatRules.captureChance(30,30,rarity));
  for(int[] hp:List.of(new int[]{-1,30},new int[]{31,30},new int[]{0,0}))assertThrows(GameFault.class,()->CombatRules.captureChance(hp[0],hp[1],"RARE"));
 }
}
