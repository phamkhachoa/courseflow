package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.StudentTimeSpent;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StudentTimeSpentRepository extends JpaRepository<StudentTimeSpent, UUID> {

    Optional<StudentTimeSpent> findByStudentIdAndCourseId(String studentId, UUID courseId);

    List<StudentTimeSpent> findByStudentIdOrderByMinutesSpentDesc(String studentId);
}
