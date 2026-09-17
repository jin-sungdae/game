package dev.luma.game;

import org.junit.jupiter.api.Test;
import java.util.List;
import java.util.Random;
import static org.junit.jupiter.api.Assertions.*;

class MonsterSelectorTest {
    private MonsterSelector.Monster monster(long id,int weight) {
        return new MonsterSelector.Monster(id,"M"+id,"M"+id,"COMMON","GROUND",1,3,weight);
    }
    @Test void weightedBoundariesAndLevel() {
        var choices=List.of(monster(1,1),monster(2,3));
        var selector=new MonsterSelector(bound -> bound-1);
        var result=selector.select(choices);
        assertEquals(2,result.monster().id());assertEquals(3,result.level());
        assertEquals(1,new MonsterSelector(bound->0).select(choices).monster().id());
    }
    @Test void seededReplay() {
        Random a=new Random(42),b=new Random(42);
        var one=new MonsterSelector(a::nextLong);var two=new MonsterSelector(b::nextLong);
        for(int i=0;i<100;i++) assertEquals(one.select(List.of(monster(1,10),monster(2,90))),two.select(List.of(monster(1,10),monster(2,90))));
    }
    @Test void invalidMastersFail() {
        assertThrows(GameUnavailable.class,()->new MonsterSelector(bound->0).select(List.of()));
        assertThrows(GameUnavailable.class,()->new MonsterSelector(bound->0).select(List.of(monster(1,0))));
        assertThrows(GameUnavailable.class,()->new MonsterSelector(bound->0).select(List.of(monster(1,-1))));
    }
}
