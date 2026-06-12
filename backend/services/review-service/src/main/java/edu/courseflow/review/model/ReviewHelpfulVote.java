package edu.courseflow.review.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "review_helpful_votes")
public class ReviewHelpfulVote {

    @Id
    private UUID id;

    @Column(name = "review_id", nullable = false)
    private UUID reviewId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected ReviewHelpfulVote() {
    }

    public ReviewHelpfulVote(UUID reviewId, String userId) {
        this.id = UUID.randomUUID();
        this.reviewId = reviewId;
        this.userId = userId;
    }
}
