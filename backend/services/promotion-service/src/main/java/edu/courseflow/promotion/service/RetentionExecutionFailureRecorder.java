package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveRetentionApproval;
import edu.courseflow.promotion.repository.IncentiveRetentionApprovalRepository;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RetentionExecutionFailureRecorder {

    private final IncentiveRetentionOperationRepository operations;
    private final IncentiveRetentionApprovalRepository approvals;
    private final IncentiveAuditEventRepository auditEvents;
    private final IncentiveAccessService access;
    private final ObjectMapper objectMapper;
    private final IncentiveMetrics metrics;

    public RetentionExecutionFailureRecorder(IncentiveRetentionOperationRepository operations,
                                             IncentiveRetentionApprovalRepository approvals,
                                             IncentiveAuditEventRepository auditEvents,
                                             IncentiveAccessService access,
                                             ObjectMapper objectMapper,
                                             IncentiveMetrics metrics) {
        this.operations = operations;
        this.approvals = approvals;
        this.auditEvents = auditEvents;
        this.access = access;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordFailure(IncentiveRetentionApproval approval,
                              CurrentUser user,
                              String correlationId,
                              RuntimeException failure,
                              Duration duration) {
        Instant failedAt = Instant.now();
        String sanitized = sanitizedError(failure);
        operations.lockByApprovalId(approval.getId())
                .filter(operation -> operation.inProgress())
                .ifPresent(operation -> operation.fail(sanitized, failedAt));
        approvals.lockById(approval.getId())
                .filter(IncentiveRetentionApproval::approved)
                .ifPresent(locked -> locked.markExecutionFailed(failedAt));

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("approvalId", approval.getId().toString());
        payload.put("policyId", approval.getPolicyId());
        payload.put("policyVersion", approval.getPolicyVersion());
        payload.put("targetDataset", approval.getTargetDataset());
        payload.put("tenantId", approval.getTenantId() == null ? "" : approval.getTenantId());
        payload.put("applicationId", approval.getApplicationId() == null ? "" : approval.getApplicationId());
        payload.put("dryRunId", approval.getDryRunId().toString());
        payload.put("resultHash", approval.getDryRunResultHash());
        payload.put("changeTicket", approval.getChangeTicket());
        payload.put("restoreDrillRef", approval.getRestoreDrillRef());
        payload.put("errorType", failure.getClass().getSimpleName());
        payload.put("error", sanitized);
        auditEvents.save(new IncentiveAuditEvent(
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getId().toString(),
                "retention-approval",
                "retention.execution_failed",
                actorId(user),
                approval.getReason(),
                toJson(payload),
                correlationId,
                access.sourceClientId(user)));
        metrics.retentionExecution(approval.getPolicyId(), approval.getTargetDataset(), "failed", 0, duration);
    }

    private String sanitizedError(RuntimeException failure) {
        if (!failure.getClass().getName().startsWith("edu.courseflow.commonlibrary.exception")) {
            return failure.getClass().getSimpleName();
        }
        String message = failure.getMessage();
        if (message == null || message.isBlank()) {
            return failure.getClass().getSimpleName();
        }
        String sanitized = message.replaceAll("[\\r\\n\\t]+", " ").trim();
        return sanitized.length() > 240 ? sanitized.substring(0, 240) : sanitized;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Could not serialize retention failure audit payload", ex);
        }
    }

    private String actorId(CurrentUser user) {
        if (user == null) {
            return "unknown";
        }
        if (user.email() != null && !user.email().isBlank()) {
            return user.email();
        }
        return user.id() == null ? "unknown" : user.id().toString();
    }
}
