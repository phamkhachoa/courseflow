package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.EnrollmentAuditLog;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface EnrollmentAuditLogJpaRepository extends JpaRepository<EnrollmentAuditLog, UUID> {

    List<EnrollmentAuditLog> findByEnrollmentIdOrderByCreatedAtDesc(UUID enrollmentId);

    @Query("""
            select a from EnrollmentAuditLog a
            join Enrollment e on e.id = a.enrollmentId
            where (:enrollmentId is null or a.enrollmentId = :enrollmentId)
              and (:courseId is null or e.courseId = :courseId)
              and (:studentId is null or e.studentId = :studentId)
              and (:correlationId is null
                   or lower(coalesce(a.reason, '')) like lower(concat('%', :correlationId, '%')))
            order by a.createdAt desc
            """)
    List<EnrollmentAuditLog> queryOperationsAudit(
            @Param("enrollmentId") UUID enrollmentId,
            @Param("courseId") UUID courseId,
            @Param("studentId") String studentId,
            @Param("correlationId") String correlationId,
            Pageable pageable);
}
