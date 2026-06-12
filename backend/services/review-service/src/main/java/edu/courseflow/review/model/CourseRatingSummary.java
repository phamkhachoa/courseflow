package edu.courseflow.review.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_rating_summary")
public class CourseRatingSummary {

    @Id
    @Column(name = "course_id")
    private UUID courseId;

    @Column(name = "review_count", nullable = false)
    private int reviewCount;

    @Column(name = "average_rating", nullable = false)
    private BigDecimal averageRating = BigDecimal.ZERO;

    @Column(name = "count_1", nullable = false)
    private int count1;

    @Column(name = "count_2", nullable = false)
    private int count2;

    @Column(name = "count_3", nullable = false)
    private int count3;

    @Column(name = "count_4", nullable = false)
    private int count4;

    @Column(name = "count_5", nullable = false)
    private int count5;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected CourseRatingSummary() {
    }

    public CourseRatingSummary(UUID courseId) {
        this.courseId = courseId;
    }

    public UUID getCourseId() { return courseId; }
    public int getReviewCount() { return reviewCount; }
    public BigDecimal getAverageRating() { return averageRating; }
    public int getCount1() { return count1; }
    public int getCount2() { return count2; }
    public int getCount3() { return count3; }
    public int getCount4() { return count4; }
    public int getCount5() { return count5; }

    public void update(int reviewCount, BigDecimal averageRating,
            int count1, int count2, int count3, int count4, int count5) {
        this.reviewCount = reviewCount;
        this.averageRating = averageRating;
        this.count1 = count1;
        this.count2 = count2;
        this.count3 = count3;
        this.count4 = count4;
        this.count5 = count5;
        this.updatedAt = Instant.now();
    }
}
