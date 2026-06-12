package edu.courseflow.quiz.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "questions")
public class Question {

    @Id
    private UUID id;

    @Column(name = "bank_id", nullable = false)
    private UUID bankId;

    @Column(nullable = false, length = 60)
    private String type;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String stem;

    @Column(nullable = false, length = 40)
    private String difficulty = "MEDIUM";

    @Column(nullable = false)
    private BigDecimal points;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "correct_answer", columnDefinition = "jsonb")
    private String correctAnswer;

    @Column(columnDefinition = "TEXT")
    private String feedback;

    protected Question() {
    }

    public Question(UUID id, UUID bankId, String type, String stem, String difficulty, BigDecimal points,
            String status, String correctAnswer, String feedback) {
        this.id = id;
        this.bankId = bankId;
        update(type, stem, difficulty, points, status, correctAnswer, feedback);
    }

    public void update(String type, String stem, String difficulty, BigDecimal points, String status,
            String correctAnswer, String feedback) {
        this.type = type;
        this.stem = stem;
        this.difficulty = difficulty;
        this.points = points;
        this.status = status;
        this.correctAnswer = correctAnswer;
        this.feedback = feedback;
    }

    public UUID getId() { return id; }
    public UUID getBankId() { return bankId; }
    public String getType() { return type; }
    public String getStem() { return stem; }
    public String getDifficulty() { return difficulty; }
    public BigDecimal getPoints() { return points; }
    public String getStatus() { return status; }
    public String getCorrectAnswer() { return correctAnswer; }
    public String getFeedback() { return feedback; }
}
