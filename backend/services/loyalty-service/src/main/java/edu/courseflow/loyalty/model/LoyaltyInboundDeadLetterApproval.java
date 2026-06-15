package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;

@Entity
@Table(name = "loyalty_inbound_dead_letter_approvals")
public class LoyaltyInboundDeadLetterApproval {

    private static final Set<String> REVIEWED_STATUSES = Set.of("APPROVED", "REJECTED", "EXECUTED");

    @Id
    private UUID id;

    @Column(name = "dead_letter_id", nullable = false)
    private UUID deadLetterId;

    @Column(nullable = false, length = 32)
    private String action;

    @Column(nullable = false, length = 24)
    private String status = "PENDING";

    @Column(nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Column(name = "evidence_reference", nullable = false, columnDefinition = "TEXT")
    private String evidenceReference;

    @Column(name = "threshold_policy", nullable = false, length = 120)
    private String thresholdPolicy;

    @Column(name = "payload_hash", nullable = false, length = 80)
    private String payloadHash;

    @Column(name = "request_hash", nullable = false, length = 80)
    private String requestHash;

    @Column(name = "requested_by", nullable = false, length = 160)
    private String requestedBy;

    @Column(name = "reviewed_by", length = 160)
    private String reviewedBy;

    @Column(name = "review_note", columnDefinition = "TEXT")
    private String reviewNote;

    @Column(name = "executed_by", length = 160)
    private String executedBy;

    @Column(name = "requested_at", nullable = false)
    private Instant requestedAt = Instant.now();

    @Column(name = "reviewed_at")
    private Instant reviewedAt;

    @Column(name = "executed_at")
    private Instant executedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyInboundDeadLetterApproval() {
    }

    public LoyaltyInboundDeadLetterApproval(
            UUID deadLetterId,
            String action,
            String reason,
            String evidenceReference,
            String thresholdPolicy,
            String payloadHash,
            String requestHash,
            String requestedBy) {
        this.id = UUID.randomUUID();
        this.deadLetterId = deadLetterId;
        this.action = action;
        this.reason = reason;
        this.evidenceReference = evidenceReference;
        this.thresholdPolicy = thresholdPolicy;
        this.payloadHash = payloadHash;
        this.requestHash = requestHash;
        this.requestedBy = requestedBy;
    }

    @PreUpdate
    void preUpdate() {
        this.updatedAt = Instant.now();
    }

    public void approve(String reviewer, String note) {
        requireReviewable();
        this.status = "APPROVED";
        this.reviewedBy = reviewer;
        this.reviewNote = note;
        this.reviewedAt = Instant.now();
    }

    public void reject(String reviewer, String note) {
        requireReviewable();
        this.status = "REJECTED";
        this.reviewedBy = reviewer;
        this.reviewNote = note;
        this.reviewedAt = Instant.now();
    }

    public void markExecuted(String actor) {
        if (!"APPROVED".equals(status)) {
            throw new IllegalStateException("Only approved inbound DLT actions can be executed");
        }
        this.status = "EXECUTED";
        this.executedBy = actor;
        this.executedAt = Instant.now();
    }

    private void requireReviewable() {
        if (REVIEWED_STATUSES.contains(status)) {
            throw new IllegalStateException("Inbound DLT approval has already been reviewed");
        }
    }

    public UUID getId() { return id; }
    public UUID getDeadLetterId() { return deadLetterId; }
    public String getAction() { return action; }
    public String getStatus() { return status; }
    public String getReason() { return reason; }
    public String getEvidenceReference() { return evidenceReference; }
    public String getThresholdPolicy() { return thresholdPolicy; }
    public String getPayloadHash() { return payloadHash; }
    public String getRequestHash() { return requestHash; }
    public String getRequestedBy() { return requestedBy; }
    public String getReviewedBy() { return reviewedBy; }
    public String getReviewNote() { return reviewNote; }
    public String getExecutedBy() { return executedBy; }
    public Instant getRequestedAt() { return requestedAt; }
    public Instant getReviewedAt() { return reviewedAt; }
    public Instant getExecutedAt() { return executedAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
