package edu.courseflow.review.repository;

import edu.courseflow.review.dto.ReviewDtos.CreateReviewRequestDto;
import edu.courseflow.review.dto.ReviewDtos.RatingSummaryDto;
import edu.courseflow.review.dto.ReviewDtos.ReviewDto;
import edu.courseflow.review.mapper.ReviewMapper;
import edu.courseflow.review.model.CourseRatingSummary;
import edu.courseflow.review.model.CourseReview;
import edu.courseflow.review.model.ReviewHelpfulVote;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class ReviewRepository {

    private final CourseReviewJpaRepository reviews;
    private final ReviewHelpfulVoteRepository helpfulVotes;
    private final CourseRatingSummaryRepository summaries;
    private final ReviewMapper mapper;

    public ReviewRepository(CourseReviewJpaRepository reviews,
            ReviewHelpfulVoteRepository helpfulVotes,
            CourseRatingSummaryRepository summaries,
            ReviewMapper mapper) {
        this.reviews = reviews;
        this.helpfulVotes = helpfulVotes;
        this.summaries = summaries;
        this.mapper = mapper;
    }

    public ReviewDto upsert(CreateReviewRequestDto request) {
        UUID courseId = UUID.fromString(request.courseId());
        CourseReview review = reviews.findByCourseIdAndUserId(courseId, request.userId())
                .orElseGet(() -> new CourseReview(request));
        review.updateFrom(request);
        return mapper.toDto(reviews.save(review));
    }

    public Optional<ReviewDto> find(UUID reviewId) {
        return reviews.findById(reviewId).map(mapper::toDto);
    }

    public List<ReviewDto> listByCourse(UUID courseId) {
        return reviews.findByCourseIdAndStatusOrderByHelpfulCountDescCreatedAtDesc(courseId, "PUBLISHED")
                .stream()
                .map(mapper::toDto)
                .toList();
    }

    public void updateStatus(UUID reviewId, String status) {
        reviews.findById(reviewId).ifPresent(review -> {
            review.updateStatus(status);
            reviews.save(review);
        });
    }

    public boolean addHelpful(UUID reviewId, String userId) {
        if (helpfulVotes.findByReviewIdAndUserId(reviewId, userId).isPresent()) {
            return false;
        }
        helpfulVotes.save(new ReviewHelpfulVote(reviewId, userId));
        reviews.incrementHelpfulCount(reviewId);
        return true;
    }

    /**
     * Recompute the aggregate read model for a course from PUBLISHED reviews.
     */
    public void recomputeSummary(UUID courseId) {
        List<CourseReview> published = reviews
                .findByCourseIdAndStatusOrderByHelpfulCountDescCreatedAtDesc(courseId, "PUBLISHED");
        int reviewCount = published.size();
        BigDecimal average = reviewCount == 0 ? BigDecimal.ZERO : published.stream()
                .map(review -> BigDecimal.valueOf(review.getRating()))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(reviewCount), 2, RoundingMode.HALF_UP);
        int count1 = countRating(published, 1);
        int count2 = countRating(published, 2);
        int count3 = countRating(published, 3);
        int count4 = countRating(published, 4);
        int count5 = countRating(published, 5);
        CourseRatingSummary summary = summaries.findById(courseId)
                .orElseGet(() -> new CourseRatingSummary(courseId));
        summary.update(reviewCount, average, count1, count2, count3, count4, count5);
        summaries.save(summary);
    }

    public RatingSummaryDto summary(UUID courseId) {
        return summaries.findById(courseId)
                .map(mapper::toDto)
                .orElse(new RatingSummaryDto(courseId.toString(), 0, 0.0, 0, 0, 0, 0, 0));
    }

    private int countRating(List<CourseReview> reviews, int rating) {
        return (int) reviews.stream().filter(review -> review.getRating() == rating).count();
    }

}
