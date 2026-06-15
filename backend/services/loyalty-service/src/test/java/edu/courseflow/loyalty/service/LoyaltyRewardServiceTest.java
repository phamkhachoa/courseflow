package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RetryRewardFulfillmentRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RewardFulfillmentCallbackRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitRewardFulfillmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitRewardRedemptionReversalApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardFulfillmentStatusRequestDto;
import edu.courseflow.loyalty.model.LoyaltyAdjustmentApproval;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyReward;
import edu.courseflow.loyalty.model.LoyaltyRewardFulfillmentAttempt;
import edu.courseflow.loyalty.model.LoyaltyRewardRedemption;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyAdjustmentApprovalRepository;
import edu.courseflow.loyalty.repository.LoyaltyAuditEventRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointLotRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardFulfillmentAttemptRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRedemptionRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRepository;
import edu.courseflow.loyalty.repository.OutboxEventRepository;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestClient;

@ExtendWith(MockitoExtension.class)
class LoyaltyRewardServiceTest {

    @Mock
    private LoyaltyRewardRepository rewards;
    @Mock
    private LoyaltyRewardRedemptionRepository redemptions;
    @Mock
    private LoyaltyProgramRepository programs;
    @Mock
    private LoyaltyAccountRepository accounts;
    @Mock
    private LoyaltyPointsEntryRepository pointsEntries;
    @Mock
    private LoyaltyPointLotRepository pointLots;
    @Mock
    private LoyaltyAdjustmentApprovalRepository adjustmentApprovals;
    @Mock
    private LoyaltyAuditEventRepository auditEvents;
    @Mock
    private LoyaltyRewardFulfillmentAttemptRepository fulfillmentAttempts;
    @Mock
    private OutboxEventRepository outboxEvents;
    @Mock
    private LoyaltyAccessService access;
    @Mock
    private LoyaltyService loyaltyService;

    private LoyaltyRewardService service;
    private CurrentUser admin;

    @BeforeEach
    void setUp() {
        service = new LoyaltyRewardService(
                rewards,
                redemptions,
                programs,
                accounts,
                pointsEntries,
                pointLots,
                adjustmentApprovals,
                auditEvents,
                fulfillmentAttempts,
                outboxEvents,
                access,
                loyaltyService,
                RestClient.builder(),
                new ObjectMapper().findAndRegisterModules(),
                5,
                60,
                3600,
                48);
        admin = new CurrentUser(1L, "admin@example.com", "ADMIN", Set.of("ADMIN"));
    }

    @Test
    void submitReversalApprovalCapturesThresholdPolicyAndEvidence() {
        LoyaltyRewardRedemption redemption = redemption();
        when(redemptions.findById(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.save(any(LoyaltyAdjustmentApproval.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var approval = service.submitReversalApproval(redemption.getId(), approvalRequest(), admin);

        assertThat(approval.status()).isEqualTo("PENDING");
        assertThat(approval.operationType()).isEqualTo("REWARD_REDEMPTION_REVERSE");
        assertThat(approval.pointsDelta()).isEqualTo(redemption.getPointsCost());
        assertThat(approval.sourceReference()).isEqualTo("reward-reversal:" + redemption.getId());
        assertThat(approval.metadata())
                .containsEntry("thresholdPolicy", "ALL_REWARD_REDEMPTION_REVERSALS_REQUIRE_MAKER_CHECKER_APPROVAL")
                .containsEntry("redemptionId", redemption.getId().toString())
                .containsEntry("burnEntryId", redemption.getBurnEntryId().toString());
    }

    @Test
    void reverseRedemptionRequiresApprovalBeforeRestoringPoints() {
        LoyaltyRewardRedemption redemption = redemption();
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));

        assertThatThrownBy(() -> service.reverseRedemption(
                        redemption.getId(),
                        new ReversePointsRequestDto("reverse-idem", "refund", "corr-reverse", Map.of("ticket", "T-1")),
                        admin))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_REWARD_REVERSAL_APPROVAL_REQUIRED));

        verifyNoInteractions(loyaltyService);
    }

