package dev.luma.game;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import java.util.*;
@Repository
public class SkillStateStore {
    public static class State {
        public int version=1;
        public String species;
        public int stage,level;
        public Map<String,Integer> ready=new HashMap<>();
        public SkillResolution.Fighter companion,monster;
    }
    private final JdbcTemplate db; private final ObjectMapper json;
    public SkillStateStore(JdbcTemplate db,ObjectMapper json){this.db=db;this.json=json;}
    public State load(UUID id) {
        var rows=db.queryForList("SELECT state::text FROM game.t_battle_skill_state WHERE battle_id=? FOR UPDATE",String.class,id);
        if(rows.isEmpty())return null;
        try {var state=json.readValue(rows.getFirst(),State.class);if(state.version!=1)throw new IllegalArgumentException();return state;}
        catch(Exception ex){throw new GameUnavailable("Invalid skill state");}
    }
    public void save(UUID id,State state){
        try {db.update("INSERT INTO game.t_battle_skill_state(battle_id,state) VALUES(?,?::jsonb) ON CONFLICT(battle_id) DO UPDATE SET state=excluded.state",id,json.writeValueAsString(state));}
        catch(com.fasterxml.jackson.core.JsonProcessingException ex){throw new GameUnavailable("Skill state serialization failed");}
    }
}
