package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.ManualRelatedCourse;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ManualRelatedCourseRepository extends JpaRepository<ManualRelatedCourse, UUID> {

    Optional<ManualRelatedCourse> findByCourseIdAndRelatedCourseIdAndPlacement(
            UUID courseId,
            UUID relatedCourseId,
            String placement);

    Optional<ManualRelatedCourse> findByIdAndCourseId(UUID id, UUID courseId);

    List<ManualRelatedCourse> findByCourseIdAndPlacementOrderByPositionAscWeightDescRelatedCourseIdAsc(
            UUID courseId,
            String placement);

    List<ManualRelatedCourse> findByCourseIdAndPlacementAndStatusOrderByPositionAscWeightDescRelatedCourseIdAsc(
            UUID courseId,
            String placement,
            String status);

    List<ManualRelatedCourse> findByCourseIdAndPlacementAndRelatedCourseIdIn(
            UUID courseId,
            String placement,
            List<UUID> relatedCourseIds);

    long countByCourseIdAndPlacement(UUID courseId, String placement);
}
