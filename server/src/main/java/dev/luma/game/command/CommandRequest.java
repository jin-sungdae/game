package dev.luma.game.command;

import java.util.Objects;
import java.util.UUID;

/** Reuse an ID only for a retry of the same intent; new actions need new IDs.
 * Domain revisions and expected identities belong in requestJson, not in the executor.
 * playerId must come from the trusted caller, never an unvalidated client payload.
 */
public record CommandRequest(long playerId, UUID commandId, String commandType,
                             String targetId, String requestJson) {
    public CommandRequest {
        if (playerId <= 0) throw new IllegalArgumentException("Invalid player ID");
        Objects.requireNonNull(commandId, "commandId");
        if (commandType == null || !commandType.matches("[A-Z][A-Z0-9_]{0,63}"))
            throw new IllegalArgumentException("Invalid command type");
        if (targetId == null || targetId.isBlank() || targetId.length() > 200)
            throw new IllegalArgumentException("Invalid target ID");
        Objects.requireNonNull(requestJson, "requestJson");
    }
}
