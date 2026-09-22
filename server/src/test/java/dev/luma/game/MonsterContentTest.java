package dev.luma.game;

import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class MonsterContentTest {
    @Test void approvedAlphaAndStableUniqueDex() {
        var all=MonsterContent.definitions();
        assertEquals(30,all.size());
        assertEquals(30,all.stream().map(MonsterContent.Definition::monsterCode).distinct().count());
        assertEquals(30,all.stream().map(MonsterContent.Definition::dexNo).distinct().count());
        var expected=List.of("1:PIP","2:MELLO","3:MOSSY","4:CHIRP","6:BUBU","7:PEBB","8:PUFF","10:TIKKI","13:MIMI","14:WISP","15:SHADE","16:EMBER","19:LUNET","21:NOVA","28:NOCT");
        assertEquals(expected,all.stream().filter(MonsterContent.Definition::alphaCandidate).map(d->d.dexNo()+":"+d.monsterCode()).toList());
        assertThrows(UnsupportedOperationException.class,()->all.clear());
    }
    @Test void exactRarityDefaultsAndCheckedProjection() {
        var names=List.of("COMMON","UNCOMMON","RARE","EPIC","SPECIAL");
        var weights=List.of(100,50,20,5,1);var rates=List.of(.35,.25,.15,.10,.05);var counts=List.of(7L,4L,3L,0L,1L);
        for(int i=0;i<names.size();i++) {
            var r=MonsterContent.rarity(names.get(i));assertEquals(weights.get(i),r.encounterWeight());assertEquals(rates.get(i),r.baseCaptureRate());
            String rarity=names.get(i);
            assertEquals(counts.get(i),MonsterContent.definitions().stream().filter(d->d.alphaCandidate() && d.rarity().equals(rarity)).count());
        }
        for(var d:MonsterContent.definitions()) if(d.alphaCandidate()) {
            assertEquals(MonsterContent.rarity(d.rarity()).encounterWeight(),d.encounterWeight());
            assertEquals(MonsterContent.rarity(d.rarity()).baseCaptureRate(),d.baseCaptureRate());
        }
        assertThrows(GameFault.class,()->MonsterContent.rarity("UNKNOWN"));
    }
    @Test void productionGateCannotBeBypassedByPositiveDatabaseWeight() {
        for(var d:MonsterContent.definitions()) {
            boolean pip=List.of("PIP","MELLO","MOSSY","CHIRP","BUBU").contains(d.monsterCode());
            assertEquals(pip,MonsterContent.productionReady(d.monsterCode()));
            var master=new MonsterSelector.Monster(d.dexNo(),d.monsterCode(),d.displayName(),d.rarity(),d.movementProfile(),1,3,100);
            assertEquals(pip,MonsterContent.eligible(master));
            if(d.alphaCandidate()) {assertEquals(d.monsterCode().toLowerCase(),d.assetIdentity());assertEquals(d.monsterCode().equals("PIP")?.8:1,d.visualScale());}
        }
        assertFalse(MonsterContent.productionReady("UNKNOWN"));
        assertFalse(MonsterContent.eligible(new MonsterSelector.Monster(99,"UNKNOWN","Unknown","COMMON","GROUND",1,3,100)));
    }
    @Test void pipMasterMismatchFailsClosedRatherThanSilentlyChangingGameplay() {
        for(var master:List.of(
            new MonsterSelector.Monster(1,"PIP","Changed","COMMON","GROUND",1,3,100),
            new MonsterSelector.Monster(1,"PIP","PIP","RARE","GROUND",1,3,100),
            new MonsterSelector.Monster(1,"PIP","PIP","COMMON","FLYING",1,3,100),
            new MonsterSelector.Monster(1,"PIP","PIP","COMMON","GROUND",1,3,999)))
            assertThrows(GameUnavailable.class,()->MonsterContent.eligible(master));
    }
    @Test void pipCaptureFormulaIsUnchangedAndBatch3UsesRarityDefaults() {
        assertEquals(.35,CombatRules.captureChance(30,30,"COMMON"),1e-9);
        assertEquals(.60,CombatRules.captureChance(15,30,"COMMON"),1e-9);
        assertEquals(.85,CombatRules.captureChance(0,30,"COMMON"),1e-9);
        for(var rarity:List.of("UNCOMMON","RARE","SPECIAL")) assertEquals(MonsterContent.rarity(rarity).baseCaptureRate(),CombatRules.captureChance(30,30,rarity),1e-9);
        assertThrows(GameFault.class,()->CombatRules.captureChance(30,30,"EPIC"));
    }
}
