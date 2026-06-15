package edu.courseflow.outboxrelay.relay;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class DeadLetterRepository {

    private final JdbcClient jdbc;

    public DeadLetterRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public void recordDeadLetter(String serviceName,
                                 UUID sourceEventId,
                                 String eventType,
                                 String aggregateId,
                                 String payload,
                                 int attempts,
                                 String errorClass,
                                 String lastError,
                                 String payloadHash) {
        jdbc.sql("""
                        INSERT INTO relay_dead_letters
                            (service_name, source_event_id, event_type, topic, aggregate_id, payload, attempts,
                             error_class, last_error, status, payload_hash, updated_at)
                        VALUES (:service, :eventId, :eventType, :topic, :aggregateId, :payload, :attempts,
                                :errorClass, :lastError, 'OPEN', :payloadHash, NOW())
                        ON CONFLICT (service_name, source_event_id) DO UPDATE
                          SET attempts = EXCLUDED.attempts,
                              topic = COALESCE(EXCLUDED.topic, relay_dead_letters.topic),
                              error_class = EXCLUDED.error_class,
                              last_error = EXCLUDED.last_error,
                              payload_hash = EXCLUDED.payload_hash,
                              status = CASE
                                  WHEN relay_dead_letters.status IN ('REPLAYED', 'DISCARDED')
                                  THEN relay_dead_letters.status
                                  ELSE 'OPEN'
                              END,
                              updated_at = NOW()
                        """)
                .param("service", serviceName)
                .param("eventId", sourceEventId)
                .param("eventType", eventType)
                .param("topic", eventType)
                .param("aggregateId", aggregateId)
                .param("payload", payload)
                .param("attempts", attempts)
                .param("errorClass", truncate(errorClass, 255))
                .param("lastError", truncate(lastError, 4000))
                .param("payloadHash", payloadHash)
                .update();
    }

    public int recordDeliveryFailure(String serviceName, UUID sourceEventId, String error) {
        return jdbc.sql("""
                        INSERT INTO relay_delivery_states
                            (service_name, source_event_id, attempts, first_failed_at, last_failed_at,
                             last_error, status)
                        VALUES (:service, :eventId, 1, NOW(), NOW(), :lastError, 'FAILING')
                        ON CONFLICT (service_name, source_event_id) DO UPDATE
                          SET attempts = relay_delivery_states.attempts + 1,
                              last_failed_at = NOW(),
                              last_error = EXCLUDED.last_error,
                              status = 'FAILING'
                        RETURNING attempts
                        """)
                .param("service", serviceName)
                .param("eventId", sourceEventId)
                .param("lastError", truncate(error, 4000))
                .query((rs, rowNum) -> rs.getInt("attempts"))
                .list()
                .stream()
                .findFirst()
                .orElse(1);
    }

    public void clearDeliveryState(String serviceName, UUID sourceEventId) {
        jdbc.sql("""
                        DELETE FROM relay_delivery_states
                        WHERE service_name = :service
                          AND source_event_id = :eventId
                        """)
                .param("service", serviceName)
                .param("eventId", sourceEventId)
                .update();
    }

    public List<DeadLetterRecord> search(String status,
                                         String serviceName,
                                         String eventType,
                                         String aggregateId,
                                         String payloadHash,
                                         int limit) {
        String normalizedStatus = blankToNull(status);
        String normalizedServiceName = blankToNull(serviceName);
        String normalizedEventType = blankToNull(eventType);
        String normalizedAggregateId = blankToNull(aggregateId);
        String normalizedPayloadHash = normalizePayloadHash(payloadHash);

        StringBuilder sql = new StringBuilder("""
                        SELECT *
                        FROM relay_dead_letters
                        WHERE 1 = 1
                        """);
        if (normalizedStatus != null) {
            sql.append("  AND status = :status\n");
        }
        if (normalizedServiceName != null) {
            sql.append("  AND service_name = :serviceName\n");
        }
        if (normalizedEventType != null) {
            sql.append("  AND event_type = :eventType\n");
        }
        if (normalizedAggregateId != null) {
            sql.append("  AND aggregate_id = :aggregateId\n");
        }
        if (normalizedPayloadHash != null) {
            sql.append("""
                            AND (
                                payload_hash = :payloadHash
                                OR (
                                    payload_hash IS NULL
                                    AND ('sha256:' || encode(digest(COALESCE(payload, ''), 'sha256'), 'hex')) = :payloadHash
                                )
                            )
                    """);
        }
        sql.append("""
                        ORDER BY created_at ASC, id ASC
                        LIMIT :limit
                        """);

        var statement = jdbc.sql(sql.toString());
        if (normalizedStatus != null) {
            statement = statement.param("status", normalizedStatus);
        }
        if (normalizedServiceName != null) {
            statement = statement.param("serviceName", normalizedServiceName);
        }
        if (normalizedEventType != null) {
            statement = statement.param("eventType", normalizedEventType);
        }
        if (normalizedAggregateId != null) {
            statement = statement.param("aggregateId", normalizedAggregateId);
        }
        if (normalizedPayloadHash != null) {
            statement = statement.param("payloadHash", normalizedPayloadHash);
        }
        return statement.param("limit", Math.max(1, Math.min(limit, 501)))
                .query(this::map)
                .list();
    }

    public Optional<DeadLetterRecord> findById(UUID id) {
        return jdbc.sql("SELECT * FROM relay_dead_letters WHERE id = :id")
                .param("id", id)
                .query(this::map)
                .list()
                .stream()
                .findFirst();
    }

    public Optional<DeadLetterRecord> claimForReplay(UUID id, String workerId, int leaseSeconds) {
        return jdbc.sql("""
                        UPDATE relay_dead_letters
                        SET status = 'REPLAYING',
                            replay_attempts = replay_attempts + 1,
                            last_replay_at = NOW(),
                            locked_by = :workerId,
                            locked_until = NOW() + (:leaseSeconds * INTERVAL '1 second'),
                            updated_at = NOW()
                        WHERE id = :id
                          AND (
                              status IN ('OPEN', 'FAILED')
                              OR (status = 'REPLAYING' AND (locked_until IS NULL OR locked_until < NOW()))
                          )
                        RETURNING *
                        """)
                .param("id", id)
                .param("workerId", workerId)
                .param("leaseSeconds", Math.max(30, Math.min(leaseSeconds, 900)))
                .query(this::map)
                .list()
                .stream()
                .findFirst();
    }

    public boolean markReplayed(UUID id, String actorId, String note, String workerId) {
        int updated = jdbc.sql("""
                        UPDATE relay_dead_letters
                        SET status = 'REPLAYED',
                            replayed_at = NOW(),
                            resolved_by = :actorId,
                            resolution_note = :note,
                            locked_by = NULL,
                            locked_until = NULL,
                            updated_at = NOW()
                        WHERE id = :id
                          AND status = 'REPLAYING'
                          AND locked_by = :workerId
                        """)
                .param("id", id)
                .param("actorId", truncate(actorId, 255))
                .param("note", truncate(note, 1000))
                .param("workerId", truncate(workerId, 120))
                .update();
        return updated > 0;
    }

    public boolean markReplayFailed(UUID id, String error, String workerId) {
        int updated = jdbc.sql("""
                        UPDATE relay_dead_letters
                        SET status = 'FAILED',
                            last_replay_error = :error,
                            locked_by = NULL,
                            locked_until = NULL,
                            updated_at = NOW()
                        WHERE id = :id
                          AND status = 'REPLAYING'
                          AND locked_by = :workerId
                        """)
                .param("id", id)
                .param("error", truncate(error, 4000))
                .param("workerId", truncate(workerId, 120))
                .update();
        return updated > 0;
    }

    public boolean discard(UUID id, String actorId, String note) {
        int updated = jdbc.sql("""
                        UPDATE relay_dead_letters
                        SET status = 'DISCARDED',
                            discarded_at = NOW(),
                            resolved_by = :actorId,
                            resolution_note = :note,
                            locked_by = NULL,
                            locked_until = NULL,
                            updated_at = NOW()
                        WHERE id = :id
                          AND status IN ('OPEN', 'FAILED')
                        """)
                .param("id", id)
                .param("actorId", truncate(actorId, 255))
                .param("note", truncate(note, 1000))
                .update();
        return updated > 0;
    }

    public Optional<OperatorActionRecord> findOperatorAction(String idempotencyKey, String action, UUID deadLetterId) {
        return jdbc.sql("""
                        SELECT status, request_hash, response_json
                        FROM relay_operator_actions
                        WHERE idempotency_key = :idempotencyKey
                          AND action = :action
                          AND dead_letter_id = :deadLetterId
                        """)
                .param("idempotencyKey", idempotencyKey)
                .param("action", action)
                .param("deadLetterId", deadLetterId)
                .query((rs, rowNum) -> new OperatorActionRecord(
                        rs.getString("status"),
                        rs.getString("request_hash"),
                        rs.getString("response_json")))
                .list()
                .stream()
                .findFirst();
    }

    public boolean insertOperatorAction(String idempotencyKey,
                                        String action,
                                        UUID deadLetterId,
                                        String requestHash,
                                        String actorId,
                                        String correlationId) {
        int inserted = jdbc.sql("""
                        INSERT INTO relay_operator_actions
                            (idempotency_key, action, dead_letter_id, request_hash, status, actor_id, correlation_id)
                        VALUES (:idempotencyKey, :action, :deadLetterId, :requestHash, 'IN_PROGRESS',
                                :actorId, :correlationId)
                        ON CONFLICT (idempotency_key, action, dead_letter_id) DO NOTHING
                        """)
                .param("idempotencyKey", idempotencyKey)
                .param("action", action)
                .param("deadLetterId", deadLetterId)
                .param("requestHash", requestHash)
                .param("actorId", truncate(actorId, 255))
                .param("correlationId", truncate(correlationId, 160))
                .update();
        return inserted > 0;
    }

    public void completeOperatorAction(String idempotencyKey,
                                       String action,
                                       UUID deadLetterId,
                                       String status,
                                       String responseJson) {
        jdbc.sql("""
                        UPDATE relay_operator_actions
                        SET status = :status,
                            response_json = :responseJson,
                            completed_at = NOW()
                        WHERE idempotency_key = :idempotencyKey
                          AND action = :action
                          AND dead_letter_id = :deadLetterId
                        """)
                .param("idempotencyKey", idempotencyKey)
                .param("action", action)
                .param("deadLetterId", deadLetterId)
                .param("status", status)
                .param("responseJson", responseJson)
                .update();
    }

    public List<DeadLetterApprovalRecord> approvals(UUID deadLetterId, String status, int limit) {
        String normalizedStatus = blankToNull(status);
        StringBuilder sql = new StringBuilder("""
                        SELECT *
                        FROM relay_dead_letter_approvals
                        WHERE dead_letter_id = :deadLetterId
                        """);
        if (normalizedStatus != null) {
            sql.append("  AND status = :status\n");
        }
        sql.append("""
                        ORDER BY requested_at DESC, id DESC
                        LIMIT :limit
                        """);

        var statement = jdbc.sql(sql.toString())
                .param("deadLetterId", deadLetterId)
                .param("limit", Math.max(1, Math.min(limit, 501)));
        if (normalizedStatus != null) {
            statement = statement.param("status", normalizedStatus);
        }
        return statement
                .query(this::mapApproval)
                .list();
    }

    public Optional<DeadLetterApprovalRecord> findApprovalById(UUID id) {
        return jdbc.sql("""
                        SELECT *
                        FROM relay_dead_letter_approvals
                        WHERE id = :id
                        """)
                .param("id", id)
                .query(this::mapApproval)
                .list()
                .stream()
                .findFirst();
    }

    public Optional<DeadLetterApprovalRecord> findEquivalentActiveApproval(
            UUID deadLetterId,
            String action,
            String requestHash) {
        return jdbc.sql("""
                        SELECT *
                        FROM relay_dead_letter_approvals
                        WHERE dead_letter_id = :deadLetterId
                          AND action = :action
                          AND request_hash = :requestHash
                          AND status IN ('PENDING', 'APPROVED', 'EXECUTED')
                        ORDER BY requested_at DESC, id DESC
                        LIMIT 1
                        """)
                .param("deadLetterId", deadLetterId)
                .param("action", action)
                .param("requestHash", requestHash)
                .query(this::mapApproval)
                .list()
                .stream()
                .findFirst();
    }

    public DeadLetterApprovalRecord insertApproval(UUID deadLetterId,
                                                   String action,
                                                   String reason,
                                                   String evidenceReference,
                                                   String thresholdPolicy,
                                                   String payloadHash,
                                                   String requestHash,
                                                   String requestedBy,
                                                   String correlationId) {
        return jdbc.sql("""
                        INSERT INTO relay_dead_letter_approvals
                            (dead_letter_id, action, reason, evidence_reference, threshold_policy, payload_hash,
                             request_hash, requested_by, correlation_id)
                        VALUES (:deadLetterId, :action, :reason, :evidenceReference, :thresholdPolicy, :payloadHash,
                                :requestHash, :requestedBy, :correlationId)
                        RETURNING *
                        """)
                .param("deadLetterId", deadLetterId)
                .param("action", action)
                .param("reason", truncate(reason, 4000))
                .param("evidenceReference", truncate(evidenceReference, 4000))
                .param("thresholdPolicy", truncate(thresholdPolicy, 120))
                .param("payloadHash", truncate(payloadHash, 80))
                .param("requestHash", truncate(requestHash, 80))
                .param("requestedBy", truncate(requestedBy, 255))
                .param("correlationId", truncate(correlationId, 160))
                .query(this::mapApproval)
                .list()
                .getFirst();
    }

    public Optional<DeadLetterApprovalRecord> approveApproval(UUID id, String reviewer, String note) {
        return jdbc.sql("""
                        UPDATE relay_dead_letter_approvals
                        SET status = 'APPROVED',
                            reviewed_by = :reviewer,
                            review_note = :note,
                            reviewed_at = NOW()
                        WHERE id = :id
                          AND status = 'PENDING'
                        RETURNING *
                        """)
                .param("id", id)
                .param("reviewer", truncate(reviewer, 255))
                .param("note", truncate(note, 4000))
                .query(this::mapApproval)
                .list()
                .stream()
                .findFirst();
    }

    public Optional<DeadLetterApprovalRecord> rejectApproval(UUID id, String reviewer, String note) {
        return jdbc.sql("""
                        UPDATE relay_dead_letter_approvals
                        SET status = 'REJECTED',
                            reviewed_by = :reviewer,
                            review_note = :note,
                            reviewed_at = NOW()
                        WHERE id = :id
                          AND status = 'PENDING'
                        RETURNING *
                        """)
                .param("id", id)
                .param("reviewer", truncate(reviewer, 255))
                .param("note", truncate(note, 4000))
                .query(this::mapApproval)
                .list()
                .stream()
                .findFirst();
    }

    public Optional<DeadLetterApprovalRecord> markApprovalExecuted(
            UUID id,
            String executedBy,
            String idempotencyKey) {
        return jdbc.sql("""
                        UPDATE relay_dead_letter_approvals
                        SET status = 'EXECUTED',
                            executed_by = :executedBy,
                            execution_idempotency_key = :idempotencyKey,
                            executed_at = NOW()
                        WHERE id = :id
                          AND status = 'APPROVED'
                        RETURNING *
                        """)
                .param("id", id)
                .param("executedBy", truncate(executedBy, 255))
                .param("idempotencyKey", truncate(idempotencyKey, 160))
                .query(this::mapApproval)
                .list()
                .stream()
                .findFirst();
    }

    public List<DeadLetterCount> openCounts() {
        return jdbc.sql("""
                        SELECT service_name,
                               COALESCE(event_type, 'unknown') AS event_type,
                               COUNT(*) AS open_count,
                               COALESCE(EXTRACT(EPOCH FROM (NOW() - MIN(created_at))), 0) AS oldest_age_seconds
                        FROM relay_dead_letters
                        WHERE status IN ('OPEN', 'FAILED')
                        GROUP BY service_name, COALESCE(event_type, 'unknown')
                        """)
                .query((rs, rowNum) -> new DeadLetterCount(
                        rs.getString("service_name"),
                        rs.getString("event_type"),
                        rs.getLong("open_count"),
                        rs.getDouble("oldest_age_seconds")))
                .list();
    }

    private DeadLetterRecord map(ResultSet rs, int rowNum) throws SQLException {
        return new DeadLetterRecord(
                rs.getObject("id", UUID.class),
                rs.getString("service_name"),
                rs.getObject("source_event_id", UUID.class),
                rs.getString("event_type"),
                rs.getString("topic"),
                boxedInt(rs, "kafka_partition"),
                boxedLong(rs, "kafka_offset"),
                rs.getString("aggregate_id"),
                rs.getString("payload"),
                rs.getInt("attempts"),
                rs.getString("error_class"),
                rs.getString("last_error"),
                instant(rs, "created_at"),
                rs.getString("status"),
                rs.getInt("replay_attempts"),
                rs.getString("last_replay_error"),
                instant(rs, "last_replay_at"),
                instant(rs, "replayed_at"),
                instant(rs, "discarded_at"),
                rs.getString("resolved_by"),
                rs.getString("resolution_note"),
                rs.getString("locked_by"),
                instant(rs, "locked_until"),
                instant(rs, "updated_at"),
                rs.getString("payload_hash"));
    }

    private DeadLetterApprovalRecord mapApproval(ResultSet rs, int rowNum) throws SQLException {
        return new DeadLetterApprovalRecord(
                rs.getObject("id", UUID.class),
                rs.getObject("dead_letter_id", UUID.class),
                rs.getString("action"),
                rs.getString("status"),
                rs.getString("reason"),
                rs.getString("evidence_reference"),
                rs.getString("threshold_policy"),
                rs.getString("payload_hash"),
                rs.getString("request_hash"),
                rs.getString("requested_by"),
                rs.getString("reviewed_by"),
                rs.getString("review_note"),
                rs.getString("executed_by"),
                rs.getString("execution_idempotency_key"),
                rs.getString("correlation_id"),
                instant(rs, "requested_at"),
                instant(rs, "reviewed_at"),
                instant(rs, "executed_at"));
    }

    private Instant instant(ResultSet rs, String column) throws SQLException {
        var timestamp = rs.getTimestamp(column);
        return timestamp == null ? null : timestamp.toInstant();
    }

    private Integer boxedInt(ResultSet rs, String column) throws SQLException {
        int value = rs.getInt(column);
        return rs.wasNull() ? null : value;
    }

    private Long boxedLong(ResultSet rs, String column) throws SQLException {
        long value = rs.getLong(column);
        return rs.wasNull() ? null : value;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String normalizePayloadHash(String value) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            return null;
        }
        return normalized.startsWith("sha256:") ? normalized : "sha256:" + normalized;
    }

    private String truncate(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.length() <= maxLength ? normalized : normalized.substring(0, maxLength);
    }
}
