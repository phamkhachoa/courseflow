package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.EnrollmentAuditLog;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EnrollmentAuditLogJpaRepository extends JpaRepository<EnrollmentAuditLog, UUID> {

    List<EnrollmentAuditLog> findByEnrollmentIdOrderByCreatedAtDesc(UUID enrollmentId);
}
