package edu.courseflow.course.repository;

import edu.courseflow.course.model.Course;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseJpaRepository extends JpaRepository<Course, UUID> {

    List<Course> findAllByOrderByCreatedAtDescTitleAsc();

    List<Course> findByStatusOrderByCreatedAtDescTitleAsc(String status);

    List<Course> findByReviewStateOrderByUpdatedAtDescTitleAsc(String reviewState);

    List<Course> findByOwnerIdOrderByCreatedAtDescTitleAsc(String ownerId);

    List<Course> findByOwnerIdAndStatusOrderByCreatedAtDescTitleAsc(String ownerId, String status);

    List<Course> findByDepartmentIdInOrderByCreatedAtDescTitleAsc(List<UUID> departmentIds);

    List<Course> findByDepartmentIdInAndStatusOrderByCreatedAtDescTitleAsc(List<UUID> departmentIds, String status);

    Optional<Course> findBySlugAndStatus(String slug, String status);
}
