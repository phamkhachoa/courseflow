package edu.courseflow.enrollment.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.enrollment.dto.EnrollmentDtos.AuditLogEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollResultDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.ChangeStatusRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.CourseAccessDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentBenefitReconciliationEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentBenefitReconciliationQueryResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentCheckoutResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentOrderDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentPromotionApplicationDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentPromotionApplicationStateDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentRemediationCaseActionDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentRemediationCaseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentStatsDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.LearnerCouponWalletDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PaymentStatusUpdateRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionApplicationActionRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionEffectDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionPreviewDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionPreviewRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RemediationCaseActionRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RemediationCaseAssignRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyActionDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyEvaluateRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyEvaluationResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyFactsDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.SetCapacityRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistRequestDto;
import edu.courseflow.enrollment.exception.ForbiddenException;
import edu.courseflow.enrollment.model.EnrollmentCheckoutAttempt;
import edu.courseflow.enrollment.model.EnrollmentOrder;
import edu.courseflow.enrollment.model.EnrollmentPromotionApplication;
import edu.courseflow.enrollment.model.EnrollmentRemediationCase;
import edu.courseflow.enrollment.model.EnrollmentRemediationCaseAction;
import edu.courseflow.enrollment.repository.EnrollmentRepository;
import edu.courseflow.enrollment.repository.EnrollmentCheckoutAttemptJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentOrderJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentPromotionApplicationJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentRemediationCaseActionJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentRemediationCaseJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentJpaRepository.EnrollmentBenefitReconciliationRow;
import edu.courseflow.enrollment.service.CoursePricingClient.CoursePricingSnapshot;
import edu.courseflow.enrollment.service.CoursePricingClient.CoursePricingUnavailableException;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.CancelResult;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.CommitResult;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.PromotionUnavailableException;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.ReservationResult;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.ReverseResult;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class EnrollmentService {

    /**
     * Allowed enrollment status transitions.
     * <ul>
     *   <li>PENDING_PAYMENT -> ACTIVE, DROPPED</li>
     *   <li>ACTIVE          -> DROPPED, COMPLETED</li>
     *   <li>DROPPED         -> ACTIVE (re-enroll)</li>
     *   <li>COMPLETED -> (terminal: no transitions)</li>
     * </ul>
     * A no-op transition to the same status is rejected as a bad request.
     */
    private static final Map<String, Set<String>> ALLOWED_TRANSITIONS = Map.of(
            "PENDING_PAYMENT", Set.of("ACTIVE", "DROPPED"),
            "ACTIVE", Set.of("DROPPED", "COMPLETED"),
            "DROPPED", Set.of("ACTIVE"),
            "COMPLETED", Set.of());
    private static final TypeReference<List<String>> STRING_LIST = new TypeReference<>() {
    };
    private static final TypeReference<List<PromotionEffectDto>> PROMOTION_EFFECT_LIST = new TypeReference<>() {
    };
    private static final TypeReference<Map<String, Object>> OBJECT_MAP = new TypeReference<>() {
    };
    private static final BigDecimal ZERO_MONEY = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
    private static final String DEFAULT_REMEDIATION_ASSIGNEE = "enrollment-ops";
    private static final Duration REMEDIATION_SLA = Duration.ofHours(24);
    private static final Duration RESERVED_REMEDIATION_AGE = Duration.ofHours(24);
    private static final Duration BENEFIT_RECONCILIATION_STALE_AGE = Duration.ofMinutes(30);
    private static final int DEFAULT_RECONCILIATION_LIMIT = 50;
    private static final int MAX_RECONCILIATION_LIMIT = 200;

    private final EnrollmentRepository enrollments;
    private final EnrollmentCheckoutAttemptJpaRepository checkoutAttempts;
    private final EnrollmentPromotionApplicationJpaRepository promotionApplications;
    private final EnrollmentOrderJpaRepository orders;
    private final EnrollmentRemediationCaseJpaRepository remediationCases;
    private final EnrollmentRemediationCaseActionJpaRepository remediationActions;
    private final ObjectMapper objectMapper;
    private final CourseAccessClient courseAccess;
    private final PromotionEnrollmentClient promotions;
    private final CoursePricingClient coursePricing;

    public EnrollmentService(EnrollmentRepository enrollments, ObjectMapper objectMapper, CourseAccessClient courseAccess) {
        this(enrollments, null, null, null, null, null, objectMapper, courseAccess, null, null);
    }

    public EnrollmentService(EnrollmentRepository enrollments,
                             EnrollmentPromotionApplicationJpaRepository promotionApplications,
                             ObjectMapper objectMapper,
                             CourseAccessClient courseAccess,
                             PromotionEnrollmentClient promotions) {
        this(enrollments, null, promotionApplications, null, null, null, objectMapper, courseAccess, promotions, null);
    }

    @Autowired
    public EnrollmentService(EnrollmentRepository enrollments,
                             EnrollmentCheckoutAttemptJpaRepository checkoutAttempts,
                             EnrollmentPromotionApplicationJpaRepository promotionApplications,
                             EnrollmentOrderJpaRepository orders,
                             EnrollmentRemediationCaseJpaRepository remediationCases,
                             EnrollmentRemediationCaseActionJpaRepository remediationActions,
                             ObjectMapper objectMapper,
                             CourseAccessClient courseAccess,
                             PromotionEnrollmentClient promotions,
                             CoursePricingClient coursePricing) {
        this.enrollments = enrollments;
        this.checkoutAttempts = checkoutAttempts;
        this.promotionApplications = promotionApplications;
        this.orders = orders;
        this.remediationCases = remediationCases;
        this.remediationActions = remediationActions;
        this.objectMapper = objectMapper;
        this.courseAccess = courseAccess;
        this.promotions = promotions;
        this.coursePricing = coursePricing;
    }

    public List<EnrollmentDto> list(Optional<UUID> courseId, Optional<String> studentId, CurrentUser user) {
        if (isPlatformAdmin(user)) {
            return enrollments.list(courseId.orElse(null), studentId.orElse(null));
        }
        if (isStaff(user)) {
            UUID scopedCourse = courseId.orElseThrow(() ->
                    new ForbiddenException("Staff roster reads must be scoped to a course"));
            courseAccess.requireCourseStaffAccess(user, scopedCourse);
            return enrollments.list(scopedCourse, studentId.orElse(null));
        }
        String caller = callerId(user);
        if (studentId.isPresent() && !studentId.get().equals(caller)) {
            throw new ForbiddenException("Students may only read their own enrollment");
        }
        return enrollments.list(courseId.orElse(null), caller);
    }

    @Transactional(readOnly = true)
    public EnrollmentBenefitReconciliationQueryResponseDto benefitReconciliation(
            Optional<UUID> enrollmentId,
            Optional<UUID> courseId,
            Optional<String> studentId,
            Optional<String> status,
            Optional<Boolean> includeMatched,
            Optional<Integer> limit,
            CurrentUser user) {
        requireBenefitReconciliationAccess(courseId, user);
        String normalizedStudentId = studentId.map(this::normalizeText).orElse(null);
        String normalizedStatus = status.map(this::normalizeReconciliationStatus).orElse(null);
        int pageSize = Math.max(1, Math.min(limit.orElse(DEFAULT_RECONCILIATION_LIMIT), MAX_RECONCILIATION_LIMIT));
        int fetchSize = Math.min(1000, pageSize * 5 + 1);
        Instant staleCutoff = Instant.now().minus(BENEFIT_RECONCILIATION_STALE_AGE);
        boolean showMatched = includeMatched.orElse(false) || "MATCHED".equals(normalizedStatus);
        List<EnrollmentBenefitReconciliationEntryDto> items = enrollments
                .benefitReconciliationRows(enrollmentId.orElse(null), courseId.orElse(null), normalizedStudentId, fetchSize)
                .stream()
                .map(row -> reconciliationEntry(row, benefitFinding(row, staleCutoff)))
                .filter(entry -> normalizedStatus == null || normalizedStatus.equals(entry.reconciliationStatus()))
                .filter(entry -> showMatched || !"MATCHED".equals(entry.reconciliationStatus()))
                .limit(pageSize + 1L)
                .toList();
        boolean hasMore = items.size() > pageSize;
        return new EnrollmentBenefitReconciliationQueryResponseDto(
                items.stream().limit(pageSize).toList(),
                pageSize,
                hasMore,
                Instant.now());
    }

    @Transactional(readOnly = true)
    public RefundDropPolicyEvaluationResponseDto evaluateRefundDropPolicy(
            RefundDropPolicyEvaluateRequestDto request,
            CurrentUser user) {
        UUID enrollmentId = parseUuid(request.enrollmentId(), "enrollmentId");
        EnrollmentDto enrollment = enrollments.findById(enrollmentId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + enrollmentId));
        UUID courseId = parseUuid(enrollment.courseId(), "courseId");
        requireBenefitReconciliationAccess(Optional.of(courseId), user);

        EnrollmentOrder order = orders == null
                ? null
                : orders.findByEnrollmentId(enrollmentId).orElse(null);
        EnrollmentPromotionApplication application = promotionApplications == null
                ? null
                : promotionApplications.findByEnrollmentId(enrollmentId).orElse(null);

        Instant generatedAt = Instant.now();
        Instant requestedAt = request.requestedAt() == null ? generatedAt : request.requestedAt();
        int refundWindowDays = refundWindowDays(request.refundWindowDays());
        Instant paidAt = request.paidAt() != null
                ? request.paidAt()
                : order == null ? null : order.getPaidAt();
        Instant refundWindowEndsAt = paidAt == null
                ? null
                : paidAt.plus(Duration.ofDays(refundWindowDays));
        boolean withinRefundWindow = refundWindowEndsAt != null && !requestedAt.isAfter(refundWindowEndsAt);

        String paymentStatus = upper(firstText(
                request.paymentStatus(),
                order == null ? null : order.getStatus()));
        BigDecimal paidAmount = money(request.paidAmount() != null
                ? request.paidAmount()
                : order == null ? null : order.getAmount());
        String currency = upper(firstText(request.currency(), order == null ? null : order.getCurrency(), "USD"));
        String promotionStatus = upper(firstText(
                request.promotionStatus(),
                application == null ? null : application.getStatus(),
                "SKIPPED"));
        String reservationId = firstText(
                request.reservationId(),
                application == null || application.getReservationId() == null
                        ? null
                        : application.getReservationId().toString());
        String redemptionId = firstText(
                request.redemptionId(),
                application == null || application.getRedemptionId() == null
                        ? null
                        : application.getRedemptionId().toString());
        long loyaltyPointsEarned = nonNegative(request.loyaltyPointsEarned());
        long loyaltyPointsReversed = nonNegative(request.loyaltyPointsReversed());
        long loyaltyPointsOutstanding = Math.max(0, loyaltyPointsEarned - loyaltyPointsReversed);
        String loyaltyEarnEntryId = firstText(request.loyaltyEarnEntryId());
        String rewardStatus = upper(firstText(request.rewardStatus()));
        String rewardRedemptionId = firstText(request.rewardRedemptionId());
        String rewardFulfillmentStatus = upper(firstText(request.rewardFulfillmentStatus()));
        Boolean rewardFulfilled = request.rewardFulfilled();
        if (rewardFulfilled == null && rewardFulfillmentStatus != null) {
            rewardFulfilled = "ISSUED".equals(rewardFulfillmentStatus) || "FULFILLED".equals(rewardFulfillmentStatus);
        }

        RefundDropPolicyFactsDto facts = new RefundDropPolicyFactsDto(
                enrollment.status(),
                enrollment.enrolledAt(),
                enrollment.droppedAt(),
                enrollment.completedAt(),
                enrollment.dropReason(),
                order == null ? null : order.getId().toString(),
                paymentStatus,
                paidAmount,
                currency,
                paidAt,
                refundWindowDays,
                refundWindowEndsAt,
                withinRefundWindow,
                application == null ? null : application.getId().toString(),
                promotionStatus,
                reservationId,
                redemptionId,
                loyaltyPointsEarned,
                loyaltyPointsReversed,
                loyaltyPointsOutstanding,
                loyaltyEarnEntryId,
                rewardStatus,
                rewardRedemptionId,
                rewardFulfillmentStatus,
                rewardFulfilled);

        List<RefundDropPolicyActionDto> actions = new ArrayList<>();
        actions.add(dropPolicyAction(enrollment, request.reason()));
        actions.add(paymentRefundPolicyAction(enrollment, facts));
        actions.add(promotionPolicyAction(enrollment, facts));
        actions.add(pointsClawbackPolicyAction(enrollment, facts));
        actions.add(rewardReversalPolicyAction(enrollment, facts));

        LinkedHashSet<String> reasonCodes = new LinkedHashSet<>();
        for (RefundDropPolicyActionDto action : actions) {
            reasonCodes.addAll(action.reasonCodes());
        }
        boolean manualReviewRequired = actions.stream()
                .anyMatch(action -> Set.of("MANUAL_REVIEW", "BLOCKED").contains(action.decision()));
        boolean refundEligible = actions.stream()
                .anyMatch(action -> "REFUND_PAYMENT".equals(action.action())
                        && "REQUIRED".equals(action.decision()));
        boolean dropAllowed = actions.stream()
                .filter(action -> "DROP_ENROLLMENT".equals(action.action()))
                .anyMatch(action -> Set.of("REQUIRED", "ALREADY_DONE").contains(action.decision()));
        String severity = maxSeverity(actions);
        String matrixStatus = manualReviewRequired
                ? "MANUAL_REVIEW"
                : actions.stream().anyMatch(RefundDropPolicyActionDto::required)
                        ? "ACTION_REQUIRED"
                        : "NO_ACTION";

        Map<String, Object> auditPreview = evidence(
                "enrollmentId", enrollment.id(),
                "studentId", enrollment.studentId(),
                "courseId", enrollment.courseId(),
                "matrixStatus", matrixStatus,
                "severity", severity,
                "reason", normalizeText(request.reason()),
                "reasonCodes", List.copyOf(reasonCodes),
                "evidence", request.evidence() == null ? Map.of() : request.evidence());
        return new RefundDropPolicyEvaluationResponseDto(
                enrollment.id(),
                enrollment.studentId(),
                enrollment.courseId(),
                matrixStatus,
                severity,
                dropAllowed,
                refundEligible,
                manualReviewRequired,
                List.copyOf(reasonCodes),
                facts,
                List.copyOf(actions),
                auditPreview,
                generatedAt);
    }

    public List<EnrollmentDto> learnerMemberships(String studentId) {
        if (studentId == null || studentId.isBlank()) {
            throw new BadRequestException("studentId is required");
        }
        return enrollments.list(null, studentId.trim());
    }

    /**
     * Enroll a student. A STUDENT caller always enrolls themselves; the studentId in the body is
     * ignored. Only INSTRUCTOR/ADMIN may enroll someone else. Capacity is enforced inside the
     * transaction by locking the capacity row and counting active seats; a full course is rejected
     * with 409 so the caller can fall back to the waitlist.
     */
    @Transactional
    public EnrollmentDto enroll(EnrollRequestDto request, CurrentUser user) {
        return createEnrollment(request, user);
    }

    public PromotionPreviewDto previewPromotion(PromotionPreviewRequestDto request, CurrentUser user) {
        UUID courseId = parseUuid(request.courseId(), "courseId");
        courseAccess.requirePublishedCourse(courseId);
        String studentId = callerId(user);
        if (promotions == null) {
            throw new BadRequestException("Promotion enrollment client is not configured");
        }
        return promotions.preview(courseId, studentId, request.couponCode(), request.couponId());
    }

    public LearnerCouponWalletDto learnerCoupons(CurrentUser user) {
        String studentId = callerId(user);
        if (promotions == null) {
            throw new BadRequestException("Promotion enrollment client is not configured");
        }
        return promotions.learnerCoupons(studentId);
    }

    @Transactional
    public EnrollmentCheckoutResponseDto checkout(EnrollRequestDto request, CurrentUser user) {
        UUID courseId = parseUuid(request.courseId(), "courseId");
        String studentId = resolveTargetStudent(request.studentId(), user, courseId);
        String couponCode = normalizeCoupon(request.couponCode());
        String couponId = normalizeText(request.couponId());
        boolean hasPromotionSelector = couponCode != null || couponId != null;
        CheckoutAttemptClaim attemptClaim = claimCheckoutAttempt(request, courseId, studentId, couponCode, couponId);
        if (attemptClaim.replay() != null) {
            return attemptClaim.replay();
        }
        PromotionPreviewDto quote = checkoutQuote(request, courseId, studentId, couponCode, couponId);
        boolean paymentRequired = isPaymentRequired(quote.finalAmount());
        EnrollmentCheckoutAttempt attempt = attemptClaim.attempt();
        ReservationResult reservation = ReservationResult.skipped(couponCode, couponId);
        if (hasPromotionSelector && promotions == null) {
            throw new ConflictException("Promotion service is required when a coupon is supplied");
        } else if (hasPromotionSelector) {
            try {
                reservation = promotions.reserve(courseId, studentId, couponCode, couponId, reserveKey(request));
                if (!reservation.reserved()) {
                    throw new BadRequestException("Coupon is not applicable: "
                            + String.join(", ", reservation.reasonCodes()));
                }
                markAttemptReserved(attempt, reservation);
            } catch (PromotionUnavailableException ex) {
                throw new ConflictException("Promotion service is unavailable; retry coupon checkout later");
            }
        }
        try {
            EnrollmentDto enrollment = paymentRequired
                    ? createPendingPaymentEnrollment(request, user, quote)
                    : createEnrollment(request, user, true);
            markAttemptEnrollmentCreated(attempt, enrollment);
            EnrollmentPromotionApplicationDto promotion = paymentRequired
                    ? reservePromotionApplicationForPaidCheckout(
                            couponCode,
                            couponId,
                            reservation,
                            enrollment,
                            request.idempotencyKey())
                    : promotionApplication(
                            couponCode,
                            couponId,
                            reservation,
                            enrollment,
                            false,
                            request.idempotencyKey(),
                            attempt);
            EnrollmentOrder order = paymentRequired
                    ? createEnrollmentOrder(enrollment, attempt, quote, request)
                    : null;
            EnrollmentCheckoutResponseDto response = new EnrollmentCheckoutResponseDto(
                    enrollment,
                    promotion,
                    attempt == null ? null : attempt.getId().toString(),
                    order == null ? null : enrollmentOrderDto(order));
            finishCheckoutAttempt(attempt, response);
            return response;
        } catch (RuntimeException ex) {
            failCheckoutAttempt(attempt, ex);
            if (reservation.reservationId() != null) {
                promotions.cancel(reservation.reservationId(), "Enrollment failed after promotion reservation",
                        cancelKey(request));
            }
            throw ex;
        }
    }

    private CheckoutAttemptClaim claimCheckoutAttempt(
            EnrollRequestDto request,
            UUID courseId,
            String studentId,
            String couponCode,
            String couponId) {
        if (checkoutAttempts == null) {
            return new CheckoutAttemptClaim(null, null);
        }
        String idempotencyKey = normalizeText(request.idempotencyKey());
        if (idempotencyKey == null) {
            throw new BadRequestException("idempotencyKey is required for enrollment checkout");
        }
        String idempotencyKeyHash = sha256Hex(idempotencyKey);
        String requestHash = checkoutRequestHash(request, courseId, studentId, couponCode, couponId);
        Optional<EnrollmentCheckoutAttempt> existing = checkoutAttempts.lockByIdempotencyKey(idempotencyKeyHash);
        if (existing.isPresent()) {
            EnrollmentCheckoutAttempt attempt = existing.get();
            if (!attempt.getRequestHash().equals(requestHash)) {
                throw new ConflictException("Checkout idempotency key was already used for a different request");
            }
            if (attempt.getResponseJson() != null && !attempt.getResponseJson().isBlank()) {
                return new CheckoutAttemptClaim(attempt, readCheckoutResponse(attempt.getResponseJson()));
            }
            return new CheckoutAttemptClaim(attempt, null);
        }
        EnrollmentCheckoutAttempt attempt = new EnrollmentCheckoutAttempt(
                idempotencyKeyHash,
                requestHash,
                courseId,
                studentId,
                normalizeText(request.promotionPreviewId()));
        checkoutAttempts.saveAndFlush(attempt);
        return new CheckoutAttemptClaim(attempt, null);
    }

    private String checkoutRequestHash(
            EnrollRequestDto request,
            UUID courseId,
            String studentId,
            String couponCode,
            String couponId) {
        return sha256Hex(String.join("|",
                courseId.toString(),
                studentId,
                normalizeText(request.studentId()) == null ? "" : normalizeText(request.studentId()),
                couponCode == null ? "" : couponCode,
                couponId == null ? "" : couponId,
                normalizeText(request.promotionPreviewId()) == null ? "" : normalizeText(request.promotionPreviewId())));
    }

    private EnrollmentCheckoutResponseDto readCheckoutResponse(String responseJson) {
        try {
            return objectMapper.readValue(responseJson, EnrollmentCheckoutResponseDto.class);
        } catch (JsonProcessingException ex) {
            throw new ConflictException("Stored checkout attempt response is unreadable; contact support");
        }
    }

    private void markAttemptReserved(EnrollmentCheckoutAttempt attempt, ReservationResult reservation) {
        if (attempt != null && reservation.reservationId() != null) {
            attempt.markReserved(reservation.reservationId());
        }
    }

    private void markAttemptEnrollmentCreated(EnrollmentCheckoutAttempt attempt, EnrollmentDto enrollment) {
        if (attempt != null) {
            attempt.markEnrollmentCreated(UUID.fromString(enrollment.id()));
        }
    }

    private void finishCheckoutAttempt(EnrollmentCheckoutAttempt attempt, EnrollmentCheckoutResponseDto response) {
        if (attempt == null) {
            return;
        }
        EnrollmentPromotionApplicationDto promotion = response.promotion();
        if (response.order() != null && "PAYMENT_PENDING".equals(response.order().status())) {
            attempt.finish("PAYMENT_PENDING", toJson(response), null);
            checkoutAttempts.save(attempt);
            return;
        }
        String attemptStatus = checkoutAttemptStatus(promotion == null ? "SKIPPED" : promotion.status());
        String responseJson = toJson(response);
        if ("COMMIT_FAILED".equals(attemptStatus)) {
            attempt.retryFailed(
                    promotion == null ? "Promotion commit is pending retry" : promotion.message(),
                    nextPromotionCommitRetryAt(attempt),
                    responseJson);
        } else {
            attempt.finish(
                    attemptStatus,
                    responseJson,
                    promotion == null ? null : parseOptionalUuid(promotion.redemptionId()));
        }
        checkoutAttempts.save(attempt);
    }

    private String checkoutAttemptStatus(String promotionStatus) {
        return switch (promotionStatus) {
            case "COMMIT_FAILED", "RESERVED" -> "COMMIT_FAILED";
            case "MANUAL_REVIEW" -> "MANUAL_REVIEW";
            case "CANCELLED", "REVERSED" -> "CANCELLED";
            default -> "SUCCEEDED";
        };
    }

    private Instant nextPromotionCommitRetryAt(EnrollmentCheckoutAttempt attempt) {
        long delaySeconds = Math.min(1_800L, 60L * Math.max(1, attempt.getRetryCount() + 1));
        return Instant.now().plusSeconds(delaySeconds);
    }

    private Instant nextPromotionApplicationRetryAt(EnrollmentPromotionApplication application) {
        int nextAttempt = Math.max(1, application.getRetryCount() + 1);
        long delaySeconds = Math.min(1_800L, 60L * (1L << Math.min(nextAttempt - 1, 5)));
        return Instant.now().plusSeconds(delaySeconds);
    }

    private void failCheckoutAttempt(EnrollmentCheckoutAttempt attempt, RuntimeException ex) {
        if (attempt == null) {
            return;
        }
        attempt.fail(ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage());
        checkoutAttempts.save(attempt);
    }

    private PromotionPreviewDto checkoutQuote(
            EnrollRequestDto request,
            UUID courseId,
            String studentId,
            String couponCode,
            String couponId) {
        if (couponCode != null || couponId != null) {
            if (promotions == null) {
                throw new ConflictException("Promotion service is required when a coupon is supplied");
            }
            return validatePromotionPreview(request, courseId, studentId, couponCode, couponId);
        }
        CoursePricingSnapshot pricing = authoritativePricing(courseId);
        BigDecimal amount = money(pricing.listPrice());
        return new PromotionPreviewDto(
                "price-" + sha256Hex(String.join("|",
                        courseId.toString(),
                        amount.toPlainString(),
                        pricing.currency(),
                        pricing.priceSource(),
                        pricing.priceStatus())).substring(0, 24),
                courseId.toString(),
                null,
                null,
                "PREVIEWED",
                true,
                List.of(),
                "Course price quoted for enrollment checkout",
                amount,
                ZERO_MONEY,
                amount,
                pricing.currency(),
                pricing.priceSource(),
                List.of(),
                false);
    }

    private CoursePricingSnapshot authoritativePricing(UUID courseId) {
        if (coursePricing == null) {
            throw new ConflictException("Course pricing is required for enrollment checkout");
        }
        try {
            CoursePricingSnapshot snapshot = coursePricing.pricing(courseId.toString());
            if (snapshot == null || snapshot.listPrice() == null || snapshot.currency() == null) {
                throw new ConflictException("Course pricing is not configured");
            }
            return snapshot;
        } catch (CoursePricingUnavailableException ex) {
            throw new ConflictException("Course pricing is unavailable; retry checkout later");
        }
    }

    private PromotionPreviewDto validatePromotionPreview(
            EnrollRequestDto request,
            UUID courseId,
            String studentId,
            String couponCode,
            String couponId) {
        String expectedPreviewId = normalizeText(request.promotionPreviewId());
        if (expectedPreviewId == null) {
            throw new BadRequestException("promotionPreviewId is required when a coupon is supplied");
        }
        PromotionPreviewDto preview = promotions.preview(courseId, studentId, couponCode, couponId);
        if (preview.promotionUnavailable()) {
            throw new ConflictException("Promotion preview is unavailable; retry coupon checkout later");
        }
        if (!preview.eligible()) {
            throw new BadRequestException("Coupon is not applicable: " + String.join(", ", preview.reasonCodes()));
        }
        if (!expectedPreviewId.equals(preview.previewId())) {
            throw new ConflictException("Promotion preview is stale; refresh the coupon quote before checkout");
        }
        return preview;
    }

    private boolean isPaymentRequired(BigDecimal finalAmount) {
        return money(finalAmount).compareTo(ZERO_MONEY) > 0;
    }

    private BigDecimal money(BigDecimal value) {
        return (value == null ? BigDecimal.ZERO : value).setScale(2, RoundingMode.HALF_UP);
    }

    private EnrollmentDto createEnrollment(EnrollRequestDto request, CurrentUser user) {
        return createEnrollment(request, user, false);
    }

    private EnrollmentDto createEnrollment(
            EnrollRequestDto request,
            CurrentUser user,
            boolean checkoutBoundarySatisfied) {
        UUID courseId = parseUuid(request.courseId(), "courseId");
        courseAccess.requirePublishedCourse(courseId);
        String studentId = resolveTargetStudent(request.studentId(), user, courseId);
        if (!checkoutBoundarySatisfied) {
            assertDirectEnrollmentAllowedWithoutOrder(courseId);
        }

        enrollments.find(studentId, courseId).ifPresent(existing -> {
            if ("ACTIVE".equals(existing.status())) {
                throw new ConflictException("Student already actively enrolled");
            }
            if ("PENDING_PAYMENT".equals(existing.status())) {
                throw new ConflictException("Student already has a pending payment enrollment");
            }
            if ("COMPLETED".equals(existing.status())) {
                throw new ConflictException("Enrollment already completed; cannot re-enroll");
            }
        });

        enforceCapacity(courseId);

        EnrollmentDto dto = enrollments.enroll(studentId, courseId);
        // Outbox write stays in the same transaction: if it fails, the enrollment rolls back too.
        enrollments.outbox(UUID.fromString(dto.id()), "enrollment", "enrollment.created", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "enrollmentId", dto.id(),
                "studentId", dto.studentId(),
                "courseId", dto.courseId(),
                "enrolledAt", dto.enrolledAt().toString()
        )));
        return dto;
    }

    private void assertDirectEnrollmentAllowedWithoutOrder(UUID courseId) {
        if (coursePricing == null) {
            if (orders != null) {
                throw new ConflictException("Course pricing is required before direct enrollment can bypass checkout");
            }
            return;
        }
        CoursePricingSnapshot pricing = authoritativePricing(courseId);
        if (money(pricing.listPrice()).compareTo(ZERO_MONEY) > 0) {
            throw new ConflictException("Paid courses must be enrolled through checkout with a valid order/payment");
        }
    }

    private EnrollmentDto createPendingPaymentEnrollment(
            EnrollRequestDto request,
            CurrentUser user,
            PromotionPreviewDto quote) {
        if (orders == null) {
            throw new ConflictException("Enrollment order store is required for paid checkout");
        }
        UUID courseId = parseUuid(request.courseId(), "courseId");
        courseAccess.requirePublishedCourse(courseId);
        String studentId = resolveTargetStudent(request.studentId(), user, courseId);

        enrollments.find(studentId, courseId).ifPresent(existing -> {
            if ("ACTIVE".equals(existing.status())) {
                throw new ConflictException("Student already actively enrolled");
            }
            if ("PENDING_PAYMENT".equals(existing.status())) {
                throw new ConflictException("Student already has a pending payment enrollment");
            }
            if ("COMPLETED".equals(existing.status())) {
                throw new ConflictException("Enrollment already completed; cannot re-enroll");
            }
        });

        enforceCapacity(courseId);
        return enrollments.enrollPendingPayment(
                studentId,
                courseId,
                String.valueOf(user.id()),
                "Paid checkout requires payment before activation; amount "
                        + money(quote.finalAmount()).toPlainString() + " " + quote.currency());
    }

    private void assertPaymentSatisfiedForActivation(UUID enrollmentId, UUID courseId) {
        if (orders != null) {
            Optional<EnrollmentOrder> order = orders.findByEnrollmentId(enrollmentId);
            if (order.isPresent()) {
                EnrollmentOrder found = order.get();
                if (found.getAmount().compareTo(ZERO_MONEY) > 0 && !"PAID".equals(found.getStatus())) {
                    throw new ConflictException("Paid enrollment cannot become ACTIVE until payment is PAID");
                }
                return;
            }
        }
        if (coursePricing == null) {
            if (orders != null) {
                throw new ConflictException("Course pricing is required to activate an enrollment without a paid order");
            }
            return;
        }
        CoursePricingSnapshot pricing = authoritativePricing(courseId);
        if (money(pricing.listPrice()).compareTo(ZERO_MONEY) > 0) {
            throw new ConflictException("Paid course activation requires an enrollment order with PAID status");
        }
    }

    private EnrollmentPromotionApplicationDto promotionApplication(String couponCode,
                                                                  String couponId,
                                                                  ReservationResult reservation,
                                                                  EnrollmentDto enrollment,
                                                                  boolean promotionUnavailable,
                                                                  String idempotencyKey,
                                                                  EnrollmentCheckoutAttempt attempt) {
        if (couponCode == null && couponId == null) {
            return new EnrollmentPromotionApplicationDto(
                    "SKIPPED",
                    null,
                    null,
                    null,
                    null,
                    List.of("COUPON_NOT_SUPPLIED"),
                    "Enrollment completed without a coupon",
                    List.of());
        }
        if (promotionUnavailable) {
            return new EnrollmentPromotionApplicationDto(
                    "UNAVAILABLE",
                    null,
                    null,
                    couponCode,
                    couponId,
                    List.of("PROMOTION_UNAVAILABLE"),
                    "Enrollment completed, but the coupon could not be checked",
                    List.of());
        }
        if (reservation.reservationId() == null) {
            return new EnrollmentPromotionApplicationDto(
                    "SKIPPED",
                    null,
                    null,
                    couponCode,
                    couponId,
                    reservation.reasonCodes(),
                    "Enrollment completed without applying the coupon",
                    reservation.effects());
        }
        savePromotionApplication(
                enrollment,
                "RESERVED",
                couponCode,
                reservation.couponId() == null ? couponId : reservation.couponId(),
                reservation.reservationId(),
                null,
                idempotencyKey,
                reservation.reasonCodes(),
                reservation.effects(),
                "Coupon reserved for enrollment");
        try {
            if (attempt != null) {
                attempt.markCommitting();
            }
            CommitResult commit = promotions.commit(
                    reservation.reservationId(),
                    enrollment.id(),
                    commitKey(idempotencyKey));
            String status = commit.committed() ? "APPLIED" : "MANUAL_REVIEW";
            List<PromotionEffectDto> effects = commit.effects().isEmpty() ? reservation.effects() : commit.effects();
            String message = commit.committed()
                    ? "Coupon applied to enrollment"
                    : "Coupon reservation could not be committed; support review is required";
            updatePromotionApplication(
                    enrollment,
                    status,
                    commit.redemptionId(),
                    commit.reasonCodes(),
                    effects,
                    message);
            return new EnrollmentPromotionApplicationDto(
                    status,
                    reservation.reservationId().toString(),
                    commit.redemptionId() == null ? null : commit.redemptionId().toString(),
                    couponCode,
                    reservation.couponId() == null ? couponId : reservation.couponId(),
                    commit.reasonCodes(),
                    message,
                    effects);
        } catch (PromotionUnavailableException ex) {
            updatePromotionApplication(
                    enrollment,
                    "COMMIT_FAILED",
                    null,
                    List.of("PROMOTION_COMMIT_UNAVAILABLE"),
                    reservation.effects(),
                    "Enrollment completed, but coupon commit is pending support follow-up");
            return new EnrollmentPromotionApplicationDto(
                    "COMMIT_FAILED",
                    reservation.reservationId().toString(),
                    null,
                    couponCode,
                    reservation.couponId() == null ? couponId : reservation.couponId(),
                    List.of("PROMOTION_COMMIT_UNAVAILABLE"),
                    "Enrollment completed, but coupon commit is pending support follow-up",
                    reservation.effects());
        }
    }

    private EnrollmentPromotionApplicationDto reservePromotionApplicationForPaidCheckout(
            String couponCode,
            String couponId,
            ReservationResult reservation,
            EnrollmentDto enrollment,
            String idempotencyKey) {
        if (couponCode == null && couponId == null) {
            return new EnrollmentPromotionApplicationDto(
                    "SKIPPED",
                    null,
                    null,
                    null,
                    null,
                    List.of("COUPON_NOT_SUPPLIED"),
                    "Paid checkout has no coupon to reserve",
                    List.of());
        }
        if (reservation.reservationId() == null) {
            return new EnrollmentPromotionApplicationDto(
                    "SKIPPED",
                    null,
                    null,
                    couponCode,
                    couponId,
                    reservation.reasonCodes(),
                    "Paid checkout continued without applying the coupon",
                    reservation.effects());
        }
        String resolvedCouponId = reservation.couponId() == null ? couponId : reservation.couponId();
        savePromotionApplication(
                enrollment,
                "RESERVED",
                couponCode,
                resolvedCouponId,
                reservation.reservationId(),
                null,
                idempotencyKey,
                reservation.reasonCodes(),
                reservation.effects(),
                "Coupon reserved; commit is deferred until payment succeeds");
        return new EnrollmentPromotionApplicationDto(
                "RESERVED",
                reservation.reservationId().toString(),
                null,
                couponCode,
                resolvedCouponId,
                reservation.reasonCodes(),
                "Coupon reserved; commit is deferred until payment succeeds",
                reservation.effects());
    }

    private EnrollmentOrder createEnrollmentOrder(
            EnrollmentDto enrollment,
            EnrollmentCheckoutAttempt attempt,
            PromotionPreviewDto quote,
            EnrollRequestDto request) {
        if (orders == null) {
            throw new ConflictException("Enrollment order store is required for paid checkout");
        }
        EnrollmentOrder order = new EnrollmentOrder(
                UUID.fromString(enrollment.id()),
                attempt == null ? null : attempt.getId(),
                enrollment.studentId(),
                UUID.fromString(enrollment.courseId()),
                money(quote.finalAmount()),
                quote.currency(),
                normalizeText(request.idempotencyKey()));
        return orders.save(order);
    }

    private EnrollmentOrderDto enrollmentOrderDto(EnrollmentOrder order) {
        if (order == null) {
            return null;
        }
        return new EnrollmentOrderDto(
                order.getId().toString(),
                order.getEnrollmentId().toString(),
                order.getCheckoutAttemptId() == null ? null : order.getCheckoutAttemptId().toString(),
                order.getStudentId(),
                order.getCourseId().toString(),
                order.getStatus(),
                order.getAmount(),
                order.getCurrency(),
                order.getPaymentProvider(),
                order.getPaymentReference(),
                order.getFailureReason(),
                order.getPaidAt(),
                order.getCreatedAt(),
                order.getUpdatedAt());
    }

    private void savePromotionApplication(EnrollmentDto enrollment,
                                          String status,
                                          String couponCode,
                                          String couponId,
                                          UUID reservationId,
                                          UUID redemptionId,
                                          String idempotencyKey,
                                          List<String> reasonCodes,
                                          List<PromotionEffectDto> effects,
                                          String message) {
        if (promotionApplications == null) {
            return;
        }
        UUID enrollmentId = UUID.fromString(enrollment.id());
        EnrollmentPromotionApplication application = promotionApplications.findByEnrollmentId(enrollmentId)
                .orElseGet(() -> new EnrollmentPromotionApplication(
                        enrollmentId,
                        enrollment.studentId(),
                        UUID.fromString(enrollment.courseId()),
                        status,
                        couponCode,
                        parseOptionalUuid(couponId),
                        reservationId,
                        redemptionId,
                        normalizeText(idempotencyKey),
                        toJson(reasonCodes == null ? List.of() : reasonCodes),
                        toJson(effects == null ? List.of() : effects),
                        message));
        application.update(
                status,
                redemptionId,
                toJson(reasonCodes == null ? List.of() : reasonCodes),
                toJson(effects == null ? List.of() : effects),
                message);
        if ("COMMIT_FAILED".equals(status)) {
            application.scheduleRetry(message, nextPromotionApplicationRetryAt(application));
        }
        promotionApplications.save(application);
        if (Set.of("COMMIT_FAILED", "MANUAL_REVIEW").contains(status)) {
            ensureRemediationCaseForPromotion(
                    application,
                    firstReasonCode(reasonCodes, status),
                    "HIGH",
                    message,
                    "system",
                    null,
                    true);
        }
    }

    private void updatePromotionApplication(EnrollmentDto enrollment,
                                            String status,
                                            UUID redemptionId,
                                            List<String> reasonCodes,
                                            List<PromotionEffectDto> effects,
                                            String message) {
        if (promotionApplications == null) {
            return;
        }
        EnrollmentPromotionApplication application = promotionApplications
                .findByEnrollmentId(UUID.fromString(enrollment.id()))
                .orElseThrow(() -> new IllegalStateException(
                        "Promotion application state was not persisted for enrollment " + enrollment.id()));
        application.update(
                status,
                redemptionId,
                toJson(reasonCodes == null ? List.of() : reasonCodes),
                toJson(effects == null ? List.of() : effects),
                message);
        if ("COMMIT_FAILED".equals(status)) {
            application.scheduleRetry(message, nextPromotionApplicationRetryAt(application));
        }
        promotionApplications.save(application);
        if (Set.of("COMMIT_FAILED", "MANUAL_REVIEW").contains(status)) {
            ensureRemediationCaseForPromotion(
                    application,
                    firstReasonCode(reasonCodes, status),
                    "HIGH",
                    message,
                    "system",
                    null,
                    true);
        }
    }

    public EnrollmentPromotionApplicationStateDto promotionApplication(UUID enrollmentId, CurrentUser user) {
        get(enrollmentId, user);
        if (promotionApplications == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment promotion application state is not configured");
        }
        EnrollmentPromotionApplication application = promotionApplications.findByEnrollmentId(enrollmentId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment promotion application not found: " + enrollmentId));
        return promotionApplicationState(application);
    }

    public List<EnrollmentPromotionApplicationStateDto> promotionApplicationQueue(
            Optional<String> status,
            Optional<UUID> courseId,
            Optional<String> studentId,
            Optional<Integer> limit,
            CurrentUser user) {
        if (promotionApplications == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment promotion application state is not configured");
        }
        requireInstructorOrAdmin(user);
        if (courseId.isEmpty() && !isPlatformAdmin(user)) {
            throw new ForbiddenException("Staff promotion application queue reads must be scoped to a course");
        }
        courseId.ifPresent(id -> {
            if (!isPlatformAdmin(user)) {
                courseAccess.requireCourseStaffAccess(user, id);
            }
        });
        String normalizedStatus = status.map(this::normalizeStatus).orElse(null);
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 200));
        return promotionApplications.findOperationsQueue(
                        normalizedStatus,
                        courseId.orElse(null),
                        studentId.map(this::normalizeText).orElse(null),
                        PageRequest.of(0, pageSize))
                .stream()
                .map(this::promotionApplicationState)
                .toList();
    }

    @Transactional
    public EnrollmentPromotionApplicationStateDto retryPromotionApplicationCommit(
            UUID applicationId,
            PromotionApplicationActionRequestDto request,
            CurrentUser user) {
        if (promotionApplications == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment promotion application state is not configured");
        }
        if (promotions == null) {
            throw new ConflictException("Promotion service is required to retry coupon application commit");
        }
        EnrollmentPromotionApplication application = promotionApplications.findByIdForUpdate(applicationId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment promotion application not found: " + applicationId));
        requirePromotionApplicationOperator(application, user);
        if (!Set.of("COMMIT_FAILED", "RESERVED").contains(application.getStatus())) {
            throw new ConflictException("Only RESERVED or COMMIT_FAILED coupon applications can be retried");
        }
        recordRetryHistory(
                application,
                "RETRY_ATTEMPTED",
                actorId(user),
                actionReason(request, "Operator requested coupon commit retry"),
                request == null ? null : request.correlationId());
        retryPromotionCommitFailure(application, actionReason(request, "Operator requested coupon commit retry"));
        return promotionApplicationState(application);
    }

    @Transactional
    public EnrollmentPromotionApplicationStateDto cancelPromotionApplicationReservation(
            UUID applicationId,
            PromotionApplicationActionRequestDto request,
            CurrentUser user) {
        if (promotionApplications == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment promotion application state is not configured");
        }
        if (promotions == null) {
            throw new ConflictException("Promotion service is required to cancel coupon reservation");
        }
        EnrollmentPromotionApplication application = promotionApplications.findByIdForUpdate(applicationId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment promotion application not found: " + applicationId));
        requirePromotionApplicationOperator(application, user);
        if (!Set.of("COMMIT_FAILED", "RESERVED").contains(application.getStatus())) {
            throw new ConflictException("Only RESERVED or COMMIT_FAILED coupon applications can be cancelled");
        }
        EnrollmentDto enrollment = enrollments.findById(application.getEnrollmentId()).orElse(null);
        if (enrollment != null && Set.of("ACTIVE", "COMPLETED").contains(enrollment.status())) {
            throw new ConflictException(
                    "Cannot cancel a coupon reservation for an active enrollment; retry commit or drop first");
        }
        String reason = actionReason(request, "Operator cancelled coupon reservation");
        if (application.getReservationId() == null) {
            application.update(
                    "MANUAL_REVIEW",
                    application.getRedemptionId(),
                    toJson(List.of("RESERVATION_ID_MISSING")),
                    application.getEffectsJson(),
                    "Coupon reservation cannot be cancelled because reservation id is missing");
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "RESERVATION_ID_MISSING",
                    "HIGH",
                    application.getMessage(),
                    actorId(user),
                    request == null ? null : request.correlationId(),
                    true);
            if (enrollment != null) {
                syncCheckoutAttempt(enrollment, application);
            }
            return promotionApplicationState(application);
        }
        try {
            CancelResult cancelled = promotions.cancelStrict(application.getReservationId(), reason, cancelKey(application));
            application.cancel(
                    toJson(reasonsOr(cancelled.reasonCodes(), "CANCELLED")),
                    cancelled.cancelled()
                            ? "Coupon reservation cancelled by operator"
                            : "Coupon reservation cancel request completed without confirmed cancellation");
            promotionApplications.save(application);
            resolveRemediationCaseForPromotion(
                    application,
                    actorId(user),
                    application.getMessage(),
                    request == null ? null : request.correlationId());
            if (enrollment != null) {
                syncCheckoutAttempt(enrollment, application);
            }
            return promotionApplicationState(application);
        } catch (PromotionUnavailableException ex) {
            String retryMessage = "Promotion cancellation is unavailable; retry cancel later";
            application.update(
                    application.getStatus(),
                    application.getRedemptionId(),
                    toJson(List.of("PROMOTION_CANCEL_UNAVAILABLE")),
                    application.getEffectsJson(),
                    retryMessage);
            application.recordOperatorBlockingError(retryMessage);
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "PROMOTION_CANCEL_UNAVAILABLE",
                    "HIGH",
                    retryMessage,
                    actorId(user),
                    request == null ? null : request.correlationId(),
                    true);
            if (enrollment != null) {
                syncCheckoutAttempt(enrollment, application);
            }
            return promotionApplicationState(application);
        }
    }

    @Transactional
    public EnrollmentCheckoutResponseDto recordOrderPayment(
            UUID orderId,
            PaymentStatusUpdateRequestDto request,
            CurrentUser user) {
        if (orders == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment order store is not configured");
        }
        requireCheckoutOperator(user);
        EnrollmentOrder order = orders.findByIdForUpdate(orderId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment order not found: " + orderId));
        String status = normalizePaymentStatus(request.paymentStatus());
        if ("PAID".equals(order.getStatus())) {
            Optional<String> conflict = paidOrderReplayConflict(order, status, request);
            if (conflict.isPresent()) {
                ensureRemediationCaseForOrder(
                        order,
                        "PAYMENT_REPLAY_CONFLICT",
                        "HIGH",
                        conflict.get(),
                        actorId(user),
                        request.correlationId());
                syncCheckoutAttemptForOrder(order);
            }
            return checkoutResponseForOrder(order);
        }
        if ("PAID".equals(status)) {
            Optional<String> mismatch = paymentMismatch(order, request);
            if (mismatch.isPresent()) {
                order.markManualReview(mismatch.get());
                orders.save(order);
                ensureRemediationCaseForOrder(
                        order,
                        "PAYMENT_MISMATCH",
                        "HIGH",
                        mismatch.get(),
                        actorId(user),
                        request.correlationId());
                syncCheckoutAttemptForOrder(order);
                return checkoutResponseForOrder(order);
            }
            Optional<String> duplicateReference = duplicatePaymentReferenceConflict(order, request);
            if (duplicateReference.isPresent()) {
                order.markManualReview(duplicateReference.get());
                orders.save(order);
                ensureRemediationCaseForOrder(
                        order,
                        "PAYMENT_REFERENCE_CONFLICT",
                        "HIGH",
                        duplicateReference.get(),
                        actorId(user),
                        request.correlationId());
                syncCheckoutAttemptForOrder(order);
                return checkoutResponseForOrder(order);
            }
            order.markPaid(request.paymentProvider(), request.paymentReference());
            orders.save(order);
            EnrollmentDto enrollment = activatePaidEnrollment(order, user, request);
            if ("PAID".equals(order.getStatus()) && Set.of("ACTIVE", "COMPLETED").contains(enrollment.status())) {
                commitPromotionAfterPaymentSuccess(enrollment, order, user, request);
                resolveRemediationCaseForOrder(
                        order,
                        actorId(user),
                        "Payment event accepted and enrollment boundary satisfied",
                        request.correlationId());
            }
            syncCheckoutAttemptForOrder(order);
            return checkoutResponseForOrder(order);
        }
        order.markFailed(status, actionNote(request.note(), "Payment did not complete"));
        orders.save(order);
        EnrollmentDto enrollment = closePendingEnrollmentAfterPaymentFailure(order, user, request);
        cancelPromotionReservationAfterPaymentFailure(enrollment, order, request);
        syncCheckoutAttemptForOrder(order);
        return checkoutResponseForOrder(order);
    }

    private EnrollmentDto activatePaidEnrollment(
            EnrollmentOrder order,
            CurrentUser user,
            PaymentStatusUpdateRequestDto request) {
        EnrollmentDto enrollment = enrollments.findById(order.getEnrollmentId())
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + order.getEnrollmentId()));
        if ("ACTIVE".equals(enrollment.status()) || "COMPLETED".equals(enrollment.status())) {
            return enrollment;
        }
        if (!"PENDING_PAYMENT".equals(enrollment.status())) {
            order.markManualReview("Payment succeeded for enrollment status " + enrollment.status());
            orders.save(order);
            ensureRemediationCaseForOrder(
                    order,
                    "PAYMENT_STATUS_NOT_ACTIVATABLE",
                    "HIGH",
                    "Payment succeeded but enrollment is " + enrollment.status(),
                    actorId(user),
                    request.correlationId());
            return enrollment;
        }
        EnrollmentDto updated = enrollments.changeStatus(
                order.getEnrollmentId(),
                actorId(user),
                "ACTIVE",
                actionNote(request.note(), "Payment succeeded for order " + order.getId()));
        enrollments.outbox(order.getEnrollmentId(), "enrollment", "enrollment.created", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "enrollmentId", updated.id(),
                "studentId", updated.studentId(),
                "courseId", updated.courseId(),
                "orderId", order.getId().toString(),
                "paymentReference", order.getPaymentReference() == null ? "" : order.getPaymentReference(),
                "enrolledAt", updated.enrolledAt().toString())));
        return updated;
    }

    private void commitPromotionAfterPaymentSuccess(
            EnrollmentDto enrollment,
            EnrollmentOrder order,
            CurrentUser user,
            PaymentStatusUpdateRequestDto request) {
        if (promotionApplications == null) {
            return;
        }
        EnrollmentPromotionApplication application = promotionApplications
                .findByEnrollmentId(UUID.fromString(enrollment.id()))
                .orElse(null);
        if (application == null || !Set.of("RESERVED", "COMMIT_FAILED").contains(application.getStatus())) {
            return;
        }
        if (promotions == null) {
            application.update(
                    "MANUAL_REVIEW",
                    application.getRedemptionId(),
                    toJson(List.of("PROMOTION_SERVICE_NOT_CONFIGURED")),
                    application.getEffectsJson(),
                    "Payment succeeded, but promotion service is not configured for commit");
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "PROMOTION_SERVICE_NOT_CONFIGURED",
                    "HIGH",
                    application.getMessage(),
                    actorId(user),
                    request.correlationId(),
                    true);
            return;
        }
        retryPromotionCommitFailure(application, "Payment succeeded for order " + order.getId());
    }

    private EnrollmentDto closePendingEnrollmentAfterPaymentFailure(
            EnrollmentOrder order,
            CurrentUser user,
            PaymentStatusUpdateRequestDto request) {
        EnrollmentDto enrollment = enrollments.findById(order.getEnrollmentId()).orElse(null);
        if (enrollment == null || !"PENDING_PAYMENT".equals(enrollment.status())) {
            return enrollment;
        }
        return enrollments.changeStatus(
                order.getEnrollmentId(),
                actorId(user),
                "DROPPED",
                actionNote(request.note(), "Payment failed for order " + order.getId()));
    }

    private void cancelPromotionReservationAfterPaymentFailure(
            EnrollmentDto enrollment,
            EnrollmentOrder order,
            PaymentStatusUpdateRequestDto request) {
        if (enrollment == null || promotionApplications == null) {
            return;
        }
        EnrollmentPromotionApplication application = promotionApplications
                .findByEnrollmentId(UUID.fromString(enrollment.id()))
                .orElse(null);
        if (application == null || !Set.of("RESERVED", "COMMIT_FAILED").contains(application.getStatus())) {
            return;
        }
        boolean cancelled = cancelReservedPromotionAfterDrop(
                enrollment,
                application,
                actionNote(request.note(), "Payment failed for order " + order.getId()),
                false);
        if (!cancelled) {
            ensureRemediationCaseForPromotion(
                    application,
                    "PROMOTION_CANCEL_AFTER_PAYMENT_FAILURE_FAILED",
                    "HIGH",
                    "Payment failed, but coupon reservation could not be cancelled",
                    "system",
                    request.correlationId(),
                    true);
        }
    }

    public List<EnrollmentRemediationCaseDto> remediationCaseQueue(
            Optional<String> status,
            Optional<UUID> courseId,
            Optional<UUID> enrollmentId,
            Optional<UUID> promotionApplicationId,
            Optional<UUID> orderId,
            Optional<String> studentId,
            Optional<UUID> couponId,
            Optional<UUID> redemptionId,
            Optional<String> correlationId,
            Optional<String> assigneeId,
            Optional<Integer> limit,
            CurrentUser user) {
        if (remediationCases == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment remediation cases are not configured");
        }
        requireInstructorOrAdmin(user);
        if (courseId.isEmpty() && !isPlatformAdmin(user)) {
            throw new ForbiddenException("Staff remediation queue reads must be scoped to a course");
        }
        courseId.ifPresent(id -> {
            if (!isPlatformAdmin(user)) {
                courseAccess.requireCourseStaffAccess(user, id);
            }
        });
        String normalizedStatus = status.map(this::normalizeRemediationStatus).orElse(null);
        String normalizedStudentId = studentId.map(this::normalizeText).orElse(null);
        String normalizedCorrelationId = correlationId.map(this::normalizeText).orElse(null);
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 200));
        return remediationCases.findOperationsQueue(
                        normalizedStatus,
                        courseId.orElse(null),
                        enrollmentId.orElse(null),
                        promotionApplicationId.orElse(null),
                        orderId.orElse(null),
                        normalizedStudentId,
                        couponId.orElse(null),
                        redemptionId.orElse(null),
                        normalizedCorrelationId,
                        assigneeId.map(this::normalizeText).orElse(null),
                        PageRequest.of(0, pageSize))
                .stream()
                .map(this::remediationCaseDto)
                .toList();
    }

    public EnrollmentRemediationCaseDto remediationCase(UUID caseId, CurrentUser user) {
        if (remediationCases == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment remediation cases are not configured");
        }
        EnrollmentRemediationCase remediationCase = remediationCases.findById(caseId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment remediation case not found: " + caseId));
        requireRemediationCaseOperator(remediationCase, user);
        return remediationCaseDto(remediationCase);
    }

    @Transactional
    public EnrollmentRemediationCaseDto assignRemediationCase(
            UUID caseId,
            RemediationCaseAssignRequestDto request,
            CurrentUser user) {
        if (remediationCases == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment remediation cases are not configured");
        }
        EnrollmentRemediationCase remediationCase = remediationCases.findByIdForUpdate(caseId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment remediation case not found: " + caseId));
        requireRemediationCaseOperator(remediationCase, user);
        String fromStatus = remediationCase.getStatus();
        remediationCase.assign(request.assigneeId().trim(), actionNote(request.note(), "Case assigned"));
        remediationCases.save(remediationCase);
        recordCaseAction(
                remediationCase,
                "ASSIGNED",
                actorId(user),
                actionNote(request.note(), "Assigned to " + request.assigneeId().trim()),
                fromStatus,
                remediationCase.getStatus(),
                Map.of("assigneeId", request.assigneeId().trim(),
                        "correlationId", normalizeText(request.correlationId()) == null ? "" : request.correlationId().trim()));
        return remediationCaseDto(remediationCase);
    }

    @Transactional
    public EnrollmentRemediationCaseDto addRemediationCaseNote(
            UUID caseId,
            RemediationCaseActionRequestDto request,
            CurrentUser user) {
        if (remediationCases == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment remediation cases are not configured");
        }
        EnrollmentRemediationCase remediationCase = remediationCases.findByIdForUpdate(caseId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment remediation case not found: " + caseId));
        requireRemediationCaseOperator(remediationCase, user);
        String note = actionNote(request == null ? null : request.note(), "Operator added a note");
        remediationCase.updateNote(note);
        remediationCases.save(remediationCase);
        recordCaseAction(
                remediationCase,
                "NOTE_ADDED",
                actorId(user),
                note,
                remediationCase.getStatus(),
                remediationCase.getStatus(),
                Map.of("correlationId", request == null || normalizeText(request.correlationId()) == null
                        ? ""
                        : request.correlationId().trim()));
        return remediationCaseDto(remediationCase);
    }

    @Transactional
    public EnrollmentRemediationCaseDto resolveRemediationCase(
            UUID caseId,
            RemediationCaseActionRequestDto request,
            CurrentUser user) {
        if (remediationCases == null) {
            throw new edu.courseflow.commonlibrary.exception.NotFoundException(
                    "Enrollment remediation cases are not configured");
        }
        EnrollmentRemediationCase remediationCase = remediationCases.findByIdForUpdate(caseId)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment remediation case not found: " + caseId));
        requireRemediationCaseOperator(remediationCase, user);
        String fromStatus = remediationCase.getStatus();
        String note = actionNote(request == null ? null : request.note(), "Case resolved");
        remediationCase.resolve(note);
        remediationCases.save(remediationCase);
        recordCaseAction(
                remediationCase,
                "RESOLVED",
                actorId(user),
                note,
                fromStatus,
                remediationCase.getStatus(),
                Map.of("correlationId", request == null || normalizeText(request.correlationId()) == null
                        ? ""
                        : request.correlationId().trim()));
        return remediationCaseDto(remediationCase);
    }

    @Transactional
    public int openReservedPromotionRemediationCases(int limit) {
        if (promotionApplications == null || remediationCases == null || remediationActions == null) {
            return 0;
        }
        int batchSize = Math.max(1, Math.min(limit, 100));
        Instant cutoff = Instant.now().minus(RESERVED_REMEDIATION_AGE);
        List<EnrollmentPromotionApplication> reserved = promotionApplications.lockReservedOlderThan(
                cutoff,
                PageRequest.of(0, batchSize));
        int opened = 0;
        for (EnrollmentPromotionApplication application : reserved) {
            EnrollmentRemediationCase remediationCase = ensureRemediationCaseForPromotion(
                    application,
                    "RESERVED_OVERDUE",
                    "MEDIUM",
                    "Coupon reservation has remained RESERVED past the remediation SLA",
                    "system",
                    null,
                    true);
            if (remediationCase != null) {
                opened++;
            }
        }
        return opened;
    }

    private EnrollmentRemediationCase ensureRemediationCaseForPromotion(
            EnrollmentPromotionApplication application,
            String reasonCode,
            String severity,
            String note,
            String actorId,
            String correlationId,
            boolean retryRelevant) {
        if (remediationCases == null || remediationActions == null || application == null) {
            return null;
        }
        Optional<EnrollmentRemediationCase> existing = remediationCases
                .findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
                        application.getId(),
                        List.of("OPEN", "IN_PROGRESS"));
        if (existing.isPresent()) {
            return updateExistingPromotionRemediationCase(
                    existing.get(),
                    application,
                    reasonCode,
                    note,
                    actorId,
                    correlationId,
                    retryRelevant);
        }
        EnrollmentRemediationCase remediationCase = new EnrollmentRemediationCase(
                "PROMOTION_CHECKOUT",
                severity == null ? "HIGH" : severity,
                application.getEnrollmentId(),
                checkoutAttempts == null
                        ? null
                        : checkoutAttempts.findByEnrollmentId(application.getEnrollmentId())
                                .map(EnrollmentCheckoutAttempt::getId)
                                .orElse(null),
                application.getId(),
                orders == null
                        ? null
                        : orders.findByEnrollmentId(application.getEnrollmentId())
                                .map(EnrollmentOrder::getId)
                                .orElse(null),
                application.getStudentId(),
                application.getCourseId(),
                DEFAULT_REMEDIATION_ASSIGNEE,
                actionNote(note, "Promotion application requires support remediation"),
                reasonCode,
                Instant.now().plus(REMEDIATION_SLA));
        EnrollmentRemediationCase saved = saveNewPromotionRemediationCase(remediationCase, application)
                .orElseThrow(() -> new ConflictException(
                        "Unable to create or locate enrollment promotion remediation case"));
        if (!saved.getId().equals(remediationCase.getId())) {
            return updateExistingPromotionRemediationCase(
                    saved,
                    application,
                    reasonCode,
                    note,
                    actorId,
                    correlationId,
                    retryRelevant);
        }
        recordCaseAction(
                saved,
                "CASE_OPENED",
                actorId == null ? "system" : actorId,
                saved.getNote(),
                null,
                saved.getStatus(),
                remediationPayload(reasonCode, application.getStatus(), correlationId));
        if (retryRelevant) {
            recordCaseAction(
                    saved,
                    "RETRY_STATE",
                    actorId == null ? "system" : actorId,
                    retryStateNote(application),
                    saved.getStatus(),
                    saved.getStatus(),
                    remediationPayload(reasonCode, application.getStatus(), correlationId));
        }
        return saved;
    }

    private EnrollmentRemediationCase ensureRemediationCaseForOrder(
            EnrollmentOrder order,
            String reasonCode,
            String severity,
            String note,
            String actorId,
            String correlationId) {
        if (remediationCases == null || remediationActions == null || order == null) {
            return null;
        }
        Optional<EnrollmentRemediationCase> existing = remediationCases
                .findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(
                        order.getId(),
                        List.of("OPEN", "IN_PROGRESS"));
        if (existing.isPresent()) {
            return updateExistingOrderRemediationCase(
                    existing.get(),
                    order,
                    reasonCode,
                    note,
                    actorId,
                    correlationId);
        }
        EnrollmentRemediationCase remediationCase = new EnrollmentRemediationCase(
                "ORDER_PAYMENT",
                severity == null ? "HIGH" : severity,
                order.getEnrollmentId(),
                order.getCheckoutAttemptId(),
                null,
                order.getId(),
                order.getStudentId(),
                order.getCourseId(),
                DEFAULT_REMEDIATION_ASSIGNEE,
                actionNote(note, "Enrollment order requires payment remediation"),
                reasonCode,
                Instant.now().plus(REMEDIATION_SLA));
        EnrollmentRemediationCase saved = saveNewOrderRemediationCase(remediationCase, order)
                .orElseThrow(() -> new ConflictException("Unable to create or locate enrollment order remediation case"));
        if (!saved.getId().equals(remediationCase.getId())) {
            return updateExistingOrderRemediationCase(
                    saved,
                    order,
                    reasonCode,
                    note,
                    actorId,
                    correlationId);
        }
        recordCaseAction(
                saved,
                "CASE_OPENED",
                actorId == null ? "system" : actorId,
                saved.getNote(),
                null,
                saved.getStatus(),
                Map.of("reasonCode", reasonCode,
                        "orderStatus", order.getStatus(),
                        "correlationId", correlationId == null ? "" : correlationId));
        recordCaseAction(
                saved,
                "RETRY_STATE",
                actorId == null ? "system" : actorId,
                "Payment remediation is waiting for a corrected payment event",
                saved.getStatus(),
                saved.getStatus(),
                Map.of("reasonCode", reasonCode,
                        "orderStatus", order.getStatus(),
                        "correlationId", correlationId == null ? "" : correlationId));
        return saved;
    }

    private EnrollmentRemediationCase updateExistingPromotionRemediationCase(
            EnrollmentRemediationCase remediationCase,
            EnrollmentPromotionApplication application,
            String reasonCode,
            String note,
            String actorId,
            String correlationId,
            boolean retryRelevant) {
        remediationCase.updateNote(actionNote(note, remediationCase.getNote()));
        remediationCases.save(remediationCase);
        recordCaseAction(
                remediationCase,
                "CASE_UPDATED",
                actorId == null ? "system" : actorId,
                actionNote(note, "Promotion application still needs remediation"),
                remediationCase.getStatus(),
                remediationCase.getStatus(),
                remediationPayload(reasonCode, application.getStatus(), correlationId));
        if (retryRelevant) {
            recordCaseAction(
                    remediationCase,
                    "RETRY_STATE",
                    actorId == null ? "system" : actorId,
                    retryStateNote(application),
                    remediationCase.getStatus(),
                    remediationCase.getStatus(),
                    remediationPayload(reasonCode, application.getStatus(), correlationId));
        }
        return remediationCase;
    }

    private EnrollmentRemediationCase updateExistingOrderRemediationCase(
            EnrollmentRemediationCase remediationCase,
            EnrollmentOrder order,
            String reasonCode,
            String note,
            String actorId,
            String correlationId) {
        remediationCase.updateNote(actionNote(note, remediationCase.getNote()));
        remediationCases.save(remediationCase);
        recordCaseAction(
                remediationCase,
                "CASE_UPDATED",
                actorId == null ? "system" : actorId,
                actionNote(note, "Enrollment order still needs remediation"),
                remediationCase.getStatus(),
                remediationCase.getStatus(),
                Map.of("reasonCode", reasonCode,
                        "orderStatus", order.getStatus(),
                        "correlationId", correlationId == null ? "" : correlationId));
        return remediationCase;
    }

    private Optional<EnrollmentRemediationCase> saveNewPromotionRemediationCase(
            EnrollmentRemediationCase remediationCase,
            EnrollmentPromotionApplication application) {
        try {
            return Optional.of(remediationCases.saveAndFlush(remediationCase));
        } catch (DataIntegrityViolationException ex) {
            return remediationCases.findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
                    application.getId(),
                    List.of("OPEN", "IN_PROGRESS"));
        }
    }

    private Optional<EnrollmentRemediationCase> saveNewOrderRemediationCase(
            EnrollmentRemediationCase remediationCase,
            EnrollmentOrder order) {
        try {
            return Optional.of(remediationCases.saveAndFlush(remediationCase));
        } catch (DataIntegrityViolationException ex) {
            return remediationCases.findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(
                    order.getId(),
                    List.of("OPEN", "IN_PROGRESS"));
        }
    }

    private void resolveRemediationCaseForPromotion(
            EnrollmentPromotionApplication application,
            String actorId,
            String note,
            String correlationId) {
        if (remediationCases == null || remediationActions == null || application == null) {
            return;
        }
        remediationCases.findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
                        application.getId(),
                        List.of("OPEN", "IN_PROGRESS"))
                .ifPresent(remediationCase -> {
                    String fromStatus = remediationCase.getStatus();
                    remediationCase.resolve(actionNote(note, "Promotion remediation resolved"));
                    remediationCases.save(remediationCase);
                    recordCaseAction(
                            remediationCase,
                            "AUTO_RESOLVED",
                            actorId == null ? "system" : actorId,
                            remediationCase.getNote(),
                            fromStatus,
                            remediationCase.getStatus(),
                            remediationPayload(remediationCase.getReasonCode(), application.getStatus(), correlationId));
                });
    }

    private void resolveRemediationCaseForOrder(
            EnrollmentOrder order,
            String actorId,
            String note,
            String correlationId) {
        if (remediationCases == null || remediationActions == null || order == null) {
            return;
        }
        remediationCases.findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(
                        order.getId(),
                        List.of("OPEN", "IN_PROGRESS"))
                .ifPresent(remediationCase -> {
                    String fromStatus = remediationCase.getStatus();
                    remediationCase.resolve(actionNote(note, "Order remediation resolved"));
                    remediationCases.save(remediationCase);
                    recordCaseAction(
                            remediationCase,
                            "AUTO_RESOLVED",
                            actorId == null ? "system" : actorId,
                            remediationCase.getNote(),
                            fromStatus,
                            remediationCase.getStatus(),
                            Map.of("reasonCode", remediationCase.getReasonCode(),
                                    "orderStatus", order.getStatus(),
                                    "correlationId", correlationId == null ? "" : correlationId));
                });
    }

    private void recordRetryHistory(
            EnrollmentPromotionApplication application,
            String action,
            String actorId,
            String note,
            String correlationId) {
        if (remediationCases == null || remediationActions == null || application == null) {
            return;
        }
        EnrollmentRemediationCase remediationCase = remediationCases
                .findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
                        application.getId(),
                        List.of("OPEN", "IN_PROGRESS"))
                .orElse(null);
        if (remediationCase == null) {
            return;
        }
        recordCaseAction(
                remediationCase,
                action,
                actorId == null ? "system" : actorId,
                note,
                remediationCase.getStatus(),
                remediationCase.getStatus(),
                remediationPayload(application.getStatus(), application.getStatus(), correlationId));
    }

    private void recordCaseAction(
            EnrollmentRemediationCase remediationCase,
            String action,
            String actorId,
            String note,
            String fromStatus,
            String toStatus,
            Map<String, Object> payload) {
        if (remediationActions == null || remediationCase == null) {
            return;
        }
        String effectiveActorId = actorId == null ? "system" : actorId;
        String payloadJson = toJson(payload == null ? Map.of() : payload);
        remediationActions.save(new EnrollmentRemediationCaseAction(
                remediationCase.getId(),
                action,
                effectiveActorId,
                note,
                fromStatus,
                toStatus,
                payloadJson));
        recordRemediationAudit(remediationCase, action, effectiveActorId, note, fromStatus, toStatus, payloadJson);
    }

    private void recordRemediationAudit(
            EnrollmentRemediationCase remediationCase,
            String action,
            String actorId,
            String note,
            String fromStatus,
            String toStatus,
            String payloadJson) {
        if (remediationCase.getEnrollmentId() == null) {
            return;
        }
        Map<String, Object> auditPayload = evidence(
                "caseId", remediationCase.getId().toString(),
                "caseType", remediationCase.getCaseType(),
                "caseAction", action,
                "fromCaseStatus", fromStatus,
                "toCaseStatus", toStatus,
                "reasonCode", remediationCase.getReasonCode(),
                "note", note,
                "payload", readMap(payloadJson));
        enrollments.recordAudit(
                remediationCase.getEnrollmentId(),
                actorId,
                remediationAuditAction(action),
                null,
                null,
                toJson(auditPayload));
    }

    private String remediationAuditAction(String action) {
        String normalized = upper(action);
        String candidate = "REMEDIATION_"
                + (normalized == null ? "ACTION" : normalized.replaceAll("[^A-Z0-9_]", "_"));
        return candidate.length() <= 60 ? candidate : candidate.substring(0, 60);
    }

    private EnrollmentRemediationCaseDto remediationCaseDto(EnrollmentRemediationCase remediationCase) {
        List<EnrollmentRemediationCaseActionDto> actions = remediationActions == null
                ? List.of()
                : remediationActions.findByCaseIdOrderByCreatedAtAsc(remediationCase.getId()).stream()
                        .map(this::remediationActionDto)
                        .toList();
        Instant now = Instant.now();
        Instant ageEnd = remediationCase.getClosedAt() == null ? now : remediationCase.getClosedAt();
        long slaAgeMinutes = Math.max(0, Duration.between(remediationCase.getCreatedAt(), ageEnd).toMinutes());
        boolean slaBreached = remediationCase.getClosedAt() == null
                ? now.isAfter(remediationCase.getSlaDueAt())
                : remediationCase.getClosedAt().isAfter(remediationCase.getSlaDueAt());
        return new EnrollmentRemediationCaseDto(
                remediationCase.getId().toString(),
                remediationCase.getCaseType(),
                remediationCase.getStatus(),
                remediationCase.getSeverity(),
                remediationCase.getEnrollmentId() == null ? null : remediationCase.getEnrollmentId().toString(),
                remediationCase.getCheckoutAttemptId() == null ? null : remediationCase.getCheckoutAttemptId().toString(),
                remediationCase.getPromotionApplicationId() == null ? null : remediationCase.getPromotionApplicationId().toString(),
                remediationCase.getOrderId() == null ? null : remediationCase.getOrderId().toString(),
                remediationCase.getStudentId(),
                remediationCase.getCourseId().toString(),
                remediationCase.getAssigneeId(),
                remediationCase.getNote(),
                remediationCase.getReasonCode(),
                remediationCase.getSlaDueAt(),
                slaAgeMinutes,
                slaBreached,
                remediationCase.getCreatedAt(),
                remediationCase.getUpdatedAt(),
                remediationCase.getClosedAt(),
                actions,
                actions.stream()
                        .filter(action -> action.action() != null && action.action().startsWith("RETRY_"))
                        .toList());
    }

    private EnrollmentRemediationCaseActionDto remediationActionDto(EnrollmentRemediationCaseAction action) {
        return new EnrollmentRemediationCaseActionDto(
                action.getId().toString(),
                action.getAction(),
                action.getActorId(),
                action.getNote(),
                action.getFromStatus(),
                action.getToStatus(),
                readMap(action.getPayloadJson()),
                action.getCreatedAt());
    }

    private EnrollmentPromotionApplicationStateDto promotionApplicationState(
            EnrollmentPromotionApplication application) {
        return new EnrollmentPromotionApplicationStateDto(
                application.getId().toString(),
                application.getEnrollmentId().toString(),
                application.getStudentId(),
                application.getCourseId().toString(),
                application.getStatus(),
                application.getCouponCode(),
                application.getCouponId() == null ? null : application.getCouponId().toString(),
                application.getReservationId() == null ? null : application.getReservationId().toString(),
                application.getRedemptionId() == null ? null : application.getRedemptionId().toString(),
                application.getIdempotencyKey(),
                readList(application.getReasonCodesJson(), STRING_LIST),
                application.getMessage(),
                readList(application.getEffectsJson(), PROMOTION_EFFECT_LIST),
                application.getRetryCount(),
                application.getNextRetryAt(),
                application.getLastRetryError(),
                application.getCreatedAt(),
                application.getUpdatedAt());
    }

    public Optional<EnrollmentDto> get(UUID id) {
        return enrollments.findById(id);
    }

    public EnrollmentDto get(UUID id, CurrentUser user) {
        EnrollmentDto enrollment = enrollments.findById(id)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + id));
        requireSelfOrCourseStaff(enrollment, user);
        return enrollment;
    }

    public CourseAccessDto courseAccess(UUID courseId, String studentId) {
        Optional<EnrollmentDto> found = enrollments.findCourseAccess(studentId, courseId);
        return new CourseAccessDto(
                courseId.toString(),
                studentId,
                found.isPresent(),
                found.map(EnrollmentDto::status).orElse(null));
    }

    public List<EnrollmentDto> activeRoster(UUID courseId, Optional<UUID> cohortId) {
        return enrollments.listActiveRoster(courseId, cohortId.orElse(null));
    }

    /**
     * Drive an enrollment through its state machine.
     * <ul>
     *   <li>DROPPED: a STUDENT may only drop their own enrollment; INSTRUCTOR/ADMIN may drop anyone.</li>
     *   <li>COMPLETED: INSTRUCTOR/ADMIN only.</li>
     *   <li>ACTIVE (re-enroll from DROPPED): a STUDENT may re-enroll themselves; INSTRUCTOR/ADMIN anyone.
     *       Capacity is re-checked.</li>
     * </ul>
     */
    @Transactional
    public EnrollmentDto changeStatus(UUID id, ChangeStatusRequestDto req, CurrentUser user) {
        String newStatus = req.newStatus();
        if (!ALLOWED_TRANSITIONS.containsKey(newStatus)) {
            throw new BadRequestException("Invalid status: " + newStatus);
        }
        EnrollmentDto existing = enrollments.findById(id)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + id));
        String oldStatus = existing.status();

        Set<String> allowedFrom = ALLOWED_TRANSITIONS.getOrDefault(oldStatus, Set.of());
        if (!allowedFrom.contains(newStatus)) {
            throw new BadRequestException(
                    "Illegal transition " + oldStatus + " -> " + newStatus);
        }

        authorizeTransition(existing, newStatus, user);

        if ("ACTIVE".equals(newStatus)) {
            UUID courseId = parseUuid(existing.courseId(), "courseId");
            courseAccess.requirePublishedCourse(courseId);
            assertPaymentSatisfiedForActivation(id, courseId);
            enforceCapacity(courseId);
        }

        String actorId = String.valueOf(user.id());
        EnrollmentDto updated = enrollments.changeStatus(id, actorId, newStatus, req.reason());

        if ("DROPPED".equals(newStatus)) {
            enrollments.outbox(id, "enrollment", "enrollment.dropped", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "enrollmentId", updated.id(),
                    "studentId", updated.studentId(),
                    "courseId", updated.courseId(),
                    "actorId", actorId,
                    "reason", req.reason() == null ? "" : req.reason())));
            promoteWaitlist(UUID.fromString(updated.courseId()));
            reversePromotionApplicationIfApplied(updated, req.reason());
        } else if ("COMPLETED".equals(newStatus)) {
            enrollments.outbox(id, "enrollment", "enrollment.completed", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "enrollmentId", updated.id(),
                    "studentId", updated.studentId(),
                    "courseId", updated.courseId(),
                    "actorId", actorId)));
            promoteWaitlist(UUID.fromString(updated.courseId()));
        } else if ("ACTIVE".equals(newStatus)) {
            enrollments.outbox(id, "enrollment", "enrollment.created", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "enrollmentId", updated.id(),
                    "studentId", updated.studentId(),
                    "courseId", updated.courseId(),
                    "enrolledAt", updated.enrolledAt().toString())));
        }
        return updated;
    }

    private void reversePromotionApplicationIfApplied(EnrollmentDto enrollment, String reason) {
        if (promotionApplications == null) {
            return;
        }
        EnrollmentPromotionApplication application = promotionApplications
                .findByEnrollmentId(UUID.fromString(enrollment.id()))
                .orElse(null);
        if (application == null) {
            return;
        }
        if ("REVERSED".equals(application.getStatus()) || "CANCELLED".equals(application.getStatus())) {
            return;
        }
        if (Set.of("RESERVED", "COMMIT_FAILED").contains(application.getStatus())) {
            cancelReservedPromotionAfterDrop(enrollment, application, reason, true);
            return;
        }
        if (!"APPLIED".equals(application.getStatus())) {
            return;
        }
        if (application.getRedemptionId() == null) {
            application.update(
                    "MANUAL_REVIEW",
                    null,
                    toJson(List.of("REDEMPTION_ID_MISSING")),
                    application.getEffectsJson(),
                    "Coupon application is marked applied without a redemption id");
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "REDEMPTION_ID_MISSING",
                    "HIGH",
                    application.getMessage(),
                    "system",
                    null,
                    true);
            throw new ConflictException("Promotion application needs manual review before dropping");
        }
        if (promotions == null) {
            throw new ConflictException("Promotion service is required to reverse an applied coupon before dropping");
        }
        try {
            ReverseResult reversal = promotions.reverse(
                    application.getRedemptionId(),
                    dropReversalReason(enrollment, reason),
                    reverseKey(application));
            application.update(
                    "REVERSED",
                    reversal.redemptionId() == null ? application.getRedemptionId() : reversal.redemptionId(),
                    toJson(reversal.reasonCodes()),
                    toJson(reversal.effects().isEmpty()
                            ? readList(application.getEffectsJson(), PROMOTION_EFFECT_LIST)
                            : reversal.effects()),
                    "Coupon application reversed after enrollment drop");
            promotionApplications.save(application);
        } catch (PromotionUnavailableException ex) {
            throw new ConflictException("Promotion reversal is unavailable; retry dropping the enrollment later");
        }
    }

    private boolean cancelReservedPromotionAfterDrop(
            EnrollmentDto enrollment,
            EnrollmentPromotionApplication application,
            String reason,
            boolean failClosed) {
        if (application.getReservationId() == null) {
            application.update(
                    "MANUAL_REVIEW",
                    application.getRedemptionId(),
                    toJson(List.of("RESERVATION_ID_MISSING")),
                    application.getEffectsJson(),
                    "Coupon reservation cannot be closed because reservation id is missing");
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "RESERVATION_ID_MISSING",
                    "HIGH",
                    application.getMessage(),
                    "system",
                    null,
                    true);
            syncCheckoutAttempt(enrollment, application);
            return true;
        }
        if (promotions == null) {
            if (failClosed) {
                throw new ConflictException(
                        "Promotion service is required to cancel a reserved coupon before dropping");
            }
            return false;
        }
        try {
            CancelResult cancelled = promotions.cancelStrict(
                    application.getReservationId(),
                    dropReversalReason(enrollment, reason),
                    cancelKey(application));
            application.cancel(
                    toJson(reasonsOr(cancelled.reasonCodes(), "CANCELLED")),
                    "Coupon reservation closed after enrollment drop");
            promotionApplications.save(application);
            resolveRemediationCaseForPromotion(
                    application,
                    "system",
                    "Coupon reservation closed after enrollment drop",
                    null);
            syncCheckoutAttempt(enrollment, application);
            return true;
        } catch (PromotionUnavailableException ex) {
            if (failClosed) {
                throw new ConflictException(
                        "Promotion cancellation is unavailable; retry dropping the enrollment later");
            }
            String retryMessage = "Promotion cancellation is unavailable; retry cancel later";
            application.update(
                    application.getStatus(),
                    application.getRedemptionId(),
                    toJson(List.of("PROMOTION_CANCEL_UNAVAILABLE")),
                    application.getEffectsJson(),
                    retryMessage);
            application.recordOperatorBlockingError(retryMessage);
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "PROMOTION_CANCEL_UNAVAILABLE",
                    "HIGH",
                    retryMessage,
                    "system",
                    null,
                    true);
            syncCheckoutAttempt(enrollment, application);
            return false;
        }
    }

    @Transactional
    public int retryPromotionCommitFailures(int limit) {
        if (promotionApplications == null || promotions == null) {
            return 0;
        }
        int batchSize = Math.max(1, Math.min(limit, 100));
        List<EnrollmentPromotionApplication> applications = promotionApplications.lockRetryableByStatus(
                "COMMIT_FAILED",
                Instant.now(),
                PageRequest.of(0, batchSize));
        int resolved = 0;
        for (EnrollmentPromotionApplication application : applications) {
            recordRetryHistory(
                    application,
                    "RETRY_ATTEMPTED",
                    "system",
                    "Scheduled promotion commit retry",
                    null);
            if (retryPromotionCommitFailure(application, "Scheduled promotion commit retry")) {
                resolved++;
            }
        }
        return resolved;
    }

    private boolean retryPromotionCommitFailure(EnrollmentPromotionApplication application, String reason) {
        EnrollmentDto enrollment = enrollments.findById(application.getEnrollmentId()).orElse(null);
        if (enrollment == null) {
            application.update(
                    "MANUAL_REVIEW",
                    application.getRedemptionId(),
                    toJson(List.of("ENROLLMENT_NOT_FOUND")),
                    application.getEffectsJson(),
                    "Promotion commit cannot be retried because enrollment is missing");
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "ENROLLMENT_NOT_FOUND",
                    "HIGH",
                    application.getMessage(),
                    "system",
                    null,
                    true);
            recordRetryHistory(
                    application,
                    "RETRY_FAILED",
                    "system",
                    application.getMessage(),
                    null);
            return true;
        }
        if (application.getReservationId() == null) {
            application.update(
                    "MANUAL_REVIEW",
                    application.getRedemptionId(),
                    toJson(List.of("RESERVATION_ID_MISSING")),
                    application.getEffectsJson(),
                    "Promotion commit cannot be retried because reservation id is missing");
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "RESERVATION_ID_MISSING",
                    "HIGH",
                    application.getMessage(),
                    "system",
                    null,
                    true);
            recordRetryHistory(
                    application,
                    "RETRY_FAILED",
                    "system",
                    application.getMessage(),
                    null);
            syncCheckoutAttempt(enrollment, application);
            return true;
        }
        if ("DROPPED".equals(enrollment.status())) {
            return cancelReservedPromotionAfterDrop(
                    enrollment,
                    application,
                    reason == null ? "Enrollment was dropped before promotion commit retry" : reason,
                    false);
        }
        if (!Set.of("ACTIVE", "COMPLETED").contains(enrollment.status())) {
            application.update(
                    "MANUAL_REVIEW",
                    application.getRedemptionId(),
                    toJson(List.of("ENROLLMENT_STATUS_NOT_COMMITTABLE")),
                    application.getEffectsJson(),
                    "Promotion commit cannot be retried for enrollment status " + enrollment.status());
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "ENROLLMENT_STATUS_NOT_COMMITTABLE",
                    "HIGH",
                    application.getMessage(),
                    "system",
                    null,
                    true);
            recordRetryHistory(
                    application,
                    "RETRY_FAILED",
                    "system",
                    application.getMessage(),
                    null);
            syncCheckoutAttempt(enrollment, application);
            return true;
        }
        try {
            CommitResult commit = promotions.commit(
                    application.getReservationId(),
                    application.getEnrollmentId().toString(),
                    commitKey(application));
            List<PromotionEffectDto> effects = commit.effects().isEmpty()
                    ? readList(application.getEffectsJson(), PROMOTION_EFFECT_LIST)
                    : commit.effects();
            if (commit.committed()) {
                application.update(
                        "APPLIED",
                        commit.redemptionId(),
                        toJson(reasonsOr(commit.reasonCodes(), "COMMITTED")),
                        toJson(effects),
                        "Coupon applied after promotion commit retry");
                recordRetryHistory(
                        application,
                        "RETRY_SUCCEEDED",
                        "system",
                        "Coupon applied after promotion commit retry",
                        null);
                resolveRemediationCaseForPromotion(
                        application,
                        "system",
                        "Coupon applied after promotion commit retry",
                        null);
            } else {
                application.update(
                        "MANUAL_REVIEW",
                        commit.redemptionId(),
                        toJson(reasonsOr(commit.reasonCodes(), "PROMOTION_COMMIT_REJECTED")),
                        toJson(effects),
                        "Coupon reservation could not be committed after retry");
                ensureRemediationCaseForPromotion(
                        application,
                        firstReasonCode(commit.reasonCodes(), "PROMOTION_COMMIT_REJECTED"),
                        "HIGH",
                        application.getMessage(),
                        "system",
                        null,
                        true);
                recordRetryHistory(
                        application,
                        "RETRY_FAILED",
                        "system",
                        application.getMessage(),
                        null);
            }
            promotionApplications.save(application);
            syncCheckoutAttempt(enrollment, application);
            return true;
        } catch (PromotionUnavailableException ex) {
            String retryMessage = "Promotion commit retry is still unavailable";
            application.update(
                    "COMMIT_FAILED",
                    application.getRedemptionId(),
                    toJson(List.of("PROMOTION_COMMIT_UNAVAILABLE")),
                    application.getEffectsJson(),
                    retryMessage);
            application.scheduleRetry(retryMessage, nextPromotionApplicationRetryAt(application));
            promotionApplications.save(application);
            ensureRemediationCaseForPromotion(
                    application,
                    "PROMOTION_COMMIT_UNAVAILABLE",
                    "HIGH",
                    retryMessage,
                    "system",
                    null,
                    true);
            recordRetryHistory(
                    application,
                    "RETRY_SCHEDULED",
                    "system",
                    retryMessage,
                    null);
            syncCheckoutAttempt(enrollment, application);
            return false;
        }
    }

    private void syncCheckoutAttempt(EnrollmentDto enrollment, EnrollmentPromotionApplication application) {
        if (checkoutAttempts == null) {
            return;
        }
        checkoutAttempts.findByEnrollmentId(application.getEnrollmentId()).ifPresent(attempt -> {
            EnrollmentPromotionApplicationDto promotion = promotionApplicationDto(application);
            EnrollmentOrder order = orders == null
                    ? null
                    : orders.findByEnrollmentId(application.getEnrollmentId()).orElse(null);
            EnrollmentCheckoutResponseDto response = new EnrollmentCheckoutResponseDto(
                    enrollment,
                    promotion,
                    attempt.getId().toString(),
                    enrollmentOrderDto(order));
            String responseJson = toJson(response);
            String attemptStatus = order == null
                    ? checkoutAttemptStatus(application.getStatus())
                    : checkoutAttemptStatusForOrder(order, promotion);
            if ("COMMIT_FAILED".equals(attemptStatus)) {
                Instant nextRetryAt = application.getNextRetryAt() == null
                        ? nextPromotionCommitRetryAt(attempt)
                        : application.getNextRetryAt();
                attempt.retryFailed(promotion.message(), nextRetryAt, responseJson);
            } else {
                attempt.finish(attemptStatus, responseJson, application.getRedemptionId());
            }
            checkoutAttempts.save(attempt);
        });
    }

    private EnrollmentPromotionApplicationDto promotionApplicationDto(EnrollmentPromotionApplication application) {
        return new EnrollmentPromotionApplicationDto(
                application.getStatus(),
                application.getReservationId() == null ? null : application.getReservationId().toString(),
                application.getRedemptionId() == null ? null : application.getRedemptionId().toString(),
                application.getCouponCode(),
                application.getCouponId() == null ? null : application.getCouponId().toString(),
                readList(application.getReasonCodesJson(), STRING_LIST),
                application.getMessage(),
                readList(application.getEffectsJson(), PROMOTION_EFFECT_LIST));
    }

    private List<String> reasonsOr(List<String> reasonCodes, String fallback) {
        return reasonCodes == null || reasonCodes.isEmpty() ? List.of(fallback) : reasonCodes;
    }

    private String firstReasonCode(List<String> reasonCodes, String fallback) {
        if (reasonCodes == null || reasonCodes.isEmpty() || normalizeText(reasonCodes.getFirst()) == null) {
            return fallback;
        }
        return reasonCodes.getFirst().trim();
    }

    /**
     * System-driven completion triggered by a {@code course.completed} event. Transitions the
     * student's ACTIVE enrollment to COMPLETED (no human actor) and emits an
     * {@code enrollment.completed} outbox event. A missing enrollment, or one not currently ACTIVE
     * (already completed/dropped), is a no-op so the consumer stays idempotent and tolerant of
     * out-of-order events. Returns the updated enrollment when a transition occurred.
     */
    @Transactional
    public Optional<EnrollmentDto> completeForCourseCompletion(String studentId, UUID courseId) {
        Optional<EnrollmentDto> found = enrollments.find(studentId, courseId);
        if (found.isEmpty() || !"ACTIVE".equals(found.get().status())) {
            return Optional.empty();
        }
        UUID id = UUID.fromString(found.get().id());
        EnrollmentDto updated = enrollments.changeStatus(id, "system", "COMPLETED",
                "Auto-completed on course completion");
        enrollments.outbox(id, "enrollment", "enrollment.completed", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "enrollmentId", updated.id(),
                "studentId", updated.studentId(),
                "courseId", updated.courseId(),
                "actorId", "system")));
        promoteWaitlist(courseId);
        return Optional.of(updated);
    }

    /** Batch enroll on behalf of other students: INSTRUCTOR/ADMIN only. */
    public BatchEnrollResultDto batchEnroll(BatchEnrollRequestDto req, CurrentUser user) {
        requireAuthenticated(user);
        for (BatchEnrollRequestDto.SingleEnrollDto entry : req.entries()) {
            UUID courseId = parseUuid(entry.courseId(), "courseId");
            courseAccess.requirePublishedCourse(courseId);
            courseAccess.requireCourseStaffAccess(user, courseId);
        }
        return enrollments.batchEnroll(req.entries(), String.valueOf(user.id()));
    }

    public EnrollmentStatsDto stats(UUID courseId) {
        return enrollments.stats(courseId);
    }

    public EnrollmentStatsDto stats(UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return enrollments.stats(courseId);
    }

    public List<AuditLogEntryDto> auditLog(UUID id) {
        return enrollments.auditLog(id);
    }

    public List<AuditLogEntryDto> auditLog(UUID id, CurrentUser user) {
        EnrollmentDto enrollment = enrollments.findById(id)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + id));
        requireSelfOrCourseStaff(enrollment, user);
        return enrollments.auditLog(id);
    }

    public List<AuditLogEntryDto> auditLog(
            Optional<UUID> enrollmentId,
            Optional<UUID> courseId,
            Optional<String> studentId,
            Optional<String> correlationId,
            Optional<Integer> limit,
            CurrentUser user) {
        UUID scopedEnrollmentId = enrollmentId.orElse(null);
        UUID scopedCourseId = courseId.orElse(null);
        String normalizedStudentId = studentId.map(this::normalizeText).orElse(null);
        String normalizedCorrelationId = correlationId.map(this::normalizeText).orElse(null);
        if (scopedEnrollmentId == null
                && scopedCourseId == null
                && normalizedStudentId == null
                && normalizedCorrelationId == null) {
            throw new BadRequestException("Enrollment audit query requires enrollment, course, learner or correlation filter");
        }
        if (scopedEnrollmentId != null) {
            EnrollmentDto enrollment = enrollments.findById(scopedEnrollmentId)
                    .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                            "Enrollment not found: " + scopedEnrollmentId));
            UUID enrollmentCourseId = parseUuid(enrollment.courseId(), "courseId");
            if (scopedCourseId != null && !scopedCourseId.equals(enrollmentCourseId)) {
                throw new BadRequestException("courseId does not match enrollment");
            }
            scopedCourseId = enrollmentCourseId;
            if (normalizedStudentId != null && !normalizedStudentId.equals(enrollment.studentId())) {
                throw new BadRequestException("studentId does not match enrollment");
            }
        }
        requireBenefitReconciliationAccess(Optional.ofNullable(scopedCourseId), user);
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 200));
        return enrollments.auditLog(
                scopedEnrollmentId,
                scopedCourseId,
                normalizedStudentId,
                normalizedCorrelationId,
                pageSize);
    }

    public List<WaitlistEntryDto> listWaitlist(UUID courseId) {
        return enrollments.listWaitlist(courseId);
    }

    public List<WaitlistEntryDto> listWaitlist(UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return enrollments.listWaitlist(courseId);
    }

    /**
     * Join the waitlist. Only allowed when the course is actually full; if seats are free the caller
     * should enroll directly (we reject with 409 to make the misuse explicit). A STUDENT joins for
     * themselves; INSTRUCTOR/ADMIN may add someone else.
     */
    @Transactional
    public WaitlistEntryDto waitlist(WaitlistRequestDto request, CurrentUser user) {
        UUID courseId = parseUuid(request.courseId(), "courseId");
        courseAccess.requirePublishedCourse(courseId);
        String studentId = resolveTargetStudent(request.studentId(), user, courseId);
        if (!isFull(courseId)) {
            throw new ConflictException("Course is not full; enroll directly instead of waitlisting");
        }
        return enrollments.addToWaitlist(studentId, courseId);
    }

    /** Set or clear (null = unlimited) per-course capacity. ADMIN/INSTRUCTOR only. */
    @Transactional
    public void setCapacity(UUID courseId, SetCapacityRequestDto request, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        if (request.capacity() != null && request.capacity() < 0) {
            throw new BadRequestException("Capacity must be zero or positive");
        }
        enrollments.setCapacity(courseId, request.capacity());
    }

    @Transactional
    public void initializePublishedCourse(UUID courseId, Integer defaultCapacity) {
        if (courseId == null || enrollments.hasCapacityRow(courseId)) {
            return;
        }
        enrollments.setCapacity(courseId, defaultCapacity);
    }

    @Transactional
    public void archiveCourse(UUID courseId) {
        if (courseId != null) {
            enrollments.setCapacity(courseId, 0);
        }
    }

    // ---- internals ----

    /**
     * Enforce capacity inside the current transaction. Locks the capacity row so concurrent enrolls
     * for the same course serialize on the seat check. No capacity row, or a NULL capacity, means
     * unlimited.
     */
    private void enforceCapacity(UUID courseId) {
        if (courseId == null) {
            return;
        }
        Optional<Integer> capacity = enrollments.lockCapacity(courseId);
        if (capacity.isEmpty()) {
            return; // unlimited
        }
        int occupied = enrollments.countOccupiedSeats(courseId);
        if (occupied >= capacity.get()) {
            throw new ConflictException("Course is full (capacity " + capacity.get() + ")");
        }
    }

    private boolean isFull(UUID courseId) {
        Optional<Integer> capacity = enrollments.lockCapacity(courseId);
        if (capacity.isEmpty()) {
            return false; // unlimited is never full
        }
        return enrollments.countOccupiedSeats(courseId) >= capacity.get();
    }

    /**
     * On a drop, promote the first FIFO-waiting student into an active enrollment, provided the
     * course now has a free seat. Runs in the same transaction as the drop.
     */
    private void promoteWaitlist(UUID courseId) {
        while (!isFull(courseId)) {
            Optional<WaitlistEntryDto> next = enrollments.firstWaiting(courseId);
            if (next.isEmpty()) {
                return;
            }
            WaitlistEntryDto entry = next.get();
            Optional<EnrollmentDto> existingEnrollment = enrollments.find(entry.studentId(), courseId);
            if (existingEnrollment.isPresent()) {
                String status = existingEnrollment.get().status();
                if ("ACTIVE".equals(status) || "COMPLETED".equals(status)) {
                    enrollments.markWaitlistSkipped(UUID.fromString(entry.id()));
                    enrollments.compactWaitlist(courseId);
                    continue;
                }
            }

            EnrollmentDto promoted = enrollments.enroll(entry.studentId(), courseId);
            enrollments.markWaitlistPromoted(UUID.fromString(entry.id()));
            // Close the FIFO gap left at the head so remaining positions stay a gapless 1..n sequence.
            enrollments.compactWaitlist(courseId);
            enrollments.outbox(UUID.fromString(promoted.id()), "enrollment", "enrollment.created",
                    toJson(Map.of(
                            "eventId", UUID.randomUUID().toString(),
                            "enrollmentId", promoted.id(),
                            "studentId", promoted.studentId(),
                            "courseId", promoted.courseId(),
                            "enrolledAt", promoted.enrolledAt().toString(),
                            "promotedFromWaitlist", true)));
            return;
        }
    }

    /**
     * Resolve who an action targets: a non-privileged caller always acts on themselves, so any
     * studentId supplied in the body is ignored. Only INSTRUCTOR/ADMIN may target a different student.
     */
    private String resolveTargetStudent(String requestedStudentId, CurrentUser user, UUID courseId) {
        requireAuthenticated(user);
        String self = String.valueOf(user.id());
        if (requestedStudentId == null || requestedStudentId.isBlank() || requestedStudentId.equals(self)) {
            return self;
        }
        courseAccess.requireCourseStaffAccess(user, courseId);
        return requestedStudentId;
    }

    private void authorizeTransition(EnrollmentDto enrollment, String newStatus, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        UUID courseId = parseUuid(enrollment.courseId(), "courseId");
        boolean privileged = isStaff(user);
        boolean self = String.valueOf(user.id()).equals(enrollment.studentId());
        switch (newStatus) {
            case "DROPPED", "ACTIVE" -> {
                // Student may drop / re-enroll their own enrollment; privileged roles may act on anyone.
                if (!self && !privileged) {
                    throw new ForbiddenException("Students may only change their own enrollment");
                }
                if (!self) {
                    courseAccess.requireCourseStaffAccess(user, courseId);
                }
            }
            case "COMPLETED" -> {
                if (!privileged) {
                    throw new ForbiddenException("Only INSTRUCTOR or ADMIN may complete an enrollment");
                }
                courseAccess.requireCourseStaffAccess(user, courseId);
            }
            default -> throw new BadRequestException("Invalid status: " + newStatus);
        }
    }

    private void requireSelfOrCourseStaff(EnrollmentDto enrollment, CurrentUser user) {
        String self = callerId(user);
        if (self.equals(enrollment.studentId())) {
            return;
        }
        if (!isStaff(user)) {
            throw new ForbiddenException("Students may only read their own enrollment");
        }
        courseAccess.requireCourseStaffAccess(user, parseUuid(enrollment.courseId(), "courseId"));
    }

    private void requireInstructorOrAdmin(CurrentUser user) {
        requireAuthenticated(user);
        if (!isStaff(user)) {
            throw new ForbiddenException("Requires INSTRUCTOR or ADMIN role");
        }
    }

    private void requirePromotionApplicationOperator(EnrollmentPromotionApplication application, CurrentUser user) {
        requireInstructorOrAdmin(user);
        if (!isPlatformAdmin(user)) {
            courseAccess.requireCourseStaffAccess(user, application.getCourseId());
        }
    }

    private void requireRemediationCaseOperator(EnrollmentRemediationCase remediationCase, CurrentUser user) {
        requireAuthenticated(user);
        if (isService(user)) {
            return;
        }
        if (!isStaff(user)) {
            throw new ForbiddenException("Requires INSTRUCTOR, ADMIN, or service role");
        }
        if (!isPlatformAdmin(user)) {
            courseAccess.requireCourseStaffAccess(user, remediationCase.getCourseId());
        }
    }

    private void requireBenefitReconciliationAccess(Optional<UUID> courseId, CurrentUser user) {
        requireAuthenticated(user);
        if (isService(user) || isPlatformAdmin(user)) {
            return;
        }
        if (!isStaff(user)) {
            throw new ForbiddenException("Requires INSTRUCTOR, ADMIN, or service role");
        }
        UUID scopedCourse = courseId.orElseThrow(() ->
                new ForbiddenException("Staff benefit reconciliation reads must be scoped to a course"));
        courseAccess.requireCourseStaffAccess(user, scopedCourse);
    }

    private void requireCheckoutOperator(CurrentUser user) {
        requireAuthenticated(user);
        if (isService(user)) {
            return;
        }
        throw new ForbiddenException("Requires checkout or payment service role");
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
    }

    private String callerId(CurrentUser user) {
        requireAuthenticated(user);
        return String.valueOf(user.id());
    }

    private String normalizeCoupon(String couponCode) {
        if (couponCode == null || couponCode.isBlank()) {
            return null;
        }
        return couponCode.trim().toUpperCase();
    }

    private String normalizeText(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String actionReason(PromotionApplicationActionRequestDto request, String fallback) {
        if (request == null || request.reason() == null || request.reason().isBlank()) {
            return fallback;
        }
        return request.reason().trim();
    }

    private String actionNote(String note, String fallback) {
        String normalized = normalizeText(note);
        return normalized == null ? fallback : normalized;
    }

    private String actorId(CurrentUser user) {
        return callerId(user);
    }

    private String normalizePaymentStatus(String value) {
        String status = normalizeText(value);
        if (status == null) {
            throw new BadRequestException("paymentStatus is required");
        }
        String normalized = status.toUpperCase();
        if ("FAILED".equals(normalized)) {
            return "PAYMENT_FAILED";
        }
        if (Set.of("PAID", "PAYMENT_FAILED", "EXPIRED").contains(normalized)) {
            return normalized;
        }
        throw new BadRequestException("Invalid paymentStatus: " + value);
    }

    private Optional<String> paymentMismatch(EnrollmentOrder order, PaymentStatusUpdateRequestDto request) {
        if (request.paidAmount() == null) {
            return Optional.of("paidAmount is required to mark an enrollment order PAID");
        }
        if (normalizeText(request.currency()) == null) {
            return Optional.of("currency is required to mark an enrollment order PAID");
        }
        if (normalizeText(request.paymentProvider()) == null) {
            return Optional.of("paymentProvider is required to mark an enrollment order PAID");
        }
        if (normalizeText(request.paymentReference()) == null) {
            return Optional.of("paymentReference is required to mark an enrollment order PAID");
        }
        BigDecimal paidAmount = money(request.paidAmount());
        if (paidAmount.compareTo(order.getAmount()) != 0) {
            return Optional.of("Payment amount mismatch: expected "
                    + order.getAmount().toPlainString() + " but received " + paidAmount.toPlainString());
        }
        if (!order.getCurrency().equalsIgnoreCase(request.currency().trim())) {
            return Optional.of("Payment currency mismatch: expected "
                    + order.getCurrency() + " but received " + request.currency().trim().toUpperCase());
        }
        return Optional.empty();
    }

    private Optional<String> paidOrderReplayConflict(
            EnrollmentOrder order,
            String incomingStatus,
            PaymentStatusUpdateRequestDto request) {
        if (!"PAID".equals(incomingStatus)) {
            return Optional.of("Paid enrollment order received contradictory payment status " + incomingStatus);
        }
        Optional<String> mismatch = paymentMismatch(order, request);
        if (mismatch.isPresent()) {
            return mismatch;
        }
        String incomingProvider = normalizeText(request.paymentProvider());
        if (order.getPaymentProvider() != null && !order.getPaymentProvider().equalsIgnoreCase(incomingProvider)) {
            return Optional.of("Payment provider mismatch for paid order replay: expected "
                    + order.getPaymentProvider() + " but received " + incomingProvider);
        }
        String incomingReference = normalizeText(request.paymentReference());
        if (order.getPaymentReference() != null && !order.getPaymentReference().equals(incomingReference)) {
            return Optional.of("Payment reference mismatch for paid order replay");
        }
        return Optional.empty();
    }

    private Optional<String> duplicatePaymentReferenceConflict(
            EnrollmentOrder order,
            PaymentStatusUpdateRequestDto request) {
        String incomingProvider = normalizeText(request.paymentProvider());
        String incomingReference = normalizeText(request.paymentReference());
        if (incomingProvider == null || incomingReference == null) {
            return Optional.empty();
        }
        return orders.findByPaymentReferenceForUpdate(incomingProvider, incomingReference)
                .stream()
                .filter(existing -> !existing.getId().equals(order.getId()))
                .findFirst()
                .map(existing -> "Payment reference already belongs to enrollment order " + existing.getId());
    }

    private EnrollmentCheckoutResponseDto checkoutResponseForOrder(EnrollmentOrder order) {
        EnrollmentDto enrollment = enrollments.findById(order.getEnrollmentId()).orElse(null);
        EnrollmentPromotionApplicationDto promotion = promotionDtoForEnrollment(order.getEnrollmentId());
        String attemptId = checkoutAttemptId(order);
        return new EnrollmentCheckoutResponseDto(
                enrollment,
                promotion,
                attemptId,
                enrollmentOrderDto(order));
    }

    private String checkoutAttemptId(EnrollmentOrder order) {
        if (order.getCheckoutAttemptId() != null) {
            return order.getCheckoutAttemptId().toString();
        }
        if (checkoutAttempts == null) {
            return null;
        }
        return checkoutAttempts.findByEnrollmentId(order.getEnrollmentId())
                .map(attempt -> attempt.getId().toString())
                .orElse(null);
    }

    private EnrollmentPromotionApplicationDto promotionDtoForEnrollment(UUID enrollmentId) {
        if (promotionApplications == null || enrollmentId == null) {
            return new EnrollmentPromotionApplicationDto(
                    "SKIPPED",
                    null,
                    null,
                    null,
                    null,
                    List.of("COUPON_NOT_SUPPLIED"),
                    "Enrollment has no coupon application",
                    List.of());
        }
        return promotionApplications.findByEnrollmentId(enrollmentId)
                .map(this::promotionApplicationDto)
                .orElseGet(() -> new EnrollmentPromotionApplicationDto(
                        "SKIPPED",
                        null,
                        null,
                        null,
                        null,
                        List.of("COUPON_NOT_SUPPLIED"),
                        "Enrollment has no coupon application",
                        List.of()));
    }

    private void syncCheckoutAttemptForOrder(EnrollmentOrder order) {
        if (checkoutAttempts == null || order == null) {
            return;
        }
        Optional<EnrollmentCheckoutAttempt> found = order.getCheckoutAttemptId() == null
                ? checkoutAttempts.findByEnrollmentId(order.getEnrollmentId())
                : checkoutAttempts.findById(order.getCheckoutAttemptId());
        found.ifPresent(attempt -> {
            EnrollmentCheckoutResponseDto response = checkoutResponseForOrder(order);
            String responseJson = toJson(response);
            EnrollmentPromotionApplicationDto promotion = response.promotion();
            String attemptStatus = checkoutAttemptStatusForOrder(order, promotion);
            if ("COMMIT_FAILED".equals(attemptStatus)) {
                Instant nextRetryAt = promotionApplications == null
                        ? nextPromotionCommitRetryAt(attempt)
                        : promotionApplications.findByEnrollmentId(order.getEnrollmentId())
                                .map(EnrollmentPromotionApplication::getNextRetryAt)
                                .orElse(nextPromotionCommitRetryAt(attempt));
                attempt.retryFailed(
                        promotion == null ? "Promotion commit is pending retry" : promotion.message(),
                        nextRetryAt == null ? nextPromotionCommitRetryAt(attempt) : nextRetryAt,
                        responseJson);
            } else {
                UUID redemptionId = promotionApplications == null
                        ? null
                        : promotionApplications.findByEnrollmentId(order.getEnrollmentId())
                                .map(EnrollmentPromotionApplication::getRedemptionId)
                                .orElse(null);
                attempt.finish(attemptStatus, responseJson, redemptionId);
            }
            checkoutAttempts.save(attempt);
        });
    }

    private String checkoutAttemptStatusForOrder(
            EnrollmentOrder order,
            EnrollmentPromotionApplicationDto promotion) {
        return switch (order.getStatus()) {
            case "PAYMENT_PENDING" -> "PAYMENT_PENDING";
            case "PAYMENT_FAILED", "EXPIRED" -> "FAILED";
            case "MANUAL_REVIEW" -> "MANUAL_REVIEW";
            case "PAID" -> checkoutAttemptStatus(promotion == null ? "SKIPPED" : promotion.status());
            default -> "MANUAL_REVIEW";
        };
    }

    private Map<String, Object> remediationPayload(
            String reasonCode,
            String subjectStatus,
            String correlationId) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("reasonCode", reasonCode == null ? "" : reasonCode);
        payload.put("subjectStatus", subjectStatus == null ? "" : subjectStatus);
        payload.put("correlationId", correlationId == null ? "" : correlationId);
        return payload;
    }

    private String retryStateNote(EnrollmentPromotionApplication application) {
        if ("COMMIT_FAILED".equals(application.getStatus())) {
            return "Next promotion commit retry is scheduled at "
                    + (application.getNextRetryAt() == null ? "unscheduled" : application.getNextRetryAt());
        }
        if ("RESERVED".equals(application.getStatus())) {
            return "Coupon reservation is waiting for payment success or operator action before commit retry";
        }
        return "Promotion application is not currently retryable";
    }

    private RefundDropPolicyActionDto dropPolicyAction(EnrollmentDto enrollment, String reason) {
        String enrollmentStatus = upper(enrollment.status());
        if ("COMPLETED".equals(enrollmentStatus)) {
            return policyAction(
                    "ENROLLMENT",
                    "DROP_ENROLLMENT",
                    "MANUAL_REVIEW",
                    "HIGH",
                    false,
                    true,
                    true,
                    "/internal/enrollments/" + enrollment.id() + "/status",
                    policyKey(enrollment.id(), "drop"),
                    List.of("COURSE_COMPLETED", "COMPLETED_ENROLLMENT_DROP_REQUIRES_REVIEW"),
                    evidence("enrollmentStatus", enrollment.status(), "completedAt", enrollment.completedAt()));
        }
        if ("DROPPED".equals(enrollmentStatus)) {
            return policyAction(
                    "ENROLLMENT",
                    "DROP_ENROLLMENT",
                    "ALREADY_DONE",
                    "LOW",
                    false,
                    false,
                    false,
                    "/internal/enrollments/" + enrollment.id() + "/status",
                    policyKey(enrollment.id(), "drop"),
                    List.of("ENROLLMENT_ALREADY_DROPPED"),
                    evidence("droppedAt", enrollment.droppedAt(), "dropReason", enrollment.dropReason()));
        }
        if (Set.of("ACTIVE", "PENDING_PAYMENT").contains(enrollmentStatus)) {
            return policyAction(
                    "ENROLLMENT",
                    "DROP_ENROLLMENT",
                    "REQUIRED",
                    "MEDIUM",
                    true,
                    false,
                    false,
                    "/internal/enrollments/" + enrollment.id() + "/status",
                    policyKey(enrollment.id(), "drop"),
                    List.of("DROP_ALLOWED", reason == null || reason.isBlank() ? "OPERATOR_REASON_RECOMMENDED" : "OPERATOR_REASON_SUPPLIED"),
                    evidence("targetStatus", "DROPPED", "reason", normalizeText(reason)));
        }
        return policyAction(
                "ENROLLMENT",
                "DROP_ENROLLMENT",
                "MANUAL_REVIEW",
                "HIGH",
                false,
                true,
                true,
                "/internal/enrollments/" + enrollment.id() + "/status",
                policyKey(enrollment.id(), "drop"),
                List.of("UNKNOWN_ENROLLMENT_STATUS"),
                evidence("enrollmentStatus", enrollment.status()));
    }

    private RefundDropPolicyActionDto paymentRefundPolicyAction(
            EnrollmentDto enrollment,
            RefundDropPolicyFactsDto facts) {
        String paymentStatus = upper(facts.paymentStatus());
        if (Set.of("PAYMENT_PENDING", "PAYMENT_FAILED", "FAILED", "EXPIRED", "CANCELLED").contains(paymentStatus)) {
            return policyAction(
                    "PAYMENT",
                    "REFUND_PAYMENT",
                    "NOT_REQUIRED",
                    "LOW",
                    false,
                    false,
                    false,
                    "payment-provider://refunds",
                    policyKey(enrollment.id(), "refund-payment"),
                    List.of("PAYMENT_NOT_SETTLED"),
                    evidence("orderId", facts.orderId(), "paymentStatus", paymentStatus));
        }
        if (facts.orderId() == null || facts.paidAmount().compareTo(ZERO_MONEY) <= 0 || paymentStatus == null) {
            return policyAction(
                    "PAYMENT",
                    "REFUND_PAYMENT",
                    "NOT_REQUIRED",
                    "LOW",
                    false,
                    false,
                    false,
                    "payment-provider://refunds",
                    policyKey(enrollment.id(), "refund-payment"),
                    List.of("NO_SETTLED_PAYMENT"),
                    evidence("orderId", facts.orderId(), "paymentStatus", paymentStatus, "paidAmount", facts.paidAmount()));
        }
        if ("PAID".equals(paymentStatus)) {
            if ("COMPLETED".equals(upper(facts.enrollmentStatus()))) {
                return policyAction(
                        "PAYMENT",
                        "REFUND_PAYMENT",
                        "MANUAL_REVIEW",
                        "CRITICAL",
                        false,
                        true,
                        true,
                        "payment-provider://refunds",
                        policyKey(enrollment.id(), "refund-payment"),
                        List.of("COURSE_COMPLETED", "REFUND_REQUIRES_FINANCE_APPROVAL"),
                        evidence("orderId", facts.orderId(), "paidAt", facts.paidAt()));
            }
            if (facts.withinRefundWindow()) {
                return policyAction(
                        "PAYMENT",
                        "REFUND_PAYMENT",
                        "REQUIRED",
                        "HIGH",
                        true,
                        true,
                        true,
                        "payment-provider://refunds",
                        policyKey(enrollment.id(), "refund-payment"),
                        List.of("REFUND_WINDOW_OPEN", "PAYMENT_REFUND_REQUIRED"),
                        evidence(
                                "orderId", facts.orderId(),
                                "amount", facts.paidAmount(),
                                "currency", facts.currency(),
                                "refundWindowEndsAt", facts.refundWindowEndsAt()));
            }
            return policyAction(
                    "PAYMENT",
                    "REFUND_PAYMENT",
                    "MANUAL_REVIEW",
                    "HIGH",
                    false,
                    true,
                    true,
                    "payment-provider://refunds",
                    policyKey(enrollment.id(), "refund-payment"),
                    List.of("REFUND_WINDOW_CLOSED", "REFUND_REQUIRES_FINANCE_APPROVAL"),
                    evidence("orderId", facts.orderId(), "refundWindowEndsAt", facts.refundWindowEndsAt()));
        }
        return policyAction(
                "PAYMENT",
                "REFUND_PAYMENT",
                "MANUAL_REVIEW",
                "HIGH",
                false,
                true,
                true,
                "payment-provider://refunds",
                policyKey(enrollment.id(), "refund-payment"),
                List.of("PAYMENT_STATUS_REQUIRES_REVIEW"),
                evidence("orderId", facts.orderId(), "paymentStatus", paymentStatus));
    }

    private RefundDropPolicyActionDto promotionPolicyAction(
            EnrollmentDto enrollment,
            RefundDropPolicyFactsDto facts) {
        String promotionStatus = upper(facts.promotionStatus());
        if (promotionStatus == null || Set.of("SKIPPED", "UNAVAILABLE").contains(promotionStatus)) {
            return policyAction(
                    "PROMOTION",
                    "CLOSE_PROMOTION_BENEFIT",
                    "NOT_REQUIRED",
                    "LOW",
                    false,
                    false,
                    false,
                    "/internal/incentives/redemptions/{redemptionId}/reverse",
                    policyKey(enrollment.id(), "promotion-close"),
                    List.of("NO_PROMOTION_BENEFIT"),
                    evidence("promotionStatus", promotionStatus));
        }
        if (Set.of("REVERSED", "CANCELLED").contains(promotionStatus)) {
            return policyAction(
                    "PROMOTION",
                    "CLOSE_PROMOTION_BENEFIT",
                    "ALREADY_DONE",
                    "LOW",
                    false,
                    false,
                    false,
                    "/internal/incentives/redemptions/{redemptionId}/reverse",
                    policyKey(enrollment.id(), "promotion-close"),
                    List.of("PROMOTION_ALREADY_CLOSED"),
                    evidence("promotionStatus", promotionStatus, "redemptionId", facts.redemptionId()));
        }
        if (Set.of("RESERVED", "COMMIT_FAILED").contains(promotionStatus)) {
            if (facts.reservationId() == null) {
                return policyAction(
                        "PROMOTION",
                        "CANCEL_PROMOTION_RESERVATION",
                        "MANUAL_REVIEW",
                        "HIGH",
                        false,
                        true,
                        true,
                        "/internal/incentives/reservations/{reservationId}/cancel",
                        policyKey(enrollment.id(), "promotion-cancel"),
                        List.of("RESERVATION_ID_MISSING", "PROMOTION_RESERVATION_REQUIRES_REMEDIATION"),
                        evidence("promotionStatus", promotionStatus));
            }
            return policyAction(
                    "PROMOTION",
                    "CANCEL_PROMOTION_RESERVATION",
                    "REQUIRED",
                    "HIGH",
                    true,
                    true,
                    false,
                    "/internal/incentives/reservations/" + facts.reservationId() + "/cancel",
                    policyKey(enrollment.id(), "promotion-cancel"),
                    List.of("PROMOTION_RESERVATION_CANCEL_REQUIRED"),
                    evidence("promotionStatus", promotionStatus, "reservationId", facts.reservationId()));
        }
        if ("APPLIED".equals(promotionStatus)) {
            if (facts.redemptionId() == null) {
                return policyAction(
                        "PROMOTION",
                        "REVERSE_PROMOTION_REDEMPTION",
                        "MANUAL_REVIEW",
                        "CRITICAL",
                        false,
                        true,
                        true,
                        "/internal/incentives/redemptions/{redemptionId}/reverse",
                        policyKey(enrollment.id(), "promotion-reverse"),
                        List.of("REDEMPTION_ID_MISSING", "PROMOTION_REVERSE_REQUIRES_REMEDIATION"),
                        evidence("promotionStatus", promotionStatus));
            }
            return policyAction(
                    "PROMOTION",
                    "REVERSE_PROMOTION_REDEMPTION",
                    "REQUIRED",
                    "CRITICAL",
                    true,
                    true,
                    true,
                    "/internal/incentives/redemptions/" + facts.redemptionId() + "/reverse",
                    policyKey(enrollment.id(), "promotion-reverse"),
                    List.of("PROMOTION_REDEMPTION_REVERSE_REQUIRED"),
                    evidence("promotionStatus", promotionStatus, "redemptionId", facts.redemptionId()));
        }
        return policyAction(
                "PROMOTION",
                "CLOSE_PROMOTION_BENEFIT",
                "MANUAL_REVIEW",
                "HIGH",
                false,
                true,
                true,
                "/internal/enrollments/remediation-cases",
                policyKey(enrollment.id(), "promotion-review"),
                List.of("PROMOTION_STATUS_REQUIRES_REVIEW"),
                evidence("promotionStatus", promotionStatus));
    }

    private RefundDropPolicyActionDto pointsClawbackPolicyAction(
            EnrollmentDto enrollment,
            RefundDropPolicyFactsDto facts) {
        if (facts.loyaltyPointsEarned() <= 0) {
            return policyAction(
                    "LOYALTY",
                    "CLAWBACK_LOYALTY_POINTS",
                    "NOT_REQUIRED",
                    "LOW",
                    false,
                    false,
                    false,
                    "/internal/loyalty/points/{entryId}:reverse",
                    policyKey(enrollment.id(), "points-clawback"),
                    List.of("NO_LOYALTY_POINTS_EARNED"),
                    evidence("loyaltyPointsEarned", facts.loyaltyPointsEarned()));
        }
        if (facts.loyaltyPointsOutstanding() <= 0) {
            return policyAction(
                    "LOYALTY",
                    "CLAWBACK_LOYALTY_POINTS",
                    "ALREADY_DONE",
                    "LOW",
                    false,
                    false,
                    false,
                    "/internal/loyalty/points/{entryId}:reverse",
                    policyKey(enrollment.id(), "points-clawback"),
                    List.of("LOYALTY_POINTS_ALREADY_REVERSED"),
                    evidence(
                            "loyaltyPointsEarned", facts.loyaltyPointsEarned(),
                            "loyaltyPointsReversed", facts.loyaltyPointsReversed()));
        }
        if (facts.loyaltyEarnEntryId() == null) {
            return policyAction(
                    "LOYALTY",
                    "CLAWBACK_LOYALTY_POINTS",
                    "MANUAL_REVIEW",
                    "HIGH",
                    false,
                    true,
                    true,
                    "/internal/loyalty/reconciliation/entries",
                    policyKey(enrollment.id(), "points-clawback"),
                    List.of("LOYALTY_EARN_ENTRY_REQUIRED", "POINT_CLAWBACK_REQUIRES_RECONCILIATION"),
                    evidence("loyaltyPointsOutstanding", facts.loyaltyPointsOutstanding()));
        }
        return policyAction(
                "LOYALTY",
                "CLAWBACK_LOYALTY_POINTS",
                "REQUIRED",
                "HIGH",
                true,
                true,
                true,
                "/internal/loyalty/points/" + facts.loyaltyEarnEntryId() + ":reverse",
                policyKey(enrollment.id(), "points-clawback"),
                List.of("LOYALTY_POINTS_CLAWBACK_REQUIRED"),
                evidence(
                        "loyaltyEarnEntryId", facts.loyaltyEarnEntryId(),
                        "loyaltyPointsOutstanding", facts.loyaltyPointsOutstanding()));
    }

    private RefundDropPolicyActionDto rewardReversalPolicyAction(
            EnrollmentDto enrollment,
            RefundDropPolicyFactsDto facts) {
        String rewardStatus = upper(firstText(facts.rewardStatus(), facts.rewardFulfillmentStatus()));
        if (rewardStatus == null && facts.rewardRedemptionId() == null) {
            return policyAction(
                    "LOYALTY",
                    "REVERSE_REWARD_REDEMPTION",
                    "NOT_REQUIRED",
                    "LOW",
                    false,
                    false,
                    false,
                    "/internal/loyalty/reward-redemptions/{redemptionId}:reverse",
                    policyKey(enrollment.id(), "reward-reverse"),
                    List.of("NO_REWARD_REDEMPTION_FACTS"),
                    evidence());
        }
        if (Set.of("REVERSED", "CANCELLED").contains(rewardStatus)) {
            return policyAction(
                    "LOYALTY",
                    "REVERSE_REWARD_REDEMPTION",
                    "ALREADY_DONE",
                    "LOW",
                    false,
                    false,
                    false,
                    "/internal/loyalty/reward-redemptions/{redemptionId}:reverse",
                    policyKey(enrollment.id(), "reward-reverse"),
                    List.of("REWARD_REDEMPTION_ALREADY_REVERSED"),
                    evidence("rewardStatus", rewardStatus, "rewardRedemptionId", facts.rewardRedemptionId()));
        }
        if ("FAILED".equals(rewardStatus)) {
            return policyAction(
                    "LOYALTY",
                    "REVERSE_REWARD_REDEMPTION",
                    "NOT_REQUIRED",
                    "MEDIUM",
                    false,
                    false,
                    false,
                    "/internal/loyalty/reward-redemptions/{redemptionId}:reverse",
                    policyKey(enrollment.id(), "reward-reverse"),
                    List.of("REWARD_FULFILLMENT_FAILED"),
                    evidence("rewardStatus", rewardStatus, "rewardRedemptionId", facts.rewardRedemptionId()));
        }
        boolean reversalCandidate = Boolean.TRUE.equals(facts.rewardFulfilled())
                || Set.of("COMMITTED", "PENDING", "ISSUED", "MANUAL_REQUIRED", "FULFILLED").contains(rewardStatus)
                || facts.rewardRedemptionId() != null;
        if (reversalCandidate && facts.rewardRedemptionId() == null) {
            return policyAction(
                    "LOYALTY",
                    "REVERSE_REWARD_REDEMPTION",
                    "MANUAL_REVIEW",
                    "HIGH",
                    false,
                    true,
                    true,
                    "/internal/loyalty/reward-redemptions",
                    policyKey(enrollment.id(), "reward-reverse"),
                    List.of("REWARD_REDEMPTION_ID_REQUIRED", "REWARD_REVERSAL_REQUIRES_RECONCILIATION"),
                    evidence("rewardStatus", rewardStatus, "rewardFulfillmentStatus", facts.rewardFulfillmentStatus()));
        }
        if (reversalCandidate) {
            return policyAction(
                    "LOYALTY",
                    "REVERSE_REWARD_REDEMPTION",
                    "REQUIRED",
                    "HIGH",
                    true,
                    true,
                    true,
                    "/internal/loyalty/reward-redemptions/" + facts.rewardRedemptionId() + ":reverse",
                    policyKey(enrollment.id(), "reward-reverse"),
                    List.of("REWARD_REDEMPTION_REVERSE_REQUIRED"),
                    evidence(
                            "rewardStatus", rewardStatus,
                            "rewardFulfillmentStatus", facts.rewardFulfillmentStatus(),
                            "rewardRedemptionId", facts.rewardRedemptionId()));
        }
        return policyAction(
                "LOYALTY",
                "REVERSE_REWARD_REDEMPTION",
                "MANUAL_REVIEW",
                "MEDIUM",
                false,
                true,
                true,
                "/internal/loyalty/reward-redemptions",
                policyKey(enrollment.id(), "reward-reverse"),
                List.of("REWARD_STATUS_REQUIRES_REVIEW"),
                evidence("rewardStatus", rewardStatus));
    }

    private RefundDropPolicyActionDto policyAction(
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
            Map<String, Object> evidence) {
        return new RefundDropPolicyActionDto(
                domain,
                action,
                decision,
                severity,
                required,
                blocking,
                makerCheckerRequired,
                endpoint,
                idempotencyKey,
                reasonCodes == null ? List.of() : reasonCodes,
                evidence == null ? Map.of() : evidence);
    }

    private String policyKey(String enrollmentId, String action) {
        return "refund-drop-" + action + "-" + enrollmentId;
    }

    private Map<String, Object> evidence(Object... pairs) {
        Map<String, Object> evidence = new HashMap<>();
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            Object key = pairs[i];
            Object value = pairs[i + 1];
            if (key != null && value != null) {
                evidence.put(String.valueOf(key), value);
            }
        }
        return evidence;
    }

    private String firstText(String... values) {
        for (String value : values) {
            String normalized = normalizeText(value);
            if (normalized != null) {
                return normalized;
            }
        }
        return null;
    }

    private long nonNegative(Long value) {
        if (value == null) {
            return 0L;
        }
        if (value < 0) {
            throw new BadRequestException("Loyalty point facts must be non-negative");
        }
        return value;
    }

    private int refundWindowDays(Integer value) {
        int days = value == null ? 14 : value;
        if (days < 0 || days > 365) {
            throw new BadRequestException("refundWindowDays must be between 0 and 365");
        }
        return days;
    }

    private String maxSeverity(List<RefundDropPolicyActionDto> actions) {
        return actions.stream()
                .map(RefundDropPolicyActionDto::severity)
                .max((left, right) -> Integer.compare(severityRank(left), severityRank(right)))
                .orElse("LOW");
    }

    private int severityRank(String value) {
        return switch (upper(value)) {
            case "CRITICAL" -> 4;
            case "HIGH" -> 3;
            case "MEDIUM" -> 2;
            default -> 1;
        };
    }

    private String normalizeStatus(String value) {
        String status = normalizeText(value);
        if (status == null) {
            return null;
        }
        String normalized = status.toUpperCase();
        Set<String> allowed = Set.of(
                "RESERVED",
                "APPLIED",
                "COMMIT_FAILED",
                "SKIPPED",
                "UNAVAILABLE",
                "REVERSED",
                "CANCELLED",
                "MANUAL_REVIEW");
        if (!allowed.contains(normalized)) {
            throw new BadRequestException("Invalid promotion application status: " + value);
        }
        return normalized;
    }

    private String normalizeReconciliationStatus(String value) {
        String status = normalizeText(value);
        if (status == null) {
            return null;
        }
        String normalized = status.toUpperCase();
        Set<String> allowed = Set.of(
                "MATCHED",
                "ACTIVE_WITH_UNPAID_ORDER",
                "DROPPED_PROMOTION_NOT_REVERSED",
                "DROPPED_PROMOTION_HOLD_OPEN",
                "PAYMENT_FAILED_PROMOTION_OPEN",
                "PAID_ORDER_NOT_ACTIVE",
                "COMMIT_FAILED_WITH_PAID_ORDER",
                "PROMOTION_COMMIT_FAILED",
                "PROMOTION_MANUAL_REVIEW",
                "PROMOTION_RESERVED_STALE",
                "PAYMENT_PENDING_STALE",
                "PROMOTION_APPLIED_MISSING_REDEMPTION");
        if (!allowed.contains(normalized)) {
            throw new BadRequestException("Invalid enrollment benefit reconciliation status: " + value);
        }
        return normalized;
    }

    private EnrollmentBenefitReconciliationEntryDto reconciliationEntry(
            EnrollmentBenefitReconciliationRow row,
            BenefitFinding finding) {
        return new EnrollmentBenefitReconciliationEntryDto(
                reconciliationKey(row),
                finding.status(),
                finding.reasonCodes(),
                finding.severity(),
                uuidString(row.getEnrollmentId()),
                row.getStudentId(),
                uuidString(row.getCourseId()),
                row.getEnrollmentStatus(),
                row.getEnrolledAt(),
                row.getDroppedAt(),
                row.getDropReason(),
                uuidString(row.getOrderId()),
                row.getOrderStatus(),
                row.getOrderAmount(),
                row.getOrderCurrency(),
                row.getPaidAt(),
                row.getOrderCreatedAt(),
                row.getOrderUpdatedAt(),
                uuidString(row.getPromotionApplicationId()),
                row.getPromotionStatus(),
                uuidString(row.getReservationId()),
                uuidString(row.getRedemptionId()),
                row.getPromotionRetryCount() == null ? 0 : row.getPromotionRetryCount(),
                row.getPromotionNextRetryAt(),
                row.getPromotionLastRetryError(),
                row.getPromotionUpdatedAt());
    }

    private BenefitFinding benefitFinding(EnrollmentBenefitReconciliationRow row, Instant staleCutoff) {
        String enrollmentStatus = upper(row.getEnrollmentStatus());
        String orderStatus = upper(row.getOrderStatus());
        String promotionStatus = upper(row.getPromotionStatus());
        if (isActiveLike(enrollmentStatus)
                && row.getOrderId() != null
                && !"PAID".equals(orderStatus)) {
            return finding(
                    "ACTIVE_WITH_UNPAID_ORDER",
                    "CRITICAL",
                    "Enrollment is active/completed but its paid order is not PAID");
        }
        if ("DROPPED".equals(enrollmentStatus) && promotionNeedsClosure(promotionStatus)) {
            if ("APPLIED".equals(promotionStatus)) {
                return finding(
                        "DROPPED_PROMOTION_NOT_REVERSED",
                        "CRITICAL",
                        "Enrollment is dropped but committed promotion redemption is not reversed");
            }
            return finding(
                    "DROPPED_PROMOTION_HOLD_OPEN",
                    "HIGH",
                    "Enrollment is dropped but promotion reservation/application is still open");
        }
        if (paymentFailed(orderStatus) && promotionNeedsClosure(promotionStatus)) {
            return finding(
                    "PAYMENT_FAILED_PROMOTION_OPEN",
                    "HIGH",
                    "Payment failed or needs review but promotion reservation/application is still open");
        }
        if ("PAID".equals(orderStatus) && "PENDING_PAYMENT".equals(enrollmentStatus)) {
            return finding(
                    "PAID_ORDER_NOT_ACTIVE",
                    "HIGH",
                    "Order is PAID but enrollment has not been activated");
        }
        if ("APPLIED".equals(promotionStatus) && row.getRedemptionId() == null) {
            return finding(
                    "PROMOTION_APPLIED_MISSING_REDEMPTION",
                    "HIGH",
                    "Promotion application is APPLIED but redemptionId is missing");
        }
        if ("COMMIT_FAILED".equals(promotionStatus) && "PAID".equals(orderStatus)) {
            return finding(
                    "COMMIT_FAILED_WITH_PAID_ORDER",
                    "HIGH",
                    "Paid checkout succeeded but promotion commit is still failed");
        }
        if ("COMMIT_FAILED".equals(promotionStatus)) {
            return finding(
                    "PROMOTION_COMMIT_FAILED",
                    "HIGH",
                    "Promotion commit failed and needs retry or manual remediation");
        }
        if ("MANUAL_REVIEW".equals(promotionStatus)) {
            return finding(
                    "PROMOTION_MANUAL_REVIEW",
                    "HIGH",
                    "Promotion application is in manual review");
        }
        if ("RESERVED".equals(promotionStatus) && olderThan(row.getPromotionUpdatedAt(), staleCutoff)) {
            return finding(
                    "PROMOTION_RESERVED_STALE",
                    "MEDIUM",
                    "Promotion reservation is still RESERVED past the operating window");
        }
        if ("PAYMENT_PENDING".equals(orderStatus) && olderThan(row.getOrderCreatedAt(), staleCutoff)) {
            return finding(
                    "PAYMENT_PENDING_STALE",
                    "MEDIUM",
                    "Enrollment order is PAYMENT_PENDING past the operating window");
        }
        return new BenefitFinding("MATCHED", List.of(), "LOW");
    }

    private BenefitFinding finding(String status, String severity, String reason) {
        return new BenefitFinding(status, List.of(status, reason), severity);
    }

    private String reconciliationKey(EnrollmentBenefitReconciliationRow row) {
        String promotion = row.getPromotionApplicationId() == null
                ? "no-promotion"
                : row.getPromotionApplicationId().toString();
        String order = row.getOrderId() == null ? "no-order" : row.getOrderId().toString();
        return row.getEnrollmentId() + ":" + order + ":" + promotion;
    }

    private boolean isActiveLike(String enrollmentStatus) {
        return "ACTIVE".equals(enrollmentStatus) || "COMPLETED".equals(enrollmentStatus);
    }

    private boolean paymentFailed(String orderStatus) {
        return orderStatus != null && Set.of("PAYMENT_FAILED", "FAILED", "CANCELLED", "EXPIRED", "MANUAL_REVIEW")
                .contains(orderStatus);
    }

    private boolean promotionNeedsClosure(String promotionStatus) {
        return promotionStatus != null
                && !Set.of("REVERSED", "CANCELLED", "SKIPPED", "UNAVAILABLE").contains(promotionStatus);
    }

    private boolean olderThan(Instant value, Instant cutoff) {
        return value != null && value.isBefore(cutoff);
    }

    private String upper(String value) {
        return value == null ? null : value.trim().toUpperCase();
    }

    private String uuidString(UUID value) {
        return value == null ? null : value.toString();
    }

    private record BenefitFinding(String status, List<String> reasonCodes, String severity) {
    }

    private String normalizeRemediationStatus(String value) {
        String status = normalizeText(value);
        if (status == null) {
            return null;
        }
        String normalized = status.toUpperCase();
        if (!Set.of("OPEN", "IN_PROGRESS", "RESOLVED").contains(normalized)) {
            throw new BadRequestException("Invalid remediation case status: " + value);
        }
        return normalized;
    }

    private String reserveKey(EnrollRequestDto request) {
        return operationKey(request.idempotencyKey(), "reserve");
    }

    private String commitKey(String idempotencyKey) {
        return operationKey(idempotencyKey, "commit");
    }

    private String commitKey(EnrollmentPromotionApplication application) {
        return operationKey(applicationKey(application), "commit");
    }

    private String cancelKey(EnrollRequestDto request) {
        return operationKey(request.idempotencyKey(), "cancel");
    }

    private String cancelKey(EnrollmentPromotionApplication application) {
        return operationKey(applicationKey(application), "cancel");
    }

    private String reverseKey(EnrollmentPromotionApplication application) {
        return operationKey(applicationKey(application), "reverse");
    }

    private String applicationKey(EnrollmentPromotionApplication application) {
        String base = normalizeText(application.getIdempotencyKey());
        return base == null ? application.getEnrollmentId().toString() : base;
    }

    private String operationKey(String idempotencyKey, String operation) {
        String base = idempotencyKey == null || idempotencyKey.isBlank()
                ? UUID.randomUUID().toString()
                : idempotencyKey.trim();
        return "enrollment-promotion-" + operation + "-" + base;
    }

    private String dropReversalReason(EnrollmentDto enrollment, String reason) {
        String suffix = normalizeText(reason);
        String base = "Enrollment dropped: " + enrollment.id();
        return suffix == null ? base : base + " - " + suffix;
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("INSTRUCTOR", "PROFESSOR", "TA", "ORG_ADMIN", "ADMIN");
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasRole("ADMIN");
    }

    private boolean isService(CurrentUser user) {
        return user != null && user.hasAnyRole("SERVICE", "CHECKOUT_SERVICE");
    }

    private String sha256Hex(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("Unable to hash checkout idempotency data", ex);
        }
    }

    private UUID parseUuid(String raw, String field) {
        try {
            return UUID.fromString(raw);
        } catch (RuntimeException ex) {
            throw new BadRequestException("Invalid " + field + ": " + raw);
        }
    }

    private UUID parseOptionalUuid(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(raw);
        } catch (RuntimeException ex) {
            throw new BadRequestException("Invalid couponId: " + raw);
        }
    }

    private <T> List<T> readList(String json, TypeReference<List<T>> type) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<T> result = objectMapper.readValue(json, type);
            return result == null ? List.of() : result;
        } catch (JsonProcessingException ex) {
            return List.of();
        }
    }

    private Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> result = objectMapper.readValue(json, OBJECT_MAP);
            return result == null ? Map.of() : result;
        } catch (JsonProcessingException ex) {
            return Map.of();
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }

    private record CheckoutAttemptClaim(
            EnrollmentCheckoutAttempt attempt,
            EnrollmentCheckoutResponseDto replay
    ) {
    }
}
