package edu.courseflow.peerreview.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "review_submissions")
public class ReviewSubmission {

    @Id
    private UUID id;

    @Column(name = "review_assignment_id", nullable = false)
    private UUID reviewAssignmentId;

    @Column(nullable = false)
    private BigDecimal score;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String comment;

    @Column(name = "submitted_at", nullable = false)
    private Instant submittedAt = Instant.now();

    @Column(nullable = false, length = 40)
    private String status = "SUBMITTED";

    protected ReviewSubmission() {
    }

    public ReviewSubmission(UUID id, UUID reviewAssignmentId, BigDecimal score, String comment) {
        this.id = id;
        this.reviewAssignmentId = reviewAssignmentId;
        this.score = score;
        this.comment = comment;
    }

    public UUID getId() { return id; }
    public UUID getReviewAssignmentId() { return reviewAssignmentId; }
    public BigDecimal getScore() { return score; }
    public String getComment() { return comment; }
    public Instant getSubmittedAt() { return submittedAt; }
    public String getStatus() { return status; }
}
