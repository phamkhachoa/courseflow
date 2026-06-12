package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.Enrollment;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EnrollmentJpaRepository extends JpaRepository<Enrollment, UUID> {

    List<Enrollment> findByCourseIdOrderByEnrolledAtDesc(UUID courseId);

    List<Enrollment> findByStudentIdOrderByEnrolledAtDesc(String studentId);

    List<Enrollment> findByCourseIdAndStudentIdOrderByEnrolledAtDesc(UUID courseId, String studentId);

    Optional<Enrollment> findByStudentIdAndCourseId(String studentId, UUID courseId);

    Optional<Enrollment> findFirstByStudentIdAndCourseIdAndStatusIn(
            String studentId, UUID courseId, Collection<String> statuses);

    int countByCourseIdAndStatus(UUID courseId, String status);

    int countByCourseId(UUID courseId);
}
