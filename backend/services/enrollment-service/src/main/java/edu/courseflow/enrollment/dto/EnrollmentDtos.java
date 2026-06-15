package edu.courseflow.enrollment.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

public final class EnrollmentDtos {

    private EnrollmentDtos() {
    }

    public record EnrollmentDto(
            String id,
            String studentId,
            String courseId,
            String sectionId,
            String status,
            Instant enrolledAt,
            Instant droppedAt,
            Instant completedAt,
            String dropReason
    ) {
    }

    public record WaitlistEntryDto(
            String id,
            String studentId,
            String courseId,
            int position,
            String status,
            Instant createdAt
    ) {
    }

    /**
     * {@code studentId} is optional and only honored for INSTRUCTOR/ADMIN callers enrolling someone
     * else. A STUDENT caller always enrolls themselves; the field is taken from the gateway identity.
     */
    public record EnrollRequestDto(
            String studentId,
            @NotBlank String courseId,
            String couponCode,
            String couponId,
            String promotionPreviewId,
            String idempotencyKey
    ) {
        public EnrollRequestDto(String studentId, String courseId) {
            this(studentId, courseId, null, null, null, null);
        }
    }

    public record PromotionPreviewRequestDto(
            @NotBlank String courseId,
            String couponCode,
            String couponId
    ) {
    }

    public record PromotionEffectDto(
            String type,
            String benefitType,
            String actionType,
            String targetType,
            String targetId,
            BigDecimal amount,
            String currency,
            String unit,
            BigDecimal quantity,
            Map<String, Object> metadata
    ) {
    }

    public record PromotionPreviewDto(
            String previewId,
            String courseId,
            String couponCode,
            String couponId,
            String status,
            boolean eligible,
            List<String> reasonCodes,
            String message,
            BigDecimal originalAmount,
            BigDecimal discountAmount,
            BigDecimal finalAmount,
            String currency,
            String priceSource,
            List<PromotionEffectDto> effects,
            boolean promotionUnavailable
    ) {
    }

    public record EnrollmentPromotionApplicationDto(
            String status,
            String reservationId,
            String redemptionId,
            String couponCode,
            String couponId,
            List<String> reasonCodes,
            String message,
            List<PromotionEffectDto> effects
    ) {
    }

