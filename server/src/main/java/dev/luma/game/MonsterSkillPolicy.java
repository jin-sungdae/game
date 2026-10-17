package dev.luma.game;
import java.util.*;
/** Pure turn-boundary selection. Concept identifiers are never aliases for legacy monsters. */
public final class MonsterSkillPolicy {
    private MonsterSkillPolicy() {}
    public static Optional<SkillCatalog.Entry> choose(String species,int level,int turn,int hp,int maxHp,Map<String,Integer> ready) {
        if(turn<0||hp<=0||maxHp<1)return Optional.empty();
        return SkillCatalog.unlocked(species,1,level).stream()
            .filter(e->e.definition().kind()==SkillDefinitions.Kind.ACTIVE)
            .filter(e->ready.getOrDefault(e.definition().code(),0)<=turn)
            .filter(e->e.effect()!=SkillCatalog.Effect.HEAL || hp*2L<maxHp)
            .filter(e->e.effect()!=SkillCatalog.Effect.GUARD || turn%2==0)
            .findFirst();
    }
    public static SkillResolution.Result resolve(SkillCatalog.Entry active,int level,SkillResolution.Fighter caster,SkillResolution.Fighter target) {
        var passive=SkillCatalog.unlocked(active.definition().speciesCode(),1,level).stream()
            .filter(e->e.definition().kind()==SkillDefinitions.Kind.PASSIVE).findFirst();
        if(passive.isPresent()){var p=SkillResolution.apply(passive.get(),level,caster,target);caster=p.caster();target=p.target();}
        return SkillResolution.apply(active,level,caster,target);
    }
}
