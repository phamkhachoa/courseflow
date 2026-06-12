package edu.courseflow.review.model;

import edu.courseflow.review.dto.ReviewDtos.CreateReviewRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_reviews")
public class CourseReview {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(nullable = false)
    private short rating;

    private String title;

    @Column(columnDefinition = "TEXT")
    private String body;

    @Column(nullable = false, length = 40)
    private String status = "PUBLISHED";

    @Column(name = "helpful_count", nullable = false)
    private int helpfulCount;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected CourseReview() {
    }

    public CourseReview(CreateReviewRequestDto request) {
        this.id = UUID.randomUUID();
        this.courseId = UUID.fromString(request.courseId());
        this.userId = request.userId();
        updateFrom(request);
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getUserId() { return userId; }
    public int getRating() { return rating; }
    public String getTitle() { return title; }
    public String getBody() { return body; }
    public String getStatus() { return status; }
    public int getHelpfulCount() { return helpfulCount; }
    public Instant getCreatedAt() { return createdAt; }

    public void updateFrom(CreateReviewRequestDto request) {
        this.rating = request.rating().shortValue();
        this.title = request.title();
        this.body = request.body();
        this.status = "PUBLISHED";
        this.updatedAt = Instant.now();
    }

    public void updateStatus(String status) {
        this.status = status;
        this.updatedAt = Instant.now();
    }

    public void incrementHelpful() {
        this.helpfulCount++;
        this.updatedAt = Instant.now();
    }
}
