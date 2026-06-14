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

    public record PromotionApplicationActionRequestDto(
            String reason,
            String correlationId
    ) {
    }

    public record EnrollmentCheckoutResponseDto(
            EnrollmentDto enrollment,
            EnrollmentPromotionApplicationDto promotion,
            String attemptId
    ) {
        public EnrollmentCheckoutResponseDto(EnrollmentDto enrollment, EnrollmentPromotionApplicationDto promotion) {
            this(enrollment, promotion, null);
        }
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
