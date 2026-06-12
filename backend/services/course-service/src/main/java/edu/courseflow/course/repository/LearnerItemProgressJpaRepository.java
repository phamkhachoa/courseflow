package edu.courseflow.course.repository;

import edu.courseflow.course.model.LearnerItemProgress;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LearnerItemProgressJpaRepository extends JpaRepository<LearnerItemProgress, UUID> {

    Optional<LearnerItemProgress> findByItemIdAndStudentId(UUID itemId, String studentId);

    List<LearnerItemProgress> findByCourseIdAndStudentId(UUID courseId, String studentId);

    List<LearnerItemProgress> findByModuleIdAndStudentId(UUID moduleId, String studentId);
}
