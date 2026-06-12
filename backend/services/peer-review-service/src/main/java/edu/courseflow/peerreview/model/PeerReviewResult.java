package edu.courseflow.peerreview.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "peer_review_results")
public class PeerReviewResult {

    @Id
    private UUID id;

    @Column(name = "submission_id", nullable = false)
    private UUID submissionId;

    @Column(name = "final_score", nullable = false)
    private BigDecimal finalScore;

    @Column(name = "finalized_by", nullable = false, length = 64)
    private String finalizedBy;

    @Column(name = "finalized_at", nullable = false)
    private Instant finalizedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected PeerReviewResult() {
    }

    public PeerReviewResult(UUID submissionId, BigDecimal finalScore, String finalizedBy) {
        this.id = UUID.randomUUID();
        this.submissionId = submissionId;
        finalizeWith(finalScore, finalizedBy);
    }

    public UUID getId() { return id; }
    public UUID getSubmissionId() { return submissionId; }
    public BigDecimal getFinalScore() { return finalScore; }
    public String getFinalizedBy() { return finalizedBy; }
    public Instant getFinalizedAt() { return finalizedAt; }

    public void finalizeWith(BigDecimal finalScore, String finalizedBy) {
        this.finalScore = finalScore;
        this.finalizedBy = finalizedBy;
        this.finalizedAt = Instant.now();
    }
}
