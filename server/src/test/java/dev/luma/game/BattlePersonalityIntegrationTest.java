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
class BattlePersonalityIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired JdbcTemplate db;@Autowired GameRepository repository;@Autowired TestRestTemplate http;@LocalServerPort int port;@MockitoBean RandomSource random;
 String url(String p){return "http://127.0.0.1:"+port+"/api/v1"+p;}
 @BeforeEach void reset(){clean();db.update("UPDATE game.t_player SET gold=10000");when(random.nextLong(anyLong())).thenReturn(0L);}
 @AfterEach void clean(){
  for(String t:List.of("t_battle_item_effect","t_item_purchase","t_inventory","t_companion_evolution_history","t_reward","t_collection","t_battle","t_encounter"))db.update("DELETE FROM game."+t);
  db.update("UPDATE game.m_monster SET use_yn=true");db.update("UPDATE game.t_player SET gold=0");db.update("UPDATE game.t_player_companion SET evolution_stage=1,level=1,exp=0,bond=0,active=true");
 }
 BattleDtos.Battle start(String code){
  var list=repository.monsters();long total=list.stream().mapToLong(MonsterSelector.Monster::weight).sum(),point=0;
  for(var m:list){if(m.code().equals(code))break;point+=m.weight();}when(random.nextLong(total)).thenReturn(point);
  var e=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);assertEquals(code,e.monster().code());
  return http.postForObject(url("/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);
 }
 BattleDtos.Battle attack(UUID id){return http.postForObject(url("/battles/"+id+"/attack"),null,BattleDtos.Battle.class);}
 BattleDtos.Capture capture(UUID id){return http.postForObject(url("/battles/"+id+"/capture"),null,BattleDtos.Capture.class);}
 @ParameterizedTest @ValueSource(strings={"PIP","MELLO","MOSSY","CHIRP","BUBU","PEBB","PUFF","TIKKI","MIMI","WISP","SHADE","EMBER","LUNET","NOVA","NOCT"})
 void waitAttackItemCaptureAndNoCaptureSuccessAction(String code){
  var b=start(code);when(random.nextLong(100)).thenReturn(99L);clearInvocations(random);
  b=attack(b.battleId());boolean aggressive=MonsterContent.find(code).orElseThrow().battlePersonality()==BattlePersonality.AGGRESSIVE;
  assertEquals(18,b.monster().hp());assertEquals(aggressive?95:100,b.companion().hp());assertEquals(1,b.turn());
  assertEquals(List.of("PLAYER_ATTACK",aggressive?"MONSTER_ATTACK":"MONSTER_WAIT"),b.events());
  assertEquals(aggressive?2:1,b.presentationEvents().size());verify(random,times(1)).nextLong(100);
  for(String item:List.of("SMALL_POTION","CAPTURE_CHARM"))http.postForObject(url("/shop/purchases"),new ItemDtos.PurchaseRequest(item,1),ItemDtos.Purchase.class);
  when(random.nextLong(100)).thenReturn(0L);b=attack(b.battleId());assertEquals(6,b.monster().hp());
  var potion=http.postForObject(url("/inventory/items/SMALL_POTION/use"),new ItemDtos.UseRequest(b.battleId()),ItemDtos.Use.class);assertEquals(100,potion.currentHp());
  http.postForObject(url("/inventory/items/CAPTURE_CHARM/use"),new ItemDtos.UseRequest(b.battleId()),ItemDtos.Use.class);
  clearInvocations(random);var c=capture(b.battleId());assertTrue(c.success());verify(random,never()).nextLong(100);
  double base=MonsterContent.rarity(MonsterContent.find(code).orElseThrow().rarity()).baseCaptureRate()+.4;
  assertEquals(base,c.baseChance(),1e-9);assertEquals(.1,c.itemBonus(),1e-9);assertEquals(base+.1,c.finalChance(),1e-9);assertEquals(code,c.collection().monsterCode());
  assertTrue(c.battle().presentationEvents().isEmpty());
 }
 @ParameterizedTest @ValueSource(strings={"PIP","MELLO","MOSSY","CHIRP","BUBU","PEBB","PUFF","TIKKI","MIMI","WISP","SHADE","EMBER","LUNET","NOVA","NOCT"})
 void victoryTerminalRewardAndNoExtraAction(String code){
  var b=start(code);clearInvocations(random);
  b=attack(b.battleId());b=attack(b.battleId());b=attack(b.battleId());
  assertEquals("VICTORY",b.status());assertEquals(3,b.turn());assertEquals(10,b.reward().gold());assertEquals(20,b.reward().exp());verify(random,times(2)).nextLong(100);
  clearInvocations(random);assertEquals(409,http.postForEntity(url("/battles/"+b.battleId()+"/attack"),null,String.class).getStatusCode().value());verifyNoInteractions(random);
  assertTrue(capture(b.battleId()).success());verify(random,never()).nextLong(100);
 }
 @Test void erraticParityWaitOnFailedCaptureAndRestartTurn(){
  var b=start("SHADE");when(random.nextLong(100)).thenReturn(50L);
  b=attack(b.battleId());assertTrue(b.events().contains("MONSTER_WAIT"));assertEquals(100,b.companion().hp());
  b=http.getForObject(url("/battles/"+b.battleId()),BattleDtos.Battle.class);assertEquals(1,b.turn());
  when(random.nextLong(1_000_000)).thenReturn(999999L);var c=capture(b.battleId());assertFalse(c.success());assertEquals(95,c.battle().companion().hp());assertEquals(18,c.battle().monster().hp());
  c=capture(b.battleId());assertEquals(95,c.battle().companion().hp());assertEquals(List.of("MONSTER_WAIT"),c.battle().events());assertTrue(c.battle().presentationEvents().isEmpty());
 }
 @Test void invalidDecisionRngRollsBackTurnAndDamage(){
  var b=start("PIP");when(random.nextLong(100)).thenReturn(100L);
  assertEquals(503,http.postForEntity(url("/battles/"+b.battleId()+"/attack"),null,String.class).getStatusCode().value());
  var restored=http.getForObject(url("/battles/"+b.battleId()),BattleDtos.Battle.class);assertEquals(0,restored.turn());assertEquals(30,restored.monster().hp());assertEquals(100,restored.companion().hp());
 }
 @Test void failedCaptureWaitConsumesCharmOnceAndInvalidDecisionRollsBack(){
  var b=start("MOSSY");
  http.postForObject(url("/shop/purchases"),new ItemDtos.PurchaseRequest("CAPTURE_CHARM",1),ItemDtos.Purchase.class);
  http.postForObject(url("/inventory/items/CAPTURE_CHARM/use"),new ItemDtos.UseRequest(b.battleId()),ItemDtos.Use.class);
  when(random.nextLong(1_000_000)).thenReturn(999999L);when(random.nextLong(100)).thenReturn(100L);
  assertEquals(503,http.postForEntity(url("/battles/"+b.battleId()+"/capture"),null,String.class).getStatusCode().value());
  assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_battle_item_effect WHERE consumed_at IS NULL",Integer.class));
  when(random.nextLong(100)).thenReturn(99L);var c=capture(b.battleId());
  assertFalse(c.success());assertEquals(.1,c.itemBonus(),1e-9);assertEquals(100,c.battle().companion().hp());assertEquals(30,c.battle().monster().hp());assertEquals(List.of("MONSTER_WAIT"),c.battle().events());
  assertEquals(0,capture(b.battleId()).itemBonus());
 }

}
