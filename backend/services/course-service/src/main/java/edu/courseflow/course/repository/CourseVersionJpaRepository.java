package edu.courseflow.course.repository;

import edu.courseflow.course.model.CourseVersion;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CourseVersionJpaRepository extends JpaRepository<CourseVersion, UUID> {

    List<CourseVersion> findByCourseIdOrderByVersionNoDesc(UUID courseId);

    List<CourseVersion> findByCourseIdAndStateOrderByVersionNoDesc(UUID courseId, String state);

    Optional<CourseVersion> findByCourseIdAndVersionNo(UUID courseId, int versionNo);

    boolean existsByCourseIdAndVersionNo(UUID courseId, int versionNo);

    @Query("select coalesce(max(v.versionNo), 0) + 1 from CourseVersion v where v.courseId = :courseId")
    int nextVersionNo(@Param("courseId") UUID courseId);
}
