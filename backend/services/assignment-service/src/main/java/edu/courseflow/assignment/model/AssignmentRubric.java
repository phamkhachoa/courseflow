package edu.courseflow.assignment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "assignment_rubrics")
public class AssignmentRubric {

    @Id
    private UUID id;

    @Column(name = "assignment_id", nullable = false, unique = true)
    private UUID assignmentId;

    @Column(nullable = false)
    private String title;

    @Column(name = "max_score", nullable = false)
    private BigDecimal maxScore;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected AssignmentRubric() {
    }

    public AssignmentRubric(UUID id, UUID assignmentId, String title, BigDecimal maxScore) {
        this.id = id;
        this.assignmentId = assignmentId;
        this.title = title;
        this.maxScore = maxScore;
        this.createdAt = Instant.now();
    }

    public UUID getId() { return id; }
    public UUID getAssignmentId() { return assignmentId; }
    public String getTitle() { return title; }
    public BigDecimal getMaxScore() { return maxScore; }

    public void update(String title, BigDecimal maxScore) {
        this.title = title;
        this.maxScore = maxScore;
    }
}
