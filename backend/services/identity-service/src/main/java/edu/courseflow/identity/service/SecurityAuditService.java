package edu.courseflow.identity.service;

import edu.courseflow.identity.model.SecurityAuditLog;
import edu.courseflow.identity.repository.SecurityAuditLogRepository;
import org.springframework.stereotype.Service;

@Service
public class SecurityAuditService {

    private final SecurityAuditLogRepository logs;

    public SecurityAuditService(SecurityAuditLogRepository logs) {
        this.logs = logs;
    }

    public void record(String eventType, Long userId, String email, String actorId,
            boolean success, String detail) {
        logs.save(new SecurityAuditLog(eventType, userId, email, actorId, success, detail));
    }
}
