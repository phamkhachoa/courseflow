package edu.courseflow.peerreview.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "peer_review_settings")
public class PeerReviewSetting {

    @Id
    private UUID id;

    @Column(name = "assignment_id", nullable = false)
    private UUID assignmentId;

    @Column(name = "reviewers_per_submission", nullable = false)
    private int reviewersPerSubmission;

    @Column(nullable = false)
    private boolean anonymous = true;

    @Column(name = "review_due_at", nullable = false)
    private Instant reviewDueAt;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    protected PeerReviewSetting() {
    }

    public UUID getId() { return id; }
    public UUID getAssignmentId() { return assignmentId; }
    public int getReviewersPerSubmission() { return reviewersPerSubmission; }
    public boolean isAnonymous() { return anonymous; }
    public Instant getReviewDueAt() { return reviewDueAt; }
    public String getStatus() { return status; }
}
