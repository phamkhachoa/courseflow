package edu.courseflow.course.repository;

import edu.courseflow.course.model.ModuleItem;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ModuleItemJpaRepository extends JpaRepository<ModuleItem, UUID> {

    List<ModuleItem> findByModuleIdOrderByPositionAsc(UUID moduleId);

    Optional<ModuleItem> findByIdAndModuleId(UUID id, UUID moduleId);

    @Query("""
            select i
            from ModuleItem i, CourseModule m
            where i.moduleId = m.id
              and m.courseId = :courseId
              and m.status = 'PUBLISHED'
            order by m.position asc, i.position asc
            """)
    List<ModuleItem> findPublishedCourseItems(@Param("courseId") UUID courseId);

    @Query("select coalesce(max(i.position), -1) + 1 from ModuleItem i where i.moduleId = :moduleId")
    int nextPosition(@Param("moduleId") UUID moduleId);
}
