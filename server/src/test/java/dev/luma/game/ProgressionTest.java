package dev.luma.game;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class ProgressionTest {
    @Test void existingThresholdsAndEveryNewBoundary(){
        long[] expected={0,100,300,600,1000,1500,2100,2800,3600,4500,5500,6600,7800,9100,10500,12000,13600,15300,17100,19000};
        assertEquals(expected.length,CombatRules.MAX_LEVEL);
        for(int level=1;level<=expected.length;level++){
            assertEquals(expected[level-1],CombatRules.levelThreshold(level));
            assertEquals(level,CombatRules.level(expected[level-1]));
            if(level>1)assertEquals(level-1,CombatRules.level(expected[level-1]-1));
        }
        assertThrows(IllegalArgumentException.class,()->CombatRules.levelThreshold(21));
    }
    @Test void multiLevelAndMaxWithoutExpTruncation(){
        long total=Math.addExact(99,CombatRules.exp(100));
        assertEquals(2099,total);assertEquals(6,CombatRules.level(total));
        assertEquals(CombatRules.MAX_LEVEL,CombatRules.level(Long.MAX_VALUE));
        assertEquals(CombatRules.MAX_LEVEL,CombatRules.level(19020));
    }
    @Test void deterministicUnchangedRewardPacing(){
        int[][] expected={{5,10,15,20,25},{3,5,7,10,13},{2,3,5,7,8}};
        for(int monster=1;monster<=3;monster++){
            long exp=0;int total=0;
            for(int level=2;level<=6;level++){
                int battles=0;
                while(CombatRules.level(exp)<level){exp+=CombatRules.exp(monster);battles++;total++;}
                assertEquals(expected[monster-1][level-2],battles);
            }
            assertEquals((1500+CombatRules.exp(monster)-1)/CombatRules.exp(monster),total);
        }
    }
}
