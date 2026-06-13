package edu.courseflow.review.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.review.dto.ReviewDtos.CreateReviewRequestDto;
import edu.courseflow.review.dto.ReviewDtos.HelpfulRequestDto;
import edu.courseflow.review.dto.ReviewDtos.ModerateRequestDto;
import edu.courseflow.review.dto.ReviewDtos.RatingSummaryDto;
import edu.courseflow.review.dto.ReviewDtos.ReviewDto;
import edu.courseflow.review.model.OutboxEvent;
import edu.courseflow.review.repository.OutboxEventRepository;
import edu.courseflow.review.repository.ReviewRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ReviewService {

    private final ReviewRepository reviews;
    private final OutboxEventRepository outboxEvents;
    private final ObjectMapper objectMapper;

    public ReviewService(ReviewRepository reviews,
            OutboxEventRepository outboxEvents,
            ObjectMapper objectMapper) {
        this.reviews = reviews;
        this.outboxEvents = outboxEvents;
        this.objectMapper = objectMapper;
    }

    public List<ReviewDto> listByCourse(String courseId) {
        return reviews.listByCourse(UUID.fromString(courseId));
    }

    public RatingSummaryDto summary(String courseId) {
        return reviews.summary(UUID.fromString(courseId));
    }

    public ReviewDto get(UUID reviewId) {
        return reviews.find(reviewId).orElseThrow(() -> new NotFoundException("Review not found: " + reviewId));
    }

    @Transactional
    public ReviewDto create(CreateReviewRequestDto request) {
        ReviewDto review = reviews.upsert(request);
        UUID courseId = UUID.fromString(review.courseId());
        reviews.recomputeSummary(courseId);
        saveOutbox(UUID.fromString(review.id()), "review.posted", Map.of(
                "reviewId", review.id(),
                "courseId", review.courseId(),
                "userId", review.userId(),
                "rating", review.rating()));
        return review;
    }

    @Transactional
    public ReviewDto addHelpful(UUID reviewId, HelpfulRequestDto request) {
        get(reviewId);
        reviews.addHelpful(reviewId, request.userId());
        return reviews.find(reviewId).orElseThrow();
    }

    @Transactional
    public ReviewDto moderate(UUID reviewId, ModerateRequestDto request) {
        ReviewDto review = get(reviewId);
        reviews.updateStatus(reviewId, request.status());
        reviews.recomputeSummary(UUID.fromString(review.courseId()));
        return reviews.find(reviewId).orElseThrow();
    }

    private void saveOutbox(UUID aggregateId, String eventType, Map<String, ?> payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "course-review", eventType, toJson(payload)));
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
