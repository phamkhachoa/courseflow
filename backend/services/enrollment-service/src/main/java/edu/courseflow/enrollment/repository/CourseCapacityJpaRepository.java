package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.CourseCapacity;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CourseCapacityJpaRepository extends JpaRepository<CourseCapacity, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select c from CourseCapacity c where c.courseId = :courseId")
    Optional<CourseCapacity> lockByCourseId(@Param("courseId") UUID courseId);
}
