package edu.courseflow.assignment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "assignments")
public class Assignment {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private String title;

    @Column(name = "assignment_type", nullable = false, length = 60)
    private String assignmentType;

    @Column(columnDefinition = "TEXT")
    private String instructions;

    @Column(name = "available_at")
    private Instant availableAt;

    @Column(name = "due_at", nullable = false)
    private Instant dueAt;

    @Column(name = "lock_at")
    private Instant lockAt;

    @Column(name = "max_score", nullable = false)
    private BigDecimal maxScore;

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "submission_types", nullable = false, length = 120)
    private String submissionTypes = "FILE";

    @Column(name = "max_attempts", nullable = false)
    private int maxAttempts = 1;

    @Column(name = "allow_resubmission", nullable = false)
    private boolean allowResubmission;

    @Column(name = "late_penalty_percent", nullable = false)
    private BigDecimal latePenaltyPercent = BigDecimal.ZERO;

    @Column(name = "late_penalty_interval", nullable = false, length = 10)
    private String latePenaltyInterval = "DAY";

    @Column(name = "late_penalty_max_percent", nullable = false)
    private BigDecimal latePenaltyMaxPercent = new BigDecimal("100");

    @Column(name = "rubric_id")
    private UUID rubricId;

    protected Assignment() {
    }

    public Assignment(UUID id, UUID courseId, String title, String assignmentType, String instructions,
            Instant availableAt, Instant dueAt, Instant lockAt, BigDecimal maxScore,
            String submissionTypes, int maxAttempts, boolean allowResubmission,
            BigDecimal latePenaltyPercent, String latePenaltyInterval, BigDecimal latePenaltyMaxPercent) {
        this.id = id;
        this.courseId = courseId;
        this.title = title;
        this.assignmentType = assignmentType;
        this.instructions = instructions;
        this.availableAt = availableAt;
        this.dueAt = dueAt;
        this.lockAt = lockAt;
        this.maxScore = maxScore;
        this.status = "DRAFT";
        this.submissionTypes = submissionTypes;
        this.maxAttempts = maxAttempts;
        this.allowResubmission = allowResubmission;
        this.latePenaltyPercent = latePenaltyPercent;
        this.latePenaltyInterval = latePenaltyInterval;
        this.latePenaltyMaxPercent = latePenaltyMaxPercent;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getTitle() { return title; }
    public String getAssignmentType() { return assignmentType; }
    public String getInstructions() { return instructions; }
    public Instant getAvailableAt() { return availableAt; }
    public Instant getDueAt() { return dueAt; }
    public Instant getLockAt() { return lockAt; }
    public BigDecimal getMaxScore() { return maxScore; }
    public String getStatus() { return status; }
    public String getSubmissionTypes() { return submissionTypes; }
    public int getMaxAttempts() { return maxAttempts; }
    public boolean isAllowResubmission() { return allowResubmission; }
    public BigDecimal getLatePenaltyPercent() { return latePenaltyPercent; }
    public String getLatePenaltyInterval() { return latePenaltyInterval; }
    public BigDecimal getLatePenaltyMaxPercent() { return latePenaltyMaxPercent; }
    public UUID getRubricId() { return rubricId; }

    public void setStatus(String status) {
        this.status = status;
    }

    public void setRubricId(UUID rubricId) {
        this.rubricId = rubricId;
    }
}
