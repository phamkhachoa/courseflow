package edu.courseflow.identity.repository;

import edu.courseflow.identity.model.SecurityAuditLog;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SecurityAuditLogRepository extends JpaRepository<SecurityAuditLog, Long> {
}
