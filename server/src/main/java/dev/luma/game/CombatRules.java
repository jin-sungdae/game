package dev.luma.game;

/** Pure server formulas; no presentation or random state. */
public final class CombatRules {
    private CombatRules() {}
    public static int companionHp() {return 100;}
    public static int companionAttack(int level) {return Math.addExact(10,Math.multiplyExact(level,2));}
    public static int monsterHp(int level) {return Math.addExact(20,Math.multiplyExact(level,10));}
    public static int monsterAttack(int level) {return Math.addExact(3,Math.multiplyExact(level,2));}
    public static final int MAX_LEVEL = 20;
    /** Cumulative EXP: preserve 0/100/300/600/1000, then linear growth of each level cost. */
    public static long levelThreshold(int level) {
        if(level<1 || level>MAX_LEVEL) throw new IllegalArgumentException("Unsupported level");
        return 50L*level*(level-1);
    }
    public static int level(long exp) {
        int level=1;
        while(level<MAX_LEVEL && exp>=levelThreshold(level+1)) level++;
        return level;
    }
    public static double captureChance(int hp,int maxHp,String rarity) {
        if(maxHp<=0 || hp<0 || hp>maxHp || rarity==null || !java.util.List.of("COMMON","UNCOMMON","RARE","SPECIAL").contains(rarity)) throw new GameFault(409,"INVALID_STATE");
        return Math.clamp(MonsterContent.rarity(rarity).baseCaptureRate()+(1-(double)hp/maxHp)*0.50,0.05,0.95);
    }
    public static long gold(int level) {return level*10L;}
    public static long exp(int level) {return level*20L;}
}
