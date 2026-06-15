package edu.courseflow.enrollment.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.enrollment.dto.EnrollmentDtos.AuditLogEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.ChangeStatusRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentCheckoutResponseDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PaymentStatusUpdateRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionApplicationActionRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyActionDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.RefundDropPolicyEvaluateRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.exception.ForbiddenException;
import edu.courseflow.enrollment.model.EnrollmentCheckoutAttempt;
import edu.courseflow.enrollment.model.EnrollmentOrder;
import edu.courseflow.enrollment.model.EnrollmentPromotionApplication;
import edu.courseflow.enrollment.model.EnrollmentRemediationCase;
import edu.courseflow.enrollment.model.EnrollmentRemediationCaseAction;
import edu.courseflow.enrollment.repository.EnrollmentCheckoutAttemptJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentOrderJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentPromotionApplicationJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentRemediationCaseActionJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentRemediationCaseJpaRepository;
import edu.courseflow.enrollment.repository.EnrollmentRepository;
import edu.courseflow.enrollment.repository.EnrollmentJpaRepository.EnrollmentBenefitReconciliationRow;
import edu.courseflow.enrollment.service.CoursePricingClient.CoursePricingSnapshot;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.CommitResult;
import edu.courseflow.enrollment.service.PromotionEnrollmentClient.ReverseResult;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InOrder;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataIntegrityViolationException;

@ExtendWith(MockitoExtension.class)
class EnrollmentServiceTest {

    @Mock
    private EnrollmentRepository repo;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private EnrollmentCheckoutAttemptJpaRepository checkoutAttempts;
    @Mock
    private EnrollmentOrderJpaRepository orders;
    @Mock
    private EnrollmentPromotionApplicationJpaRepository promotionApplications;
    @Mock
    private EnrollmentRemediationCaseJpaRepository remediationCases;
    @Mock
    private EnrollmentRemediationCaseActionJpaRepository remediationActions;
    @Mock
    private PromotionEnrollmentClient promotions;
    @Mock
    private CoursePricingClient coursePricing;

    private EnrollmentService service;

    private static final UUID COURSE = UUID.fromString("00000000-0000-0000-0000-0000000000c1");

    @BeforeEach
    void setUp() {
        service = new EnrollmentService(repo, objectMapper(), courseAccess);
    }

    private static ObjectMapper objectMapper() {
        return new ObjectMapper().findAndRegisterModules();
    }

    private static CurrentUser student(long id) {
        return new CurrentUser(id, "s" + id + "@x.io", "STUDENT", Set.of("STUDENT"));
    }

