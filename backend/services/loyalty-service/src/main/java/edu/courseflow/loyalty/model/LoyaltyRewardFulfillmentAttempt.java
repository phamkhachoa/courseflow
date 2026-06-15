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
@Table(name = "loyalty_reward_fulfillment_attempts")
public class LoyaltyRewardFulfillmentAttempt {

    @Id
    private UUID id;

    @Column(name = "redemption_id", nullable = false)
    private UUID redemptionId;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(name = "profile_id", nullable = false, length = 160)
    private String profileId;

    @Column(name = "reward_id", nullable = false)
    private UUID rewardId;

    @Column(name = "reward_code", nullable = false, length = 120)
    private String rewardCode;

    @Column(nullable = false, length = 80)
    private String provider;

    @Column(name = "attempt_number", nullable = false)
    private int attemptNumber;

    @Column(nullable = false, length = 40)
    private String status;

    @Column(name = "fulfillment_ref", length = 180)
    private String fulfillmentRef;

    @Column(name = "error_class", length = 160)
    private String errorClass;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "requested_at", nullable = false)
    private Instant requestedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "next_attempt_at")
    private Instant nextAttemptAt;

    @Column(name = "correlation_id", length = 160)
    private String correlationId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "payload_json", nullable = false, columnDefinition = "jsonb")
    private String payloadJson = "{}";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected LoyaltyRewardFulfillmentAttempt() {
    }

    public LoyaltyRewardFulfillmentAttempt(
            LoyaltyRewardRedemption redemption,
            String provider,
            int attemptNumber,
            String status,
            String fulfillmentRef,
            String errorClass,
            String errorMessage,
            Instant requestedAt,
            Instant completedAt,
            Instant nextAttemptAt,
            String correlationId,
            String payloadJson) {
        this.id = UUID.randomUUID();
        this.redemptionId = redemption.getId();
        this.tenantId = redemption.getTenantId();
        this.applicationId = redemption.getApplicationId();
        this.programId = redemption.getProgramId();
        this.profileId = redemption.getProfileId();
        this.rewardId = redemption.getRewardId();
        this.rewardCode = redemption.getRewardCode();
        this.provider = provider;
        this.attemptNumber = attemptNumber;
        this.status = status;
        this.fulfillmentRef = fulfillmentRef;
        this.errorClass = errorClass;
        this.errorMessage = errorMessage;
        this.requestedAt = requestedAt;
        this.completedAt = completedAt;
        this.nextAttemptAt = nextAttemptAt;
        this.correlationId = correlationId;
        this.payloadJson = payloadJson == null || payloadJson.isBlank() ? "{}" : payloadJson;
    }

    public UUID getId() { return id; }
    public UUID getRedemptionId() { return redemptionId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public UUID getRewardId() { return rewardId; }
    public String getRewardCode() { return rewardCode; }
    public String getProvider() { return provider; }
    public int getAttemptNumber() { return attemptNumber; }
    public String getStatus() { return status; }
    public String getFulfillmentRef() { return fulfillmentRef; }
    public String getErrorClass() { return errorClass; }
    public String getErrorMessage() { return errorMessage; }
    public Instant getRequestedAt() { return requestedAt; }
    public Instant getCompletedAt() { return completedAt; }
    public Instant getNextAttemptAt() { return nextAttemptAt; }
    public String getCorrelationId() { return correlationId; }
    public String getPayloadJson() { return payloadJson; }
    public Instant getCreatedAt() { return createdAt; }
}
