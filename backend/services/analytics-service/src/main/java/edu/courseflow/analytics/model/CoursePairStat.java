package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_pair_stats")
public class CoursePairStat {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "related_course_id", nullable = false)
    private UUID relatedCourseId;

    @Column(name = "support_count", nullable = false)
    private int supportCount;

    @Column(name = "impression_count", nullable = false)
    private int impressionCount;

    @Column(name = "click_count", nullable = false)
    private int clickCount;

    @Column(name = "enroll_count", nullable = false)
    private int enrollCount;

    @Column(nullable = false)
    private BigDecimal score = BigDecimal.ZERO;

    @Column(name = "model_version", nullable = false, length = 80)
    private String modelVersion;

    @Column(name = "generated_at", nullable = false)
    private Instant generatedAt = Instant.now();

    protected CoursePairStat() {
    }

    public CoursePairStat(UUID id, UUID courseId, UUID relatedCourseId) {
        this.id = id;
        this.courseId = courseId;
        this.relatedCourseId = relatedCourseId;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public UUID getRelatedCourseId() { return relatedCourseId; }
    public int getSupportCount() { return supportCount; }
    public int getImpressionCount() { return impressionCount; }
    public int getClickCount() { return clickCount; }
    public int getEnrollCount() { return enrollCount; }
    public BigDecimal getScore() { return score; }
    public String getModelVersion() { return modelVersion; }
    public Instant getGeneratedAt() { return generatedAt; }

    public void update(int supportCount,
                       int impressionCount,
                       int clickCount,
                       int enrollCount,
                       BigDecimal score,
                       String modelVersion,
                       Instant generatedAt) {
        this.supportCount = supportCount;
        this.impressionCount = impressionCount;
        this.clickCount = clickCount;
        this.enrollCount = enrollCount;
        this.score = score == null ? BigDecimal.ZERO : score;
        this.modelVersion = modelVersion;
        this.generatedAt = generatedAt == null ? Instant.now() : generatedAt;
    }
}
