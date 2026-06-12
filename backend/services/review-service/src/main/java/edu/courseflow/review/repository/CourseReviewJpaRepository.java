package edu.courseflow.review.repository;

import edu.courseflow.review.model.CourseReview;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CourseReviewJpaRepository extends JpaRepository<CourseReview, UUID> {

    Optional<CourseReview> findByCourseIdAndUserId(UUID courseId, String userId);

    List<CourseReview> findByCourseIdAndStatusOrderByHelpfulCountDescCreatedAtDesc(UUID courseId, String status);

    @Modifying
    @Query("update CourseReview r set r.helpfulCount = r.helpfulCount + 1 where r.id = :reviewId")
    int incrementHelpfulCount(@Param("reviewId") UUID reviewId);
}
