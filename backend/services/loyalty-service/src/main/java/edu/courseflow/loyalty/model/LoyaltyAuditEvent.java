package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "loyalty_audit_events")
public class LoyaltyAuditEvent {

    @Id
    private UUID id;

    @Column(name = "tenant_id", length = 80)
    private String tenantId;

    @Column(name = "application_id", length = 80)
    private String applicationId;

    @Column(name = "aggregate_id", nullable = false, length = 160)
    private String aggregateId;

    @Column(name = "aggregate_type", nullable = false, length = 80)
    private String aggregateType;

    @Column(nullable = false, length = 80)
    private String action;

    @Column(name = "actor_id", length = 160)
    private String actorId;

    @Column(columnDefinition = "TEXT")
    private String note;

    @Column(name = "correlation_id", length = 160)
    private String correlationId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "payload_json", nullable = false, columnDefinition = "jsonb")
    private String payloadJson;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected LoyaltyAuditEvent() {
    }

    public LoyaltyAuditEvent(String tenantId, String applicationId, String aggregateId, String aggregateType,
                             String action, String actorId, String note, String correlationId, String payloadJson) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.aggregateId = aggregateId;
        this.aggregateType = aggregateType;
        this.action = action;
        this.actorId = actorId;
        this.note = note;
        this.correlationId = correlationId;
        this.payloadJson = payloadJson == null || payloadJson.isBlank() ? "{}" : payloadJson;
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getAggregateId() { return aggregateId; }
    public String getAggregateType() { return aggregateType; }
    public String getAction() { return action; }
    public String getActorId() { return actorId; }
    public String getNote() { return note; }
    public String getCorrelationId() { return correlationId; }
    public String getPayloadJson() { return payloadJson; }
    public Instant getCreatedAt() { return createdAt; }
}
