package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "related_courses")
public class RelatedCourse {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "related_course_id", nullable = false)
    private UUID relatedCourseId;

    @Column(nullable = false)
    private BigDecimal score = BigDecimal.ZERO;

    @Column(nullable = false, length = 60)
    private String source = "BEHAVIORAL";

    @Column(length = 160)
    private String reason;

    @Column(name = "reason_code", length = 80)
    private String reasonCode;

    @Column(name = "model_version", length = 80)
    private String modelVersion;

    @Column(name = "generated_at", nullable = false)
    private Instant generatedAt = Instant.now();

    protected RelatedCourse() {
    }

    public RelatedCourse(UUID id, UUID courseId, UUID relatedCourseId) {
        this.id = id;
        this.courseId = courseId;
        this.relatedCourseId = relatedCourseId;
    }

    public void updateScore(BigDecimal score, String source, String reason, String reasonCode, String modelVersion, Instant generatedAt) {
        this.score = score == null ? BigDecimal.ZERO : score;
        this.source = source == null || source.isBlank() ? "BEHAVIORAL" : source;
        this.reason = reason;
        this.reasonCode = reasonCode;
        this.modelVersion = modelVersion;
        this.generatedAt = generatedAt == null ? Instant.now() : generatedAt;
    }

    public UUID getCourseId() { return courseId; }
    public UUID getRelatedCourseId() { return relatedCourseId; }
    public BigDecimal getScore() { return score; }
    public String getSource() { return source; }
    public String getReason() { return reason; }
    public String getReasonCode() { return reasonCode; }
    public String getModelVersion() { return modelVersion; }
    public Instant getGeneratedAt() { return generatedAt; }
}
