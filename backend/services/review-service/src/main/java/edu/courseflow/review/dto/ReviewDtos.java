package edu.courseflow.review.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;

public final class ReviewDtos {

    private ReviewDtos() {
    }

    public record ReviewDto(
            String id,
            String courseId,
            String userId,
            int rating,
            String title,
            String body,
            String status,
            int helpfulCount,
            Instant createdAt
    ) {
    }

    public record RatingSummaryDto(
            String courseId,
            int reviewCount,
            double averageRating,
            int count1,
            int count2,
            int count3,
            int count4,
            int count5
    ) {
    }

    // ---- requests ----

    public record CreateReviewRequestDto(
            @NotBlank String courseId,
            String userId,
            @NotNull @Min(1) @Max(5) Integer rating,
            String title,
            String body
    ) {
    }

    public record HelpfulRequestDto(
            String userId
    ) {
    }

    public record ModerateRequestDto(
            @NotBlank String status
    ) {
    }
}
