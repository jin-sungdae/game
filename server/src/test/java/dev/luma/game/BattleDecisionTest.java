package dev.luma.game;

import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class BattleDecisionTest {
 @Test void mappingAndExhaustiveBoundaries(){
  var mapping=Map.of(BattlePersonality.BALANCED,"PIP MELLO BUBU PUFF TIKKI",BattlePersonality.DEFENSIVE,"MOSSY PEBB WISP LUNET",BattlePersonality.AGGRESSIVE,"EMBER NOCT",BattlePersonality.ERRATIC,"CHIRP MIMI SHADE NOVA");
  assertEquals(15,MonsterContent.definitions().stream().filter(MonsterContent.Definition::alphaCandidate).count());
  mapping.forEach((p,codes)->{for(String code:codes.split(" "))assertEquals(p,MonsterContent.find(code).orElseThrow().battlePersonality());});
  for(var p:BattlePersonality.values())for(int turn=0;turn<2;turn++){
   int attacks=0;for(int roll=0;roll<100;roll++){final int r=roll;if(BattleDecision.choose(p,turn,b->{assertEquals(100,b);return r;})==BattleDecision.Action.ATTACK)attacks++;}
   assertEquals(switch(p){case BALANCED->85;case DEFENSIVE->45;case AGGRESSIVE->100;case ERRATIC->turn==0?25:90;},attacks);
  }
 }
 @Test void sameSeedSameSequenceDifferentSeedsVaryWithinPolicy(){
  for(var p:BattlePersonality.values()){
   var a=new Random(42);var b=new Random(42);var c=new Random(43);int differences=0;
   for(int t=0;t<1000;t++){var x=BattleDecision.choose(p,t,a::nextLong);assertEquals(x,BattleDecision.choose(p,t,b::nextLong));if(x!=BattleDecision.choose(p,t,c::nextLong))differences++;}
   if(p==BattlePersonality.AGGRESSIVE)assertEquals(0,differences);else assertTrue(differences>100);
  }
 }
 @Test void invalidInputFailsClosed(){
  for(long bad:new long[]{-1,100,Long.MAX_VALUE})assertThrows(GameUnavailable.class,()->BattleDecision.choose(BattlePersonality.BALANCED,0,b->bad));
  assertThrows(GameUnavailable.class,()->BattleDecision.choose(null,0,b->0));
  assertThrows(GameUnavailable.class,()->BattleDecision.choose(BattlePersonality.BALANCED,-1,b->0));
 }
 @Test void actualJavaPolicyBattleSimulation(){
  for(var p:BattlePersonality.values()){
   long actions=0,attacks=0,opportunities=0,terminals=0;var histogram=new TreeMap<Integer,Integer>();
   for(int seed=0;seed<30000;seed++){
    var random=new Random(seed);int level=seed%3+1,hp=CombatRules.monsterHp(level),player=CombatRules.companionHp(),turn=0;
    while(hp>0 && player>0){
     hp=Math.max(0,hp-CombatRules.companionAttack(1));
     if(hp>0){opportunities++;if(BattleDecision.choose(p,turn,random::nextLong)==BattleDecision.Action.ATTACK){attacks++;player=Math.max(0,player-CombatRules.monsterAttack(level));}}
     turn++;
    }
    assertEquals(0,hp);assertTrue(player>0);assertEquals(level+2,turn);terminals++;actions+=turn;histogram.merge(turn,1,Integer::sum);
   }
   assertEquals(30000,terminals);
   System.out.printf(Locale.ROOT,"JAVA_PERSONALITY_SIM %s battles=30000 attack=%.6f wait=%.6f avgPlayerActions=%.6f avgMonsterCounters=%.6f terminals=%d histogram=%s%n",p,(double)attacks/opportunities,1-(double)attacks/opportunities,actions/30000.,attacks/30000.,terminals,histogram);
  }
 }
}
