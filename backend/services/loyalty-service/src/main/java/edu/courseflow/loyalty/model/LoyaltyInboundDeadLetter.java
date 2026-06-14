package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(
        name = "loyalty_inbound_dead_letters",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_loyalty_inbound_dlt_location",
                columnNames = {"dlt_topic", "kafka_partition", "kafka_offset"}))
public class LoyaltyInboundDeadLetter {

    private static final Set<String> REPLAYABLE_STATUSES = Set.of("OPEN", "FAILED");
    private static final Set<String> DISCARDABLE_STATUSES = Set.of("OPEN", "FAILED");

    @Id
    private UUID id;

    @Column(name = "source_topic", nullable = false, length = 240)
    private String sourceTopic;

    @Column(name = "dlt_topic", nullable = false, length = 240)
    private String dltTopic;

    @Column(name = "consumer_group", length = 160)
    private String consumerGroup;

    @Column(name = "kafka_partition", nullable = false)
    private int kafkaPartition;

    @Column(name = "kafka_offset", nullable = false)
    private long kafkaOffset;

    @Column(name = "original_partition")
    private Integer originalPartition;

    @Column(name = "original_offset")
    private Long originalOffset;

    @Column(name = "record_key", length = 512)
    private String recordKey;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String payload;

    @Column(name = "payload_hash", nullable = false, length = 80)
    private String payloadHash;

    @Column(name = "exception_class", length = 240)
    private String exceptionClass;

    @Column(name = "exception_message", columnDefinition = "TEXT")
    private String exceptionMessage;

    @Column(name = "stacktrace", columnDefinition = "TEXT")
    private String stacktrace;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "headers_json", nullable = false, columnDefinition = "jsonb")
    private String headersJson = "{}";

    @Column(nullable = false, length = 40)
    private String status = "OPEN";

    @Column(name = "replay_attempts", nullable = false)
    private int replayAttempts;

    @Column(name = "last_replay_error", columnDefinition = "TEXT")
    private String lastReplayError;

    @Column(name = "last_replay_at")
    private Instant lastReplayAt;

    @Column(name = "replayed_at")
    private Instant replayedAt;

    @Column(name = "discarded_at")
    private Instant discardedAt;

    @Column(name = "resolved_by", length = 160)
    private String resolvedBy;

    @Column(name = "resolution_note", columnDefinition = "TEXT")
    private String resolutionNote;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyInboundDeadLetter() {
    }

    public LoyaltyInboundDeadLetter(
            String sourceTopic,
            String dltTopic,
            String consumerGroup,
            int kafkaPartition,
            long kafkaOffset,
            Integer originalPartition,
            Long originalOffset,
            String recordKey,
            String payload,
            String payloadHash,
            String exceptionClass,
            String exceptionMessage,
            String stacktrace,
            String headersJson) {
        this.id = UUID.randomUUID();
        this.sourceTopic = sourceTopic;
        this.dltTopic = dltTopic;
        this.consumerGroup = consumerGroup;
        this.kafkaPartition = kafkaPartition;
        this.kafkaOffset = kafkaOffset;
        this.originalPartition = originalPartition;
        this.originalOffset = originalOffset;
        this.recordKey = recordKey;
        this.payload = payload == null ? "" : payload;
        this.payloadHash = payloadHash;
        this.exceptionClass = exceptionClass;
        this.exceptionMessage = exceptionMessage;
        this.stacktrace = stacktrace;
        this.headersJson = headersJson == null || headersJson.isBlank() ? "{}" : headersJson;
    }

    @PreUpdate
    void preUpdate() {
        this.updatedAt = Instant.now();
    }

    public boolean replayable() {
        return REPLAYABLE_STATUSES.contains(status);
    }

    public boolean discardable() {
        return DISCARDABLE_STATUSES.contains(status);
    }

    public void markReplayFailed(String error) {
        requireReplayable();
        this.status = "FAILED";
        this.replayAttempts++;
        this.lastReplayAt = Instant.now();
        this.lastReplayError = error;
    }

    public void markReplayed(String actorId, String note) {
        requireReplayable();
        this.status = "REPLAYED";
        this.replayAttempts++;
        this.lastReplayAt = Instant.now();
        this.replayedAt = this.lastReplayAt;
        this.resolvedBy = actorId;
        this.resolutionNote = note;
        this.lastReplayError = null;
    }

    public void discard(String actorId, String note) {
        if (!discardable()) {
            throw new IllegalStateException("Inbound dead letter is not discardable");
        }
        this.status = "DISCARDED";
        this.discardedAt = Instant.now();
        this.resolvedBy = actorId;
        this.resolutionNote = note;
    }

    private void requireReplayable() {
        if (!replayable()) {
            throw new IllegalStateException("Inbound dead letter is not replayable");
        }
    }

    public UUID getId() { return id; }
    public String getSourceTopic() { return sourceTopic; }
    public String getDltTopic() { return dltTopic; }
    public String getConsumerGroup() { return consumerGroup; }
    public int getKafkaPartition() { return kafkaPartition; }
    public long getKafkaOffset() { return kafkaOffset; }
    public Integer getOriginalPartition() { return originalPartition; }
    public Long getOriginalOffset() { return originalOffset; }
    public String getRecordKey() { return recordKey; }
    public String getPayload() { return payload; }
    public String getPayloadHash() { return payloadHash; }
    public String getExceptionClass() { return exceptionClass; }
    public String getExceptionMessage() { return exceptionMessage; }
    public String getStacktrace() { return stacktrace; }
    public String getHeadersJson() { return headersJson; }
    public String getStatus() { return status; }
    public int getReplayAttempts() { return replayAttempts; }
    public String getLastReplayError() { return lastReplayError; }
    public Instant getLastReplayAt() { return lastReplayAt; }
    public Instant getReplayedAt() { return replayedAt; }
    public Instant getDiscardedAt() { return discardedAt; }
    public String getResolvedBy() { return resolvedBy; }
    public String getResolutionNote() { return resolutionNote; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
