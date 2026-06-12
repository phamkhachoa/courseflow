package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.RelatedCourse;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RelatedCourseRepository extends JpaRepository<RelatedCourse, UUID> {

    List<RelatedCourse> findByCourseIdOrderByScoreDesc(UUID courseId, Pageable pageable);
}
