package dev.luma.game.command;

import dev.luma.game.GameFault;
import dev.luma.game.GameUnavailable;
import java.util.Objects;
import java.util.function.Supplier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.transaction.support.TransactionTemplate;

/** Opt-in infrastructure; no gameplay service is wired to it in v1.
 * REQUIRED joins an existing transaction or creates one, never REQUIRES_NEW.
 * Invoke before domain locks/mutations: player -> receipt lookup -> domain locks.
 * The callback must use the same datasource/transaction and have no external effects.
 * Returning a response commits it; throwing rolls back state and receipt together.
 * An outer transaction owns final commit. Do not send its response before commit.
 * A noRollbackFor caller may receive UnexpectedRollbackException instead of its
 * original domain error when it attempts to commit a poisoned transaction.
 * READ_COMMITTED is required so receipt reads see a lock predecessor's commit.
 * No receipt expiry: deleting receipts would allow old commands to execute again.
 */
@Service
public class CommandReceiptExecutor {
    private final JdbcTemplate db;
    private final TransactionTemplate transaction;

    public CommandReceiptExecutor(JdbcTemplate db, PlatformTransactionManager manager) {
        this.db = db;
        this.transaction = new TransactionTemplate(manager);
        this.transaction.setIsolationLevel(TransactionDefinition.ISOLATION_READ_COMMITTED);
    }

    public CommandResponse execute(CommandRequest request, Supplier<CommandResponse> mutation) {
        Objects.requireNonNull(request, "request");
        Objects.requireNonNull(mutation, "mutation");
        return transaction.execute(status -> {
            try {
                if (TransactionSynchronizationManager.isCurrentTransactionReadOnly())
                    throw new IllegalStateException("Command requires a write transaction");
                Integer isolation = TransactionSynchronizationManager.getCurrentTransactionIsolationLevel();
                if (isolation != null && isolation != TransactionDefinition.ISOLATION_READ_COMMITTED)
                    throw new IllegalStateException("Command requires READ_COMMITTED isolation");
                String fingerprint = CommandFingerprint.of(request);
                var player = db.queryForList(
                    "SELECT player_id FROM game.t_player WHERE player_id=? FOR UPDATE",
                    Long.class, request.playerId());
                if (player.size() != 1) throw new GameUnavailable("Command player missing");
                var existing = db.query("""
                    SELECT command_type,target_id,request_fingerprint,response_status,
                           response_body,response_schema_version
                    FROM game.t_command_receipt WHERE player_id=? AND command_id=?
                    """, (r, n) -> {
                        if (!request.commandType().equals(r.getString(1))
                                || !request.targetId().equals(r.getString(2))
                                || !fingerprint.equals(r.getString(3)))
                            throw new GameFault(409, "COMMAND_ID_REUSED");
                        return new CommandResponse(r.getInt(4), r.getString(5), r.getInt(6));
                    }, request.playerId(), request.commandId());
                if (!existing.isEmpty()) return existing.getFirst();
                CommandResponse response = Objects.requireNonNull(mutation.get(), "response");
                CommandFingerprint.parse(response.body());
                db.update("""
                    INSERT INTO game.t_command_receipt
                    (player_id,command_id,command_type,target_id,request_fingerprint,
                     response_status,response_body,response_schema_version)
                    VALUES (?,?,?,?,?,?,?,?)
                    """, request.playerId(), request.commandId(), request.commandType(), request.targetId(),
                    fingerprint, response.status(), response.body(), response.schemaVersion());
                return response;
            } catch (RuntimeException | Error ex) {
                // Also poisons an outer noRollbackFor transaction if its caller catches the error.
                status.setRollbackOnly();
                throw ex;
            }
        });
    }
}
