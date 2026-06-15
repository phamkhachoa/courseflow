package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RedemptionReversalApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RedemptionReversalApprovalRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveOperationApproval;
import edu.courseflow.promotion.model.IncentiveRedemption;
import edu.courseflow.promotion.model.IncentiveReservation;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveOperationApprovalRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RedemptionReversalApprovalServiceTest {

    @Mock
    IncentiveRedemptionRepository redemptions;
    @Mock
    IncentiveReservationRepository reservations;
    @Mock
    IncentiveOperationApprovalRepository approvals;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private RedemptionReversalApprovalService service;

    @BeforeEach
    void setUp() {
        service = new RedemptionReversalApprovalService(
                redemptions,
                reservations,
                approvals,
                auditEvents,
                AdminOperationRateGuard.disabled(metrics),
                access,
                objectMapper,
                60);
    }

    @Test
    void requestApprovalPersistsPendingEvidenceWithoutRawEffects() {
        CurrentUser requester = user(1L);
        Scenario scenario = scenario();
        stubActor(requester, "api-gateway");
        stubRedemption(scenario);
        when(approvals.findActiveForSubject(any(), any(), any(), any())).thenReturn(Optional.empty());
        when(approvals.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var response = service.requestApproval(
                scenario.redemption().getId(),
                approvalRequest("reverse-1"),
                requester,
                "corr-request");

        assertThat(response.status()).isEqualTo(IncentiveOperationApproval.STATUS_PENDING);
        assertThat(response.redemptionId()).isEqualTo(scenario.redemption().getId());
        assertThat(response.reservationId()).isEqualTo(scenario.reservation().getId());
        assertThat(response.requestedBy()).isEqualTo("1");
        assertThat(response.reason()).isEqualTo("order refunded");
        assertThat(response.changeTicket()).isEqualTo("INC-1001");

        ArgumentCaptor<IncentiveOperationApproval> approvalCaptor =
                ArgumentCaptor.forClass(IncentiveOperationApproval.class);
        verify(approvals).save(approvalCaptor.capture());
        IncentiveOperationApproval approval = approvalCaptor.getValue();
        assertThat(approval.getOperationType())
                .isEqualTo(IncentiveOperationApproval.OPERATION_REDEMPTION_REVERSE);
        assertThat(approval.getTargetType()).isEqualTo(IncentiveOperationApproval.TARGET_REDEMPTION);
        assertThat(approval.getRequestedRows()).isEqualTo(1);
        assertThat(approval.getSubjectJson())
                .contains("\"currentStatus\":\"REDEEMED\"")
                .contains("\"effectsHash\"")
                .contains("\"quotaPolicy\":\"NO_RELEASE_ON_COMMITTED_REVERSAL\"")
                .doesNotContain("\"amount\":");

        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        assertThat(auditCaptor.getValue().getAction()).isEqualTo("redemption.reversal_approval_requested");
        assertThat(auditCaptor.getValue().getAggregateType()).isEqualTo("redemption-reversal-approval");
    }

    @Test
    void requestApprovalRejectsDuplicateActiveApproval() {
        CurrentUser requester = user(1L);
        Scenario scenario = scenario();
        stubActor(requester, "api-gateway");
        stubRedemption(scenario);
        when(approvals.findActiveForSubject(any(), any(), any(), any()))
                .thenReturn(Optional.of(existingApproval(scenario, "1")));

        assertThatThrownBy(() -> service.requestApproval(
                scenario.redemption().getId(),
                approvalRequest("reverse-duplicate"),
                requester,
                "corr-request"))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_ALREADY_EXISTS));
    }

    @Test
    void approverCannotBeRequester() {
        CurrentUser requester = user(1L);
        Scenario scenario = scenario();
        IncentiveOperationApproval approval = pendingApproval(scenario, requester, "reverse-self");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));

        assertThatThrownBy(() -> service.approve(
                approval.getId(),
                new RedemptionReversalApprovalDecisionRequestDto("looks good"),
                requester,
                "corr-approve"))
                .isInstanceOf(ForbiddenException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.REDEMPTION_REVERSAL_SELF_APPROVAL_BLOCKED));
    }

    @Test
    void approvedPayloadCanBeExecutedByDifferentOperatorAndMarkedExecuted() {
        CurrentUser requester = user(1L);
        CurrentUser reviewer = user(2L);
        CurrentUser executor = user(3L);
        Scenario scenario = scenario();
        IncentiveOperationApproval approval = pendingApproval(scenario, requester, "reverse-approved");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        stubActor(reviewer, "api-gateway");
        stubActor(executor, "api-gateway");

        service.approve(
                approval.getId(),
                new RedemptionReversalApprovalDecisionRequestDto("approved"),
                reviewer,
                "corr-approve");
        IncentiveOperationApproval approved = service.requireApprovedForReverse(
                scenario.redemption(),
                new ReverseRedemptionRequestDto(
                        "reverse-approved",
                        "order refunded",
                        approval.getId(),
                        "INC-1001"),
                executor);
        service.markExecuted(approved, "3", Instant.now(), "corr-execute", "api-gateway");

        assertThat(approval.getStatus()).isEqualTo(IncentiveOperationApproval.STATUS_EXECUTED);
        assertThat(approval.getApprovedBy()).isEqualTo("2");
        assertThat(approval.getExecutedBy()).isEqualTo("3");
    }

    @Test
    void approverCannotExecuteApprovedReversal() {
        CurrentUser requester = user(1L);
        CurrentUser reviewer = user(2L);
        Scenario scenario = scenario();
        IncentiveOperationApproval approval = pendingApproval(scenario, requester, "reverse-self-execute");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        stubActor(reviewer, "api-gateway");

        service.approve(
                approval.getId(),
                new RedemptionReversalApprovalDecisionRequestDto("approved"),
                reviewer,
                "corr-approve");

        assertThatThrownBy(() -> service.requireApprovedForReverse(
                scenario.redemption(),
                new ReverseRedemptionRequestDto(
                        "reverse-self-execute",
                        "order refunded",
                        approval.getId(),
                        "INC-1001"),
                reviewer))
                .isInstanceOf(ForbiddenException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.REDEMPTION_REVERSAL_SELF_EXECUTION_BLOCKED));
    }

    @Test
    void subjectDriftBlocksApproval() {
        CurrentUser requester = user(1L);
        CurrentUser reviewer = user(2L);
        Scenario scenario = scenario();
        IncentiveOperationApproval approval = pendingApproval(scenario, requester, "reverse-drift");
        scenario.redemption().reverse("system");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        stubActor(reviewer, "api-gateway");

        assertThatThrownBy(() -> service.approve(
                approval.getId(),
                new RedemptionReversalApprovalDecisionRequestDto("approved"),
                reviewer,
                "corr-approve"))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_SUBJECT_CHANGED));
    }

    @Test
    void requireApprovedRejectsChangedExecutionPayload() {
        CurrentUser requester = user(1L);
        CurrentUser reviewer = user(2L);
        CurrentUser executor = user(3L);
        Scenario scenario = scenario();
        IncentiveOperationApproval approval = pendingApproval(scenario, requester, "reverse-payload");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        stubActor(reviewer, "api-gateway");
        stubActor(executor, "api-gateway");
        service.approve(
                approval.getId(),
                new RedemptionReversalApprovalDecisionRequestDto("approved"),
                reviewer,
                "corr-approve");

        assertThatThrownBy(() -> service.requireApprovedForReverse(
                scenario.redemption(),
                new ReverseRedemptionRequestDto(
                        "reverse-payload",
                        "different reason",
                        approval.getId(),
                        "INC-1001"),
                executor))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_PAYLOAD_CHANGED));
    }

    private IncentiveOperationApproval pendingApproval(Scenario scenario, CurrentUser requester, String idempotencyKey) {
        stubActor(requester, "api-gateway");
        stubRedemption(scenario);
        when(approvals.findActiveForSubject(any(), any(), any(), any())).thenReturn(Optional.empty());
        when(approvals.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        service.requestApproval(
                scenario.redemption().getId(),
                approvalRequest(idempotencyKey),
                requester,
                "corr-request");
        ArgumentCaptor<IncentiveOperationApproval> captor = ArgumentCaptor.forClass(IncentiveOperationApproval.class);
        verify(approvals).save(captor.capture());
        return captor.getValue();
    }

    private void stubRedemption(Scenario scenario) {
        when(redemptions.lockById(scenario.redemption().getId())).thenReturn(Optional.of(scenario.redemption()));
        when(reservations.lockById(scenario.reservation().getId())).thenReturn(Optional.of(scenario.reservation()));
    }

    private void stubActor(CurrentUser user, String sourceClientId) {
        when(access.actorType(user)).thenReturn("user");
        org.mockito.Mockito.lenient().when(access.sourceClientId(user)).thenReturn(sourceClientId);
    }

    private RedemptionReversalApprovalRequestDto approvalRequest(String idempotencyKey) {
        return new RedemptionReversalApprovalRequestDto(
                idempotencyKey,
                "order refunded",
                "INC-1001",
                Map.of("evidenceRef", "refund-case-42"));
    }

    private IncentiveOperationApproval existingApproval(Scenario scenario, String requestedBy) {
        return new IncentiveOperationApproval(
                IncentiveOperationApproval.OPERATION_REDEMPTION_REVERSE,
                IncentiveOperationApproval.TARGET_REDEMPTION,
                scenario.redemption().getId(),
                "courseflow",
                "lms",
                scenario.redemption().getCampaignId(),
                "courseflow/lms/redemption/" + scenario.redemption().getId(),
                "request-hash",
                "result-hash",
                "subject-hash",
                1,
                1,
                0,
                0,
                0,
                true,
                true,
                "{}",
                "order refunded",
                "INC-1001",
                requestedBy,
                "corr",
                "api-gateway",
                Instant.now().plusSeconds(3600));
    }

    private Scenario scenario() {
        UUID campaignId = UUID.randomUUID();
        UUID couponId = UUID.randomUUID();
        IncentiveReservation reservation = new IncentiveReservation(
                "courseflow",
                "lms",
                campaignId,
                7,
                couponId,
                "profile-1",
                "order-1",
                "[{\"type\":\"DISCOUNT\",\"amount\":10.00,\"currency\":\"USD\"}]",
                "{\"profileId\":\"profile-1\"}",
                "reservation-request-hash",
                "[]",
                Instant.now().plusSeconds(3600));
        reservation.commit("order-1");
        return new Scenario(reservation, new IncentiveRedemption(reservation));
    }

    private CurrentUser user(Long id) {
        return new CurrentUser(id, "operator-" + id + "@example.com", "ADMIN", Set.of("ADMIN"), Set.of());
    }

    private record Scenario(IncentiveReservation reservation, IncentiveRedemption redemption) {
    }
}
