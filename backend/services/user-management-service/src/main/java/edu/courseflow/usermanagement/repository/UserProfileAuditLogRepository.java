package edu.courseflow.usermanagement.repository;

import edu.courseflow.usermanagement.model.UserProfileAuditLog;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserProfileAuditLogRepository extends JpaRepository<UserProfileAuditLog, Long> {
}
