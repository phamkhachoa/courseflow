package edu.courseflow.review.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.review.dto.ReviewDtos.CreateReviewRequestDto;
import edu.courseflow.review.dto.ReviewDtos.HelpfulRequestDto;
import edu.courseflow.review.dto.ReviewDtos.ModerateRequestDto;
import edu.courseflow.review.dto.ReviewDtos.RatingSummaryDto;
import edu.courseflow.review.dto.ReviewDtos.ReviewDto;
import edu.courseflow.review.service.ReviewService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class ReviewController {

    private final ReviewService reviews;
    private final CourseAccessClient courseAccess;

    public ReviewController(ReviewService reviews, CourseAccessClient courseAccess) {
        this.reviews = reviews;
        this.courseAccess = courseAccess;
    }

    // ---- public read model ----

    @GetMapping("/public/reviews/courses/{courseId}")
    public List<ReviewDto> listByCourse(@PathVariable String courseId) {
        return reviews.listByCourse(courseId);
    }

    @GetMapping("/public/reviews/courses/{courseId}/summary")
    public RatingSummaryDto summary(@PathVariable String courseId) {
        return reviews.summary(courseId);
    }

    // ---- authenticated writes ----

    @PostMapping("/internal/reviews")
    public ReviewDto create(@Valid @RequestBody CreateReviewRequestDto request, CurrentUser user) {
        courseAccess.requireCourseAccess(user, UUID.fromString(request.courseId()));
        CreateReviewRequestDto trusted = new CreateReviewRequestDto(
                request.courseId(),
                callerId(user),
                request.rating(),
                request.title(),
                request.body());
        return reviews.create(trusted);
    }

    @PostMapping("/internal/reviews/{reviewId}/helpful")
    public ReviewDto helpful(@PathVariable UUID reviewId, @Valid @RequestBody HelpfulRequestDto request,
                             CurrentUser user) {
        ReviewDto review = reviews.get(reviewId);
        courseAccess.requireCourseAccess(user, UUID.fromString(review.courseId()));
        return reviews.addHelpful(reviewId, new HelpfulRequestDto(callerId(user)));
    }

    @PostMapping("/internal/reviews/{reviewId}/moderate")
    public ReviewDto moderate(@PathVariable UUID reviewId, @Valid @RequestBody ModerateRequestDto request,
                              CurrentUser user) {
        requireStaff(user);
        ReviewDto review = reviews.get(reviewId);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(review.courseId()));
        return reviews.moderate(reviewId, request);
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated user required");
        }
        return String.valueOf(user.id());
    }

    private void requireStaff(CurrentUser user) {
        callerId(user);
        if (!user.hasAnyRole("ADMIN", "ORG_ADMIN", "TA", "INSTRUCTOR", "PROFESSOR")) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires course staff role");
        }
    }
}
