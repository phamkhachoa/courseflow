package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.GradeItem;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GradeItemRepository extends JpaRepository<GradeItem, UUID> {
    List<GradeItem> findByCourseId(UUID courseId);
    Optional<GradeItem> findBySourceTypeAndSourceId(String sourceType, String sourceId);
}
