package edu.courseflow.promotion.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class PromotionDtos {

    private PromotionDtos() {
    }

    private static Integer integerValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Integer.parseInt(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    public record RuleSpecDto(
            @NotBlank String type,
            Integer schemaVersion,
            Map<String, Object> parameters
    ) {
    }

    public record ActionSpecDto(
            @NotBlank String type,
            Integer schemaVersion,
            Map<String, Object> parameters
    ) {
    }

    public record IncentiveItemDto(
            @NotBlank String id,
            @NotBlank String type,
            @Min(1) int quantity,
            @NotNull @DecimalMin("0.00") BigDecimal unitPrice,
            Map<String, Object> attributes
    ) {
    }

    public record TransactionContextDto(
            @NotNull @DecimalMin("0.00") BigDecimal subtotal,
            @DecimalMin("0.00") BigDecimal shippingAmount
    ) {
    }

    public record IncentiveEffectDto(
            String type,
            String targetType,
            String targetId,
            BigDecimal amount,
            String currency,
            Map<String, Object> metadata,
            String effectId,
            String benefitType,
            String actionType,
            String unit,
            BigDecimal quantity,
            Integer campaignVersion
    ) {
        public IncentiveEffectDto(String type,
                                  String targetType,
                                  String targetId,
                                  BigDecimal amount,
                                  String currency,
                                  Map<String, Object> metadata) {
            this(type, targetType, targetId, amount, currency, metadata, null, null, type, currency, amount,
                    metadata == null ? null : integerValue(metadata.get("campaignVersion")));
        }
    }

    public record CatalogParameterDto(
            String name,
            String type,
            boolean required,
            String description,
            List<String> allowedValues
    ) {
    }

    public record RuleCatalogItemDto(
            String type,
            int schemaVersion,
            String description,
            List<CatalogParameterDto> parameters,
            List<String> requiredFacts,
            String missingFactReasonCode
    ) {
    }

    public record ActionCatalogItemDto(
            String type,
            int schemaVersion,
            String benefitType,
            String description,
            List<CatalogParameterDto> parameters,
            List<String> emittedEffectTypes
    ) {
    }

    public record EffectCatalogItemDto(
            String benefitType,
            String unit,
            List<String> actionTypes,
            List<String> targetTypes,
            String description
    ) {
    }

    public record ReasonCodeCatalogItemDto(
            String code,
            String category,
            boolean terminal,
            String description
    ) {
    }

    public record IdempotencyContractDto(
            String preferredLocation,
            String headerName,
            List<String> bodyFields,
            String ttl,
            String replayBehavior,
            String conflictBehavior
    ) {
    }

    public record IncentiveCatalogDto(
            String catalogVersion,
            String factContractVersion,
            List<RuleCatalogItemDto> rules,
            List<ActionCatalogItemDto> actions,
            List<EffectCatalogItemDto> effects,
            List<ReasonCodeCatalogItemDto> reasonCodes,
            IdempotencyContractDto idempotency,
            List<String> portabilityNotes
    ) {
    }

    public record CampaignDto(
            UUID id,
            String tenantId,
            String applicationId,
            String code,
            String name,
            String description,
            String incentiveType,
            String status,
            Instant startsAt,
            Instant endsAt,
            int priority,
            boolean exclusive,
            boolean stackable,
            boolean couponRequired,
            String matchPolicy,
            String currency,
            List<RuleSpecDto> rules,
            List<ActionSpecDto> actions,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Instant createdAt,
            Instant updatedAt,
            Instant publishedAt,
            Integer draftVersion,
            Integer publishedVersion
    ) {
    }

    public record ApplicationDto(
            UUID id,
            String tenantId,
            String applicationId,
            String name,
            String status,
            List<ApplicationClientBindingDto> clientBindings,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record ApplicationClientBindingDto(
            UUID id,
            String tenantId,
            String applicationId,
            String clientId,
            String status,
            List<String> allowedOperations,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record CampaignVersionDto(
            UUID id,
            UUID campaignId,
            int versionNumber,
            String versionStatus,
            boolean activeSnapshot,
            String createdBy,
            String submittedBy,
            String reviewedBy,
            String publishedBy,
            String reviewNote,
            Instant createdAt,
            Instant submittedAt,
            Instant reviewedAt,
            Instant publishedAt
    ) {
    }

    public record CampaignVersionReviewQueueItemDto(
            CampaignVersionDto version,
            String tenantId,
            String applicationId,
            String campaignCode,
            String campaignName,
            int blockerCount,
            int warningCount,
            boolean publishable
    ) {
    }

    public record CampaignVersionReviewQueueResponseDto(
            List<CampaignVersionReviewQueueItemDto> items,
            int limit,
            boolean hasMore
    ) {
    }

    public record CampaignVersionDetailDto(
            UUID id,
            UUID campaignId,
            int versionNumber,
            String versionStatus,
            boolean activeSnapshot,
            String tenantId,
            String applicationId,
            String code,
            String name,
            String description,
            String incentiveType,
            Instant startsAt,
            Instant endsAt,
            int priority,
            boolean exclusive,
            boolean stackable,
            boolean couponRequired,
            String matchPolicy,
            String currency,
            List<RuleSpecDto> rules,
            List<ActionSpecDto> actions,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Integer rollbackSourceVersion,
            String createdBy,
            String submittedBy,
            String reviewedBy,
            String publishedBy,
            String reviewNote,
            Instant createdAt,
            Instant submittedAt,
            Instant reviewedAt,
            Instant publishedAt
    ) {
    }

    public record UpdateCampaignVersionDraftRequestDto(
            String code,
            String name,
            String description,
            String incentiveType,
            Instant startsAt,
            Instant endsAt,
            Integer priority,
            Boolean exclusive,
            Boolean stackable,
            Boolean couponRequired,
            String matchPolicy,
            String currency,
            @Valid List<RuleSpecDto> rules,
            @Valid List<ActionSpecDto> actions,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile
    ) {
    }

    public record ValidationMessageDto(
            String severity,
            String code,
            String field,
            String message
    ) {
    }

    public record CampaignVersionValidationDto(
            UUID campaignId,
            int versionNumber,
            boolean publishable,
            List<ValidationMessageDto> blockers,
            List<ValidationMessageDto> warnings
    ) {
    }

    public record CampaignVersionDiffEntryDto(
            String field,
            Object leftValue,
            Object rightValue
    ) {
    }

    public record CampaignVersionDiffDto(
            UUID campaignId,
            int leftVersion,
            int rightVersion,
            List<CampaignVersionDiffEntryDto> changes
    ) {
    }

    public record RollbackCampaignVersionRequestDto(
            String note
    ) {
    }

    public record AuditEventDto(
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
            String sourceClientId,
            Instant createdAt
    ) {
    }

    public record AuditQueryResponseDto(
            List<AuditEventDto> items,
            int limit,
            boolean hasMore
    ) {
    }

    public record CouponDto(
            UUID id,
            UUID campaignId,
            String code,
            String normalizedCode,
            String codeMask,
            String status,
            String holderProfileId,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Map<String, Object> metadata,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record LearnerCouponDto(
            UUID couponId,
            UUID campaignId,
            String campaignCode,
            String campaignName,
            String codeMask,
            String status,
            String walletStatus,
            Instant startsAt,
            Instant expiresAt,
            UUID redemptionId,
            Instant redeemedAt,
            String message
    ) {
    }

    public record LearnerCouponWalletDto(
            String tenantId,
            String applicationId,
            String profileId,
            Instant generatedAt,
            int availableCount,
            int expiringSoonCount,
            int usedCount,
            int expiredCount,
            List<LearnerCouponDto> items
    ) {
    }

    public record CouponStorageInventoryItemDto(
            String storageFormat,
            long count
    ) {
    }

    public record CouponStorageInventoryDto(
            String tenantId,
            String applicationId,
            UUID campaignId,
            boolean activeOnly,
            boolean legacyFallbackEnabled,
            boolean fallbackDisableReady,
            long totalCoupons,
            long legacyCoupons,
            long malformedCoupons,
            Instant generatedAt,
            List<CouponStorageInventoryItemDto> items
    ) {
    }

    public record CouponDistributionRecipientInputDto(
            @NotBlank String profileId,
            Map<String, Object> metadata
    ) {
    }

    public record PreviewCouponDistributionRequestDto(
            @NotNull UUID campaignId,
            @NotBlank String sourceType,
            String sourceReference,
            Boolean notifyLearners,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Map<String, Object> metadata,
            @NotEmpty @Valid List<CouponDistributionRecipientInputDto> recipients
    ) {
    }

    public record CouponDistributionPreviewRecipientDto(
            String profileId,
            String status,
            String reason,
            Map<String, Object> metadata
    ) {
    }

    public record CouponDistributionPreviewResponseDto(
            UUID campaignId,
            String sourceType,
            String sourceReference,
            boolean notifyLearners,
            int requestedRecipients,
            int uniqueRecipients,
            int duplicateRecipients,
            String previewHash,
            List<CouponDistributionPreviewRecipientDto> sampleRecipients
    ) {
    }

    public record CreateCouponDistributionRequestDto(
            @NotNull UUID campaignId,
            @NotBlank String name,
            @NotBlank String sourceType,
            String sourceReference,
            Boolean notifyLearners,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Map<String, Object> metadata,
            @NotBlank String previewHash,
            String reason,
            @NotEmpty @Valid List<CouponDistributionRecipientInputDto> recipients
    ) {
    }

    public record CouponDistributionActionRequestDto(
            String reason
    ) {
    }

    public record CouponDistributionRecipientDto(
            UUID id,
            UUID distributionId,
            String profileId,
            String status,
            UUID couponId,
            String notificationStatus,
            String failureReason,
            Map<String, Object> metadata,
            Instant createdAt,
            Instant issuedAt,
            Instant revokedAt
    ) {
    }

    public record CouponDistributionDto(
            UUID id,
            String tenantId,
            String applicationId,
            UUID campaignId,
            String name,
            String sourceType,
            String sourceReference,
            String status,
            boolean notifyLearners,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            int recipientCount,
            int issuedCount,
            int revokedCount,
            String previewHash,
            String reason,
            Map<String, Object> metadata,
            String createdBy,
            String approvedBy,
            String issuedBy,
            String revokedBy,
            Instant createdAt,
            Instant approvedAt,
            Instant issuedAt,
            Instant revokedAt,
            Instant updatedAt,
            List<CouponDistributionRecipientDto> recipients
    ) {
    }

    public record CouponDistributionQueryResponseDto(
            List<CouponDistributionDto> items,
            int limit
    ) {
    }

    public record CouponImportDryRunRequestDto(
            @NotNull UUID campaignId,
            @NotBlank String csvContent,
            Integer maxRows,
            String holderProfileId,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Map<String, Object> metadata,
            String idempotencyKey
    ) {
    }

    public record CouponImportDryRunIssueDto(
            int rowNumber,
            String codeMask,
            String field,
            String reasonCode,
            String message
    ) {
    }

    public record CouponImportDryRunRowDto(
            int rowNumber,
            String codeMask,
            String status,
            List<String> issueCodes
    ) {
    }

    public record CouponImportDryRunResponseDto(
            UUID dryRunId,
            UUID campaignId,
            boolean dryRun,
            int requestedRows,
            int validRows,
            int invalidRows,
            int duplicateInFileRows,
            int duplicateExistingRows,
            boolean storageInventoryReady,
            boolean commitReady,
            String resultHash,
            Instant generatedAt,
            List<String> warnings,
            List<CouponImportDryRunIssueDto> issues,
            List<CouponImportDryRunRowDto> sampleRows
    ) {
    }

    public record CouponImportDryRunListItemDto(
            UUID dryRunId,
            String tenantId,
            String applicationId,
            UUID campaignId,
            String status,
            int requestedRows,
            int validRows,
            int invalidRows,
            int duplicateInFileRows,
            int duplicateExistingRows,
            boolean storageInventoryReady,
            boolean commitReady,
            String resultHash,
            String createdBy,
            String correlationId,
            String sourceClientId,
            Instant createdAt,
            Instant expiresAt,
            Instant committedAt,
            String committedBy,
            UUID committedOperationId,
            int committedRows,
            String failureReason
    ) {
    }

    public record CouponImportDryRunQueryResponseDto(
            List<CouponImportDryRunListItemDto> items,
            int limit,
            boolean hasMore,
            Instant generatedAt
    ) {
    }

    public record CouponImportCommitRequestDto(
            UUID approvalId,
            UUID dryRunId,
            UUID campaignId,
            @NotBlank String csvContent,
            Integer maxRows,
            String holderProfileId,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Map<String, Object> metadata,
            String reason,
            String changeTicket,
            @NotBlank String approvedResultHash,
            @NotBlank String idempotencyKey,
            boolean confirm
    ) {
    }

    public record CouponImportCommitResponseDto(
            UUID importId,
            UUID approvalId,
            UUID dryRunId,
            UUID campaignId,
            String status,
            int requestedRows,
            int importedRows,
            String resultHash,
            boolean idempotencyReplay,
            Instant committedAt,
            List<String> warnings
    ) {
    }

    public record CouponImportOperationDto(
            UUID importId,
            UUID approvalId,
            UUID dryRunId,
            String tenantId,
            String applicationId,
            UUID campaignId,
            String status,
            int requestedRows,
            int importedRows,
            String resultHash,
            String reason,
            String changeTicket,
            String createdBy,
            String correlationId,
            String sourceClientId,
            Instant createdAt
    ) {
    }

    public record CouponImportOperationQueryResponseDto(
            List<CouponImportOperationDto> items,
            int limit,
            boolean hasMore,
            Instant generatedAt
    ) {
    }

    public record CouponImportOperationExportDto(
            UUID importId,
            UUID approvalId,
            UUID dryRunId,
            UUID campaignId,
            String tenantId,
            String applicationId,
            String filename,
            String contentType,
            String content,
            Instant generatedAt
    ) {
    }

    public record CouponImportIssueExportDto(
            UUID dryRunId,
            UUID campaignId,
            String tenantId,
            String applicationId,
            String rowStatus,
            int rowCount,
            String filename,
            String contentType,
            String content,
            Instant generatedAt
    ) {
    }

    public record CouponImportApprovalDecisionRequestDto(
            String note
    ) {
    }

    public record CouponImportApprovalResponseDto(
            UUID approvalId,
            String status,
            UUID dryRunId,
            UUID campaignId,
            String approvedResultHash,
            int requestedRows,
            int validRows,
            int invalidRows,
            int duplicateInFileRows,
            int duplicateExistingRows,
            boolean storageInventoryReady,
            boolean commitReady,
            String reason,
            String changeTicket,
            String requestedBy,
            String approvedBy,
            String rejectedBy,
            String committedBy,
            Instant expiresAt,
            Instant createdAt,
            Instant approvedAt,
            Instant rejectedAt,
            Instant committedAt
    ) {
    }

    public record RedemptionReversalApprovalRequestDto(
            @NotBlank String idempotencyKey,
            @NotBlank String reason,
            @NotBlank String changeTicket,
            Map<String, Object> metadata
    ) {
    }

    public record RedemptionReversalApprovalDecisionRequestDto(
            String note
    ) {
    }

    public record RedemptionReversalApprovalResponseDto(
            UUID approvalId,
            String status,
            UUID redemptionId,
            UUID reservationId,
            String tenantId,
            String applicationId,
            UUID campaignId,
            Integer campaignVersion,
            UUID couponId,
            String profileId,
            String externalReference,
            String idempotencyKey,
            String requestHash,
            String resultHash,
            String subjectHash,
            String reason,
            String changeTicket,
            String requestedBy,
            String approvedBy,
            String rejectedBy,
            String executedBy,
            Instant expiresAt,
            Instant createdAt,
            Instant approvedAt,
            Instant rejectedAt,
            Instant executedAt,
            Map<String, Object> subject
    ) {
    }

    public record RetentionPolicyDto(
            String policyId,
            String policyVersion,
            String targetDataset,
            String actionType,
            int defaultRetentionDays,
            int minimumRetentionDays,
            int defaultBatchLimit,
            boolean destructiveExecutionSupported,
            List<String> scopeTypes,
            String eligibleWhen,
            List<String> blockerRules
    ) {
    }

    public record RetentionPolicyRegistryDto(
            List<RetentionPolicyDto> policies
    ) {
    }

    public record RetentionDryRunRequestDto(
            String tenantId,
            String applicationId,
            List<String> policyIds,
            Instant asOf,
            Map<String, Integer> retentionDaysOverride,
            Integer batchLimit,
            String reason
    ) {
    }

    public record RetentionDryRunResultDto(
            String policyId,
            String policyVersion,
            String targetDataset,
            String actionType,
            Instant cutoff,
            int retentionDays,
            long eligibleCount,
            long blockedCount,
            String blockedReason,
            Instant oldestCandidateAt,
            Instant newestCandidateAt,
            int batchLimit,
            boolean destructiveExecutionSupported,
            String resultHash
    ) {
    }

    public record RetentionDryRunResponseDto(
            UUID dryRunId,
            String resultHash,
            boolean dryRun,
            boolean nonDestructive,
            String tenantId,
            String applicationId,
            Instant generatedAt,
            List<RetentionDryRunResultDto> results,
            List<String> warnings
    ) {
    }

    public record RetentionRestoreDrillRequestDto(
            String restoreDrillRef,
            String databaseName,
            String backupPath,
            String artifactHash,
            String status,
            Instant checkedAt,
            Instant expiresAt,
            String note
    ) {
    }

    public record RetentionRestoreDrillResponseDto(
            UUID id,
            String restoreDrillRef,
            String databaseName,
            String backupPath,
            String artifactHash,
            String status,
            Instant checkedAt,
            Instant expiresAt,
            String createdBy,
            Instant createdAt
    ) {
    }

    public record RetentionApprovalRequestDto(
            String tenantId,
            String applicationId,
            String policyId,
            Instant asOf,
            Map<String, Integer> retentionDaysOverride,
            Integer batchLimit,
            UUID approvedDryRunId,
            String approvedResultHash,
            String reason,
            String changeTicket,
            String restoreDrillRef
    ) {
    }

    public record RetentionApprovalDecisionRequestDto(
            String note
    ) {
    }

    public record RetentionApprovalResponseDto(
            UUID approvalId,
            String status,
            String policyId,
            String policyVersion,
            String targetDataset,
            String tenantId,
            String applicationId,
            Instant asOf,
            Instant cutoff,
            int retentionDays,
            UUID dryRunId,
            String approvedResultHash,
            long eligibleCount,
            int batchLimit,
            String restoreDrillRef,
            String changeTicket,
            String reason,
            String note,
            String requestedBy,
            String approvedBy,
            String rejectedBy,
            String executedBy,
            String correlationId,
            String sourceClientId,
            Instant expiresAt,
            Instant createdAt,
            Instant approvedAt,
            Instant rejectedAt,
            Instant failedAt,
            Instant executedAt
    ) {
    }

    public record RetentionApprovalQueryResponseDto(
            List<RetentionApprovalResponseDto> items,
            int limit,
            boolean hasMore,
            Instant generatedAt
    ) {
    }

    public record RetentionRestoreDrillEvidenceDto(
            UUID id,
            String restoreDrillRef,
            String databaseName,
            String backupPath,
            String artifactHash,
            String status,
            Instant checkedAt,
            Instant expiresAt,
            String createdBy,
            String note,
            String correlationId,
            String sourceClientId,
            Instant createdAt
    ) {
    }

    public record RetentionExecutionEvidenceDto(
            UUID executionId,
            UUID approvalId,
            String status,
            String policyId,
            String policyVersion,
            String targetDataset,
            String tenantId,
            String applicationId,
            UUID dryRunId,
            String approvedResultHash,
            Instant cutoff,
            long expectedEligibleCount,
            long redactedCount,
            int batchLimit,
            Boolean hasMore,
            String idempotencyKeyHash,
            String changeTicket,
            String restoreDrillRef,
            String approvedBy,
            String executedBy,
            String correlationId,
            String lastError,
            Instant createdAt,
            Instant startedAt,
            Instant completedAt
    ) {
    }

    public record RetentionAuditEvidenceEventDto(
            UUID eventId,
            String action,
            String aggregateType,
            String aggregateId,
            String actorId,
            String note,
            String correlationId,
            String sourceClientId,
            Instant createdAt,
            Map<String, Object> payloadSummary
    ) {
    }

    public record RetentionEvidencePackDto(
            String schemaVersion,
            String artifactType,
            UUID approvalId,
            Instant generatedAt,
            RetentionApprovalResponseDto approval,
            RetentionRestoreDrillEvidenceDto restoreDrill,
            RetentionExecutionEvidenceDto execution,
            List<RetentionAuditEvidenceEventDto> auditTrail,
            List<String> warnings
    ) {
    }

    public record RetentionEvidencePackExportDto(
            UUID approvalId,
            String filename,
            String contentType,
            String content,
            String contentSha256,
            Instant generatedAt
    ) {
    }

    public record RetentionExecutionRequestDto(
            UUID approvalId,
            String tenantId,
            String applicationId,
            String policyId,
            Instant asOf,
            Map<String, Integer> retentionDaysOverride,
            Integer batchLimit,
            UUID approvedDryRunId,
            String approvedResultHash,
            String idempotencyKey,
            String reason,
            String changeTicket,
            String restoreDrillRef,
            Boolean confirm
    ) {
    }

    public record RetentionExecutionResponseDto(
            UUID executionId,
            String status,
            String policyId,
            String policyVersion,
            String targetDataset,
            String tenantId,
            String applicationId,
            Instant cutoff,
            UUID dryRunId,
            String approvedResultHash,
            long eligibleBefore,
            long redactedCount,
            int batchLimit,
            boolean hasMore,
            boolean idempotencyReplay,
            Instant executedAt
    ) {
    }

    public record RedemptionDto(
            UUID id,
            UUID reservationId,
            String tenantId,
            String applicationId,
            UUID campaignId,
            Integer campaignVersion,
            UUID couponId,
            String profileId,
            String externalReference,
            String status,
            List<IncentiveEffectDto> effects,
            Instant redeemedAt,
            Instant reversedAt
    ) {
    }

    public record ReservationQuotaSnapshotDto(
            String scopeType,
            String scopeId,
            String profileId,
            int limit
    ) {
    }

    public record ReservationDto(
            UUID id,
            String tenantId,
            String applicationId,
            UUID campaignId,
            Integer campaignVersion,
            UUID couponId,
            String profileId,
            String externalReference,
            String status,
            List<IncentiveEffectDto> effects,
            List<ReservationQuotaSnapshotDto> quotaSnapshot,
            String requestHash,
            Instant reservedAt,
            Instant expiresAt,
            Instant committedAt,
            Instant cancelledAt,
            String failureReason,
            boolean expired
    ) {
    }

    public record IncentiveReconciliationEffectDto(
            String effectId,
            String type,
            String benefitType,
            String actionType,
            String targetType,
            String targetId,
            BigDecimal amount,
            String currency,
            String unit,
            BigDecimal quantity,
            Integer campaignVersion,
            Map<String, Object> metadata
    ) {
    }

    public record IncentiveReconciliationEntryDto(
            UUID ledgerEntryId,
            String reconciliationKey,
            String reconciliationStatus,
            List<String> reasonCodes,
            String direction,
            String entryType,
            UUID redemptionId,
            UUID reservationId,
            String tenantId,
            String applicationId,
            UUID campaignId,
            Integer campaignVersion,
            UUID couponId,
            String profileId,
            String externalReference,
            String redemptionStatus,
            String quotaPolicy,
            Boolean quotaReleased,
            String outboxStatus,
            String outboxEventType,
            Instant outboxPublishedAt,
            String correlationId,
            String sourceClientId,
            Instant ledgerCreatedAt,
            Instant redeemedAt,
            Instant reversedAt,
            IncentiveReconciliationEffectDto effect
    ) {
    }

    public record IncentiveReconciliationQueryResponseDto(
            List<IncentiveReconciliationEntryDto> items,
            int limit,
            boolean hasMore,
            Instant generatedAt
    ) {
    }

    public record CreateCampaignRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String code,
            @NotBlank String name,
            String description,
            String incentiveType,
            Instant startsAt,
            Instant endsAt,
            Integer priority,
            Boolean exclusive,
            Boolean stackable,
            Boolean couponRequired,
            String matchPolicy,
            String currency,
            @Valid List<RuleSpecDto> rules,
            @NotEmpty @Valid List<ActionSpecDto> actions,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile
    ) {
    }

    public record CreateApplicationRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String name,
            String status,
            List<String> allowedClientIds
    ) {
    }

    public record UpdateApplicationRequestDto(
            String name,
            List<String> allowedClientIds
    ) {
    }

    public record UpdateApplicationStatusRequestDto(
            @NotBlank String status,
            String note
    ) {
    }

    public record CreateApplicationClientBindingRequestDto(
            @NotBlank String clientId,
            String status,
            List<String> allowedOperations
    ) {
    }

    public record UpdateCampaignStatusRequestDto(
            @NotBlank String status,
            String note
    ) {
    }

    public record CampaignVersionTransitionRequestDto(
            String note
    ) {
    }

    public record CreateCouponRequestDto(
            @NotNull UUID campaignId,
            @NotBlank String code,
            String holderProfileId,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Map<String, Object> metadata
    ) {
    }

    public record UpdateCouponStatusRequestDto(
            @NotBlank String status,
            String reason
    ) {
    }

    public record GenerateCouponsRequestDto(
            @NotNull UUID campaignId,
            String prefix,
            @Min(1) int quantity,
            Integer codeLength,
            String holderProfileId,
            Instant startsAt,
            Instant expiresAt,
            Integer maxRedemptions,
            Integer maxRedemptionsPerProfile,
            Map<String, Object> metadata
    ) {
    }

    public record GenerateCouponsResponseDto(
            UUID campaignId,
            int requested,
            int created,
            int duplicateRetries,
            List<CouponDto> coupons
    ) {
    }

    public record EvaluateIncentivesRequestDto(
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            @NotBlank String profileId,
            String externalReference,
            String channel,
            @NotBlank String currency,
            List<String> couponCodes,
            List<UUID> couponIds,
            @NotNull @Valid TransactionContextDto transaction,
            @Valid List<IncentiveItemDto> items,
            Map<String, Object> attributes
    ) {
        public EvaluateIncentivesRequestDto(
                String tenantId,
                String applicationId,
                String profileId,
                String externalReference,
                String channel,
                String currency,
                List<String> couponCodes,
                TransactionContextDto transaction,
                List<IncentiveItemDto> items,
                Map<String, Object> attributes) {
            this(
                    tenantId,
                    applicationId,
                    profileId,
                    externalReference,
                    channel,
                    currency,
                    couponCodes,
                    List.of(),
                    transaction,
                    items,
                    attributes);
        }
    }

    public record EvaluateIncentivesResponseDto(
            boolean eligible,
            UUID campaignId,
            Integer campaignVersion,
            String campaignCode,
            UUID couponId,
            List<IncentiveEffectDto> effects,
            List<String> reasonCodes
    ) {
    }

    public record AdminPreviewIncentivesRequestDto(
            @NotNull @Valid EvaluateIncentivesRequestDto context,
            String note
    ) {
    }

    public record AdminSimulationTotalsDto(
            BigDecimal subtotal,
            BigDecimal totalDiscount,
            BigDecimal finalAmount,
            String currency,
            BigDecimal totalPoints
    ) {
    }

    public record AdminSimulationQuotaExposureDto(
            String scopeType,
            String scopeId,
            String profileId,
            int limit,
            int used,
            int remaining,
            boolean available,
            boolean wouldConsume
    ) {
    }

    public record AdminSimulationCandidateDto(
            UUID campaignId,
            Integer campaignVersion,
            String campaignCode,
            UUID couponId,
            boolean matched,
            boolean selected,
            boolean exclusive,
            boolean stackable,
            String stackingStatus,
            List<String> stackingReasonCodes,
            List<IncentiveEffectDto> effects,
            List<String> reasonCodes,
            List<AdminSimulationQuotaExposureDto> quotaExposure
    ) {
    }

    public record AdminPreviewIncentivesResponseDto(
            boolean preview,
            boolean ledgerImpact,
            String contextHash,
            EvaluateIncentivesResponseDto decision,
            UUID winningCampaignId,
            Integer winningCampaignVersion,
            String winningCampaignCode,
            UUID couponId,
            AdminSimulationTotalsDto totals,
            List<AdminSimulationQuotaExposureDto> quotaExposure,
            List<AdminSimulationCandidateDto> candidates,
            Instant generatedAt
    ) {
        public AdminPreviewIncentivesResponseDto(
                boolean preview,
                boolean ledgerImpact,
                String contextHash,
                EvaluateIncentivesResponseDto decision) {
            this(
                    preview,
                    ledgerImpact,
                    contextHash,
                    decision,
                    decision == null ? null : decision.campaignId(),
                    decision == null ? null : decision.campaignVersion(),
                    decision == null ? null : decision.campaignCode(),
                    decision == null ? null : decision.couponId(),
                    null,
                    List.of(),
                    List.of(),
                    Instant.now());
        }
    }

    public record ExperimentVariantPreviewRequestDto(
            @NotBlank String key,
            @Min(0) Integer weightBps,
            Boolean holdout,
            String campaignCode,
            Map<String, Object> metadata
    ) {
    }

    public record ExperimentPreviewRequestDto(
            @NotNull @Valid EvaluateIncentivesRequestDto context,
            @NotBlank String experimentKey,
            String assignmentUnit,
            String assignmentAttributeKey,
            @NotEmpty @Valid List<ExperimentVariantPreviewRequestDto> variants,
            String note
    ) {
    }

    public record ExperimentVariantAllocationDto(
            String key,
            int weightBps,
            boolean holdout,
            String campaignCode,
            int startBucketInclusive,
            int endBucketExclusive,
            boolean selected,
            Map<String, Object> metadata
    ) {
    }

    public record ExperimentPreviewResponseDto(
            boolean preview,
            boolean ledgerImpact,
            String policyVersion,
            String tenantId,
            String applicationId,
            String experimentKey,
            String assignmentUnit,
            String assignmentKeyHash,
            int bucket,
            String selectedVariantKey,
            boolean holdout,
            String recommendedAction,
            List<String> reasonCodes,
            List<ExperimentVariantAllocationDto> variants,
            Instant generatedAt
    ) {
    }

    public record FraudScorePreviewRequestDto(
            @NotNull @Valid EvaluateIncentivesRequestDto context,
            Integer lookbackMinutes,
            String sourceClientId,
            String note
    ) {
    }

    public record FraudScoreSignalDto(
            String code,
            String severity,
            int points,
            String message,
            Map<String, Object> evidence
    ) {
    }

    public record FraudScorePreviewResponseDto(
            boolean preview,
            boolean ledgerImpact,
            String policyVersion,
            String tenantId,
            String applicationId,
            String profileId,
            int lookbackMinutes,
            int score,
            String severity,
            String recommendedAction,
            List<FraudScoreSignalDto> signals,
            Instant generatedAt
    ) {
    }

    public record ReserveIncentiveRequestDto(
            String idempotencyKey,
            @Valid @NotNull EvaluateIncentivesRequestDto context
    ) {
    }

    public record ReserveIncentiveResponseDto(
            boolean reserved,
            UUID reservationId,
            UUID campaignId,
            Integer campaignVersion,
            UUID couponId,
            Instant expiresAt,
            List<IncentiveEffectDto> effects,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }

    public record CommitReservationRequestDto(
            String idempotencyKey,
            String externalReference
    ) {
    }

    public record CommitReservationResponseDto(
            boolean committed,
            UUID reservationId,
            UUID redemptionId,
            UUID campaignId,
            Integer campaignVersion,
            String status,
            List<IncentiveEffectDto> effects,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }

    public record CancelReservationRequestDto(
            String idempotencyKey,
            String reason
    ) {
    }

    public record CancelReservationResponseDto(
            boolean cancelled,
            UUID reservationId,
            String status,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }

    public record ReverseRedemptionRequestDto(
            String idempotencyKey,
            @NotBlank String reason,
            UUID approvalId,
            String changeTicket
    ) {
        public ReverseRedemptionRequestDto(String idempotencyKey, String reason) {
            this(idempotencyKey, reason, null, null);
        }

        public ReverseRedemptionRequestDto(String idempotencyKey, String reason, UUID approvalId) {
            this(idempotencyKey, reason, approvalId, null);
        }
    }

    public record ReverseRedemptionResponseDto(
            boolean reversed,
            UUID redemptionId,
            String status,
            List<IncentiveEffectDto> effects,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }
}
