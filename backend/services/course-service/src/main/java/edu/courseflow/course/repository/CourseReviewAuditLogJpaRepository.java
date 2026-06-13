package edu.courseflow.course.repository;

import edu.courseflow.course.model.CourseReviewAuditLog;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseReviewAuditLogJpaRepository extends JpaRepository<CourseReviewAuditLog, UUID> {

    List<CourseReviewAuditLog> findByCourseIdOrderByCreatedAtDesc(UUID courseId);
}
