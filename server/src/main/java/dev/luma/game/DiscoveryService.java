package dev.luma.game;

import com.fasterxml.jackson.annotation.JsonInclude;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.*;

@Service
public class DiscoveryService {
    private static final long LOCAL_PLAYER=1;
    private final JdbcTemplate db;
    private final GameRepository repository;
    public DiscoveryService(JdbcTemplate db,GameRepository repository){this.db=db;this.repository=repository;}
    public record Request(UUID encounterId) {}
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Entry(int dexNo,String state,String rarity,String monsterCode,String monsterName,String assetIdentity,String baseAsset,
        long encounterCount,Instant firstDiscoveredAt,Instant lastSeenAt,long captureCount,Instant firstCapturedAt,Instant lastCapturedAt) {}
    private record Progress(String code,long seen,Instant first,Instant last,long captured,Instant firstCapture,Instant lastCapture) {}
    private Instant instant(java.sql.ResultSet r,int index)throws java.sql.SQLException {
        var t=r.getObject(index,OffsetDateTime.class);return t==null?null:t.toInstant();
    }
    @Transactional(readOnly=true)
    public List<Entry> dex(){
        // One SQL snapshot for both concepts: captures win even without a discovery row.
        var rows=db.query("""
            SELECT m.code,COALESCE(d.encounter_count,0),d.first_discovered_at,d.last_seen_at,
                   COALESCE(c.capture_count,0),c.first_captured_at,c.last_captured_at
            FROM game.m_monster m
            LEFT JOIN game.t_monster_discovery d ON d.monster_id=m.monster_id AND d.player_id=?
            LEFT JOIN game.t_collection c ON c.monster_id=m.monster_id AND c.player_id=?
            """,(r,n)->new Progress(r.getString(1),r.getLong(2),instant(r,3),instant(r,4),r.getLong(5),instant(r,6),instant(r,7)),LOCAL_PLAYER,LOCAL_PLAYER);
        var progress=new HashMap<String,Progress>();rows.forEach(r->progress.put(r.code(),r));
        return MonsterContent.definitions().stream().map(d->{
            var p=progress.get(d.monsterCode());long seen=p==null?0:p.seen();long captured=p==null?0:p.captured();
            String state=captured>0?"CAPTURED":seen>0?"DISCOVERED":"UNDISCOVERED";
            boolean known=seen>0||captured>0;
            return new Entry(d.dexNo(),state,d.rarity(),known?d.monsterCode():null,known?d.displayName():null,
                known?d.assetIdentity():null,known&&d.alphaCandidate()?"/assets/monsters/"+d.assetIdentity()+"/base.png":null,
                seen,p==null?null:p.first(),p==null?null:p.last(),captured,p==null?null:p.firstCapture(),p==null?null:p.lastCapture());
        }).toList();
    }
    @Transactional
    public Entry discover(String code,UUID encounterId){
        if(encounterId==null)throw new GameFault(400,"INVALID_REQUEST");
        var content=MonsterContent.find(code).orElseThrow(()->new GameFault(404,"UNKNOWN_MONSTER"));
        if(!MonsterContent.productionReady(code))throw new GameFault(409,"INVALID_STATE");
        repository.lockPlayer(LOCAL_PLAYER); // Same database lock/order as Battle/Capture.
        var masters=repository.monsters();
        var master=masters.stream().filter(m->m.code().equals(code)).findFirst().orElseThrow(()->new GameFault(409,"INVALID_STATE"));
        var ids=db.queryForList("SELECT monster_id FROM game.t_encounter WHERE encounter_id=? AND player_id=?",Long.class,encounterId,LOCAL_PLAYER);
        if(ids.size()!=1 || ids.getFirst()!=master.id())throw new GameFault(409,"INVALID_ENCOUNTER");
        var now=OffsetDateTime.ofInstant(repository.now(),ZoneOffset.UTC);
        int inserted=db.update("INSERT INTO game.t_monster_discovery_receipt(encounter_id,acknowledged_at) VALUES (?,?) ON CONFLICT DO NOTHING",encounterId,now);
        if(inserted==1)db.update("""
            INSERT INTO game.t_monster_discovery(player_id,monster_id,first_discovered_at,last_seen_at,encounter_count,created_at,updated_at)
            VALUES (?,?,?,?,1,?,?)
            ON CONFLICT (player_id,monster_id) DO UPDATE SET
              last_seen_at=GREATEST(game.t_monster_discovery.last_seen_at,EXCLUDED.last_seen_at),
              encounter_count=game.t_monster_discovery.encounter_count+1,
              updated_at=GREATEST(game.t_monster_discovery.updated_at,EXCLUDED.updated_at)
            """,LOCAL_PLAYER,master.id(),now,now,now,now);
        return dex().stream().filter(e->e.dexNo()==content.dexNo()).findFirst().orElseThrow();
    }
}
