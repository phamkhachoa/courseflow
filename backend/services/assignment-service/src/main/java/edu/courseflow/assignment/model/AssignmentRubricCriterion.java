package edu.courseflow.assignment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "assignment_rubric_criteria")
public class AssignmentRubricCriterion {

    @Id
    private UUID id;

    @Column(name = "rubric_id", nullable = false)
    private UUID rubricId;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "max_points", nullable = false)
    private BigDecimal maxPoints;

    @Column(nullable = false)
    private int position;

    protected AssignmentRubricCriterion() {
    }

    public AssignmentRubricCriterion(UUID rubricId, String name, String description,
            BigDecimal maxPoints, int position) {
        this.id = UUID.randomUUID();
        this.rubricId = rubricId;
        this.name = name;
        this.description = description;
        this.maxPoints = maxPoints;
        this.position = position;
    }

    public UUID getId() { return id; }
    public String getName() { return name; }
    public String getDescription() { return description; }
    public BigDecimal getMaxPoints() { return maxPoints; }
    public int getPosition() { return position; }
}
