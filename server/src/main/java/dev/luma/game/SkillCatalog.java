package dev.luma.game;

import java.util.*;
import static dev.luma.game.SkillDefinitions.*;

/** Review defaults; concept monsters are identities, never spawn activation or legacy aliases. */
public final class SkillCatalog {
    private SkillCatalog() {}
    public enum Effect { DAMAGE, HEAL, GUARD, WEAKEN, BURN, REGEN }
    public record Entry(Definition definition, String name, String element, Effect effect,
                        String castMotion, String delivery, String assetStatus, boolean released) {}
    private static final List<Entry> ENTRIES = build();
    public static List<Entry> all() { return ENTRIES; }
    public static Optional<Entry> find(String code) { return ENTRIES.stream().filter(e -> e.definition().code().equals(code)).findFirst(); }
    public static List<Entry> unlocked(String species,int stage,int level) {
        return ENTRIES.stream().filter(e -> SkillRules.unlocked(e.definition(),species,stage,level)).toList();
    }
    private static Entry entry(String code,String species,String name,String element,int stage,Kind kind,
                               Effect effect,String motion,String delivery,boolean released) {
        int[] levels={1,3,6,20,50};
        int power=kind==Kind.PASSIVE?2:effect==Effect.DAMAGE?8+stage*2:4+stage*2;
        return new Entry(new Definition(code,1,species,kind,stage,levels[stage-1],
            Set.of(Effect.HEAL,Effect.GUARD,Effect.REGEN).contains(effect)?Target.SELF:Target.ENEMY,
            effect.name(),power,kind==Kind.PASSIVE?0:1,kind==Kind.PASSIVE?power:power+20,kind==Kind.PASSIVE?0:2+stage/2,true),
            name,element,effect,motion,delivery,"ASSET_REQUIRED",released);
    }
    private static List<Entry> build() {
        var out=new ArrayList<Entry>();
        String[][] names={{"생명의 숨결","숲의 결계","뿌리의 심판","대지의 맥동","생명의 순환"},
            {"바람의 길","하늘의 창","천공의 폭풍","상승 기류","천공의 여명"},
            {"그림자 소환","달의 영역","어둠의 심판","잔영의 장막","영원의 월식"}};
        String[][] motions={{"seed_inhale_leaf_release","forelegs_brace_leaf_dome","antlers_lower_root_surge","tree_stance_ground_pulse","canopy_open_life_ring"},
            {"chick_crouch_wing_gust","wings_draw_back_feather_lance","leap_spiral_wing_sweep","hover_wings_lift_updraft","crest_raise_full_wing_storm"},
            {"kitten_crouch_shadow_split","tail_arc_moon_circle","shoulders_lower_shadow_pounce","body_coil_afterimage_fan","antlers_tilt_eclipse_crown"}};
        Effect[][] effects={{Effect.HEAL,Effect.GUARD,Effect.DAMAGE,Effect.REGEN,Effect.DAMAGE},
            {Effect.GUARD,Effect.DAMAGE,Effect.DAMAGE,Effect.WEAKEN,Effect.DAMAGE},
            {Effect.DAMAGE,Effect.WEAKEN,Effect.DAMAGE,Effect.GUARD,Effect.BURN}};
        String[] species={"MOA","RUU","NOX"},elements={"NATURE","WIND","SHADOW"};
        for(int s=0;s<3;s++) for(int stage=1;stage<=5;stage++) {
            String code=species[s]+"_S"+stage;
            out.add(entry(code,species[s],names[s][stage-1],elements[s],stage,Kind.ACTIVE,effects[s][stage-1],motions[s][stage-1],stage>=3?"AREA":"PROJECTILE",true));
            out.add(entry(code+"_PASSIVE",species[s],names[s][stage-1]+" · 공명",elements[s],stage,Kind.PASSIVE,
                s==0?Effect.REGEN:s==1?Effect.GUARD:Effect.WEAKEN,motions[s][stage-1]+"_resonance","AREA",true));
        }
        String[] regions={"NATURE","WIND","SHADOW","FIRE","ICE","SAND","WATER","MACHINE","CHAOS","LIGHT"};
        String[][] bodies={
            {"seed_sprite","antler_deer","leaf_bear","tree_guardian","cap_sprite","mushroom_toad","vine_deer","leaf_mammal","moss_bear","bark_stag"},
            {"crest_chick","winged_fox","cloud_chick","feather_unicorn","cloud_owl","glider_bird","winged_ray","plume_fox","cloud_cat","sky_giant"},
            {"shadow_kitten","horned_hound","orb_mouth","masked_spirit","crystal_imp","ghost_ray","shadow_dragon","veil_serpent","flame_imp","armored_beast"},
            {"ember_kitten","fire_lizard","lava_golem","magma_tortoise","flame_giant","fire_dragon","coal_guardian","rock_bear","ember_fox","flame_stag"},
            {"ice_deer","frost_fox","crystal_dragon","frozen_unicorn","snow_kitten","snow_owl","ice_rabbit","glacier_golem","tundra_cub","frost_wolf"},
            {"sand_golem","scarab","desert_fox","ruin_serpent","stone_beetle","scorpion","bandaged_hare","sand_wyrm","masked_owl","dune_fox"},
            {"jellyfish","coral_drake","wave_ray","shell_crab","water_dragon","shell_turtle","tidal_whale","fin_dragon","deep_jellyfish","tentacle_beast"},
            {"stone_golem","clock_owl","bronze_guardian","gear_spider","book_construct","ring_core","ruin_sentinel","crystal_golem","portal_shield","orbit_core"},
            {"chaos_dragon","void_wolf","crescent_imp","corrupt_stag","tentacle_shade","toxic_serpent","void_eye","thorn_spirit","chaos_eye","corrupt_fox"},
            {"star_dragon","moon_deer","celestial_owl","solar_orb","crown_stag","star_stag","light_owl","winged_unicorn","moon_fox","halo_penguin"}};
        for(int region=0;region<10;region++) for(int i=0;i<10;i++) {
            String code=String.format(Locale.ROOT,"M%03d",region*10+i+1);
            String body=bodies[region][i];
            Effect effect= switch(i%5) { case 1 -> Effect.WEAKEN; case 2 -> Effect.GUARD; case 3 -> Effect.BURN; case 4 -> Effect.HEAL; default -> Effect.DAMAGE; };
            String motion=body+"_"+switch(i%5) {case 0->"coil_release";case 1->"lower_focus_project";case 2->"brace_expand";case 3->"rise_sweep";default->"fold_gather_pulse";};
            out.add(entry(code+"_ACTIVE",code,body+" · "+regions[region],regions[region],1,Kind.ACTIVE,effect,motion,i%2==0?"PROJECTILE":"AREA",false));
            out.add(entry(code+"_PASSIVE",code,body+" · resonance",regions[region],1,Kind.PASSIVE,
                i%2==0?Effect.GUARD:Effect.REGEN,motion+"_resonance","AREA",false));
        }
        return List.copyOf(out);
    }
}
