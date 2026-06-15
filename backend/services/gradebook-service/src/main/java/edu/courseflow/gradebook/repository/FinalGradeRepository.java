package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.FinalGrade;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FinalGradeRepository extends JpaRepository<FinalGrade, UUID> {
    Optional<FinalGrade> findByCourseIdAndStudentId(UUID courseId, String studentId);
    List<FinalGrade> findByCourseId(UUID courseId);
}
