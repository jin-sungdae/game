package dev.luma.game;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.luma.game.command.CommandReceiptExecutor;
import dev.luma.game.command.CommandRequest;
import dev.luma.game.command.CommandResponse;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;

/** Structured commands only; bodyless compatibility remains outside this contract.
 * The existing executor owns the transaction and player lock. Replay precedes
 * current-state checks. New mutation fails closed without a Switching provider.
 * Stored bootstrap is the historical command result, not a live snapshot:
 * future clients must refresh bootstrap and deduplicate presentation by commandId.
 */
@Service
public class EvolutionCommandService {
    private static final long LOCAL_PLAYER = 1;
    private static final Set<String> FIELDS = Set.of("commandId", "expectedCompanionId",
        "expectedStage", "expectedSelectionRevision");
    private final CommandReceiptExecutor receipts;
    private final EvolutionRepository companions;
    private final EvolutionService evolution;
    private final ObjectProvider<EvolutionSelectionRevision> selection;
    private final ObjectMapper json;

    public EvolutionCommandService(CommandReceiptExecutor receipts, EvolutionRepository companions,
            EvolutionService evolution, ObjectProvider<EvolutionSelectionRevision> selection,
            ObjectMapper json) {
        this.receipts = receipts;
        this.companions = companions;
        this.evolution = evolution;
        this.selection = selection;
        this.json = json.copy().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    }

    public EvolutionCommandRequest parse(String body) {
        try {
            var node = json.readTree(body);
            if (node == null || !node.isObject()) throw new IllegalArgumentException();
            var fields = new HashSet<String>(); node.fieldNames().forEachRemaining(fields::add);
            if (!fields.equals(FIELDS) || !node.get("commandId").isTextual()) throw new IllegalArgumentException();
            for (String name : Set.of("expectedCompanionId", "expectedStage", "expectedSelectionRevision"))
                if (!node.get(name).isIntegralNumber() || !node.get(name).canConvertToLong())
                    throw new IllegalArgumentException();
            UUID id = UUID.fromString(node.get("commandId").textValue());
            if (!id.toString().equalsIgnoreCase(node.get("commandId").textValue())) throw new IllegalArgumentException();
            long stage = node.get("expectedStage").longValue();
            if (stage < 1 || stage > 5) throw new IllegalArgumentException();
            return new EvolutionCommandRequest(id, node.get("expectedCompanionId").longValue(),
                (int) stage, node.get("expectedSelectionRevision").longValue());
        } catch (JsonProcessingException | IllegalArgumentException ex) {
            throw new GameFault(400, "INVALID_EVOLUTION_COMMAND");
        }
    }

    private String encode(Object value) {
        try { return json.writeValueAsString(value); }
        catch (JsonProcessingException ex) { throw new GameUnavailable("Evolution result serialization failed"); }
    }

    public CommandResponse execute(EvolutionCommandRequest request) {
        var command = new CommandRequest(LOCAL_PLAYER, request.commandId(), "EVOLUTION",
            Long.toString(request.expectedCompanionId()), encode(request));
        return receipts.execute(command, () -> {
            var current = companions.lockActive(LOCAL_PLAYER);
            if (current.playerCompanionId() != request.expectedCompanionId())
                throw new GameFault(409, "COMPANION_MISMATCH");
            var revision = selection.getIfAvailable();
            if (revision == null) throw new GameFault(503, "BLOCKED_BY_SWITCHING_CONTRACT");
            long actualRevision = revision.current(LOCAL_PLAYER);
            if (actualRevision < 0) throw new GameUnavailable("Invalid selection revision");
            if (actualRevision != request.expectedSelectionRevision())
                throw new GameFault(409, "STALE_SELECTION");
            if (current.evolutionStage() != request.expectedStage())
                throw new GameFault(409, "STALE_STAGE");
            // The injected service is a Spring proxy; REQUIRED joins the executor transaction.
            // Serialization is inside that transaction, so failure also rolls back stage/history.
            return new CommandResponse(200, encode(evolution.evolve()), 1);
        });
    }
}
