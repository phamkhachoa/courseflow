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
@Table(name = "loyalty_idempotency_keys")
public class LoyaltyIdempotencyKey {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(nullable = false, length = 40)
    private String operation;

    @Column(name = "idempotency_key", nullable = false, length = 180)
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

    protected LoyaltyIdempotencyKey() {
    }

    public LoyaltyIdempotencyKey(String tenantId, String applicationId, String operation, String idempotencyKey,
                                 String requestHash, String responseJson, Instant expiresAt) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.operation = operation;
        this.idempotencyKey = idempotencyKey;
        this.requestHash = requestHash;
        this.responseJson = responseJson == null || responseJson.isBlank() ? "{}" : responseJson;
        this.expiresAt = expiresAt;
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getOperation() { return operation; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getRequestHash() { return requestHash; }
    public String getResponseJson() { return responseJson; }
    public String getStatus() { return status; }
}
