package dev.luma.game;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** Versioned Monster content only; never Companion state or a spawn director. */
public final class MonsterContent {
    public record RarityDefaults(int encounterWeight, double baseCaptureRate) {}
    public record Definition(int dexNo, String monsterCode, String displayName, String rarity,
        String archetype, String movementProfile, String behaviorProfile, String spawnProfile,
        String spawnCondition, int encounterWeight, Double baseCaptureRate, double visualScale,
        String assetIdentity, boolean enabled, boolean contentReady, boolean alphaCandidate,
        String productionStatus) {}
    private static final Map<String,RarityDefaults> DEFAULTS = loadDefaults();
    private static final Map<String,Definition> DEFINITIONS = loadDefinitions();
    private MonsterContent() {}

    public static RarityDefaults rarity(String rarity) {
        var value=DEFAULTS.get(rarity);
        if(value==null) throw new GameFault(409,"INVALID_STATE");
        return value;
    }
    public static Collection<Definition> definitions() {return DEFINITIONS.values();}
    public static Optional<Definition> find(String code) {return Optional.ofNullable(DEFINITIONS.get(code));}
    public static boolean productionReady(String code) {
        var d=DEFINITIONS.get(code);
        return d!=null && d.enabled() && d.contentReady() && "PRODUCTION".equals(d.productionStatus());
    }
    /** A DB enable flag alone cannot authorize unfinished content. Approved Alpha level ranges must match the desktop 1–3 contract. */
    public static boolean eligible(MonsterSelector.Monster master) {
        if(!productionReady(master.code())) return false;
        var d=DEFINITIONS.get(master.code());
        if(!d.displayName().equals(master.name()) || !d.rarity().equals(master.rarity())
            || !d.movementProfile().equals(master.movementProfile()) || d.encounterWeight()!=master.weight()
            || (d.alphaCandidate() && (master.minLevel()!=1 || master.maxLevel()!=3)))
            throw new GameUnavailable("Production monster master differs from approved content");
        return true;
    }
    private static JsonNode read(String name) {
        try(var input=MonsterContent.class.getResourceAsStream("/content/"+name)) {
            if(input==null) throw new IllegalStateException("Missing Monster content: "+name);
            return new ObjectMapper().readTree(input);
        } catch(IOException e) {throw new IllegalStateException("Invalid Monster content: "+name,e);}
    }
    private static Map<String,RarityDefaults> loadDefaults() {
        var json=read("rarity-defaults.json");var values=new LinkedHashMap<String,RarityDefaults>();
        var names=List.of("COMMON","UNCOMMON","RARE","EPIC","SPECIAL");
        if(!json.isObject() || json.size()!=names.size()) throw new IllegalStateException("Invalid rarity defaults");
        for(var name:names) {
            var node=json.required(name);
            int weight=integer(node,"encounterWeight");double rate=decimal(node,"baseCaptureRate");
            if(weight<=0 || rate<0 || rate>1) throw new IllegalStateException("Invalid rarity balance");
            values.put(name,new RarityDefaults(weight,rate));
        }
        return Collections.unmodifiableMap(values);
    }
    private static Map<String,Definition> loadDefinitions() {
        var rows=read("monster-dex.json");var values=new LinkedHashMap<String,Definition>();var numbers=new HashSet<Integer>();
        if(!rows.isArray()) throw new IllegalStateException("Expected Monster content array");
        for(var n:rows) {
            var d=new Definition(integer(n,"dexNo"),text(n,"monsterCode"),n.required("displayName").isNull()?null:text(n,"displayName"),
                text(n,"rarity"),text(n,"archetype"),text(n,"movementProfile"),text(n,"behaviorProfile"),text(n,"spawnProfile"),text(n,"spawnCondition"),
                integer(n,"encounterWeight"),n.required("baseCaptureRate").isNull()?null:decimal(n,"baseCaptureRate"),decimal(n,"visualScale"),text(n,"assetIdentity"),
                flag(n,"enabled"),flag(n,"contentReady"),flag(n,"alphaCandidate"),text(n,"productionStatus"));
            if(d.dexNo()<1 || values.putIfAbsent(d.monsterCode(),d)!=null || !numbers.add(d.dexNo())) throw new IllegalStateException("Duplicate content identity");
            if(!d.monsterCode().matches("[A-Z][A-Z0-9_]*") || !d.assetIdentity().matches("[a-z][a-z0-9_]*")
                || d.visualScale()<.5 || d.visualScale()>1.5 || d.encounterWeight()<0
                || (d.baseCaptureRate()!=null && (d.baseCaptureRate()<0 || d.baseCaptureRate()>1))) throw new IllegalStateException("Invalid content bounds");
            var defaults=rarity(d.rarity());
            if(d.alphaCandidate() && (d.encounterWeight()!=defaults.encounterWeight() || !Objects.equals(d.baseCaptureRate(),defaults.baseCaptureRate())))
                throw new IllegalStateException("Stale rarity projection: "+d.monsterCode());
            if(d.enabled() && !d.contentReady()) throw new IllegalStateException("Enabled unfinished content");
            if(d.contentReady() && (!"PRODUCTION".equals(d.productionStatus()) || d.displayName()==null || d.encounterWeight()==0 || d.baseCaptureRate()==null))
                throw new IllegalStateException("Unconfirmed production metadata");
        }
        return Collections.unmodifiableMap(values);
    }
    private static String text(JsonNode n,String key) {
        var v=n.required(key);if(!v.isTextual() || v.textValue().isBlank()) throw new IllegalStateException("Invalid content text: "+key);return v.textValue();
    }
    private static int integer(JsonNode n,String key) {
        var v=n.required(key);if(!v.isIntegralNumber() || !v.canConvertToInt()) throw new IllegalStateException("Invalid content integer: "+key);return v.intValue();
    }
    private static double decimal(JsonNode n,String key) {
        var v=n.required(key);if(!v.isNumber() || !Double.isFinite(v.doubleValue())) throw new IllegalStateException("Invalid content decimal: "+key);return v.doubleValue();
    }
    private static boolean flag(JsonNode n,String key) {
        var v=n.required(key);if(!v.isBoolean()) throw new IllegalStateException("Invalid content flag: "+key);return v.booleanValue();
    }
}
