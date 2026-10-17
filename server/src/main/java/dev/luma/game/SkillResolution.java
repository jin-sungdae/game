package dev.luma.game;

import static dev.luma.game.SkillCatalog.*;

/** Pure server effect arithmetic. Turns, targets and power are never accepted from clients. */
public final class SkillResolution {
    private SkillResolution() {}
    public record Fighter(int hp,int maxHp,int guard,int weaken,int burn,int regen) {
        public Fighter { if(maxHp<1||hp<0||hp>maxHp||guard<0||weaken<0||burn<0||regen<0) throw new IllegalArgumentException(); }
        public Fighter hp(int value) { return new Fighter(Math.clamp(value,0,maxHp),maxHp,guard,weaken,burn,regen); }
        public Fighter tick() { return new Fighter(Math.clamp(hp-burn+regen,0,maxHp),maxHp,0,0,0,0); }
    }
    public record Result(Fighter caster,Fighter target,int damage) {}
    public static Result apply(Entry entry,int level,Fighter caster,Fighter target) {
        int power=SkillRules.power(entry.definition(),level);
        int damage=0;
        switch(entry.effect()) {
            case DAMAGE -> {damage=Math.min(target.hp(),Math.max(0,power-caster.weaken()-target.guard()));target=target.hp(target.hp()-damage);}
            case HEAL -> caster=caster.hp(caster.hp()+power);
            case GUARD -> caster=new Fighter(caster.hp(),caster.maxHp(),Math.max(caster.guard(),power),caster.weaken(),caster.burn(),caster.regen());
            case WEAKEN -> target=new Fighter(target.hp(),target.maxHp(),target.guard(),Math.max(target.weaken(),power),target.burn(),target.regen());
            case BURN -> target=new Fighter(target.hp(),target.maxHp(),target.guard(),target.weaken(),Math.max(target.burn(),power),target.regen());
            case REGEN -> caster=new Fighter(caster.hp(),caster.maxHp(),caster.guard(),caster.weaken(),caster.burn(),Math.max(caster.regen(),power));
        }
        return new Result(caster,target,damage);
    }
}
