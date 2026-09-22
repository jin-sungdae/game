package dev.luma.game;

/** Pure modifier at an existing counterattack opportunity; never damage rules. */
public final class BattleDecision {
    private BattleDecision() {}
    public enum Action { ATTACK, WAIT }
    public static Action choose(BattlePersonality personality,int completedTurns,RandomSource random) {
        if(personality==null || completedTurns<0) throw new GameUnavailable("Invalid battle decision input");
        int attackPercent=switch(personality){
            case BALANCED -> 85;
            case AGGRESSIVE -> 100;
            case DEFENSIVE -> 45;
            case ERRATIC -> completedTurns%2==0?25:90;
        };
        long roll=random.nextLong(100);
        if(roll<0 || roll>=100) throw new GameUnavailable("Invalid battle decision random source");
        return roll<attackPercent?Action.ATTACK:Action.WAIT;
    }
}
