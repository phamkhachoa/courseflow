package edu.courseflow.gradebook.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "grade_categories")
public class GradeCategory {
    @Id
    private UUID id;
    @Column(name = "course_id", nullable = false)
    private UUID courseId;
    @Column(nullable = false)
    private String name;
    @Column(name = "weight_percent", nullable = false)
    private BigDecimal weightPercent;
    @Column(nullable = false)
    private int position;
    @Column(name = "aggregation_method", nullable = false, length = 20)
    private String aggregationMethod = "WEIGHTED_MEAN";
    @Column(name = "drop_lowest", nullable = false)
    private int dropLowest;

    protected GradeCategory() {
    }

    public GradeCategory(UUID id, UUID courseId, String name, BigDecimal weightPercent,
            int position, String aggregationMethod, int dropLowest) {
        this.id = id;
        this.courseId = courseId;
        this.name = name;
        this.weightPercent = weightPercent;
        this.position = position;
        this.aggregationMethod = aggregationMethod;
        this.dropLowest = dropLowest;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getName() { return name; }
    public BigDecimal getWeightPercent() { return weightPercent; }
    public int getPosition() { return position; }
    public String getAggregationMethod() { return aggregationMethod; }
    public int getDropLowest() { return dropLowest; }

    public void update(String name, BigDecimal weightPercent, String aggregationMethod, int dropLowest) {
        this.name = name;
        this.weightPercent = weightPercent;
        this.aggregationMethod = aggregationMethod;
        this.dropLowest = dropLowest;
    }
}
