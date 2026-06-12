package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.WaitlistEntry;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface WaitlistEntryJpaRepository extends JpaRepository<WaitlistEntry, UUID> {

    List<WaitlistEntry> findByCourseIdOrderByPositionAsc(UUID courseId);

    List<WaitlistEntry> findByCourseIdAndStatusOrderByPositionAsc(UUID courseId, String status);

    Optional<WaitlistEntry> findByStudentIdAndCourseId(String studentId, UUID courseId);

    int countByCourseId(UUID courseId);

    @Query("select coalesce(max(w.position), 0) + 1 from WaitlistEntry w "
            + "where w.courseId = :courseId and w.status = 'WAITING'")
    int nextPosition(@Param("courseId") UUID courseId);

    Optional<WaitlistEntry> findFirstByCourseIdAndStatusOrderByPositionAsc(UUID courseId, String status);
}
