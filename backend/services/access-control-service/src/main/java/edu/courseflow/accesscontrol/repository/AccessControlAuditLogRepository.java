package edu.courseflow.accesscontrol.repository;

import edu.courseflow.accesscontrol.model.AccessControlAuditLog;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AccessControlAuditLogRepository extends JpaRepository<AccessControlAuditLog, Long> {
}
