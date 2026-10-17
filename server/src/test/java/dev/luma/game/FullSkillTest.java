package dev.luma.game;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class FullSkillTest {
 @Test void completeUniqueCatalogWithoutLegacyAliases(){
  var entries=SkillCatalog.all();assertEquals(230,entries.size());assertEquals(230,entries.stream().map(x->x.definition().code()).distinct().count());
  assertEquals(100,entries.stream().filter(x->!x.released()).map(x->x.definition().speciesCode()).distinct().count());
  assertEquals(115,entries.stream().filter(x->x.definition().kind()==SkillDefinitions.Kind.ACTIVE).map(SkillCatalog.Entry::castMotion).distinct().count());
  for(var e:entries){assertEquals("ASSET_REQUIRED",e.assetStatus());assertFalse(e.definition().speciesCode().equals("PIP"));}
 }
 @Test void unlocksAndUpgradeCaps(){
  assertEquals(2,SkillCatalog.unlocked("MOA",1,1).size());assertEquals(4,SkillCatalog.unlocked("MOA",2,3).size());assertEquals(6,SkillCatalog.unlocked("MOA",3,6).size());
  for(String s:List.of("MOA","RUU","NOX"))assertEquals(10,SkillCatalog.unlocked(s,5,100).size());
  for(var e:SkillCatalog.all()){assertTrue(SkillRules.power(e.definition(),100)<=e.definition().maxPower());assertEquals(e.definition().maxPower(),SkillRules.power(e.definition(),Integer.MAX_VALUE));}
 }
 @Test void effectsRespectBoundsAndTargets(){
  var a=new SkillResolution.Fighter(40,100,0,0,0,0);var b=new SkillResolution.Fighter(30,30,0,0,0,0);
  for(var e:SkillCatalog.all()){
   var result=SkillResolution.apply(e,100,a,b);assertTrue(result.caster().hp()<=100);assertTrue(result.target().hp()<=30);assertTrue(result.damage()>=0);
   if(e.effect()==SkillCatalog.Effect.HEAL)assertTrue(result.caster().hp()>40);
   if(e.effect()==SkillCatalog.Effect.DAMAGE)assertTrue(result.target().hp()<30);
   if(e.effect()==SkillCatalog.Effect.GUARD)assertTrue(result.caster().guard()>0);
   if(e.effect()==SkillCatalog.Effect.WEAKEN)assertTrue(result.target().weaken()>0);
  }
  assertEquals(0,new SkillResolution.Fighter(1,100,2,3,5,0).tick().hp());
 }
 @Test void hundredMonsterPoliciesRespectContextAndCooldown(){
  for(int n=1;n<=100;n++){
   String species=String.format(java.util.Locale.ROOT,"M%03d",n);
   var selected=MonsterSkillPolicy.choose(species,1,0,5,30,Map.of()).orElseThrow();
   assertEquals(species,selected.definition().speciesCode());assertFalse(selected.released());
   assertTrue(MonsterSkillPolicy.choose(species,1,0,5,30,Map.of(selected.definition().code(),2)).isEmpty());
   var resolved=MonsterSkillPolicy.resolve(selected,1,new SkillResolution.Fighter(5,30,0,0,0,0),new SkillResolution.Fighter(100,100,0,0,0,0));assertTrue(resolved.caster().hp()>0);
  }
  assertTrue(MonsterSkillPolicy.choose("PIP",1,0,5,30,Map.of()).isEmpty());
 }
}
