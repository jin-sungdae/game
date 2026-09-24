package dev.luma.game;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class NeblaEligibilityBoundaryTest {
 @Test void exactBondBoundaryUsesServerRuleWithoutMutatingProgression(){
  for(int bond:new int[]{11,12}){
   var companion=new GameDtos.Companion(1,"MOA",2,"MOKORI",6,1500,bond);
   var rule=EvolutionRules.next(companion).orElseThrow();assertEquals(3,rule.toStage());assertEquals(bond==12,rule.eligible(companion));
  }
 }
}
