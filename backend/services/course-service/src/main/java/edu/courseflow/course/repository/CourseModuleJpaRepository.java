package edu.courseflow.course.repository;

import edu.courseflow.course.model.CourseModule;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CourseModuleJpaRepository extends JpaRepository<CourseModule, UUID> {

    List<CourseModule> findByCourseIdAndStatusOrderByPositionAsc(UUID courseId, String status);

    List<CourseModule> findByCourseIdOrderByPositionAsc(UUID courseId);

    Optional<CourseModule> findByIdAndCourseId(UUID id, UUID courseId);

    int countByCourseIdAndStatus(UUID courseId, String status);

    @Query("select coalesce(max(m.position), -1) + 1 from CourseModule m where m.courseId = :courseId")
    int nextPosition(@Param("courseId") UUID courseId);
}
