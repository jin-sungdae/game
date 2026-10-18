package dev.luma.game;

import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Random;
import static org.junit.jupiter.api.Assertions.*;

class MonsterTierTest {
    MonsterSelector.Monster candidate(String code,int low,int high,int weight) {
        return new MonsterSelector.Monster(1,code,code,"COMMON","GROUND",low,high,weight);
    }
    @Test void approvedBoundariesAndInvalidLevels() {
        int[] starts={1,20,40,60,80},ends={19,39,59,79,100};
        for(int i=0;i<5;i++) for(int level=starts[i];level<=ends[i];level++) {
            assertEquals(new MonsterTier(i+1,starts[i],ends[i]),MonsterTier.forLevel(level));
            var choice=new MonsterSelector(bound->bound-1).select(List.of(candidate("FUTURE_TEST",1,100,1)),level);
            assertEquals(ends[i],choice.level());
            assertEquals(starts[i],new MonsterSelector(bound->0).select(List.of(candidate("FUTURE_TEST",1,100,1)),level).level());
        }
        for(int level:new int[]{Integer.MIN_VALUE,0,101,Integer.MAX_VALUE})
            assertThrows(GameUnavailable.class,()->MonsterTier.forLevel(level));
    }
    @Test void outOfBandContentNeverConsumesRandomOrFallsBack() {
        var selector=new MonsterSelector(bound->{fail("No eligible content must not draw RNG");return 0;});
        assertThrows(GameUnavailable.class,()->selector.select(List.of(candidate("FUTURE_TEST",40,59,1)),20));
        assertThrows(GameUnavailable.class,()->selector.select(List.of(candidate("FUTURE_TEST",1,101,1)),20));
    }
    @Test void existingAlphaDistributionIsIdenticalAtEveryGrowthBand() {
        var legacy=MonsterContent.definitions().stream().filter(d->d.alphaCandidate()&&MonsterContent.productionReady(d.monsterCode()))
            .map(d->new MonsterSelector.Monster(d.dexNo(),d.monsterCode(),d.displayName(),d.rarity(),d.movementProfile(),1,3,d.encounterWeight())).toList();
        assertEquals(15,legacy.size());
        for(int level:new int[]{1,19,20,39,40,59,60,79,80,100}) {
            var oldRandom=new Random(42);var newRandom=new Random(42);
            var oldSelector=new MonsterSelector(oldRandom::nextLong);var newSelector=new MonsterSelector(newRandom::nextLong);
            for(int i=0;i<100;i++) assertEquals(oldSelector.select(legacy),newSelector.select(legacy,level));
        }
    }
}
