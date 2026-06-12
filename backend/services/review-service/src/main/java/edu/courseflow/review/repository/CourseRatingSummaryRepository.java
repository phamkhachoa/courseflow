package edu.courseflow.review.repository;

import edu.courseflow.review.model.CourseRatingSummary;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseRatingSummaryRepository extends JpaRepository<CourseRatingSummary, UUID> {
}
