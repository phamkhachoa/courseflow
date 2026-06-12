package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.StudentEngagement;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StudentEngagementRepository extends JpaRepository<StudentEngagement, UUID> {

    Optional<StudentEngagement> findByStudentIdAndCourseId(String studentId, UUID courseId);

    List<StudentEngagement> findByStudentIdOrderByUpdatedAtDesc(String studentId);

    List<StudentEngagement> findByStudentIdAndCourseIdOrderByUpdatedAtDesc(String studentId, UUID courseId);

    List<StudentEngagement> findByCourseIdAndRiskLevelInOrderByEngagementScoreAsc(UUID courseId, List<String> riskLevels);
}