    public record EnrollmentPromotionApplicationStateDto(
            String id,
            String enrollmentId,
            String studentId,
            String courseId,
            String status,
            String couponCode,
            String couponId,
            String reservationId,
            String redemptionId,
            String idempotencyKey,
            List<String> reasonCodes,
            String message,
            List<PromotionEffectDto> effects,
            int retryCount,
            Instant nextRetryAt,
            String lastRetryError,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record EnrollmentOrderDto(
            String id,
            String enrollmentId,
            String checkoutAttemptId,
            String studentId,
            String courseId,
            String status,
            BigDecimal amount,
            String currency,
            String paymentProvider,
            String paymentReference,
            String failureReason,
            Instant paidAt,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record EnrollmentRemediationCaseDto(
            String id,
            String caseType,
            String status,
            String severity,
            String enrollmentId,
            String checkoutAttemptId,
            String promotionApplicationId,
            String orderId,
            String studentId,
            String courseId,
            String assigneeId,
            String note,
            String reasonCode,
            Instant slaDueAt,
            long slaAgeMinutes,
            boolean slaBreached,
            Instant createdAt,
            Instant updatedAt,
            Instant closedAt,
            List<EnrollmentRemediationCaseActionDto> actionHistory,
            List<EnrollmentRemediationCaseActionDto> retryHistory
    ) {
    }

    public record EnrollmentRemediationCaseActionDto(
            String id,
            String action,
            String actorId,
            String note,
            String fromStatus,
            String toStatus,
            Map<String, Object> payload,
            Instant createdAt
    ) {
    }

    public record PromotionApplicationActionRequestDto(
            String reason,
            String correlationId
    ) {
    }

    public record PaymentStatusUpdateRequestDto(
            @NotBlank String paymentStatus,
            String paymentProvider,
            String paymentReference,
            BigDecimal paidAmount,
            String currency,
            String note,
            String correlationId
    ) {
    }

    public record RemediationCaseActionRequestDto(
            String note,
            String correlationId
    ) {
    }

    public record RemediationCaseAssignRequestDto(
            @NotBlank String assigneeId,
            String note,
            String correlationId
    ) {
    }

    public record EnrollmentCheckoutResponseDto(
            EnrollmentDto enrollment,
            EnrollmentPromotionApplicationDto promotion,
            String attemptId,
            EnrollmentOrderDto order
    ) {
        public EnrollmentCheckoutResponseDto(EnrollmentDto enrollment, EnrollmentPromotionApplicationDto promotion) {
            this(enrollment, promotion, null, null);
        }

        public EnrollmentCheckoutResponseDto(
                EnrollmentDto enrollment,
                EnrollmentPromotionApplicationDto promotion,
                String attemptId) {
            this(enrollment, promotion, attemptId, null);
        }
    }

    public record EnrollmentBenefitReconciliationEntryDto(
            String reconciliationKey,
            String reconciliationStatus,
            List<String> reasonCodes,
            String severity,
            String enrollmentId,
            String studentId,
            String courseId,
            String enrollmentStatus,
            Instant enrolledAt,
            Instant droppedAt,
            String dropReason,
            String orderId,
            String orderStatus,
            BigDecimal orderAmount,
            String currency,
            Instant paidAt,
            Instant orderCreatedAt,
            Instant orderUpdatedAt,
            String promotionApplicationId,
            String promotionStatus,
            String reservationId,
            String redemptionId,
            int promotionRetryCount,
            Instant promotionNextRetryAt,
            String promotionLastRetryError,
            Instant promotionUpdatedAt
    ) {
    }

    public record EnrollmentBenefitReconciliationQueryResponseDto(
            List<EnrollmentBenefitReconciliationEntryDto> items,
            int limit,
            boolean hasMore,
            Instant generatedAt
    ) {
    }

    public record RefundDropPolicyEvaluateRequestDto(
            @NotBlank String enrollmentId,
            String reason,
            Instant requestedAt,
            Integer refundWindowDays,
            String paymentStatus,
            BigDecimal paidAmount,
            String currency,
            Instant paidAt,
            String promotionStatus,
            String reservationId,
            String redemptionId,
            Long loyaltyPointsEarned,
            Long loyaltyPointsReversed,
            String loyaltyEarnEntryId,
            String rewardStatus,
            String rewardRedemptionId,
            String rewardFulfillmentStatus,
            Boolean rewardFulfilled,
            Map<String, Object> evidence
    ) {
    }

    public record RefundDropPolicyFactsDto(
            String enrollmentStatus,
            Instant enrolledAt,
            Instant droppedAt,
            Instant completedAt,
            String dropReason,
            String orderId,
            String paymentStatus,
            BigDecimal paidAmount,
            String currency,
            Instant paidAt,
            int refundWindowDays,
            Instant refundWindowEndsAt,
            boolean withinRefundWindow,
            String promotionApplicationId,
            String promotionStatus,
            String reservationId,
            String redemptionId,
            long loyaltyPointsEarned,
            long loyaltyPointsReversed,
            long loyaltyPointsOutstanding,
            String loyaltyEarnEntryId,
            String rewardStatus,
            String rewardRedemptionId,
            String rewardFulfillmentStatus,
            Boolean rewardFulfilled
    ) {
    }

    public record RefundDropPolicyActionDto(
            String domain,
            String action,
            String decision,
            String severity,
            boolean required,
            boolean blocking,
            boolean makerCheckerRequired,
            String endpoint,
            String idempotencyKey,
            List<String> reasonCodes,
            Map<String, Object> evidence
    ) {
    }

    public record RefundDropPolicyEvaluationResponseDto(
            String enrollmentId,
            String studentId,
            String courseId,
            String matrixStatus,
            String severity,
            boolean dropAllowed,
            boolean refundEligible,
            boolean manualReviewRequired,
            List<String> reasonCodes,
            RefundDropPolicyFactsDto facts,
            List<RefundDropPolicyActionDto> actions,
            Map<String, Object> auditPreview,
            Instant generatedAt
    ) {
    }

    public record LearnerCouponDto(
            String couponId,
            String campaignId,
            String campaignCode,
            String campaignName,
            String codeMask,
            String status,
            String walletStatus,
            Instant startsAt,
            Instant expiresAt,
            String redemptionId,
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

    /**
     * {@code studentId} is optional and only honored for INSTRUCTOR/ADMIN callers acting on someone
     * else. A STUDENT caller always acts on themselves.
     */
    public record WaitlistRequestDto(
            String studentId,
            @NotBlank String courseId
    ) {
    }

    /** The actor is taken from the gateway identity, never from the body. */
    public record ChangeStatusRequestDto(
            @NotBlank String newStatus,
            String reason
    ) {
    }

    public record SetCapacityRequestDto(
            Integer capacity
    ) {
    }

    public record BatchEnrollRequestDto(
            @NotNull @NotEmpty List<@Valid SingleEnrollDto> entries
    ) {
        public record SingleEnrollDto(
                @NotBlank String studentId,
                @NotBlank String courseId,
                String sectionId
        ) {
        }
    }

    public record BatchEnrollResultDto(
            int enrolled,
            int skipped,
            List<String> errors
    ) {
    }

    public record EnrollmentStatsDto(
            String courseId,
            int totalActive,
            int totalDropped,
            int totalCompleted,
            int waitlistCount
    ) {
    }

    public record CourseAccessDto(
            String courseId,
            String studentId,
            boolean enrolled,
            String status
    ) {
    }

    public record AuditLogEntryDto(
            String id,
            String enrollmentId,
            String actorId,
            String action,
            String oldStatus,
            String newStatus,
            String reason,
            Instant createdAt
    ) {
    }
}
