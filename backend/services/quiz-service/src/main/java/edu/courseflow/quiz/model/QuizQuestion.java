package edu.courseflow.quiz.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "quiz_questions")
public class QuizQuestion {

    @Id
    private UUID id;

    @Column(name = "quiz_id", nullable = false)
    private UUID quizId;

    @Column(name = "question_id", nullable = false)
    private UUID questionId;

    @Column(nullable = false)
    private BigDecimal points;

    @Column(nullable = false)
    private int position;

    protected QuizQuestion() {
    }

    public QuizQuestion(UUID id, UUID quizId, UUID questionId, BigDecimal points, int position) {
        this.id = id;
        this.quizId = quizId;
        this.questionId = questionId;
        update(points, position);
    }

    public void update(BigDecimal points, int position) {
        this.points = points;
        this.position = position;
    }

    public UUID getId() { return id; }
    public UUID getQuizId() { return quizId; }
    public UUID getQuestionId() { return questionId; }
    public BigDecimal getPoints() { return points; }
    public int getPosition() { return position; }
}
