package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.GradeEntry;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface GradeEntryRepository extends JpaRepository<GradeEntry, UUID> {
    Optional<GradeEntry> findByGradeItemIdAndStudentId(UUID gradeItemId, String studentId);
    List<GradeEntry> findByGradeItemIdInAndStudentIdAndStatus(Collection<UUID> gradeItemIds, String studentId, String status);
    List<GradeEntry> findByGradeItemIdIn(Collection<UUID> gradeItemIds);

    @Query("""
            select distinct e.studentId
            from GradeEntry e
            where e.gradeItemId in :gradeItemIds
            order by e.studentId
            """)
    List<String> distinctStudentsForItems(@Param("gradeItemIds") Collection<UUID> gradeItemIds);
}
