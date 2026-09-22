package dev.luma.game;

/** Pure server formulas; no presentation or random state. */
public final class CombatRules {
    private CombatRules() {}
    public static int companionHp() {return 100;}
    public static int companionAttack(int level) {return Math.addExact(10,Math.multiplyExact(level,2));}
    public static int monsterHp(int level) {return Math.addExact(20,Math.multiplyExact(level,10));}
    public static int monsterAttack(int level) {return Math.addExact(3,Math.multiplyExact(level,2));}
    public static int level(long exp) {return exp>=1000?5:exp>=600?4:exp>=300?3:exp>=100?2:1;}
    public static double captureChance(int hp,int maxHp,String rarity) {
        if(maxHp<=0 || hp<0 || hp>maxHp || (!"COMMON".equals(rarity) && !"UNCOMMON".equals(rarity))) throw new GameFault(409,"INVALID_STATE");
        return Math.clamp(MonsterContent.rarity(rarity).baseCaptureRate()+(1-(double)hp/maxHp)*0.50,0.05,0.95);
    }
    public static long gold(int level) {return level*10L;}
    public static long exp(int level) {return level*20L;}
}
