package edu.courseflow.gradebook.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "grade_items")
public class GradeItem {
    @Id
    private UUID id;
    @Column(name = "course_id", nullable = false)
    private UUID courseId;
    @Column(name = "category_id", nullable = false)
    private UUID categoryId;
    @Column(name = "source_type", nullable = false, length = 60)
    private String sourceType;
    @Column(name = "source_id", nullable = false, length = 120)
    private String sourceId;
    @Column(nullable = false)
    private String title;
    @Column(name = "max_score", nullable = false)
    private BigDecimal maxScore;
    @Column(name = "weight_percent", nullable = false)
    private BigDecimal weightPercent;
    @Column(nullable = false)
    private boolean published = true;
    @Column(name = "late_penalty_percent", nullable = false)
    private BigDecimal latePenaltyPercent = BigDecimal.ZERO;

    protected GradeItem() {
    }

    public GradeItem(UUID id, UUID courseId, UUID categoryId, String sourceType, String sourceId,
            String title, BigDecimal maxScore, BigDecimal weightPercent, BigDecimal latePenaltyPercent) {
        this.id = id;
        this.courseId = courseId;
        this.categoryId = categoryId;
        this.sourceType = sourceType;
        this.sourceId = sourceId;
        this.title = title;
        this.maxScore = maxScore;
        this.weightPercent = weightPercent;
        this.published = true;
        this.latePenaltyPercent = latePenaltyPercent;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public UUID getCategoryId() { return categoryId; }
    public String getSourceType() { return sourceType; }
    public String getSourceId() { return sourceId; }
    public String getTitle() { return title; }
    public BigDecimal getMaxScore() { return maxScore; }
    public BigDecimal getWeightPercent() { return weightPercent; }
    public BigDecimal getLatePenaltyPercent() { return latePenaltyPercent; }
    public boolean isPublished() { return published; }
    public void setTitle(String title) { this.title = title; }

    public void update(UUID categoryId, String sourceType, String sourceId, String title,
            BigDecimal maxScore, BigDecimal weightPercent, BigDecimal latePenaltyPercent, boolean published) {
        this.categoryId = categoryId;
        this.sourceType = sourceType;
        this.sourceId = sourceId;
        this.title = title;
        this.maxScore = maxScore;
        this.weightPercent = weightPercent;
        this.latePenaltyPercent = latePenaltyPercent;
        this.published = published;
    }
}
