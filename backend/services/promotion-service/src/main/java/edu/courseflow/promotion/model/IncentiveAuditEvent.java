package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "incentive_audit_events")
public class IncentiveAuditEvent {

    @Id
    private UUID id;

    @Column(name = "tenant_id", length = 80)
    private String tenantId;

    @Column(name = "application_id", length = 80)
    private String applicationId;

    @Column(name = "aggregate_id", nullable = false, length = 120)
    private String aggregateId;

    @Column(name = "aggregate_type", nullable = false, length = 80)
    private String aggregateType;

    @Column(nullable = false, length = 80)
    private String action;

    @Column(name = "actor_id", length = 80)
    private String actorId;

    @Column(columnDefinition = "TEXT")
    private String note;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "payload_json", nullable = false, columnDefinition = "jsonb")
    private String payloadJson;

    @Column(name = "correlation_id", length = 120)
    private String correlationId;

    @Column(name = "source_client_id", length = 160)
    private String sourceClientId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected IncentiveAuditEvent() {
    }

    public IncentiveAuditEvent(String tenantId, String applicationId, String aggregateId, String aggregateType,
                               String action, String actorId, String note, String payloadJson) {
        this(tenantId, applicationId, aggregateId, aggregateType, action, actorId, note, payloadJson, null, null);
    }

    public IncentiveAuditEvent(String tenantId, String applicationId, String aggregateId, String aggregateType,
                               String action, String actorId, String note, String payloadJson,
                               String correlationId, String sourceClientId) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.aggregateId = aggregateId;
        this.aggregateType = aggregateType;
        this.action = action;
        this.actorId = actorId;
        this.note = note;
        this.payloadJson = payloadJson == null || payloadJson.isBlank() ? "{}" : payloadJson;
        this.correlationId = correlationId;
        this.sourceClientId = sourceClientId;
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getAggregateId() { return aggregateId; }
    public String getAggregateType() { return aggregateType; }
    public String getAction() { return action; }
    public String getActorId() { return actorId; }
    public String getNote() { return note; }
    public String getPayloadJson() { return payloadJson; }
    public String getCorrelationId() { return correlationId; }
    public String getSourceClientId() { return sourceClientId; }
    public Instant getCreatedAt() { return createdAt; }
}
