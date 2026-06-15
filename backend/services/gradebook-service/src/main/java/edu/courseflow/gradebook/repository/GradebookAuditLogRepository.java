package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.GradebookAuditLog;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GradebookAuditLogRepository extends JpaRepository<GradebookAuditLog, UUID> {
    List<GradebookAuditLog> findByCourseIdOrderByCreatedAtDesc(UUID courseId, Pageable pageable);

    List<GradebookAuditLog> findByCourseIdAndStudentIdOrderByCreatedAtDesc(UUID courseId, String studentId,
            Pageable pageable);

    List<GradebookAuditLog> findByCourseIdAndGradeItemIdOrderByCreatedAtDesc(UUID courseId, UUID gradeItemId,
            Pageable pageable);

    List<GradebookAuditLog> findByCourseIdAndStudentIdAndGradeItemIdOrderByCreatedAtDesc(UUID courseId,
            String studentId, UUID gradeItemId, Pageable pageable);
}
