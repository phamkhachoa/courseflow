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
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentCheckoutResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentPromotionApplicationDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentPromotionApplicationStateDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentStatsDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.LearnerCouponWalletDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionApplicationActionRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionEffectDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionPreviewDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionPreviewRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.SetCapacityRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistRequestDto;
import edu.courseflow.enrollment.exception.ForbiddenException;
import edu.courseflow.enrollment.model.EnrollmentCheckoutAttempt;
import edu.courseflow.enrollment.model.EnrollmentPromotionApplication;
import edu.courseflow.enrollment.repository.EnrollmentRepository;
import edu.courseflow.enrollment.repository.EnrollmentCheckoutAttemptJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentPromotionApplicationJpaRepository;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.CancelResult;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.CommitResult;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.PromotionUnavailableException;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.ReservationResult;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.ReverseResult;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class EnrollmentService {

    /**
     * Allowed enrollment status transitions.
     * <ul>
     *   <li>ACTIVE    -> DROPPED, COMPLETED</li>
     *   <li>DROPPED   -> ACTIVE (re-enroll)</li>
     *   <li>COMPLETED -> (terminal: no transitions)</li>
     * </ul>
     * A no-op transition to the same status is rejected as a bad request.
     */
    private static final Map<String, Set<String>> ALLOWED_TRANSITIONS = Map.of(
            "ACTIVE", Set.of("DROPPED", "COMPLETED"),
            "DROPPED", Set.of("ACTIVE"),
            "COMPLETED", Set.of());
    private static final TypeReference<List<String>> STRING_LIST = new TypeReference<>() {
    };
    private static final TypeReference<List<PromotionEffectDto>> PROMOTION_EFFECT_LIST = new TypeReference<>() {
    };

    private final EnrollmentRepository enrollments;
    private final EnrollmentCheckoutAttemptJpaRepository checkoutAttempts;
    private final EnrollmentPromotionApplicationJpaRepository promotionApplications;
    private final ObjectMapper objectMapper;
    private final CourseAccessClient courseAccess;
    private final PromotionEnrollmentClient promotions;

    public EnrollmentService(EnrollmentRepository enrollments, ObjectMapper objectMapper, CourseAccessClient courseAccess) {
        this(enrollments, null, null, objectMapper, courseAccess, null);
    }

    public EnrollmentService(EnrollmentRepository enrollments,
                             EnrollmentPromotionApplicationJpaRepository promotionApplications,
                             ObjectMapper objectMapper,
                             CourseAccessClient courseAccess,
                             PromotionEnrollmentClient promotions) {
        this(enrollments, null, promotionApplications, objectMapper, courseAccess, promotions);
    }

    @Autowired
    public EnrollmentService(EnrollmentRepository enrollments,
                             EnrollmentCheckoutAttemptJpaRepository checkoutAttempts,
                             EnrollmentPromotionApplicationJpaRepository promotionApplications,
                             ObjectMapper objectMapper,
                             CourseAccessClient courseAccess,
                             PromotionEnrollmentClient promotions) {
        this.enrollments = enrollments;
        this.checkoutAttempts = checkoutAttempts;
        this.promotionApplications = promotionApplications;
        this.objectMapper = objectMapper;
        this.courseAccess = courseAccess;
        this.promotions = promotions;
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
        CheckoutAttemptClaim attemptClaim = claimCheckoutAttempt(request, courseId, studentId, couponCode, couponId);
        if (attemptClaim.replay() != null) {
            return attemptClaim.replay();
        }
        EnrollmentCheckoutAttempt attempt = attemptClaim.attempt();
        ReservationResult reservation = ReservationResult.skipped(couponCode, couponId);
        boolean hasPromotionSelector = couponCode != null || couponId != null;
        if (hasPromotionSelector && promotions == null) {
            throw new ConflictException("Promotion service is required when a coupon is supplied");
        } else if (hasPromotionSelector) {
            try {
                validatePromotionPreview(request, courseId, studentId, couponCode, couponId);
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
            EnrollmentDto enrollment = createEnrollment(request, user);
            markAttemptEnrollmentCreated(attempt, enrollment);
            EnrollmentPromotionApplicationDto promotion = promotionApplication(
                    couponCode,
                    couponId,
                    reservation,
                    enrollment,
                    false,
                    request.idempotencyKey(),
                    attempt);
            EnrollmentCheckoutResponseDto response = new EnrollmentCheckoutResponseDto(
                    enrollment,
                    promotion,
                    attempt == null ? null : attempt.getId().toString());
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

    private void validatePromotionPreview(
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
    }

    private EnrollmentDto createEnrollment(EnrollRequestDto request, CurrentUser user) {
        UUID courseId = parseUuid(request.courseId(), "courseId");
        courseAccess.requirePublishedCourse(courseId);
        String studentId = resolveTargetStudent(request.studentId(), user, courseId);

        enrollments.find(studentId, courseId).ifPresent(existing -> {
            if ("ACTIVE".equals(existing.status())) {
                throw new ConflictException("Student already actively enrolled");
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
            if (enrollment != null) {
                syncCheckoutAttempt(enrollment, application);
            }
            return promotionApplicationState(application);
        }
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
            } else {
                application.update(
                        "MANUAL_REVIEW",
                        commit.redemptionId(),
                        toJson(reasonsOr(commit.reasonCodes(), "PROMOTION_COMMIT_REJECTED")),
                        toJson(effects),
                        "Coupon reservation could not be committed after retry");
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
            EnrollmentCheckoutResponseDto response = new EnrollmentCheckoutResponseDto(
                    enrollment,
                    promotion,
                    attempt.getId().toString());
            String responseJson = toJson(response);
            String attemptStatus = checkoutAttemptStatus(application.getStatus());
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
        int active = enrollments.countActive(courseId);
        if (active >= capacity.get()) {
            throw new ConflictException("Course is full (capacity " + capacity.get() + ")");
        }
    }

    private boolean isFull(UUID courseId) {
        Optional<Integer> capacity = enrollments.lockCapacity(courseId);
        if (capacity.isEmpty()) {
            return false; // unlimited is never full
        }
        return enrollments.countActive(courseId) >= capacity.get();
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
