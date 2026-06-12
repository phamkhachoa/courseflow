package edu.courseflow.organization.repository;

import edu.courseflow.organization.model.CourseSection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseSectionJpaRepository extends JpaRepository<CourseSection, UUID> {

    List<CourseSection> findAllByOrderBySectionCodeAsc();

    List<CourseSection> findByCourseIdOrderBySectionCodeAsc(UUID courseId);
}
