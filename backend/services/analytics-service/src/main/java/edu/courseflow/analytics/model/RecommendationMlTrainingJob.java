package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "recommendation_ml_training_jobs")
public class RecommendationMlTrainingJob {

    public static final String STATUS_FAILED_TO_ENQUEUE = "FAILED_TO_ENQUEUE";
    public static final String STATUS_PENDING_ACTIVATION = "PENDING_ACTIVATION";
    public static final String STATUS_ACTIVATION_REJECTED = "ACTIVATION_REJECTED";
    public static final String STATUS_QUALITY_GATE_FAILED = "QUALITY_GATE_FAILED";
    public static final String STATUS_UNAVAILABLE = "UNAVAILABLE";
    public static final String STATUS_CANCELLED = "CANCELLED";

    @Id
    @Column(name = "training_run_id")
    private UUID trainingRunId;

    @Column(name = "model_version", length = 80)
    private String modelVersion;

    @Column(nullable = false, length = 40)
    private String status;

    @Column(name = "since_at")
    private Instant since;

    @Column(name = "limit_per_course", nullable = false)
    private int limitPerCourse;

    @Column(nullable = false, length = 40)
    private String engine = "ML_ASYNC";

    @Column(name = "fallback_reason", length = 160)
    private String fallbackReason;

    @Column(name = "pair_count", nullable = false)
    private int pairCount;

    @Column(name = "generated_related_rows", nullable = false)
    private int generatedRelatedRows;

    @Column(name = "submitted_at", nullable = false)
    private Instant submittedAt;

    @Column(name = "last_checked_at")
    private Instant lastCheckedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "materialized_at")
    private Instant materializedAt;

    @Column(name = "materialization_locked_by", length = 120)
    private String materializationLockedBy;

    @Column(name = "materialization_locked_at")
    private Instant materializationLockedAt;

    @Column(name = "materialization_attempt_count", nullable = false)
    private int materializationAttemptCount;

    @Column(name = "check_count", nullable = false)
    private int checkCount;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected RecommendationMlTrainingJob() {
    }

    public RecommendationMlTrainingJob(UUID trainingRunId,
                                       String modelVersion,
                                       String status,
                                       Instant since,
                                       int limitPerCourse,
                                       Instant submittedAt) {
        this.trainingRunId = trainingRunId;
        this.modelVersion = modelVersion;
        this.status = status;
        this.since = since;
        this.limitPerCourse = Math.max(1, limitPerCourse);
        this.submittedAt = submittedAt == null ? Instant.now() : submittedAt;
        this.createdAt = this.submittedAt;
        this.updatedAt = this.submittedAt;
    }

    public void markEnqueueFailed(String fallbackReason, Instant checkedAt) {
        Instant now = checkedAt == null ? Instant.now() : checkedAt;
        this.status = STATUS_FAILED_TO_ENQUEUE;
        this.fallbackReason = truncate(fallbackReason, 160);
        this.lastCheckedAt = now;
        this.completedAt = now;
        clearMaterializationLock();
        this.updatedAt = now;
    }

    public void recordCheck(String modelVersion,
                            String status,
                            int pairCount,
                            int generatedRelatedRows,
                            String fallbackReason,
                            Instant checkedAt) {
        Instant now = checkedAt == null ? Instant.now() : checkedAt;
        this.modelVersion = modelVersion == null ? this.modelVersion : modelVersion;
        this.status = status == null || status.isBlank() ? STATUS_UNAVAILABLE : status;
        this.pairCount = Math.max(0, pairCount);
        this.generatedRelatedRows = Math.max(0, generatedRelatedRows);
        this.fallbackReason = truncate(fallbackReason, 160);
        this.lastCheckedAt = now;
        this.checkCount++;
        if (isTerminalStatus(this.status)) {
            this.completedAt = now;
        }
        if ("ACTIVE".equalsIgnoreCase(this.status) && generatedRelatedRows > 0) {
            this.materializedAt = now;
        }
        clearMaterializationLock();
        this.updatedAt = now;
    }

    public UUID getTrainingRunId() {
        return trainingRunId;
    }

    public Instant getSince() {
        return since;
    }

    public String getStatus() {
        return status;
    }

    public Instant getLastCheckedAt() {
        return lastCheckedAt;
    }

    public Instant getMaterializedAt() {
        return materializedAt;
    }

    public Instant getMaterializationLockedAt() {
        return materializationLockedAt;
    }

    public int getMaterializationAttemptCount() {
        return materializationAttemptCount;
    }

    public int getCheckCount() {
        return checkCount;
    }

    private void clearMaterializationLock() {
        this.materializationLockedBy = null;
        this.materializationLockedAt = null;
    }

    private static boolean isTerminalStatus(String status) {
        return "ACTIVE".equalsIgnoreCase(status)
                || "FAILED".equalsIgnoreCase(status)
                || STATUS_CANCELLED.equalsIgnoreCase(status)
                || STATUS_ACTIVATION_REJECTED.equalsIgnoreCase(status)
                || "INSUFFICIENT_DATA".equalsIgnoreCase(status)
                || STATUS_QUALITY_GATE_FAILED.equalsIgnoreCase(status)
                || STATUS_FAILED_TO_ENQUEUE.equalsIgnoreCase(status);
    }

    private static String truncate(String value, int maxLength) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.length() <= maxLength ? trimmed : trimmed.substring(0, maxLength);
    }
}
