package edu.courseflow.peerreview.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "review_assignments")
public class ReviewAssignment {

    @Id
    private UUID id;

    @Column(name = "assignment_id", nullable = false)
    private UUID assignmentId;

    @Column(name = "course_id")
    private UUID courseId;

    @Column(name = "submission_id", nullable = false)
    private UUID submissionId;

    @Column(name = "reviewer_id", nullable = false, length = 64)
    private String reviewerId;

    @Column(name = "reviewee_id", nullable = false, length = 64)
    private String revieweeId;

    @Column(nullable = false, length = 40)
    private String status = "ASSIGNED";

    @Column(name = "assigned_at", nullable = false)
    private Instant assignedAt = Instant.now();

    protected ReviewAssignment() {
    }

    public ReviewAssignment(UUID id, UUID courseId, UUID assignmentId, UUID submissionId,
            String reviewerId, String revieweeId) {
        this.id = id;
        this.courseId = courseId;
        this.assignmentId = assignmentId;
        this.submissionId = submissionId;
        this.reviewerId = reviewerId;
        this.revieweeId = revieweeId;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public UUID getAssignmentId() { return assignmentId; }
    public UUID getSubmissionId() { return submissionId; }
    public String getReviewerId() { return reviewerId; }
    public String getRevieweeId() { return revieweeId; }
    public String getStatus() { return status; }
    public Instant getAssignedAt() { return assignedAt; }

    public void markReviewed() {
        this.status = "REVIEWED";
    }
}
