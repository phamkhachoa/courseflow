package edu.courseflow.course.repository;

import edu.courseflow.course.model.CourseMaterial;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CourseMaterialJpaRepository extends JpaRepository<CourseMaterial, UUID> {

    List<CourseMaterial> findByCourseIdOrderByPositionAscTitleAsc(UUID courseId);

    @Query("select coalesce(max(m.position), -1) + 1 from CourseMaterial m where m.courseId = :courseId")
    int nextPosition(@Param("courseId") UUID courseId);
}
