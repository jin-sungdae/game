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
class ItemIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired TestRestTemplate http;@Autowired JdbcTemplate db;@LocalServerPort int port;
 @MockitoBean RandomSource random;
 String url(String p){return "http://127.0.0.1:"+port+"/api/v1"+p;}
 @BeforeEach void reset(){clean();db.update("UPDATE game.t_player SET gold=10000");when(random.nextLong(anyLong())).thenReturn(0L);}
 @AfterEach void clean(){
  db.update("DELETE FROM game.t_battle_item_effect");db.update("DELETE FROM game.t_item_purchase");db.update("DELETE FROM game.t_inventory");
  db.update("DELETE FROM game.t_companion_evolution_history");db.update("DELETE FROM game.t_reward");db.update("DELETE FROM game.t_collection");db.update("DELETE FROM game.t_battle");db.update("DELETE FROM game.t_encounter");
  db.update("UPDATE game.t_player SET gold=0");db.update("UPDATE game.t_player_companion SET evolution_stage=1,exp=0,level=1,bond=0,active=true");
  db.update("UPDATE game.m_item SET use_yn=true,max_stack=99,price=CASE item_code WHEN 'SMALL_POTION' THEN 20 WHEN 'BOND_BERRY' THEN 30 ELSE 40 END");
 }
 ItemDtos.Purchase buy(String code,int qty){return http.postForObject(url("/shop/purchases"),new ItemDtos.PurchaseRequest(code,qty),ItemDtos.Purchase.class);}
 String usePath(String c){return "/inventory/items/"+c+"/use";}
 ItemDtos.Use use(String c,UUID b){return http.postForObject(url(usePath(c)),new ItemDtos.UseRequest(b),ItemDtos.Use.class);}
 int quantity(String c){return db.queryForObject("SELECT COALESCE((SELECT quantity FROM game.t_inventory i JOIN game.m_item m USING(item_id) WHERE item_code=?),0)",Integer.class,c);}
 long gold(){return db.queryForObject("SELECT gold FROM game.t_player WHERE player_id=1",Long.class);}
 int count(String table){return db.queryForObject("SELECT count(*) FROM game."+table,Integer.class);}
 void error(String path,Object body,int status,String code){var r=http.postForEntity(url(path),body,Map.class);assertEquals(status,r.getStatusCode().value());assertEquals(code,r.getBody().get("code"));}
 BattleDtos.Battle battle(){var e=http.postForObject(url("/encounters"),null,GameDtos.Encounter.class);return http.postForObject(url("/encounters/"+e.encounterId()+"/battle"),null,BattleDtos.Battle.class);}
 BattleDtos.Capture capture(UUID b){return http.postForObject(url("/battles/"+b+"/capture"),null,BattleDtos.Capture.class);}
 ItemDtos.Effect[] effects(UUID b){return http.getForObject(url("/battles/"+b+"/item-effects"),ItemDtos.Effect[].class);}
 GameDtos.Bootstrap bootstrap(){return http.getForObject(url("/game/bootstrap"),GameDtos.Bootstrap.class);}
 List<Integer> concurrent(String path,Object body)throws Exception{
  var pool=Executors.newFixedThreadPool(2);var gate=new CountDownLatch(1);
  try{Callable<Integer> job=()->{gate.await();return http.postForEntity(url(path),body,String.class).getStatusCode().value();};var a=pool.submit(job);var b=pool.submit(job);gate.countDown();return List.of(a.get(15,TimeUnit.SECONDS),b.get(15,TimeUnit.SECONDS));}finally{pool.shutdownNow();}
 }
 @Test void shopDeterministicAndDisabledHidden(){var list=http.getForObject(url("/shop/items"),ItemDtos.ShopItem[].class);assertEquals(List.of("BOND_BERRY","CAPTURE_CHARM","SMALL_POTION"),Arrays.stream(list).map(ItemDtos.ShopItem::itemCode).toList());assertEquals(30,list[0].price());assertEquals(99,list[0].maxStack());db.update("UPDATE game.m_item SET use_yn=false WHERE item_code='BOND_BERRY'");assertEquals(2,http.getForObject(url("/shop/items"),ItemDtos.ShopItem[].class).length);}
 @Test void buyPotion(){var p=buy("SMALL_POTION",2);assertEquals(40,p.totalPrice());assertEquals(20,p.unitPrice());assertEquals(9960,p.goldAfter());assertEquals(2,p.remainingQuantity());assertEquals(1,count("t_item_purchase"));}
 @Test void buyBerry(){assertEquals(30,buy("BOND_BERRY",1).totalPrice());assertEquals(1,quantity("BOND_BERRY"));}
 @Test void buyCharm(){assertEquals(40,buy("CAPTURE_CHARM",1).totalPrice());assertEquals(1,quantity("CAPTURE_CHARM"));}
 @Test void purchaseSnapshotsPrice(){buy("SMALL_POTION",1);db.update("UPDATE game.m_item SET price=25 WHERE item_code='SMALL_POTION'");assertEquals(20,db.queryForObject("SELECT unit_price FROM game.t_item_purchase",Long.class));assertEquals(25,buy("SMALL_POTION",1).unitPrice());}
 @Test void insufficientGoldNoMutation(){db.update("UPDATE game.t_player SET gold=19");error("/shop/purchases",new ItemDtos.PurchaseRequest("SMALL_POTION",1),409,"INSUFFICIENT_GOLD");assertEquals(19,gold());assertEquals(0,count("t_inventory"));assertEquals(0,count("t_item_purchase"));}
 @Test void quantityAndOverflow(){for(int q:new int[]{0,-1})error("/shop/purchases",new ItemDtos.PurchaseRequest("SMALL_POTION",q),400,"INVALID_QUANTITY");db.update("UPDATE game.m_item SET price=9223372036854775807 WHERE item_code='SMALL_POTION'");error("/shop/purchases",new ItemDtos.PurchaseRequest("SMALL_POTION",2),400,"INVALID_QUANTITY");assertEquals(10000,gold());}
 @Test void stackLimit(){buy("SMALL_POTION",99);long before=gold();error("/shop/purchases",new ItemDtos.PurchaseRequest("SMALL_POTION",1),409,"MAX_STACK_EXCEEDED");assertEquals(99,quantity("SMALL_POTION"));assertEquals(before,gold());}
 @Test void concurrentPurchaseUsesOneAffordableStack()throws Exception{db.update("UPDATE game.t_player SET gold=20");var codes=concurrent("/shop/purchases",new ItemDtos.PurchaseRequest("SMALL_POTION",1));assertTrue(codes.contains(200));assertTrue(codes.contains(409));assertEquals(0,gold());assertEquals(1,quantity("SMALL_POTION"));assertEquals(1,count("t_item_purchase"));}
 @Test void concurrentPurchaseAtStackLimit()throws Exception{buy("SMALL_POTION",98);var codes=concurrent("/shop/purchases",new ItemDtos.PurchaseRequest("SMALL_POTION",1));assertTrue(codes.contains(409));assertEquals(99,quantity("SMALL_POTION"));}
 @Test void inventoryOrdered(){buy("SMALL_POTION",2);buy("BOND_BERRY",1);var rows=http.getForObject(url("/inventory"),ItemDtos.Owned[].class);assertEquals("BOND_BERRY",rows[0].itemCode());assertEquals(2,rows[1].quantity());}
 @Test void missingDisabledUntrustedPrice(){error("/shop/purchases",new ItemDtos.PurchaseRequest("NONE",1),404,"ITEM_NOT_FOUND");db.update("UPDATE game.m_item SET use_yn=false WHERE item_code='SMALL_POTION'");error("/shop/purchases",new ItemDtos.PurchaseRequest("SMALL_POTION",1),409,"ITEM_DISABLED");assertEquals(400,http.postForEntity(url("/shop/purchases"),Map.of("itemCode","SMALL_POTION","quantity",1,"price",0),String.class).getStatusCode().value());}
 @Test void potionHeal(){buy("SMALL_POTION",1);var b=battle();db.update("UPDATE game.t_battle SET companion_hp=55");var result=use("SMALL_POTION",b.battleId());assertEquals(30,result.healedAmount());assertEquals(85,result.currentHp());assertEquals(100,result.maxHp());assertEquals(0,result.remainingQuantity());assertEquals(0,quantity("SMALL_POTION"));}
 @Test void potionClamp(){buy("SMALL_POTION",1);var b=battle();db.update("UPDATE game.t_battle SET companion_hp=90");assertEquals(10,use("SMALL_POTION",b.battleId()).healedAmount());}
 @Test void fullHpDoesNotConsume(){buy("SMALL_POTION",1);var b=battle();error(usePath("SMALL_POTION"),new ItemDtos.UseRequest(b.battleId()),409,"FULL_HP");assertEquals(1,quantity("SMALL_POTION"));}
 @Test void potionContextAndOwnership(){buy("SMALL_POTION",1);error(usePath("SMALL_POTION"),null,400,"ITEM_NOT_USABLE");error(usePath("SMALL_POTION"),new ItemDtos.UseRequest(UUID.randomUUID()),404,"BATTLE_NOT_FOUND");var b=battle();http.postForObject(url("/encounters/"+b.encounterId()+"/ignore"),null,String.class);error(usePath("SMALL_POTION"),new ItemDtos.UseRequest(b.battleId()),409,"INVALID_BATTLE_STATE");assertEquals(1,quantity("SMALL_POTION"));}
 @Test void concurrentPotionNeverNegative()throws Exception{buy("SMALL_POTION",1);var b=battle();db.update("UPDATE game.t_battle SET companion_hp=55");var codes=concurrent(usePath("SMALL_POTION"),new ItemDtos.UseRequest(b.battleId()));assertTrue(codes.contains(200));assertTrue(codes.contains(409));assertEquals(0,quantity("SMALL_POTION"));assertEquals(85,db.queryForObject("SELECT companion_hp FROM game.t_battle",Integer.class));}
 @Test void berryEvolutionAndBootstrap(){db.update("UPDATE game.t_player_companion SET level=3,bond=4,exp=300");buy("BOND_BERRY",1);assertEquals(EvolutionDtos.State.LOCKED,http.getForObject(url("/companions/active/evolution"),EvolutionDtos.Status.class).status());var u=use("BOND_BERRY",null);assertEquals(4,u.bondBefore());assertEquals(5,u.bondAfter());assertEquals(0,u.remainingQuantity());assertEquals(5,bootstrap().activeCompanion().bond());assertEquals(9970,bootstrap().player().gold());assertEquals(EvolutionDtos.State.AVAILABLE,http.getForObject(url("/companions/active/evolution"),EvolutionDtos.Status.class).status());}
 @Test void berryRejectedDuringBattle(){buy("BOND_BERRY",1);battle();error(usePath("BOND_BERRY"),null,409,"ITEM_NOT_USABLE");assertEquals(1,quantity("BOND_BERRY"));assertEquals(0,bootstrap().activeCompanion().bond());}
 @Test void berryOverflowRollback(){buy("BOND_BERRY",1);db.update("UPDATE game.t_player_companion SET bond=2147483647");error(usePath("BOND_BERRY"),null,409,"ITEM_NOT_USABLE");assertEquals(1,quantity("BOND_BERRY"));assertEquals(Integer.MAX_VALUE,bootstrap().activeCompanion().bond());}
 @Test void charmArmedPersistedAndDuplicateRejected(){buy("CAPTURE_CHARM",2);var b=battle();var u=use("CAPTURE_CHARM",b.battleId());assertTrue(u.armed());assertEquals(.1,u.bonus(),1e-9);assertEquals(1,u.remainingQuantity());assertTrue(effects(b.battleId())[0].armed());error(usePath("CAPTURE_CHARM"),new ItemDtos.UseRequest(b.battleId()),409,"EFFECT_ALREADY_ACTIVE");assertEquals(1,quantity("CAPTURE_CHARM"));}
 @Test void captureBaseAndClamp(){var c=capture(battle().battleId());assertEquals(.35,c.baseChance(),1e-9);assertEquals(0,c.itemBonus());assertEquals(c.chance(),c.finalChance());assertEquals(.95,ItemRules.captureChance(.90,.1),1e-9);assertEquals(.05,ItemRules.captureChance(0,0),1e-9);}
 @Test void charmSuccessConsumed(){buy("CAPTURE_CHARM",1);var b=battle();use("CAPTURE_CHARM",b.battleId());var c=capture(b.battleId());assertTrue(c.success());assertEquals(.35,c.baseChance(),1e-9);assertEquals(.10,c.itemBonus(),1e-9);assertEquals(.45,c.finalChance(),1e-9);assertFalse(effects(b.battleId())[0].armed());assertNotNull(effects(b.battleId())[0].consumedAt());}
 @Test void charmFailureConsumedNextAttemptNoBonus(){when(random.nextLong(anyLong())).thenAnswer(call->((Long)call.getArgument(0))==1_000_000L?999999L:0L);buy("CAPTURE_CHARM",1);var b=battle();use("CAPTURE_CHARM",b.battleId());var first=capture(b.battleId());assertFalse(first.success());assertEquals(.1,first.itemBonus());assertEquals(0,capture(b.battleId()).itemBonus());assertFalse(effects(b.battleId())[0].armed());}
 @Test void explicitRearmAfterConsumption(){when(random.nextLong(anyLong())).thenAnswer(call->((Long)call.getArgument(0))==1_000_000L?999999L:0L);buy("CAPTURE_CHARM",2);var b=battle();use("CAPTURE_CHARM",b.battleId());capture(b.battleId());assertTrue(use("CAPTURE_CHARM",b.battleId()).armed());assertEquals(1,count("t_battle_item_effect"));assertEquals(.1,capture(b.battleId()).itemBonus());}
 @Test void concurrentCaptureAppliesBonusOnce()throws Exception{when(random.nextLong(anyLong())).thenAnswer(call->((Long)call.getArgument(0))==1_000_000L?999999L:0L);buy("CAPTURE_CHARM",1);var b=battle();use("CAPTURE_CHARM",b.battleId());var pool=Executors.newFixedThreadPool(2);try{var a=pool.submit(()->capture(b.battleId()));var c=pool.submit(()->capture(b.battleId()));assertEquals(.1,a.get().itemBonus()+c.get().itemBonus(),1e-9);}finally{pool.shutdownNow();}assertFalse(effects(b.battleId())[0].armed());}
 @Test void concurrentCharmUseAndCaptureSerializable()throws Exception{buy("CAPTURE_CHARM",1);var b=battle();var pool=Executors.newFixedThreadPool(2);try{var a=pool.submit(()->http.postForEntity(url(usePath("CAPTURE_CHARM")),new ItemDtos.UseRequest(b.battleId()),String.class).getStatusCode().value());var c=pool.submit(()->capture(b.battleId()));int useStatus=a.get();var result=c.get();if(useStatus==200){assertEquals(.1,result.itemBonus());assertEquals(0,quantity("CAPTURE_CHARM"));assertFalse(effects(b.battleId())[0].armed());}else{assertEquals(409,useStatus);assertEquals(0,result.itemBonus());assertEquals(1,quantity("CAPTURE_CHARM"));}}finally{pool.shutdownNow();}}
 @Test void simultaneousCharmArmConsumesOne()throws Exception{buy("CAPTURE_CHARM",2);var b=battle();var codes=concurrent(usePath("CAPTURE_CHARM"),new ItemDtos.UseRequest(b.battleId()));assertTrue(codes.contains(409));assertEquals(1,quantity("CAPTURE_CHARM"));assertEquals(1,count("t_battle_item_effect"));}
 @Test void invalidRngRollsBackCharmConsumption(){buy("CAPTURE_CHARM",1);var b=battle();use("CAPTURE_CHARM",b.battleId());when(random.nextLong(anyLong())).thenReturn(-1L);assertEquals(503,http.postForEntity(url("/battles/"+b.battleId()+"/capture"),null,String.class).getStatusCode().value());assertTrue(effects(b.battleId())[0].armed());}
 @Test void unownedAndDisabledUse(){var b=battle();error(usePath("SMALL_POTION"),new ItemDtos.UseRequest(b.battleId()),409,"ITEM_NOT_OWNED");buy("SMALL_POTION",1);db.update("UPDATE game.m_item SET use_yn=false WHERE item_code='SMALL_POTION'");error(usePath("SMALL_POTION"),new ItemDtos.UseRequest(b.battleId()),409,"ITEM_DISABLED");}
 @Test void purchaseHistoryFailureRollsBackGoldAndInventory(){
  db.execute("ALTER TABLE game.t_item_purchase ADD CONSTRAINT item_test_reject CHECK(quantity<1) NOT VALID");
  try{assertEquals(503,http.postForEntity(url("/shop/purchases"),new ItemDtos.PurchaseRequest("SMALL_POTION",1),String.class).getStatusCode().value());assertEquals(10000,gold());assertEquals(0,count("t_inventory"));assertEquals(0,count("t_item_purchase"));}
  finally{db.execute("ALTER TABLE game.t_item_purchase DROP CONSTRAINT item_test_reject");}
 }
 @Test void inventoryFailureRollsBackPotionHp(){buy("SMALL_POTION",1);var b=battle();db.update("UPDATE game.t_battle SET companion_hp=55");db.execute("ALTER TABLE game.t_inventory ADD CONSTRAINT item_test_quantity CHECK(quantity>0) NOT VALID");try{assertEquals(503,http.postForEntity(url(usePath("SMALL_POTION")),new ItemDtos.UseRequest(b.battleId()),String.class).getStatusCode().value());assertEquals(55,db.queryForObject("SELECT companion_hp FROM game.t_battle",Integer.class));assertEquals(1,quantity("SMALL_POTION"));}finally{db.execute("ALTER TABLE game.t_inventory DROP CONSTRAINT item_test_quantity");}}
}
