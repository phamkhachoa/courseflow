package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_metrics")
public class CourseMetric {

    @Id
    @Column(name = "course_id")
    private UUID courseId;

    @Column(name = "enrolled_count", nullable = false)
    private int enrolledCount;

    @Column(name = "submitted_count", nullable = false)
    private int submittedCount;

    @Column(name = "average_score")
    private BigDecimal averageScore;

    @Column(name = "discussion_count", nullable = false)
    private int discussionCount;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected CourseMetric() {
    }

    public CourseMetric(UUID courseId) {
        this.courseId = courseId;
    }

    public UUID getCourseId() { return courseId; }
    public int getEnrolledCount() { return enrolledCount; }
    public int getSubmittedCount() { return submittedCount; }
    public BigDecimal getAverageScore() { return averageScore; }
    public int getDiscussionCount() { return discussionCount; }
    public Instant getUpdatedAt() { return updatedAt; }

    public void applyDelta(int enrolledDelta, int submittedDelta, int discussionDelta, BigDecimal latestScore) {
        this.enrolledCount += enrolledDelta;
        this.submittedCount += submittedDelta;
        this.discussionCount += discussionDelta;
        if (latestScore != null) {
            this.averageScore = averageScore == null
                    ? latestScore
                    : averageScore.add(latestScore).divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP);
        }
        this.updatedAt = Instant.now();
    }
}
