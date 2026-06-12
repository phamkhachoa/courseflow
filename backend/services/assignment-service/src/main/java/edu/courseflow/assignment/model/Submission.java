package edu.courseflow.assignment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "submissions")
public class Submission {

    @Id
    private UUID id;

    @Column(name = "assignment_id", nullable = false)
    private UUID assignmentId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "attempt_no", nullable = false)
    private int attemptNo;

    @Column(name = "submitted_at", nullable = false)
    private Instant submittedAt = Instant.now();

    @Column(nullable = false, length = 40)
    private String status;

    @Column(name = "submission_text", columnDefinition = "TEXT")
    private String submissionText;

    @Column(name = "submission_url", length = 2048)
    private String submissionUrl;

    @Column(name = "is_late", nullable = false)
    private boolean late;

    @Column(name = "minutes_late", nullable = false)
    private int minutesLate;

    @Column(name = "raw_score")
    private BigDecimal rawScore;

    @Column(name = "late_penalty_applied")
    private BigDecimal latePenaltyApplied;

    @Column(name = "final_score")
    private BigDecimal finalScore;

    @Column(name = "grader_id", length = 64)
    private String graderId;

    @Column(name = "graded_at")
    private Instant gradedAt;

    @Column(columnDefinition = "TEXT")
    private String feedback;

    @Version
    @Column(nullable = false)
    private long version;

    protected Submission() {
    }

    public Submission(UUID id, UUID assignmentId, String studentId, int attemptNo,
            String submissionText, String submissionUrl, boolean late, int minutesLate) {
        this.id = id;
        this.assignmentId = assignmentId;
        this.studentId = studentId;
        this.attemptNo = attemptNo;
        this.submittedAt = Instant.now();
        this.status = attemptNo == 1 ? "SUBMITTED" : "RESUBMITTED";
        this.submissionText = submissionText;
        this.submissionUrl = submissionUrl;
        this.late = late;
        this.minutesLate = minutesLate;
    }

    public UUID getId() { return id; }
    public UUID getAssignmentId() { return assignmentId; }
    public String getStudentId() { return studentId; }
    public int getAttemptNo() { return attemptNo; }
    public Instant getSubmittedAt() { return submittedAt; }
    public String getStatus() { return status; }
    public String getSubmissionText() { return submissionText; }
    public String getSubmissionUrl() { return submissionUrl; }
    public boolean isLate() { return late; }
    public int getMinutesLate() { return minutesLate; }
    public BigDecimal getRawScore() { return rawScore; }
    public BigDecimal getLatePenaltyApplied() { return latePenaltyApplied; }
    public BigDecimal getFinalScore() { return finalScore; }
    public String getGraderId() { return graderId; }
    public Instant getGradedAt() { return gradedAt; }
    public String getFeedback() { return feedback; }

    public void grade(String graderId, BigDecimal rawScore, BigDecimal latePenaltyApplied,
            BigDecimal finalScore, String feedback) {
        this.rawScore = rawScore;
        this.latePenaltyApplied = latePenaltyApplied;
        this.finalScore = finalScore;
        this.graderId = graderId;
        this.gradedAt = Instant.now();
        this.feedback = feedback;
        this.status = "GRADED";
    }
}
