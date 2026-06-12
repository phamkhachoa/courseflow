package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_recommendations")
public class CourseRecommendation {

    @Id
    private UUID id;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private BigDecimal score = BigDecimal.ZERO;

    @Column(length = 120)
    private String reason;

    @Column(name = "generated_at", nullable = false)
    private Instant generatedAt = Instant.now();

    protected CourseRecommendation() {
    }

    public String getStudentId() { return studentId; }
    public UUID getCourseId() { return courseId; }
    public BigDecimal getScore() { return score; }
    public String getReason() { return reason; }
}
