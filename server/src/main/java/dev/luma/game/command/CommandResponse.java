package dev.luma.game.command;

import java.util.Objects;

/** Stored JSON is replayed verbatim with its original status and schema version.
 * A domain adapter must support that version; never reinterpret it as today's DTO.
 */
public record CommandResponse(int status, String body, int schemaVersion) {
    public CommandResponse {
        if (status < 200 || status > 599) throw new IllegalArgumentException("Invalid response status");
        if (schemaVersion < 1) throw new IllegalArgumentException("Invalid response schema version");
        Objects.requireNonNull(body, "body");
    }
}
