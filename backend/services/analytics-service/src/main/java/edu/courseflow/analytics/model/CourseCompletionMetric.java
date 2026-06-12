package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_completion_metrics")
public class CourseCompletionMetric {

    @Id
    @Column(name = "course_id")
    private UUID courseId;

    @Column(name = "enrolled_count", nullable = false)
    private int enrolledCount;

    @Column(name = "completed_count", nullable = false)
    private int completedCount;

    @Column(name = "completion_rate", nullable = false)
    private BigDecimal completionRate = BigDecimal.ZERO;

    @Column(name = "avg_days_to_complete")
    private BigDecimal avgDaysToComplete;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected CourseCompletionMetric() {
    }

    public CourseCompletionMetric(UUID courseId) {
        this.courseId = courseId;
    }

    public UUID getCourseId() { return courseId; }
    public int getEnrolledCount() { return enrolledCount; }
    public int getCompletedCount() { return completedCount; }
    public BigDecimal getCompletionRate() { return completionRate; }
    public BigDecimal getAvgDaysToComplete() { return avgDaysToComplete; }
    public Instant getUpdatedAt() { return updatedAt; }

    public void incrementEnrolled() {
        this.enrolledCount++;
        this.completionRate = enrolledCount == 0 ? BigDecimal.ZERO
                : BigDecimal.valueOf(completedCount)
                        .multiply(BigDecimal.valueOf(100))
                        .divide(BigDecimal.valueOf(enrolledCount), 2, RoundingMode.HALF_UP);
        this.updatedAt = Instant.now();
    }
}