    @Test
    void approvedReversalExecutesPointRestoreAndMarksApprovalExecuted() {
        LoyaltyRewardRedemption redemption = redemption();
        SubmitRewardRedemptionReversalApprovalRequestDto approvalRequest = approvalRequest();
        AtomicReference<LoyaltyAdjustmentApproval> savedApproval = new AtomicReference<>();
        when(redemptions.findById(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.save(any(LoyaltyAdjustmentApproval.class)))
                .thenAnswer(invocation -> {
                    LoyaltyAdjustmentApproval approval = invocation.getArgument(0);
                    savedApproval.set(approval);
                    return approval;
                });
        var submitted = service.submitReversalApproval(redemption.getId(), approvalRequest, admin);

        LoyaltyAdjustmentApproval approval = savedApproval.get();
        approval.approve("checker@example.com", "approved");
        UUID reversalEntryId = UUID.randomUUID();
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.findByIdForUpdate(submitted.id())).thenReturn(Optional.of(approval));
        when(loyaltyService.reverseRewardBurn(eq(redemption.getBurnEntryId()), any(), eq(admin)))
                .thenReturn(new PointsMutationResponseDto(
                        reversalEntryId,
                        redemption.getAccountId(),
                        redemption.getTenantId(),
                        redemption.getApplicationId(),
                        redemption.getProgramId(),
                        redemption.getProfileId(),
                        "REVERSE",
                        redemption.getPointsCost(),
                        100L,
                        false));
        when(redemptions.save(any(LoyaltyRewardRedemption.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var reversed = service.reverseRedemption(
                redemption.getId(),
                new ReversePointsRequestDto(
                        approvalRequest.idempotencyKey(),
                        approvalRequest.reason(),
                        approvalRequest.correlationId(),
                        approvalRequest.metadata(),
                        submitted.id()),
                admin);

        assertThat(reversed.status()).isEqualTo("REVERSED");
        assertThat(reversed.reversalEntryId()).isEqualTo(reversalEntryId);
        assertThat(approval.getStatus()).isEqualTo("EXECUTED");
        assertThat(approval.getExecutedEntryId()).isEqualTo(reversalEntryId);
        verify(loyaltyService).reverseRewardBurn(eq(redemption.getBurnEntryId()), any(), eq(admin));
    }

    @Test
    void submitFulfillmentApprovalCapturesTargetStatusAndEvidence() {
        LoyaltyRewardRedemption redemption = redemption();
        SubmitRewardFulfillmentApprovalRequestDto request = fulfillmentApprovalRequest();
        when(redemptions.findById(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.save(any(LoyaltyAdjustmentApproval.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var approval = service.submitFulfillmentApproval(redemption.getId(), request, admin);

        assertThat(approval.status()).isEqualTo("PENDING");
        assertThat(approval.operationType()).isEqualTo("REWARD_FULFILLMENT_OVERRIDE");
        assertThat(approval.pointsDelta()).isZero();
        assertThat(approval.sourceReference()).isEqualTo("reward-fulfillment:" + redemption.getId());
        assertThat(approval.metadata())
                .containsEntry("thresholdPolicy", "ALL_MANUAL_REWARD_FULFILLMENT_OVERRIDES_REQUIRE_MAKER_CHECKER_APPROVAL")
                .containsEntry("redemptionId", redemption.getId().toString())
                .containsEntry("currentFulfillmentStatus", "PENDING")
                .containsEntry("targetFulfillmentStatus", "ISSUED");
    }

    @Test
    void updateFulfillmentRequiresApprovedApproval() {
        LoyaltyRewardRedemption redemption = redemption();
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));

        assertThatThrownBy(() -> service.updateFulfillment(
                        redemption.getId(),
                        new UpdateRewardFulfillmentStatusRequestDto(
                                "ISSUED",
                                "manual:" + redemption.getId(),
                                "manual issue",
                                "fulfillment-idem",
                                "manual issue ticket",
                                "corr-fulfillment",
                                Map.of("ticketId", "T-2"),
                                null),
                        admin))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_REWARD_FULFILLMENT_APPROVAL_REQUIRED));
    }

    @Test
    void approvedFulfillmentExecutionChangesStatusAndMarksApprovalExecuted() {
        LoyaltyRewardRedemption redemption = redemption();
        SubmitRewardFulfillmentApprovalRequestDto approvalRequest = fulfillmentApprovalRequest();
        AtomicReference<LoyaltyAdjustmentApproval> savedApproval = new AtomicReference<>();
        when(redemptions.findById(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.save(any(LoyaltyAdjustmentApproval.class)))
                .thenAnswer(invocation -> {
                    LoyaltyAdjustmentApproval approval = invocation.getArgument(0);
                    savedApproval.set(approval);
                    return approval;
                });
        var submitted = service.submitFulfillmentApproval(redemption.getId(), approvalRequest, admin);

        LoyaltyAdjustmentApproval approval = savedApproval.get();
        approval.approve("checker@example.com", "approved");
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.findByIdForUpdate(submitted.id())).thenReturn(Optional.of(approval));
        when(redemptions.save(any(LoyaltyRewardRedemption.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var result = service.updateFulfillment(
                redemption.getId(),
                new UpdateRewardFulfillmentStatusRequestDto(
                        approvalRequest.status(),
                        approvalRequest.fulfillmentRef(),
                        approvalRequest.note(),
                        approvalRequest.idempotencyKey(),
                        approvalRequest.reason(),
                        approvalRequest.correlationId(),
                        approvalRequest.metadata(),
                        submitted.id()),
                admin);

        assertThat(result.fulfillmentStatus()).isEqualTo("ISSUED");
        assertThat(result.fulfillmentRef()).isEqualTo(approvalRequest.fulfillmentRef());
        assertThat(approval.getStatus()).isEqualTo("EXECUTED");
        assertThat(approval.getExecutedAt()).isNotNull();
    }

    @Test
    void fulfillmentReviewerCannotExecuteTheirOwnApproval() {
        LoyaltyRewardRedemption redemption = redemption();
        SubmitRewardFulfillmentApprovalRequestDto approvalRequest = fulfillmentApprovalRequest();
        AtomicReference<LoyaltyAdjustmentApproval> savedApproval = new AtomicReference<>();
        when(redemptions.findById(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.save(any(LoyaltyAdjustmentApproval.class)))
                .thenAnswer(invocation -> {
                    LoyaltyAdjustmentApproval approval = invocation.getArgument(0);
                    savedApproval.set(approval);
                    return approval;
                });
        var submitted = service.submitFulfillmentApproval(redemption.getId(), approvalRequest, admin);

        LoyaltyAdjustmentApproval approval = savedApproval.get();
        approval.approve("checker@example.com", "approved");
        CurrentUser checker = new CurrentUser(2L, "checker@example.com", "ADMIN", Set.of("ADMIN"));
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));
        when(adjustmentApprovals.findByIdForUpdate(submitted.id())).thenReturn(Optional.of(approval));

        assertThatThrownBy(() -> service.updateFulfillment(
                        redemption.getId(),
                        new UpdateRewardFulfillmentStatusRequestDto(
                                approvalRequest.status(),
                                approvalRequest.fulfillmentRef(),
                                approvalRequest.note(),
                                approvalRequest.idempotencyKey(),
                                approvalRequest.reason(),
                                approvalRequest.correlationId(),
                                approvalRequest.metadata(),
                                submitted.id()),
                        checker))
                .isInstanceOf(ErrorCodeCarrier.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH));
    }

    @Test
    void manualFulfillmentRetryMarksManualRequiredAndRecordsAttempt() {
        LoyaltyRewardRedemption redemption = redemption();
        LoyaltyReward reward = reward("MANUAL", "{}");
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));
        when(rewards.findById(redemption.getRewardId())).thenReturn(Optional.of(reward));
        when(redemptions.save(any(LoyaltyRewardRedemption.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(fulfillmentAttempts.save(any(LoyaltyRewardFulfillmentAttempt.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var result = service.retryFulfillment(
                redemption.getId(),
                new RetryRewardFulfillmentRequestDto("manual retry", "corr-manual"),
                admin);

        assertThat(result.fulfillmentStatus()).isEqualTo("MANUAL_REQUIRED");
        assertThat(result.fulfillmentProvider()).isEqualTo("MANUAL");
        assertThat(result.fulfillmentAttemptCount()).isEqualTo(1);
        assertThat(result.fulfillmentSlaDueAt()).isNotNull();
        verify(fulfillmentAttempts).save(any(LoyaltyRewardFulfillmentAttempt.class));
    }

    @Test
    void autoIssueFulfillmentRetryIssuesImmediately() {
        LoyaltyRewardRedemption redemption = redemption();
        redemption.initializeFulfillment("AUTO_ISSUE", null, null);
        LoyaltyReward reward = reward("AUTO_ISSUE", "{}");
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));
        when(rewards.findById(redemption.getRewardId())).thenReturn(Optional.of(reward));
        when(redemptions.save(any(LoyaltyRewardRedemption.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(fulfillmentAttempts.save(any(LoyaltyRewardFulfillmentAttempt.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var result = service.retryFulfillment(
                redemption.getId(),
                new RetryRewardFulfillmentRequestDto("auto issue", "corr-auto"),
                admin);

        assertThat(result.fulfillmentStatus()).isEqualTo("ISSUED");
        assertThat(result.fulfillmentRef()).startsWith("auto-issue:");
        assertThat(result.fulfilledAt()).isNotNull();
    }

    @Test
    void webhookFulfillmentCallbackCompletesByExternalReference() {
        LoyaltyRewardRedemption redemption = redemption();
        redemption.initializeFulfillment("WEBHOOK", null, null);
        redemption.updateFulfillment("PENDING", "provider:coupon:" + redemption.getId(), "waiting");
        when(redemptions.findByFulfillmentProviderAndFulfillmentRef(
                "WEBHOOK",
                redemption.getFulfillmentRef()))
                .thenReturn(Optional.of(redemption));
        when(redemptions.findByIdForUpdate(redemption.getId())).thenReturn(Optional.of(redemption));
        when(redemptions.save(any(LoyaltyRewardRedemption.class))).thenAnswer(invocation -> invocation.getArgument(0));

        var result = service.applyFulfillmentCallback(
                "webhook",
                new RewardFulfillmentCallbackRequestDto(
                        null,
                        redemption.getFulfillmentRef(),
                        "ISSUED",
                        "provider-issued-123",
                        "issued by provider",
                        null,
                        null,
                        null,
                        Map.of("providerEventId", "evt-1")),
                admin);

        assertThat(result.fulfillmentStatus()).isEqualTo("ISSUED");
        assertThat(result.fulfillmentRef()).isEqualTo("provider-issued-123");
        assertThat(result.fulfillmentCallbackPayloadHash()).startsWith("sha256:");
        assertThat(result.fulfillmentCallbackReceivedAt()).isNotNull();
    }

    private SubmitRewardRedemptionReversalApprovalRequestDto approvalRequest() {
        return new SubmitRewardRedemptionReversalApprovalRequestDto(
                "reward-reverse-idem",
                "customer refund",
                "corr-reward-reverse",
                Map.of("ticketId", "T-1"));
    }

    private SubmitRewardFulfillmentApprovalRequestDto fulfillmentApprovalRequest() {
        return new SubmitRewardFulfillmentApprovalRequestDto(
                "ISSUED",
                "manual:issued-123",
                "manual reward issued",
                "reward-fulfillment-idem",
                "manual issuance ticket",
                "corr-reward-fulfillment",
                Map.of("ticketId", "T-2"));
    }

    private LoyaltyRewardRedemption redemption() {
        LoyaltyProgram program = new LoyaltyProgram(
                "courseflow",
                "lms",
                "default",
                "Default points",
                "POINT",
                false,
                365,
                "admin");
        LoyaltyReward reward = new LoyaltyReward(
                program,
                "voucher",
                "Voucher",
                null,
                60,
                "ACTIVE",
                null,
                null,
                null,
                null,
                "MANUAL",
                "{}",
                "admin");
        return new LoyaltyRewardRedemption(
                reward,
                UUID.randomUUID(),
                UUID.randomUUID(),
                "profile-1",
                "reward-source",
                "redeem-idem",
                "sha256:redeem",
                "{}",
                "corr-redemption",
                "redeemed",
                "{}");
    }

    private LoyaltyReward reward(String provider, String config) {
        LoyaltyProgram program = new LoyaltyProgram(
                "courseflow",
                "lms",
                "default",
                "Default points",
                "POINT",
                false,
                365,
                "admin");
        return new LoyaltyReward(
                program,
                "voucher",
                "Voucher",
                null,
                60,
                "ACTIVE",
                null,
                null,
                null,
                null,
                provider,
                config,
                "admin");
    }
}
