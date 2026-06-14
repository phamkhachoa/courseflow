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
@Table(name = "incentive_idempotency_keys")
public class IncentiveIdempotencyKey {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(nullable = false, length = 40)
    private String operation;

    @Column(name = "idempotency_key", nullable = false, length = 160)
    private String idempotencyKey;

    @Column(name = "request_hash", nullable = false, length = 128)
    private String requestHash;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "response_json", nullable = false, columnDefinition = "jsonb")
    private String responseJson;

    @Column(nullable = false, length = 40)
    private String status = "SUCCEEDED";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    protected IncentiveIdempotencyKey() {
    }

    public IncentiveIdempotencyKey(String tenantId, String applicationId, String operation, String idempotencyKey,
                                   String requestHash, String responseJson, Instant expiresAt) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.operation = operation;
        this.idempotencyKey = idempotencyKey;
        this.requestHash = requestHash;
        this.responseJson = responseJson;
        this.expiresAt = expiresAt;
    }

    public boolean succeeded() {
        return "SUCCEEDED".equals(status);
    }

    public boolean inProgress() {
        return "IN_PROGRESS".equals(status);
    }

    public boolean expired(Instant now) {
        return expiresAt != null && now.isAfter(expiresAt);
    }

    public void complete(String responseJson, Instant expiresAt) {
        this.responseJson = responseJson;
        this.expiresAt = expiresAt;
        this.status = "SUCCEEDED";
    }

    public String getRequestHash() { return requestHash; }
    public String getResponseJson() { return responseJson; }
    public String getStatus() { return status; }
}
