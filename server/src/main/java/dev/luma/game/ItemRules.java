package dev.luma.game;

/** Approved v0.1 effects. No client-supplied magnitudes. */
public final class ItemRules {
    private ItemRules() {}
    public static final int POTION_HEAL=30, BERRY_BOND=1;
    public static final double CHARM_BONUS=0.10;
    public static long total(long price,int quantity) {
        if(quantity<=0) throw new GameFault(400,"INVALID_QUANTITY");
        try {return Math.multiplyExact(price,(long)quantity);}
        catch(ArithmeticException e) {throw new GameFault(400,"INVALID_QUANTITY");}
    }
    public static double captureChance(double base,double bonus) {return Math.clamp(base+bonus,0.05,0.95);}
}
