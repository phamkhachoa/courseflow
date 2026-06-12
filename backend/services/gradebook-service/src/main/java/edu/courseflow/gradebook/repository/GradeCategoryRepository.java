package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.GradeCategory;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface GradeCategoryRepository extends JpaRepository<GradeCategory, UUID> {
    List<GradeCategory> findByCourseIdOrderByPositionAscNameAsc(UUID courseId);
    Optional<GradeCategory> findByCourseIdAndName(UUID courseId, String name);

    @Query("select coalesce(max(c.position), 0) + 1 from GradeCategory c where c.courseId = :courseId")
    int nextPosition(@Param("courseId") UUID courseId);

    @Query("""
            select coalesce(sum(c.weightPercent), 0)
            from GradeCategory c
            where c.courseId = :courseId
              and (:excludeId is null or c.id <> :excludeId)
            """)
    BigDecimal sumWeightsExcluding(@Param("courseId") UUID courseId, @Param("excludeId") UUID excludeId);
}