    private static CurrentUser instructor(long id) {
        return new CurrentUser(id, "i" + id + "@x.io", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static CurrentUser admin(long id) {
        return new CurrentUser(id, "a" + id + "@x.io", "ADMIN", Set.of("ADMIN"));
    }

    private static CurrentUser serviceUser() {
        return new CurrentUser(0L, "checkout@courseflow.internal", "SERVICE", Set.of("SERVICE"));
    }

    private static EnrollmentDto enrollment(UUID id, String studentId, String status) {
        return new EnrollmentDto(id.toString(), studentId, COURSE.toString(), null, status,
                Instant.parse("2026-01-01T00:00:00Z"), null, null, null);
    }

    private static EnrollmentPromotionApplication appliedPromotion(UUID enrollmentId, UUID redemptionId) {
        return new EnrollmentPromotionApplication(
                enrollmentId,
                "7",
                COURSE,
                "APPLIED",
                "SAVE10",
                null,
                UUID.randomUUID(),
                redemptionId,
                "flow-1",
                "[]",
                "[]",
                "Coupon applied");
    }

    private static EnrollmentOrder paidOrder(UUID enrollmentId, String studentId, BigDecimal amount) {
        EnrollmentOrder order = new EnrollmentOrder(
                enrollmentId,
                null,
                studentId,
                COURSE,
                amount,
                "USD",
                "idem-paid");
        order.markPaid("stripe", "pi_refund");
        return order;
    }

    private static RefundDropPolicyRequestBuilder refundRequest(UUID enrollmentId, Instant requestedAt) {
        return new RefundDropPolicyRequestBuilder(enrollmentId, requestedAt);
    }

    private static RefundDropPolicyActionDto action(List<RefundDropPolicyActionDto> actions, String action) {
        return actions.stream()
                .filter(item -> action.equals(item.action()))
                .findFirst()
                .orElseThrow(() -> new AssertionError("Missing refund/drop policy action " + action));
    }

    private static final class RefundDropPolicyRequestBuilder {
        private final UUID enrollmentId;
        private final Instant requestedAt;
        private String reason = "learner refund request";
        private Integer refundWindowDays = 14;
        private String paymentStatus;
        private BigDecimal paidAmount;
        private String currency;
        private Instant paidAt;
        private String promotionStatus;
        private String reservationId;
        private String redemptionId;
        private Long loyaltyPointsEarned;
        private Long loyaltyPointsReversed;
        private String loyaltyEarnEntryId;
        private String rewardStatus;
        private String rewardRedemptionId;
        private String rewardFulfillmentStatus;
        private Boolean rewardFulfilled;

        private RefundDropPolicyRequestBuilder(UUID enrollmentId, Instant requestedAt) {
            this.enrollmentId = enrollmentId;
            this.requestedAt = requestedAt;
        }

        private RefundDropPolicyRequestBuilder paidAt(Instant paidAt) {
            this.paidAt = paidAt;
            return this;
        }

        private RefundDropPolicyRequestBuilder paymentStatus(String paymentStatus) {
            this.paymentStatus = paymentStatus;
            return this;
        }

        private RefundDropPolicyRequestBuilder withLoyalty(
                Long earned,
                Long reversed,
                String earnEntryId) {
            this.loyaltyPointsEarned = earned;
            this.loyaltyPointsReversed = reversed;
            this.loyaltyEarnEntryId = earnEntryId;
            return this;
        }

        private RefundDropPolicyRequestBuilder withReward(
                String status,
                String redemptionId,
                String fulfillmentStatus,
                Boolean fulfilled) {
            this.rewardStatus = status;
            this.rewardRedemptionId = redemptionId;
            this.rewardFulfillmentStatus = fulfillmentStatus;
            this.rewardFulfilled = fulfilled;
            return this;
        }

        private RefundDropPolicyEvaluateRequestDto build() {
            return new RefundDropPolicyEvaluateRequestDto(
                    enrollmentId.toString(),
                    reason,
                    requestedAt,
                    refundWindowDays,
                    paymentStatus,
                    paidAmount,
                    currency,
                    paidAt,
                    promotionStatus,
                    reservationId,
                    redemptionId,
                    loyaltyPointsEarned,
                    loyaltyPointsReversed,
                    loyaltyEarnEntryId,
                    rewardStatus,
                    rewardRedemptionId,
                    rewardFulfillmentStatus,
                    rewardFulfilled,
                    Map.of("source", "unit-test"));
        }
    }

    private EnrollmentService fullService() {
        return new EnrollmentService(
                repo,
                checkoutAttempts,
                promotionApplications,
                orders,
                remediationCases,
                remediationActions,
                objectMapper(),
                courseAccess,
                promotions,
                coursePricing);
    }

    private EnrollmentService checkoutServiceWithoutRemediation() {
        return new EnrollmentService(
                repo,
                checkoutAttempts,
                promotionApplications,
                orders,
                null,
                null,
                objectMapper(),
                courseAccess,
                promotions,
                coursePricing);
    }

    // ---------------------------------------------------------------------------------------------
    // Status transition rules
    // ---------------------------------------------------------------------------------------------

    @Nested
    class BenefitReconciliation {

        @Test
        void flagsDroppedEnrollmentWithAppliedPromotion() {
            EnrollmentBenefitReconciliationRow row = Mockito.mock(EnrollmentBenefitReconciliationRow.class);
            UUID enrollmentId = UUID.randomUUID();
            UUID promotionApplicationId = UUID.randomUUID();
            UUID redemptionId = UUID.randomUUID();
            when(row.getEnrollmentId()).thenReturn(enrollmentId);
            when(row.getStudentId()).thenReturn("7");
            when(row.getCourseId()).thenReturn(COURSE);
            when(row.getEnrollmentStatus()).thenReturn("DROPPED");
            when(row.getDroppedAt()).thenReturn(Instant.parse("2026-01-01T01:00:00Z"));
            when(row.getPromotionApplicationId()).thenReturn(promotionApplicationId);
            when(row.getPromotionStatus()).thenReturn("APPLIED");
            when(row.getRedemptionId()).thenReturn(redemptionId);
            when(repo.benefitReconciliationRows(isNull(), eq(COURSE), eq("7"), anyInt())).thenReturn(List.of(row));
            CurrentUser user = instructor(99);

            var result = service.benefitReconciliation(
                    Optional.empty(),
                    Optional.of(COURSE),
                    Optional.of("7"),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.of(10),
                    user);

            assertThat(result.items()).hasSize(1);
            assertThat(result.items().get(0).reconciliationStatus())
                    .isEqualTo("DROPPED_PROMOTION_NOT_REVERSED");
            assertThat(result.items().get(0).severity()).isEqualTo("CRITICAL");
            assertThat(result.items().get(0).redemptionId()).isEqualTo(redemptionId.toString());
            verify(courseAccess).requireCourseStaffAccess(user, COURSE);
        }

        @Test
        void staffReadsMustBeScopedToCourse() {
            assertThatThrownBy(() -> service.benefitReconciliation(
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.of(10),
                    instructor(99)))
                    .isInstanceOf(ForbiddenException.class)
                    .hasMessageContaining("scoped to a course");
        }
    }

    @Nested
    class RefundDropPolicyMatrix {

        @Test
        void paidActiveEnrollmentWithinWindowRequiresRefundPromotionReversePointsAndRewardReversal() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            UUID redemptionId = UUID.randomUUID();
            UUID earnEntryId = UUID.randomUUID();
            UUID rewardRedemptionId = UUID.randomUUID();
            EnrollmentOrder order = paidOrder(enrollmentId, "7", new BigDecimal("80.00"));
            EnrollmentPromotionApplication application = appliedPromotion(enrollmentId, redemptionId);
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "ACTIVE")));
            when(orders.findByEnrollmentId(enrollmentId)).thenReturn(Optional.of(order));
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.of(application));

            var result = service.evaluateRefundDropPolicy(
                    refundRequest(enrollmentId, order.getPaidAt())
                            .withLoyalty(120L, 0L, earnEntryId.toString())
                            .withReward("COMMITTED", rewardRedemptionId.toString(), "ISSUED", true)
                            .build(),
                    instructor(99));

            assertThat(result.matrixStatus()).isEqualTo("ACTION_REQUIRED");
            assertThat(result.severity()).isEqualTo("CRITICAL");
            assertThat(result.dropAllowed()).isTrue();
            assertThat(result.refundEligible()).isTrue();
            assertThat(result.manualReviewRequired()).isFalse();
            assertThat(action(result.actions(), "REFUND_PAYMENT").decision()).isEqualTo("REQUIRED");
            assertThat(action(result.actions(), "REVERSE_PROMOTION_REDEMPTION").endpoint())
                    .endsWith("/internal/incentives/redemptions/" + redemptionId + "/reverse");
            assertThat(action(result.actions(), "CLAWBACK_LOYALTY_POINTS").endpoint())
                    .endsWith("/internal/loyalty/points/" + earnEntryId + ":reverse");
            assertThat(action(result.actions(), "REVERSE_REWARD_REDEMPTION").endpoint())
                    .endsWith("/internal/loyalty/reward-redemptions/" + rewardRedemptionId + ":reverse");
            assertThat(result.reasonCodes()).contains(
                    "REFUND_WINDOW_OPEN",
                    "PROMOTION_REDEMPTION_REVERSE_REQUIRED",
                    "LOYALTY_POINTS_CLAWBACK_REQUIRED",
                    "REWARD_REDEMPTION_REVERSE_REQUIRED");
            verify(courseAccess).requireCourseStaffAccess(instructor(99), COURSE);
        }

        @Test
        void completedEnrollmentRequiresManualReviewEvenWithPaidOrder() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            Instant paidAt = Instant.parse("2026-01-01T00:00:00Z");
            EnrollmentOrder order = paidOrder(enrollmentId, "7", new BigDecimal("100.00"));
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "COMPLETED")));
            when(orders.findByEnrollmentId(enrollmentId)).thenReturn(Optional.of(order));
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());

            var result = service.evaluateRefundDropPolicy(
                    refundRequest(enrollmentId, Instant.parse("2026-02-01T00:00:00Z"))
                            .paidAt(paidAt)
                            .build(),
                    instructor(99));

            assertThat(result.matrixStatus()).isEqualTo("MANUAL_REVIEW");
            assertThat(result.manualReviewRequired()).isTrue();
            assertThat(result.refundEligible()).isFalse();
            assertThat(action(result.actions(), "DROP_ENROLLMENT").decision()).isEqualTo("MANUAL_REVIEW");
            assertThat(action(result.actions(), "REFUND_PAYMENT").decision()).isEqualTo("MANUAL_REVIEW");
            assertThat(action(result.actions(), "REFUND_PAYMENT").makerCheckerRequired()).isTrue();
            assertThat(result.reasonCodes()).contains("COURSE_COMPLETED", "REFUND_REQUIRES_FINANCE_APPROVAL");
        }

        @Test
        void failedPaymentWithReservedPromotionSkipsRefundAndRequiresReservationCancel() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            UUID reservationId = UUID.randomUUID();
            EnrollmentPromotionApplication application = new EnrollmentPromotionApplication(
                    enrollmentId,
                    "7",
                    COURSE,
                    "RESERVED",
                    "SAVE20",
                    null,
                    reservationId,
                    null,
                    "idem-paid",
                    "[]",
                    "[]",
                    "Coupon reserved; commit is deferred until payment succeeds");
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "PENDING_PAYMENT")));
            when(orders.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.of(application));

            var result = service.evaluateRefundDropPolicy(
                    refundRequest(enrollmentId, Instant.now())
                            .paymentStatus("PAYMENT_FAILED")
                            .build(),
                    serviceUser());

            assertThat(result.matrixStatus()).isEqualTo("ACTION_REQUIRED");
            assertThat(result.manualReviewRequired()).isFalse();
            assertThat(result.refundEligible()).isFalse();
            assertThat(action(result.actions(), "REFUND_PAYMENT").decision()).isEqualTo("NOT_REQUIRED");
            assertThat(action(result.actions(), "CANCEL_PROMOTION_RESERVATION").decision()).isEqualTo("REQUIRED");
            assertThat(action(result.actions(), "CANCEL_PROMOTION_RESERVATION").endpoint())
                    .endsWith("/internal/incentives/reservations/" + reservationId + "/cancel");
            assertThat(result.reasonCodes()).contains("PAYMENT_NOT_SETTLED", "PROMOTION_RESERVATION_CANCEL_REQUIRED");
            verify(courseAccess, never()).requireCourseStaffAccess(any(), any());
        }
    }

    @Nested
    class StatusTransitions {

        @Test
        void activeToDropped_isAllowed() {
            UUID id = UUID.randomUUID();
            EnrollmentDto active = enrollment(id, "7", "ACTIVE");
            when(repo.findById(id)).thenReturn(Optional.of(active));
            when(repo.changeStatus(eq(id), eq("7"), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            // no waitlist to promote
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty());

            EnrollmentDto result = service.changeStatus(id,
                    new ChangeStatusRequestDto("DROPPED", "changed mind"), student(7));

            assertThat(result.status()).isEqualTo("DROPPED");
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.dropped"), anyString());
        }

        @Test
        void activeToCompleted_isAllowed_forStaff() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("COMPLETED"), any()))
                    .thenReturn(enrollment(id, "7", "COMPLETED"));

            EnrollmentDto result = service.changeStatus(id,
                    new ChangeStatusRequestDto("COMPLETED", null), instructor(99));

            assertThat(result.status()).isEqualTo("COMPLETED");
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.completed"), anyString());
        }

        @Test
        void droppedToActive_reEnroll_isAllowed_andRechecksCapacity() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "DROPPED")));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty()); // unlimited
            when(repo.changeStatus(eq(id), anyString(), eq("ACTIVE"), any()))
                    .thenReturn(enrollment(id, "7", "ACTIVE"));

            EnrollmentDto result = service.changeStatus(id,
                    new ChangeStatusRequestDto("ACTIVE", null), student(7));

            assertThat(result.status()).isEqualTo("ACTIVE");
            verify(repo).lockCapacity(COURSE);
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.created"), anyString());
        }

        @Test
        void completedIsTerminal_rejectsAnyTransition() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "COMPLETED")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("ACTIVE", null), instructor(1)))
                    .isInstanceOf(BadRequestException.class)
                    .hasMessageContaining("Illegal transition COMPLETED -> ACTIVE");
        }

        @Test
        void droppedToCompleted_isRejected() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "DROPPED")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("COMPLETED", null), instructor(1)))
                    .isInstanceOf(BadRequestException.class)
                    .hasMessageContaining("Illegal transition DROPPED -> COMPLETED");
        }

        @Test
        void unknownStatus_isRejected() {
            UUID id = UUID.randomUUID();

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("ARCHIVED", null), instructor(1)))
                    .isInstanceOf(BadRequestException.class)
                    .hasMessageContaining("Invalid status");
        }

        @Test
        void student_cannotComplete_ownEnrollment() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("COMPLETED", null), student(7)))
                    .isInstanceOf(ForbiddenException.class);
        }

        @Test
        void student_cannotDrop_someoneElsesEnrollment() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "8", "ACTIVE")));

            assertThatThrownBy(() -> service.changeStatus(id,
                    new ChangeStatusRequestDto("DROPPED", null), student(7)))
                    .isInstanceOf(ForbiddenException.class);
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Capacity "last seat" behavior
    // ---------------------------------------------------------------------------------------------

    @Nested
    class Capacity {

        @Test
        void lastSeat_enrollSucceeds() {
            // capacity 10, 9 active -> one seat left
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(10));
            when(repo.countOccupiedSeats(COURSE)).thenReturn(9);
            when(repo.enroll("7", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "7", "ACTIVE"));

            EnrollmentDto result = service.enroll(new EnrollRequestDto(null, COURSE.toString()), student(7));

            assertThat(result.status()).isEqualTo("ACTIVE");
            verify(repo).enroll("7", COURSE);
        }

        @Test
        void courseFull_enrollRejectedWith409() {
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(10));
            when(repo.countOccupiedSeats(COURSE)).thenReturn(10); // full

            assertThatThrownBy(() -> service.enroll(new EnrollRequestDto(null, COURSE.toString()), student(7)))
                    .isInstanceOf(ConflictException.class)
                    .hasMessageContaining("full");

            verify(repo, never()).enroll(anyString(), any());
        }

        @Test
        void noCapacityRow_meansUnlimited() {
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty());
            when(repo.enroll("7", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "7", "ACTIVE"));

            EnrollmentDto result = service.enroll(new EnrollRequestDto(null, COURSE.toString()), student(7));

            assertThat(result.status()).isEqualTo("ACTIVE");
            // occupied seat count never consulted when capacity is unlimited
            verify(repo, never()).countOccupiedSeats(any());
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Waitlist promotion ordering
    // ---------------------------------------------------------------------------------------------

    @Nested
    class WaitlistPromotion {

        @Test
        void drop_promotesHeadOfWaitlist_andCompacts() {
            UUID id = UUID.randomUUID();
            EnrollmentDto active = enrollment(id, "7", "ACTIVE");
            when(repo.findById(id)).thenReturn(Optional.of(active));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));

            // After the drop: capacity 1, 0 active -> a seat is free, so the head must be promoted.
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countOccupiedSeats(COURSE)).thenReturn(0);

            WaitlistEntryDto head = new WaitlistEntryDto(
                    UUID.randomUUID().toString(), "42", COURSE.toString(), 1, "WAITING",
                    Instant.parse("2026-01-01T00:00:00Z"));
            when(repo.firstWaiting(COURSE)).thenReturn(Optional.of(head));
            when(repo.enroll("42", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "42", "ACTIVE"));

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            InOrder inOrder = Mockito.inOrder(repo);
            inOrder.verify(repo).enroll("42", COURSE);
            inOrder.verify(repo).markWaitlistPromoted(UUID.fromString(head.id()));
            inOrder.verify(repo).compactWaitlist(COURSE);
        }

        @Test
        void drop_skipsCompletedWaitlistHead_andPromotesNextEligibleStudent() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countOccupiedSeats(COURSE)).thenReturn(0);

            WaitlistEntryDto completedHead = new WaitlistEntryDto(
                    UUID.randomUUID().toString(), "42", COURSE.toString(), 1, "WAITING",
                    Instant.parse("2026-01-01T00:00:00Z"));
            WaitlistEntryDto next = new WaitlistEntryDto(
                    UUID.randomUUID().toString(), "43", COURSE.toString(), 2, "WAITING",
                    Instant.parse("2026-01-01T00:01:00Z"));
            when(repo.firstWaiting(COURSE)).thenReturn(Optional.of(completedHead), Optional.of(next));
            when(repo.find("42", COURSE)).thenReturn(Optional.of(enrollment(UUID.randomUUID(), "42", "COMPLETED")));
            when(repo.find("43", COURSE)).thenReturn(Optional.empty());
            when(repo.enroll("43", COURSE)).thenReturn(enrollment(UUID.randomUUID(), "43", "ACTIVE"));

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            InOrder inOrder = Mockito.inOrder(repo);
            inOrder.verify(repo).markWaitlistSkipped(UUID.fromString(completedHead.id()));
            inOrder.verify(repo).compactWaitlist(COURSE);
            inOrder.verify(repo).enroll("43", COURSE);
            inOrder.verify(repo).markWaitlistPromoted(UUID.fromString(next.id()));
            inOrder.verify(repo).compactWaitlist(COURSE);
        }

        @Test
        void drop_whenStillFull_doesNotPromote() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));

            // capacity 1 but still 1 active after the drop (e.g. another seat taken) -> no free seat
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countOccupiedSeats(COURSE)).thenReturn(1);

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            verify(repo, never()).firstWaiting(any());
            verify(repo, never()).enroll(anyString(), any());
        }

        @Test
        void drop_withEmptyWaitlist_promotesNobody() {
            UUID id = UUID.randomUUID();
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.of(1));
            when(repo.countOccupiedSeats(COURSE)).thenReturn(0);
            when(repo.firstWaiting(COURSE)).thenReturn(Optional.empty());

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", null), instructor(1));

            verify(repo, never()).markWaitlistPromoted(any());
            verify(repo, never()).compactWaitlist(any());
        }
    }

    @Nested
    class PaidCheckoutBoundary {

        @Test
        void paidCheckout_createsPendingEnrollmentAndOrder_withoutActivating() {
            service = checkoutServiceWithoutRemediation();
            UUID enrollmentId = UUID.randomUUID();
            when(coursePricing.pricing(COURSE.toString()))
                    .thenReturn(new CoursePricingSnapshot(
                            COURSE.toString(),
                            new BigDecimal("100.00"),
                            "USD",
                            "ACTIVE",
                            true,
                            "COURSE_PRICE"));
            when(checkoutAttempts.lockByIdempotencyKey(anyString())).thenReturn(Optional.empty());
            when(checkoutAttempts.saveAndFlush(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(checkoutAttempts.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(orders.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty());
            when(repo.enrollPendingPayment(eq("7"), eq(COURSE), eq("7"), anyString()))
                    .thenReturn(enrollment(enrollmentId, "7", "PENDING_PAYMENT"));

            EnrollmentCheckoutResponseDto response = service.checkout(
                    new EnrollRequestDto(null, COURSE.toString(), null, null, null, "idem-paid"),
                    student(7));

            assertThat(response.enrollment().status()).isEqualTo("PENDING_PAYMENT");
            assertThat(response.order()).isNotNull();
            assertThat(response.order().status()).isEqualTo("PAYMENT_PENDING");
            assertThat(response.order().amount()).isEqualByComparingTo("100.00");
            verify(repo, never()).enroll(anyString(), any());
            verify(promotions, never()).commit(any(), anyString(), anyString());
        }

        @Test
        void paidPaymentSuccess_activatesEnrollment_thenCommitsReservedPromotion() {
            service = checkoutServiceWithoutRemediation();
            UUID enrollmentId = UUID.randomUUID();
            UUID redemptionId = UUID.randomUUID();
            EnrollmentOrder order = new EnrollmentOrder(
                    enrollmentId,
                    null,
                    "7",
                    COURSE,
                    new BigDecimal("80.00"),
                    "USD",
                    "idem-paid");
            EnrollmentPromotionApplication application = new EnrollmentPromotionApplication(
                    enrollmentId,
                    "7",
                    COURSE,
                    "RESERVED",
                    "SAVE20",
                    null,
                    UUID.randomUUID(),
                    null,
                    "idem-paid",
                    "[]",
                    "[]",
                    "Coupon reserved; commit is deferred until payment succeeds");
            EnrollmentDto pending = enrollment(enrollmentId, "7", "PENDING_PAYMENT");
            EnrollmentDto active = enrollment(enrollmentId, "7", "ACTIVE");

            when(orders.findByIdForUpdate(order.getId())).thenReturn(Optional.of(order));
            when(orders.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(repo.findById(enrollmentId)).thenReturn(
                    Optional.of(pending),
                    Optional.of(active),
                    Optional.of(active));
            when(repo.changeStatus(eq(enrollmentId), eq("0"), eq("ACTIVE"), anyString())).thenReturn(active);
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.of(application));
            when(promotions.commit(eq(application.getReservationId()), eq(enrollmentId.toString()), anyString()))
                    .thenReturn(new CommitResult(true, redemptionId, List.of("COMMITTED"), List.of()));
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());

            EnrollmentCheckoutResponseDto response = service.recordOrderPayment(
                    order.getId(),
                    new PaymentStatusUpdateRequestDto(
                            "PAID",
                            "stripe",
                            "pi_123",
                            new BigDecimal("80.00"),
                            "USD",
                            null,
                            "corr-paid"),
                    serviceUser());

            assertThat(order.getStatus()).isEqualTo("PAID");
            assertThat(response.enrollment().status()).isEqualTo("ACTIVE");
            assertThat(response.promotion().status()).isEqualTo("APPLIED");
            assertThat(application.getStatus()).isEqualTo("APPLIED");
            verify(promotions).commit(eq(application.getReservationId()), eq(enrollmentId.toString()), anyString());
            verify(repo).outbox(eq(enrollmentId), eq("enrollment"), eq("enrollment.created"), anyString());
        }

        @Test
        void staffCannotRecordPaymentEvent() {
            service = fullService();

            assertThatThrownBy(() -> service.recordOrderPayment(
                    UUID.randomUUID(),
                    new PaymentStatusUpdateRequestDto(
                            "PAID",
                            "stripe",
                            "pi_staff",
                            new BigDecimal("80.00"),
                            "USD",
                            null,
                            "corr-staff"),
                    instructor(99)))
                    .isInstanceOf(ForbiddenException.class)
                    .hasMessageContaining("checkout or payment service");
            verify(orders, never()).findByIdForUpdate(any());
        }

        @Test
        void paidPaymentRequiresProviderAndReferenceBeforeActivation() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            EnrollmentOrder order = new EnrollmentOrder(
                    enrollmentId,
                    null,
                    "7",
                    COURSE,
                    new BigDecimal("80.00"),
                    "USD",
                    "idem-paid");
            when(orders.findByIdForUpdate(order.getId())).thenReturn(Optional.of(order));
            when(orders.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(remediationCases.findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(eq(order.getId()), any()))
                    .thenReturn(Optional.empty());
            when(remediationCases.saveAndFlush(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "PENDING_PAYMENT")));
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());

            EnrollmentCheckoutResponseDto response = service.recordOrderPayment(
                    order.getId(),
                    new PaymentStatusUpdateRequestDto(
                            "PAID",
                            "stripe",
                            null,
                            new BigDecimal("80.00"),
                            "USD",
                            null,
                            "corr-missing-ref"),
                    serviceUser());

            assertThat(order.getStatus()).isEqualTo("MANUAL_REVIEW");
            assertThat(order.getFailureReason())
                    .isEqualTo("paymentReference is required to mark an enrollment order PAID");
            assertThat(response.order().status()).isEqualTo("MANUAL_REVIEW");
            verify(repo, never()).changeStatus(eq(enrollmentId), anyString(), eq("ACTIVE"), anyString());
            ArgumentCaptor<EnrollmentRemediationCase> caseCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCase.class);
            verify(remediationCases).saveAndFlush(caseCaptor.capture());
            assertThat(caseCaptor.getValue().getReasonCode()).isEqualTo("PAYMENT_MISMATCH");
        }

        @Test
        void paidPaymentReplayConflictOpensRemediationCaseWithoutMutatingPaidOrder() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            EnrollmentOrder order = new EnrollmentOrder(
                    enrollmentId,
                    null,
                    "7",
                    COURSE,
                    new BigDecimal("80.00"),
                    "USD",
                    "idem-paid");
            order.markPaid("stripe", "pi_original");
            when(orders.findByIdForUpdate(order.getId())).thenReturn(Optional.of(order));
            when(remediationCases.findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(eq(order.getId()), any()))
                    .thenReturn(Optional.empty());
            when(remediationCases.saveAndFlush(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "ACTIVE")));
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());

            EnrollmentCheckoutResponseDto response = service.recordOrderPayment(
                    order.getId(),
                    new PaymentStatusUpdateRequestDto(
                            "PAID",
                            "stripe",
                            "pi_conflict",
                            new BigDecimal("80.00"),
                            "USD",
                            null,
                            "corr-replay"),
                    serviceUser());

            assertThat(response.order().status()).isEqualTo("PAID");
            assertThat(order.getPaymentReference()).isEqualTo("pi_original");
            ArgumentCaptor<EnrollmentRemediationCase> caseCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCase.class);
            verify(remediationCases).saveAndFlush(caseCaptor.capture());
            assertThat(caseCaptor.getValue().getReasonCode()).isEqualTo("PAYMENT_REPLAY_CONFLICT");
            verify(orders, never()).save(order);
        }

        @Test
        void duplicatePaymentReferenceAcrossOrdersOpensManualReviewWithoutActivatingEnrollment() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            UUID existingEnrollmentId = UUID.randomUUID();
            EnrollmentOrder order = new EnrollmentOrder(
                    enrollmentId,
                    null,
                    "7",
                    COURSE,
                    new BigDecimal("80.00"),
                    "USD",
                    "idem-paid");
            EnrollmentOrder existing = new EnrollmentOrder(
                    existingEnrollmentId,
                    null,
                    "8",
                    COURSE,
                    new BigDecimal("80.00"),
                    "USD",
                    "idem-existing");
            existing.markPaid("stripe", "pi_shared");
            when(orders.findByIdForUpdate(order.getId())).thenReturn(Optional.of(order));
            when(orders.findByPaymentReferenceForUpdate("stripe", "pi_shared")).thenReturn(List.of(existing));
            when(orders.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(remediationCases.findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(eq(order.getId()), any()))
                    .thenReturn(Optional.empty());
            when(remediationCases.saveAndFlush(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "PENDING_PAYMENT")));
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());

            EnrollmentCheckoutResponseDto response = service.recordOrderPayment(
                    order.getId(),
                    new PaymentStatusUpdateRequestDto(
                            "PAID",
                            "stripe",
                            "pi_shared",
                            new BigDecimal("80.00"),
                            "USD",
                            null,
                            "corr-duplicate-ref"),
                    serviceUser());

            assertThat(order.getStatus()).isEqualTo("MANUAL_REVIEW");
            assertThat(order.getFailureReason()).contains(existing.getId().toString());
            assertThat(response.order().status()).isEqualTo("MANUAL_REVIEW");
            verify(repo, never()).changeStatus(eq(enrollmentId), anyString(), eq("ACTIVE"), anyString());
            verify(promotions, never()).commit(any(), anyString(), anyString());
            ArgumentCaptor<EnrollmentRemediationCase> caseCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCase.class);
            verify(remediationCases).saveAndFlush(caseCaptor.capture());
            assertThat(caseCaptor.getValue().getReasonCode()).isEqualTo("PAYMENT_REFERENCE_CONFLICT");
        }

        @Test
        void orderRemediationCaseDedupeRaceUpdatesExistingOpenCase() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            EnrollmentOrder order = new EnrollmentOrder(
                    enrollmentId,
                    null,
                    "7",
                    COURSE,
                    new BigDecimal("80.00"),
                    "USD",
                    "idem-paid");
            EnrollmentRemediationCase existingCase = new EnrollmentRemediationCase(
                    "ORDER_PAYMENT",
                    "HIGH",
                    enrollmentId,
                    null,
                    null,
                    order.getId(),
                    "7",
                    COURSE,
                    "enrollment-ops",
                    "Existing payment remediation",
                    "PAYMENT_MISMATCH",
                    Instant.now().plusSeconds(3600));
            when(orders.findByIdForUpdate(order.getId())).thenReturn(Optional.of(order));
            when(orders.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
            when(remediationCases.findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(eq(order.getId()), any()))
                    .thenReturn(Optional.empty(), Optional.of(existingCase));
            when(remediationCases.saveAndFlush(any()))
                    .thenThrow(new DataIntegrityViolationException("duplicate open order remediation case"));
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "PENDING_PAYMENT")));
            when(promotionApplications.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());

            EnrollmentCheckoutResponseDto response = service.recordOrderPayment(
                    order.getId(),
                    new PaymentStatusUpdateRequestDto(
                            "PAID",
                            "stripe",
                            null,
                            new BigDecimal("80.00"),
                            "USD",
                            null,
                            "corr-dedupe"),
                    serviceUser());

            assertThat(response.order().status()).isEqualTo("MANUAL_REVIEW");
            assertThat(existingCase.getNote())
                    .isEqualTo("paymentReference is required to mark an enrollment order PAID");
            verify(remediationCases).save(existingCase);
            ArgumentCaptor<EnrollmentRemediationCaseAction> actionCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCaseAction.class);
            verify(remediationActions).save(actionCaptor.capture());
            assertThat(actionCaptor.getValue().getCaseId()).isEqualTo(existingCase.getId());
            assertThat(actionCaptor.getValue().getAction()).isEqualTo("CASE_UPDATED");
        }

        @Test
        void retryCommitSuccessAutoResolvesOpenRemediationCase() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            EnrollmentPromotionApplication application = new EnrollmentPromotionApplication(
                    enrollmentId,
                    "7",
                    COURSE,
                    "COMMIT_FAILED",
                    "SAVE20",
                    null,
                    UUID.randomUUID(),
                    null,
                    "idem-paid",
                    "[]",
                    "[]",
                    "Promotion commit is pending retry");
            EnrollmentRemediationCase remediationCase = new EnrollmentRemediationCase(
                    "PROMOTION_CHECKOUT",
                    "HIGH",
                    enrollmentId,
                    null,
                    application.getId(),
                    null,
                    "7",
                    COURSE,
                    "enrollment-ops",
                    "Promotion commit failed",
                    "PROMOTION_COMMIT_UNAVAILABLE",
                    Instant.now().plusSeconds(3600));
            UUID redemptionId = UUID.randomUUID();
            when(promotionApplications.findByIdForUpdate(application.getId())).thenReturn(Optional.of(application));
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "ACTIVE")));
            when(remediationCases.findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
                    eq(application.getId()),
                    any()))
                    .thenReturn(Optional.of(remediationCase));
            when(promotions.commit(eq(application.getReservationId()), eq(enrollmentId.toString()), anyString()))
                    .thenReturn(new CommitResult(true, redemptionId, List.of("COMMITTED"), List.of()));
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());

            service.retryPromotionApplicationCommit(
                    application.getId(),
                    new PromotionApplicationActionRequestDto("retry now", "corr-retry"),
                    instructor(99));

            assertThat(application.getStatus()).isEqualTo("APPLIED");
            assertThat(remediationCase.getStatus()).isEqualTo("RESOLVED");
            ArgumentCaptor<EnrollmentRemediationCaseAction> actionCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCaseAction.class);
            verify(remediationActions, times(3)).save(actionCaptor.capture());
            assertThat(actionCaptor.getAllValues())
                    .extracting(EnrollmentRemediationCaseAction::getAction)
                    .contains("RETRY_ATTEMPTED", "RETRY_SUCCEEDED", "AUTO_RESOLVED");
        }

        @Test
        void reservedPromotionOverdue_opensAssignedRemediationCaseWithActionHistory() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            EnrollmentPromotionApplication application = new EnrollmentPromotionApplication(
                    enrollmentId,
                    "7",
                    COURSE,
                    "RESERVED",
                    "SAVE20",
                    null,
                    UUID.randomUUID(),
                    null,
                    "idem-paid",
                    "[]",
                    "[]",
                    "Coupon reserved; commit is deferred until payment succeeds");
            when(promotionApplications.lockReservedOlderThan(any(), any()))
                    .thenReturn(List.of(application));
            when(remediationCases.findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
                    eq(application.getId()),
                    any()))
                    .thenReturn(Optional.empty());
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(orders.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(remediationCases.saveAndFlush(any())).thenAnswer(invocation -> invocation.getArgument(0));

            int opened = service.openReservedPromotionRemediationCases(10);

            assertThat(opened).isEqualTo(1);
            ArgumentCaptor<EnrollmentRemediationCase> caseCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCase.class);
            verify(remediationCases).saveAndFlush(caseCaptor.capture());
            assertThat(caseCaptor.getValue().getAssigneeId()).isEqualTo("enrollment-ops");
            assertThat(caseCaptor.getValue().getReasonCode()).isEqualTo("RESERVED_OVERDUE");
            ArgumentCaptor<EnrollmentRemediationCaseAction> actionCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCaseAction.class);
            verify(remediationActions, times(2)).save(actionCaptor.capture());
            assertThat(actionCaptor.getAllValues())
                    .extracting(EnrollmentRemediationCaseAction::getAction)
                    .contains("CASE_OPENED", "RETRY_STATE");
            ArgumentCaptor<String> auditActionCaptor = ArgumentCaptor.forClass(String.class);
            verify(repo, times(2)).recordAudit(
                    eq(enrollmentId),
                    eq("system"),
                    auditActionCaptor.capture(),
                    isNull(),
                    isNull(),
                    anyString());
            assertThat(auditActionCaptor.getAllValues())
                    .contains("REMEDIATION_CASE_OPENED", "REMEDIATION_RETRY_STATE");
        }

        @Test
        void reservedPromotionOverdueDedupeRaceUpdatesExistingOpenCase() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            EnrollmentPromotionApplication application = new EnrollmentPromotionApplication(
                    enrollmentId,
                    "7",
                    COURSE,
                    "RESERVED",
                    "SAVE20",
                    null,
                    UUID.randomUUID(),
                    null,
                    "idem-paid",
                    "[]",
                    "[]",
                    "Coupon reserved; commit is deferred until payment succeeds");
            EnrollmentRemediationCase existingCase = new EnrollmentRemediationCase(
                    "PROMOTION_CHECKOUT",
                    "MEDIUM",
                    enrollmentId,
                    null,
                    application.getId(),
                    null,
                    "7",
                    COURSE,
                    "enrollment-ops",
                    "Existing reserved remediation",
                    "RESERVED_OVERDUE",
                    Instant.now().plusSeconds(3600));
            when(promotionApplications.lockReservedOlderThan(any(), any()))
                    .thenReturn(List.of(application));
            when(remediationCases.findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
                    eq(application.getId()),
                    any()))
                    .thenReturn(Optional.empty(), Optional.of(existingCase));
            when(checkoutAttempts.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(orders.findByEnrollmentId(enrollmentId)).thenReturn(Optional.empty());
            when(remediationCases.saveAndFlush(any()))
                    .thenThrow(new DataIntegrityViolationException("duplicate open promotion remediation case"));

            int opened = service.openReservedPromotionRemediationCases(10);

            assertThat(opened).isEqualTo(1);
            assertThat(existingCase.getNote())
                    .isEqualTo("Coupon reservation has remained RESERVED past the remediation SLA");
            verify(remediationCases).save(existingCase);
            ArgumentCaptor<EnrollmentRemediationCaseAction> actionCaptor =
                    ArgumentCaptor.forClass(EnrollmentRemediationCaseAction.class);
            verify(remediationActions, times(2)).save(actionCaptor.capture());
            assertThat(actionCaptor.getAllValues())
                    .extracting(EnrollmentRemediationCaseAction::getAction)
                    .contains("CASE_UPDATED", "RETRY_STATE");
            assertThat(actionCaptor.getAllValues())
                    .extracting(EnrollmentRemediationCaseAction::getCaseId)
                    .containsOnly(existingCase.getId());
        }
    }

    @Nested
    class PromotionCompensation {

        @Test
        void drop_reversesAppliedCouponRedemption() {
            service = new EnrollmentService(repo, promotionApplications, objectMapper(), courseAccess, promotions);
            UUID id = UUID.randomUUID();
            UUID redemptionId = UUID.randomUUID();
            EnrollmentPromotionApplication application = appliedPromotion(id, redemptionId);
            when(repo.findById(id)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), anyString(), eq("DROPPED"), any()))
                    .thenReturn(enrollment(id, "7", "DROPPED"));
            when(repo.lockCapacity(COURSE)).thenReturn(Optional.empty());
            when(promotionApplications.findByEnrollmentId(id)).thenReturn(Optional.of(application));
            when(promotions.reverse(eq(redemptionId), anyString(), anyString()))
                    .thenReturn(new ReverseResult(true, redemptionId, "REVERSED", List.of("REVERSED"), List.of()));

            service.changeStatus(id, new ChangeStatusRequestDto("DROPPED", "refund"), student(7));

            verify(promotions).reverse(eq(redemptionId), anyString(), anyString());
            verify(promotionApplications).save(application);
            assertThat(application.getStatus()).isEqualTo("REVERSED");
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Operations remediation queue
    // ---------------------------------------------------------------------------------------------

    @Nested
    class OperationsRemediationQueue {

        @Test
        void queueSupportsCrossDomainCaseAnchorsForOpsConsole() {
            service = fullService();
            UUID enrollmentId = UUID.randomUUID();
            UUID promotionApplicationId = UUID.randomUUID();
            UUID orderId = UUID.randomUUID();
            UUID couponId = UUID.randomUUID();
            UUID redemptionId = UUID.randomUUID();
            EnrollmentRemediationCase remediationCase = new EnrollmentRemediationCase(
                    "PROMOTION_CHECKOUT",
                    "HIGH",
                    enrollmentId,
                    null,
                    promotionApplicationId,
                    orderId,
                    "7",
                    COURSE,
                    "ops-a",
                    "Commit failed",
                    "PROMOTION_COMMIT_UNAVAILABLE",
                    Instant.now().plusSeconds(3600));
            when(remediationCases.findOperationsQueue(
                    eq("IN_PROGRESS"),
                    eq(COURSE),
                    eq(enrollmentId),
                    eq(promotionApplicationId),
                    eq(orderId),
                    eq("7"),
                    eq(couponId),
                    eq(redemptionId),
                    eq("corr-ops-1"),
                    eq("ops-a"),
                    any()))
                    .thenReturn(List.of(remediationCase));
            when(remediationActions.findByCaseIdOrderByCreatedAtAsc(remediationCase.getId()))
                    .thenReturn(List.of());

            var result = service.remediationCaseQueue(
                    Optional.of(" in_progress "),
                    Optional.of(COURSE),
                    Optional.of(enrollmentId),
                    Optional.of(promotionApplicationId),
                    Optional.of(orderId),
                    Optional.of(" 7 "),
                    Optional.of(couponId),
                    Optional.of(redemptionId),
                    Optional.of(" corr-ops-1 "),
                    Optional.of(" ops-a "),
                    Optional.of(20),
                    admin(99));

            assertThat(result).hasSize(1);
            assertThat(result.getFirst().id()).isEqualTo(remediationCase.getId().toString());
        }

        @Test
        void staffQueueStillRequiresCourseScopeForCrossDomainFilters() {
            service = fullService();

            assertThatThrownBy(() -> service.remediationCaseQueue(
                    Optional.empty(),
                    Optional.empty(),
                    Optional.of(UUID.randomUUID()),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.of("corr-ops-1"),
                    Optional.empty(),
                    Optional.of(20),
                    instructor(99)))
                    .isInstanceOf(ForbiddenException.class)
                    .hasMessageContaining("scoped to a course");
            verify(remediationCases, never()).findOperationsQueue(
                    any(),
                    any(),
                    any(),
                    any(),
                    any(),
                    any(),
                    any(),
                    any(),
                    any(),
                    any(),
                    any());
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Operations audit query
    // ---------------------------------------------------------------------------------------------

    @Nested
    class OperationsAudit {

        @Test
        void auditQueryByEnrollmentResolvesCourseScopeForStaff() {
            UUID enrollmentId = UUID.randomUUID();
            CurrentUser user = instructor(99);
            AuditLogEntryDto entry = new AuditLogEntryDto(
                    UUID.randomUUID().toString(),
                    enrollmentId.toString(),
                    "system",
                    "REMEDIATION_CASE_OPENED",
                    null,
                    null,
                    "{\"correlationId\":\"corr-1\"}",
                    Instant.now());
            when(repo.findById(enrollmentId)).thenReturn(Optional.of(enrollment(enrollmentId, "7", "ACTIVE")));
            when(repo.auditLog(eq(enrollmentId), eq(COURSE), isNull(), eq("corr-1"), eq(10)))
                    .thenReturn(List.of(entry));

            List<AuditLogEntryDto> result = service.auditLog(
                    Optional.of(enrollmentId),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.of("corr-1"),
                    Optional.of(10),
                    user);

            assertThat(result).containsExactly(entry);
            verify(courseAccess).requireCourseStaffAccess(user, COURSE);
        }

        @Test
        void staffAuditQueryRequiresCourseScopeWhenEnrollmentIsMissing() {
            assertThatThrownBy(() -> service.auditLog(
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    Optional.of("corr-1"),
                    Optional.of(10),
                    instructor(99)))
                    .isInstanceOf(ForbiddenException.class)
                    .hasMessageContaining("scoped to a course");
            verify(repo, never()).auditLog(any(), any(), any(), any(), anyInt());
        }
    }

    // ---------------------------------------------------------------------------------------------
    // System completion (course.completed consumer path)
    // ---------------------------------------------------------------------------------------------

    @Nested
    class SystemCompletion {

        @Test
        void completesActiveEnrollment_andEmitsEvent() {
            UUID id = UUID.randomUUID();
            when(repo.find("7", COURSE)).thenReturn(Optional.of(enrollment(id, "7", "ACTIVE")));
            when(repo.changeStatus(eq(id), eq("system"), eq("COMPLETED"), any()))
                    .thenReturn(enrollment(id, "7", "COMPLETED"));

            Optional<EnrollmentDto> result = service.completeForCourseCompletion("7", COURSE);

            assertThat(result).isPresent();
            assertThat(result.get().status()).isEqualTo("COMPLETED");
            verify(repo).outbox(eq(id), eq("enrollment"), eq("enrollment.completed"), anyString());
        }

        @Test
        void noOp_whenAlreadyCompleted() {
            UUID id = UUID.randomUUID();
            when(repo.find("7", COURSE)).thenReturn(Optional.of(enrollment(id, "7", "COMPLETED")));

            Optional<EnrollmentDto> result = service.completeForCourseCompletion("7", COURSE);

            assertThat(result).isEmpty();
            verify(repo, never()).changeStatus(any(), anyString(), anyString(), any());
            verify(repo, never()).outbox(any(), anyString(), anyString(), anyString());
        }

        @Test
        void noOp_whenEnrollmentMissing() {
            when(repo.find("7", COURSE)).thenReturn(Optional.empty());

            Optional<EnrollmentDto> result = service.completeForCourseCompletion("7", COURSE);

            assertThat(result).isEmpty();
            verify(repo, never()).changeStatus(any(), anyString(), anyString(), any());
        }
    }
}
