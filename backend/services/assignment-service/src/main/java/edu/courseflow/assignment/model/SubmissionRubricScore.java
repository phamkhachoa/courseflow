package edu.courseflow.assignment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "submission_rubric_scores")
public class SubmissionRubricScore {

    @Id
    private UUID id;

    @Column(name = "submission_id", nullable = false)
    private UUID submissionId;

    @Column(name = "criterion_id", nullable = false)
    private UUID criterionId;

    @Column(nullable = false)
    private BigDecimal points;

    @Column(columnDefinition = "TEXT")
    private String comment;

    protected SubmissionRubricScore() {
    }

    public SubmissionRubricScore(UUID submissionId, UUID criterionId, BigDecimal points, String comment) {
        this.id = UUID.randomUUID();
        this.submissionId = submissionId;
        this.criterionId = criterionId;
        this.points = points;
        this.comment = comment;
    }
}
