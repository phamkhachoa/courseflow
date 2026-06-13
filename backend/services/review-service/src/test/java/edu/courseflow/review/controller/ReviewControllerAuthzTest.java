package edu.courseflow.review.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.review.dto.ReviewDtos.HelpfulRequestDto;
import edu.courseflow.review.dto.ReviewDtos.ModerateRequestDto;
import edu.courseflow.review.dto.ReviewDtos.ReviewDto;
import edu.courseflow.review.service.ReviewService;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ReviewControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID REVIEW_ID = UUID.fromString("82000000-0000-0000-0000-000000000001");

    @Mock
    private ReviewService reviews;
    @Mock
    private CourseAccessClient courseAccess;

    private ReviewController controller;

    @BeforeEach
    void setUp() {
        controller = new ReviewController(reviews, courseAccess);
    }

    @Test
    void helpfulVoteRequiresLearnerCourseAccess() {
        CurrentUser learner = learner();
        when(reviews.get(REVIEW_ID)).thenReturn(review());
        when(reviews.addHelpful(REVIEW_ID, new HelpfulRequestDto("4"))).thenReturn(review());

        controller.helpful(REVIEW_ID, new HelpfulRequestDto("spoofed"), learner);

        verify(courseAccess).requireCourseAccess(learner, COURSE_ID);
    }

    @Test
    void moderationRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        ModerateRequestDto request = new ModerateRequestDto("APPROVED");
        when(reviews.get(REVIEW_ID)).thenReturn(review());
        when(reviews.moderate(REVIEW_ID, request)).thenReturn(review());

        controller.moderate(REVIEW_ID, request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    private static CurrentUser learner() {
        return new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static ReviewDto review() {
        return new ReviewDto(
                REVIEW_ID.toString(),
                COURSE_ID.toString(),
                "4",
                5,
                "Great",
                "Useful course",
                "PUBLISHED",
                0,
                Instant.parse("2026-06-13T00:00:00Z"));
    }
}
