package dev.luma.game;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.luma.game.command.*;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CompanionSelectionService {
    private static final long PLAYER = 1;
    public record Request(UUID commandId, long companionId, long expectedSelectionRevision) {
        public Request {
            if (commandId == null || companionId <= 0 || expectedSelectionRevision < 0)
                throw new GameFault(400, "INVALID_SELECTION_COMMAND");
        }
    }
    public record Snapshot(long activeCompanionId, long activeSelectionRevision) {}
    private final JdbcTemplate db;
    private final CommandReceiptExecutor receipts;
    private final ObjectMapper json;
    public CompanionSelectionService(JdbcTemplate db, CommandReceiptExecutor receipts, ObjectMapper json) {
        this.db = db; this.receipts = receipts;
        this.json = json.copy().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    }
    @Transactional(readOnly=true)
    public Snapshot snapshot() {
        // One statement keeps active identity and revision in the same MVCC snapshot.
        var rows = db.query("""
            SELECT c.player_companion_id,p.active_selection_revision FROM game.t_player p
            JOIN game.t_player_companion c USING(player_id) WHERE p.player_id=? AND c.active
            """, (r,n)->new Snapshot(r.getLong(1),r.getLong(2)), PLAYER);
        if (rows.size()!=1) throw new GameUnavailable("Exactly one active companion required");
        return rows.getFirst();
    }
    public Request parse(String body) {
        try {
            var node=json.readTree(body);
            if (node==null || !node.isObject()) throw new IllegalArgumentException();
            var fields=new HashSet<String>(); node.fieldNames().forEachRemaining(fields::add);
            if (!fields.equals(Set.of("commandId","companionId","expectedSelectionRevision"))
                || !node.get("commandId").isTextual()) throw new IllegalArgumentException();
            for (String field:List.of("companionId","expectedSelectionRevision"))
                if (!node.get(field).isIntegralNumber() || !node.get(field).canConvertToLong()) throw new IllegalArgumentException();
            String value=node.get("commandId").textValue(); UUID id=UUID.fromString(value);
            if (!id.toString().equalsIgnoreCase(value)) throw new IllegalArgumentException();
            return new Request(id,node.get("companionId").longValue(),node.get("expectedSelectionRevision").longValue());
        } catch (JsonProcessingException | IllegalArgumentException e) {
            throw new GameFault(400,"INVALID_SELECTION_COMMAND");
        }
    }
    private String encode(Object value) {
        try { return json.writeValueAsString(value); }
        catch (JsonProcessingException e) { throw new GameUnavailable("Selection serialization failed"); }
    }
    public CommandResponse select(Request request) {
        return receipts.execute(new CommandRequest(PLAYER,request.commandId(),"COMPANION_SELECTION",
            Long.toString(request.companionId()),encode(request)), () -> {
            var before=snapshot();
            if (before.activeSelectionRevision()!=request.expectedSelectionRevision())
                throw new GameFault(409,"STALE_SELECTION");
            var target=db.queryForList("SELECT player_companion_id FROM game.t_player_companion WHERE player_id=? AND player_companion_id=? FOR UPDATE",
                Long.class,PLAYER,request.companionId());
            if (target.size()!=1) throw new GameFault(404,"COMPANION_NOT_OWNED");
            if (before.activeCompanionId()==request.companionId())
                return new CommandResponse(200,encode(before),1);
            if (Boolean.TRUE.equals(db.queryForObject("SELECT EXISTS(SELECT 1 FROM game.t_battle b JOIN game.t_player_companion c USING(player_companion_id) WHERE c.player_id=? AND b.status='ACTIVE')",Boolean.class,PLAYER)))
                throw new GameFault(409,"BATTLE_IN_PROGRESS");
            // The player lock serializes selection with evolution, interaction and battle start.
            // Clear first to preserve the existing partial unique active-companion index.
            db.update("UPDATE game.t_player_companion SET active=false,updated_at=clock_timestamp() WHERE player_id=? AND active",PLAYER);
            db.update("UPDATE game.t_player_companion SET active=true,updated_at=clock_timestamp() WHERE player_id=? AND player_companion_id=?",PLAYER,request.companionId());
            db.update("UPDATE game.t_player SET active_selection_revision=active_selection_revision+1 WHERE player_id=?",PLAYER);
            return new CommandResponse(200,encode(snapshot()),1);
        });
    }
}
