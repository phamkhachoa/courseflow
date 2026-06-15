package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "enrollment_remediation_case_actions")
public class EnrollmentRemediationCaseAction {

    @Id
    private UUID id;

    @Column(name = "case_id", nullable = false)
    private UUID caseId;

    @Column(nullable = false, length = 80)
    private String action;

    @Column(name = "actor_id", nullable = false, length = 80)
    private String actorId;

    @Column(columnDefinition = "TEXT")
    private String note;

    @Column(name = "from_status", length = 40)
    private String fromStatus;

    @Column(name = "to_status", length = 40)
    private String toStatus;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "payload_json", nullable = false, columnDefinition = "jsonb")
    private String payloadJson = "{}";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected EnrollmentRemediationCaseAction() {
    }

    public EnrollmentRemediationCaseAction(
            UUID caseId,
            String action,
            String actorId,
            String note,
            String fromStatus,
            String toStatus,
            String payloadJson) {
        this.id = UUID.randomUUID();
        this.caseId = caseId;
        this.action = action;
        this.actorId = actorId;
        this.note = note;
        this.fromStatus = fromStatus;
        this.toStatus = toStatus;
        this.payloadJson = payloadJson == null || payloadJson.isBlank() ? "{}" : payloadJson;
    }

    public UUID getId() { return id; }
    public UUID getCaseId() { return caseId; }
    public String getAction() { return action; }
    public String getActorId() { return actorId; }
    public String getNote() { return note; }
    public String getFromStatus() { return fromStatus; }
    public String getToStatus() { return toStatus; }
    public String getPayloadJson() { return payloadJson; }
    public Instant getCreatedAt() { return createdAt; }
}
