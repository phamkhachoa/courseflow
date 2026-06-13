package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.GradeOverride;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GradeOverrideRepository extends JpaRepository<GradeOverride, UUID> {
    List<GradeOverride> findByGradeEntryIdOrderByCreatedAtDesc(UUID gradeEntryId);
}
