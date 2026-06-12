package edu.courseflow.quiz.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "question_options")
public class QuestionOption {

    @Id
    private UUID id;

    @Column(name = "question_id", nullable = false)
    private UUID questionId;

    @Column(nullable = false, length = 20)
    private String label;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(nullable = false)
    private boolean correct;

    @Column(nullable = false, precision = 5, scale = 4)
    private BigDecimal weight = BigDecimal.ONE;

    @Column(columnDefinition = "TEXT")
    private String feedback;

    protected QuestionOption() {
    }

    public QuestionOption(UUID id, UUID questionId, String label, String content, boolean correct, BigDecimal weight,
            String feedback) {
        this.id = id;
        this.questionId = questionId;
        update(label, content, correct, weight, feedback);
    }

    public void update(String label, String content, boolean correct, BigDecimal weight, String feedback) {
        this.label = label;
        this.content = content;
        this.correct = correct;
        this.weight = weight == null ? BigDecimal.ONE : weight;
        this.feedback = feedback;
    }

    public UUID getId() { return id; }
    public UUID getQuestionId() { return questionId; }
    public String getLabel() { return label; }
    public String getContent() { return content; }
    public boolean isCorrect() { return correct; }
    public BigDecimal getWeight() { return weight; }
    public String getFeedback() { return feedback; }
}
