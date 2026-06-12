package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.StudentActivityLog;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StudentActivityLogRepository extends JpaRepository<StudentActivityLog, UUID> {

    List<StudentActivityLog> findByStudentIdAndCourseId(String studentId, UUID courseId);
}
