package edu.courseflow.quiz.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "quiz_answers")
public class QuizAnswer {

    @Id
    private UUID id;

    @Column(name = "attempt_id", nullable = false)
    private UUID attemptId;

    @Column(name = "question_id", nullable = false)
    private UUID questionId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "answer_payload", nullable = false, columnDefinition = "jsonb")
    private String answerPayload;

    private BigDecimal score;

    @Column(name = "graded_at")
    private Instant gradedAt;

    @Column(name = "auto_score")
    private BigDecimal autoScore;

    @Column(name = "manual_score")
    private BigDecimal manualScore;

    @Column(name = "manual_feedback", columnDefinition = "TEXT")
    private String manualFeedback;

    @Column(name = "grader_id", length = 64)
    private String graderId;

    protected QuizAnswer() {
    }

    public QuizAnswer(UUID attemptId, UUID questionId, String answerPayload, BigDecimal autoScore) {
        this.id = UUID.randomUUID();
        this.attemptId = attemptId;
        this.questionId = questionId;
        updateAuto(answerPayload, autoScore);
    }

    public UUID getQuestionId() { return questionId; }
    public String getAnswerPayload() { return answerPayload; }
    public BigDecimal getAutoScore() { return autoScore; }
    public BigDecimal getManualScore() { return manualScore; }
    public BigDecimal getScore() { return score; }
    public String getManualFeedback() { return manualFeedback; }
    public String getGraderId() { return graderId; }
    public Instant getGradedAt() { return gradedAt; }

    public void updateAuto(String answerPayload, BigDecimal autoScore) {
        this.answerPayload = answerPayload;
        this.autoScore = autoScore;
        this.score = manualScore != null ? manualScore : autoScore;
        this.gradedAt = Instant.now();
    }

    public void updateDraft(String answerPayload) {
        this.answerPayload = answerPayload;
        this.autoScore = null;
        this.score = manualScore;
        if (manualScore == null) {
            this.gradedAt = null;
        }
    }

    public void manualGrade(BigDecimal score, String feedback, String graderId) {
        this.manualScore = score;
        this.score = score;
        this.manualFeedback = feedback;
        this.graderId = graderId;
        this.gradedAt = Instant.now();
    }
}
