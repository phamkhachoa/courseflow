package edu.courseflow.quiz.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "quiz_attempts")
public class QuizAttempt {

    @Id
    private UUID id;

    @Column(name = "quiz_id", nullable = false)
    private UUID quizId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "attempt_no", nullable = false)
    private int attemptNo;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt = Instant.now();

    @Column(name = "submitted_at")
    private Instant submittedAt;

    @Column(nullable = false, length = 40)
    private String status = "IN_PROGRESS";

    private BigDecimal score;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "questions_snapshot", columnDefinition = "jsonb")
    private String questionsSnapshot;

    @Column(name = "deadline_at")
    private Instant deadlineAt;

    @Column(name = "auto_submitted", nullable = false)
    private boolean autoSubmitted;

    @Version
    @Column(nullable = false)
    private long version;

    protected QuizAttempt() {
    }

    public QuizAttempt(UUID id, UUID quizId, String studentId, int attemptNo, Instant startedAt, Instant deadlineAt) {
        this.id = id;
        this.quizId = quizId;
        this.studentId = studentId;
        this.attemptNo = attemptNo;
        this.startedAt = startedAt;
        this.status = "IN_PROGRESS";
        this.deadlineAt = deadlineAt;
    }

    public UUID getId() { return id; }
    public UUID getQuizId() { return quizId; }
    public String getStudentId() { return studentId; }
    public int getAttemptNo() { return attemptNo; }
    public Instant getStartedAt() { return startedAt; }
    public Instant getSubmittedAt() { return submittedAt; }
    public String getStatus() { return status; }
    public BigDecimal getScore() { return score; }
    public String getQuestionsSnapshot() { return questionsSnapshot; }
    public Instant getDeadlineAt() { return deadlineAt; }
    public boolean isAutoSubmitted() { return autoSubmitted; }

    public void setQuestionsSnapshot(String questionsSnapshot) {
        this.questionsSnapshot = questionsSnapshot;
    }

    public void submit(Instant submittedAt, String status, BigDecimal score) {
        submit(submittedAt, status, score, false);
    }

    public void submit(Instant submittedAt, String status, BigDecimal score, boolean autoSubmitted) {
        this.submittedAt = submittedAt;
        this.status = status;
        this.score = score;
        this.autoSubmitted = autoSubmitted;
    }

    public void updateScore(String status, BigDecimal score) {
        this.status = status;
        this.score = score;
    }
}
