package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.GradingScheme;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GradingSchemeRepository extends JpaRepository<GradingScheme, UUID> {
    List<GradingScheme> findByCourseIdOrderByDefaultSchemeDescNameAsc(UUID courseId);
    Optional<GradingScheme> findByCourseIdAndDefaultSchemeTrue(UUID courseId);
    List<GradingScheme> findByCourseIdAndDefaultSchemeTrueOrderByNameAsc(UUID courseId);
}
