package edu.courseflow.loyalty.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class LoyaltyDtos {

    private LoyaltyDtos() {
    }

    public record CreateProgramRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotBlank String name,
            String pointUnit,
            Boolean allowNegativeBalance,
            @Positive Integer defaultPointsExpiryDays,
            List<ClientBindingRequestDto> clientBindings
    ) {
        public CreateProgramRequestDto(
                String tenantId,
                String applicationId,
                String programId,
                String name,
                String pointUnit,
                Boolean allowNegativeBalance,
                Integer defaultPointsExpiryDays) {
            this(tenantId, applicationId, programId, name, pointUnit, allowNegativeBalance,
                    defaultPointsExpiryDays, null);
        }
    }

    public record ClientBindingRequestDto(
            @NotBlank String clientId,
            List<String> allowedOperations
    ) {
    }

    public record UpsertClientBindingRequestDto(
            @NotBlank String clientId,
            String status,
            List<String> allowedOperations
    ) {
    }

    public record LoyaltyProgramDto(
            UUID id,
            String tenantId,
            String applicationId,
            String programId,
            String name,
            String pointUnit,
            String status,
            boolean allowNegativeBalance,
            Integer defaultPointsExpiryDays,
            Instant createdAt
    ) {
    }

    public record LoyaltyProgramAdminDto(
            UUID id,
            String tenantId,
            String applicationId,
            String programId,
            String name,
            String pointUnit,
            String status,
            boolean allowNegativeBalance,
            Integer defaultPointsExpiryDays,
            Instant createdAt,
            Instant updatedAt,
            List<LoyaltyProgramClientBindingDto> clientBindings
    ) {
    }

    public record LoyaltyProgramClientBindingDto(
            UUID id,
            String tenantId,
            String applicationId,
            String programId,
            String clientId,
            String status,
            List<String> allowedOperations,
            String createdBy,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record LoyaltyProgramReadinessDto(
            UUID programUuid,
            String tenantId,
            String applicationId,
            String programId,
            String clientId,
            String operation,
            boolean ready,
            String programStatus,
            boolean clientBound,
            String bindingStatus,
            List<String> allowedOperations,
            List<String> blockers,
            List<String> warnings
    ) {
    }

    public record UpdateProgramRequestDto(
            String name,
            String pointUnit,
            Boolean allowNegativeBalance,
            @Positive Integer defaultPointsExpiryDays
    ) {
    }

    public record UpdateProgramStatusRequestDto(
            @NotBlank String status,
            String note
    ) {
    }

    public record CreateAccountRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotBlank String profileId
    ) {
    }

    public record LoyaltyAccountDto(
            UUID id,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            String status,
            long balance,
            Instant openedAt
    ) {
    }

    public record UpdateAccountStatusRequestDto(
            @NotBlank String status,
            String note
    ) {
    }

    public record CreateLoyaltyTierPolicyRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotBlank String tierCode,
            @NotBlank String name,
            @NotNull @Positive Integer rank,
            @NotNull @Min(0) Long qualificationPoints,
            @NotNull @Positive Integer qualificationWindowDays,
            @NotNull @Min(0) Integer downgradeGraceDays,
            Map<String, Object> benefits
    ) {
    }

    public record UpdateLoyaltyTierPolicyRequestDto(
            String name,
            @Positive Integer rank,
            @Min(0) Long qualificationPoints,
            @Positive Integer qualificationWindowDays,
            @Min(0) Integer downgradeGraceDays,
            Map<String, Object> benefits
    ) {
    }

    public record UpdateLoyaltyTierPolicyStatusRequestDto(
            @NotBlank String status,
            String note
    ) {
    }

    public record LoyaltyTierPolicyDto(
            UUID id,
            UUID programUuid,
            String tenantId,
            String applicationId,
            String programId,
            String tierCode,
            String name,
            int rank,
            String status,
            long qualificationPoints,
            int qualificationWindowDays,
            int downgradeGraceDays,
            Map<String, Object> benefits,
            String createdBy,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record LoyaltyTierProgressDto(
            UUID stateId,
            UUID accountId,
            UUID currentTierPolicyId,
            String currentTierCode,
            String currentTierName,
            int currentTierRank,
            long qualificationPoints,
            Integer qualificationWindowDays,
            Instant qualificationWindowStartedAt,
            Instant qualificationWindowEndsAt,
            Instant currentPeriodStartedAt,
            Instant qualifiedAt,
            Instant graceUntil,
            UUID nextTierPolicyId,
            String nextTierCode,
            String nextTierName,
            Integer nextTierRank,
            Long nextTierPointsRequired,
            Long pointsToNext,
            Instant evaluatedAt
    ) {
    }

    public record LoyaltyTierStateDto(
            UUID id,
            UUID accountId,
            UUID programUuid,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            LoyaltyTierProgressDto progress,
            Instant updatedAt
    ) {
    }

    public record LoyaltyTierStateQueryResponseDto(
            List<LoyaltyTierStateDto> items,
            int limit,
            boolean hasMore
    ) {
    }

    public record RecalculateLoyaltyTiersRequestDto(
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            UUID accountId,
            @Positive Integer limit,
            String reason,
            String correlationId
    ) {
    }

    public record LoyaltyTierRecalculateResponseDto(
            Instant runAt,
            int scanned,
            int changed,
            List<LoyaltyTierStateDto> items
    ) {
    }

    public record PointsMutationRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotBlank String profileId,
            @Positive long points,
            @NotBlank String sourceReference,
            @NotBlank String idempotencyKey,
            String reason,
            String correlationId,
            Instant occurredAt,
            Instant expiresAt,
            Map<String, Object> metadata
    ) {
    }

    public record ReversePointsRequestDto(
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            String correlationId,
            Map<String, Object> metadata,
            UUID approvalId
    ) {
        public ReversePointsRequestDto(
                String idempotencyKey,
                String reason,
                String correlationId,
                Map<String, Object> metadata) {
            this(idempotencyKey, reason, correlationId, metadata, null);
        }
    }

    public record PointsAdjustmentRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotBlank String profileId,
            @NotNull Long pointsDelta,
            @NotBlank String sourceReference,
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String correlationId,
            Instant occurredAt,
            Instant expiresAt,
            Map<String, Object> metadata
    ) {
    }

    public record PointsExpiryDryRunRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotNull Instant asOf,
            @Positive Integer limit
    ) {
    }

    public record PointsExpiryCandidateDto(
            UUID entryId,
            UUID accountId,
            String profileId,
            long pointsDelta,
            String sourceReference,
            Instant occurredAt,
            Instant expiresAt
    ) {
    }

    public record PointsExpiryDryRunResponseDto(
            String tenantId,
            String applicationId,
            String programId,
            Instant asOf,
            int candidateEntryCount,
            int affectedAccountCount,
            long expiringPoints,
            String resultHash,
            List<PointsExpiryCandidateDto> samples,
            List<String> warnings
    ) {
    }

    public record PointsExpiryExecutionRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotNull Instant asOf,
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String correlationId,
            @Positive Integer limit,
            @NotNull UUID approvalId
    ) {
    }

    public record SubmitPointsExpiryApprovalRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotNull Instant asOf,
            @NotBlank String resultHash,
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String correlationId,
            @Positive Integer limit
    ) {
    }

    public record PointsExpiryExecutionItemDto(
            UUID entryId,
            UUID accountId,
            UUID sourceLotId,
            UUID sourceEntryId,
            String profileId,
            long expiredPoints,
            String sourceReference,
            Instant expiresAt
    ) {
    }

    public record PointsExpiryExecutionResponseDto(
            String tenantId,
            String applicationId,
            String programId,
            Instant asOf,
            int expiredLotCount,
            int affectedAccountCount,
            long expiredPoints,
            boolean idempotencyReplay,
            List<PointsExpiryExecutionItemDto> items,
            List<String> warnings
    ) {
    }

    public record SubmitPointsAdjustmentApprovalRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotBlank String profileId,
            @NotNull Long pointsDelta,
            @NotBlank String sourceReference,
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String correlationId,
            Instant occurredAt,
            Instant expiresAt,
            Map<String, Object> metadata
    ) {
    }

    public record ReviewLoyaltyAdjustmentApprovalRequestDto(
            @NotBlank String note
    ) {
    }

    public record LoyaltyAdjustmentApprovalDto(
            UUID id,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            long pointsDelta,
            String sourceReference,
            String reason,
            String correlationId,
            Instant occurredAt,
            Instant expiresAt,
            String status,
            String requestedBy,
            String reviewedBy,
            String reviewNote,
            Instant requestedAt,
            Instant reviewedAt,
            Instant executedAt,
            UUID executedEntryId,
            String operationType,
            Map<String, Object> metadata
    ) {
    }

    public record LoyaltyBalanceBucketDto(
            UUID entryId,
            UUID accountId,
            String profileId,
            String entryType,
            long originalPoints,
            long consumedPoints,
            long remainingPoints,
            String sourceReference,
            Instant occurredAt,
            Instant expiresAt,
            String status
    ) {
    }

    public record LoyaltyBalanceBucketResponseDto(
            UUID accountId,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            long ledgerBalance,
            long activePoints,
            long expiredPoints,
            long unallocatedDebitPoints,
            String projectionMode,
            Instant asOf,
            List<LoyaltyBalanceBucketDto> items,
            List<String> warnings
    ) {
    }

    public record LearnerLoyaltyBalanceDto(
            UUID accountId,
            String tenantId,
            String applicationId,
            String programId,
            String pointUnit,
            String accountStatus,
            String programStatus,
            long ledgerBalance,
            long activePoints,
            long expiredPoints,
            long expiringSoonPoints,
            Instant nextExpiryAt,
            LoyaltyTierProgressDto tierProgress,
            List<String> warnings
    ) {
    }

    public record LearnerLoyaltyBalanceResponseDto(
            String profileId,
            Instant generatedAt,
            List<LearnerLoyaltyBalanceDto> items
    ) {
    }

    public record LearnerLoyaltyWalletTotalsDto(
            long ledgerBalance,
            long activePoints,
            long expiredPoints,
            long expiringSoonPoints,
            int accountCount,
            int activeAccountCount,
            Instant nextExpiryAt
    ) {
    }

    public record LearnerLoyaltyWalletAccountDto(
            LearnerLoyaltyBalanceDto balance,
            List<LoyaltyBalanceBucketDto> buckets,
            List<PointsEntryDto> recentEntries
    ) {
    }

    public record LearnerLoyaltyWalletResponseDto(
            String profileId,
            Instant generatedAt,
            LearnerLoyaltyWalletTotalsDto totals,
            List<LearnerLoyaltyWalletAccountDto> accounts,
            List<LearnerRewardDto> availableRewards,
            List<LoyaltyRewardRedemptionDto> recentRedemptions,
            List<String> warnings
    ) {
    }

    public record PointLotBackfillRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            String programId,
            String profileId,
            UUID accountId,
            Boolean dryRun,
            @Positive Integer limit,
            String expectedResultHash,
            String reason,
            String correlationId
    ) {
    }

    public record PointLotBackfillAccountResultDto(
            UUID accountId,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            long ledgerBalance,
            long projectedRemainingPoints,
            long projectedExpiredPoints,
            long unallocatedDebitPoints,
            int positiveEntryCount,
            int debitEntryCount,
            int existingLotCount,
            int missingLotCount,
            int resetLotCount,
            List<String> warnings
    ) {
    }

    public record PointLotBackfillResponseDto(
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            UUID accountId,
            boolean dryRun,
            int scannedAccountCount,
            int affectedAccountCount,
            int missingLotCount,
            int resetLotCount,
            long unallocatedDebitPoints,
            boolean hasMore,
            String resultHash,
            Instant generatedAt,
            List<PointLotBackfillAccountResultDto> items,
            List<String> warnings
    ) {
    }

    public record LoyaltyReconciliationEntryDto(
            UUID ledgerEntryId,
            String reconciliationKey,
            String reconciliationStatus,
            List<String> reasonCodes,
            String direction,
            String entryType,
            UUID accountId,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            long pointsDelta,
            String sourceReference,
            UUID reversalOfEntryId,
            String outboxStatus,
            String correlationId,
            Instant occurredAt,
            Instant expiresAt,
            Instant ledgerCreatedAt
    ) {
    }

    public record LoyaltyReconciliationQueryResponseDto(
            List<LoyaltyReconciliationEntryDto> items,
            int limit,
            boolean hasMore,
            Instant generatedAt
    ) {
    }

    public record LoyaltyBenefitReconciliationEntryDto(
            String reconciliationKey,
            String reconciliationStatus,
            List<String> reasonCodes,
            String itemType,
            String severity,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            String redemptionId,
            String effectId,
            String expectedEntryType,
            long expectedPointsDelta,
            String expectedSourceReference,
            String expectedIdempotencyKey,
            UUID ledgerEntryId,
            UUID reversalOfEntryId,
            UUID rewardRedemptionId,
            UUID rewardBurnEntryId,
            UUID rewardReversalEntryId,
            String rewardCode,
            String rewardStatus,
            long rewardPointsCost,
            String sourceEventType,
            String sourceEventId,
            String payloadHash,
            String correlationId,
            Instant observedAt,
            Instant ledgerCreatedAt,
            Instant rewardReversedAt
    ) {
    }

    public record LoyaltyBenefitReconciliationQueryResponseDto(
            List<LoyaltyBenefitReconciliationEntryDto> items,
            int limit,
            boolean hasMore,
            Instant generatedAt
    ) {
    }

    public record LoyaltyFinanceCloseoutTotalsDto(
            long earnedPoints,
            long burnedPoints,
            long reversedPoints,
            long adjustedPoints,
            long expiredPoints,
            long netPoints,
            int entryCount,
            int pendingOutboxCount,
            int missingOutboxCount
    ) {
    }

    public record LoyaltyFinanceCloseoutExportDto(
            String closeoutId,
            String tenantId,
            String applicationId,
            String programId,
            Instant from,
            Instant to,
            String resultHash,
            boolean certifiable,
            Instant generatedAt,
            LoyaltyFinanceCloseoutTotalsDto totals,
            List<LoyaltyReconciliationEntryDto> items,
            int limit,
            boolean hasMore,
            String nextCursor,
            List<String> warnings
    ) {
    }

    public record LoyaltyAdjustmentApprovalQueryResponseDto(
            List<LoyaltyAdjustmentApprovalDto> items,
            int limit,
            boolean hasMore
    ) {
    }

    public record LoyaltyApprovalEvidencePackDto(
            UUID approvalId,
            String tenantId,
            String applicationId,
            String programId,
            String operationType,
            Instant generatedAt,
            LoyaltyAdjustmentApprovalDto approval,
            List<LoyaltyAuditEventDto> auditEvents,
            List<LoyaltyReconciliationEntryDto> ledgerEntries,
            Map<String, Object> evidenceSummary,
            List<String> warnings
    ) {
    }

    public record CreateRewardRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String programId,
            @NotBlank String rewardCode,
            @NotBlank String name,
            String description,
            @Positive Long pointsCost,
            String status,
            Instant startsAt,
            Instant endsAt,
            @Positive Long inventoryLimit,
            @Positive Integer perProfileLimit,
            String fulfillmentType,
            Map<String, Object> fulfillmentConfig
    ) {
    }

    public record UpdateRewardRequestDto(
            String name,
            String description,
            @Positive Long pointsCost,
            Instant startsAt,
            Instant endsAt,
            @Positive Long inventoryLimit,
            @Positive Integer perProfileLimit,
            String fulfillmentType,
            Map<String, Object> fulfillmentConfig
    ) {
    }

    public record UpdateRewardStatusRequestDto(
            @NotBlank String status,
            String note
    ) {
    }

    public record UpdateRewardFulfillmentStatusRequestDto(
            @NotBlank String status,
            String fulfillmentRef,
            String note,
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String correlationId,
            Map<String, Object> metadata,
            UUID approvalId
    ) {
    }

    public record SubmitRewardFulfillmentApprovalRequestDto(
            @NotBlank String status,
            String fulfillmentRef,
            String note,
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String correlationId,
            Map<String, Object> metadata
    ) {
    }

    public record RetryRewardFulfillmentRequestDto(
            String reason,
            String correlationId
    ) {
    }

    public record RewardFulfillmentCallbackRequestDto(
            UUID redemptionId,
            String externalRef,
            @NotBlank String status,
            String fulfillmentRef,
            String note,
            String errorClass,
            String errorMessage,
            Instant occurredAt,
            Map<String, Object> metadata
    ) {
    }

    public record SubmitRewardRedemptionReversalApprovalRequestDto(
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String correlationId,
            Map<String, Object> metadata
    ) {
    }

    public record LoyaltyRewardDto(
            UUID id,
            UUID programUuid,
            String tenantId,
            String applicationId,
            String programId,
            String rewardCode,
            String name,
            String description,
            long pointsCost,
            String status,
            Instant startsAt,
            Instant endsAt,
            Long inventoryLimit,
            Integer perProfileLimit,
            String fulfillmentType,
            Map<String, Object> fulfillmentConfig,
            long redeemedCount,
            String createdBy,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record LearnerRewardDto(
            UUID id,
            String tenantId,
            String applicationId,
            String programId,
            String rewardCode,
            String name,
            String description,
            long pointsCost,
            String pointUnit,
            long ledgerBalance,
            long spendableBalance,
            boolean eligible,
            List<String> ineligibleReasons,
            Long inventoryRemaining,
            Integer perProfileRemaining,
            Instant startsAt,
            Instant endsAt,
            String fulfillmentType
    ) {
    }

    public record LearnerRewardCatalogResponseDto(
            String profileId,
            Instant generatedAt,
            List<LearnerRewardDto> items
    ) {
    }

    public record RedeemRewardRequestDto(
            @NotBlank String idempotencyKey,
            String correlationId,
            String note,
            Map<String, Object> metadata
    ) {
    }

    public record LoyaltyRewardRedemptionDto(
            UUID id,
            UUID rewardId,
            UUID accountId,
            UUID burnEntryId,
            UUID reversalEntryId,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            String rewardCode,
            long pointsCost,
            String sourceReference,
            String status,
            String fulfillmentStatus,
            String fulfillmentRef,
            String fulfillmentNote,
            String fulfillmentProvider,
            int fulfillmentAttemptCount,
            Instant fulfillmentLastAttemptAt,
            Instant fulfillmentNextAttemptAt,
            Instant fulfillmentSlaDueAt,
            String fulfillmentErrorClass,
            String fulfillmentErrorMessage,
            Instant fulfillmentCallbackReceivedAt,
            String fulfillmentCallbackPayloadHash,
            Map<String, Object> rewardSnapshot,
            String correlationId,
            String note,
            Map<String, Object> metadata,
            Instant redeemedAt,
            Instant fulfilledAt,
            Instant reversedAt,
            boolean idempotencyReplay
    ) {
    }

    public record RewardFulfillmentRunItemDto(
            UUID redemptionId,
            String rewardCode,
            String fulfillmentProvider,
            String fulfillmentStatus,
            String fulfillmentRef,
            int fulfillmentAttemptCount,
            Instant nextAttemptAt,
            String errorClass,
            String errorMessage
    ) {
    }

    public record RewardFulfillmentRunResponseDto(
            Instant runAt,
            int scanned,
            int dispatched,
            int issued,
            int pending,
            int failed,
            int manualRequired,
            List<RewardFulfillmentRunItemDto> items
    ) {
    }

    public record LoyaltyRewardRedemptionQueryResponseDto(
            List<LoyaltyRewardRedemptionDto> items,
            int limit,
            boolean hasMore
    ) {
    }

    public record LoyaltyInboundDeadLetterSummaryDto(
            UUID id,
            String sourceTopic,
            String dltTopic,
            String consumerGroup,
            int kafkaPartition,
            long kafkaOffset,
            Integer originalPartition,
            Long originalOffset,
            String recordKey,
            String status,
            int replayAttempts,
            String payloadHash,
            String exceptionClass,
            String exceptionMessage,
            Instant createdAt,
            Instant updatedAt,
            Instant lastReplayAt,
            Instant replayedAt,
            Instant discardedAt
    ) {
    }

    public record LoyaltyInboundDeadLetterDetailDto(
            UUID id,
            String sourceTopic,
            String dltTopic,
            String consumerGroup,
            int kafkaPartition,
            long kafkaOffset,
            Integer originalPartition,
            Long originalOffset,
            String recordKey,
            String status,
            int replayAttempts,
            String payloadHash,
            long payloadSizeBytes,
            String exceptionClass,
            String exceptionMessage,
            String stacktrace,
            String lastReplayError,
            String resolvedBy,
            String resolutionNote,
            Map<String, Object> headers,
            Instant createdAt,
            Instant updatedAt,
            Instant lastReplayAt,
            Instant replayedAt,
            Instant discardedAt
    ) {
    }

    public record LoyaltyInboundDeadLetterQueryResponseDto(
            List<LoyaltyInboundDeadLetterSummaryDto> items,
            int limit,
            boolean hasMore
    ) {
    }

    public record LoyaltyInboundDeadLetterActionRequestDto(
            @NotBlank String reason,
            Boolean dryRun,
            UUID approvalId
    ) {
    }

    public record LoyaltyInboundDeadLetterActionResponseDto(
            UUID deadLetterId,
            String action,
            String status,
            boolean dryRun,
            boolean replayed,
            boolean discarded,
            String reasonCode,
            String payloadHash,
            Instant completedAt
    ) {
    }

    public record LoyaltyInboundDeadLetterApprovalRequestDto(
            @NotBlank String action,
            @NotBlank String reason,
            @NotBlank String evidenceReference
    ) {
    }

    public record LoyaltyInboundDeadLetterApprovalReviewRequestDto(
            @NotBlank String note
    ) {
    }

    public record LoyaltyInboundDeadLetterApprovalDto(
            UUID id,
            UUID deadLetterId,
            String action,
            String status,
            String reason,
            String evidenceReference,
            String thresholdPolicy,
            String payloadHash,
            String requestHash,
            String requestedBy,
            String reviewedBy,
            String reviewNote,
            String executedBy,
            Instant requestedAt,
            Instant reviewedAt,
            Instant executedAt
    ) {
    }

    public record LoyaltyInboundDeadLetterApprovalQueryResponseDto(
            List<LoyaltyInboundDeadLetterApprovalDto> items,
            int limit,
            boolean hasMore
    ) {
    }

    public record PointsEntryDto(
            UUID id,
            UUID accountId,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            String entryType,
            long pointsDelta,
            String sourceReference,
            UUID reversalOfEntryId,
            String reason,
            String correlationId,
            Instant occurredAt,
            Instant expiresAt,
            Instant createdAt
    ) {
    }

    public record PointsMutationResponseDto(
            UUID entryId,
            UUID accountId,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            String entryType,
            long pointsDelta,
            long balance,
            boolean idempotencyReplay
    ) {
    }

    public record LedgerQueryResponseDto(
            UUID accountId,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            long balance,
            List<PointsEntryDto> items
    ) {
    }

    public record LoyaltyAuditEventDto(
            UUID id,
            String tenantId,
            String applicationId,
            String aggregateId,
            String aggregateType,
            String action,
            String actorId,
            String note,
            Map<String, Object> payload,
            String correlationId,
            Instant createdAt
    ) {
    }

    public record LoyaltyAuditQueryResponseDto(
            List<LoyaltyAuditEventDto> items,
            int limit,
            boolean hasMore
    ) {
    }
}
