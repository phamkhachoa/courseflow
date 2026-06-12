package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.CourseRecommendation;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseRecommendationRepository extends JpaRepository<CourseRecommendation, UUID> {

    List<CourseRecommendation> findByStudentIdOrderByScoreDesc(String studentId, Pageable pageable);
}
