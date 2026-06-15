package edu.courseflow.loyalty.controller;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateAccountRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateLoyaltyTierPolicyRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateProgramRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LedgerQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyBalanceResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyWalletResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerRewardCatalogResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAccountDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAdjustmentApprovalDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAdjustmentApprovalQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyApprovalEvidencePackDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAuditQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyBalanceBucketResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyBenefitReconciliationQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyFinanceCloseoutExportDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterActionRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterActionResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterApprovalDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterApprovalQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterApprovalReviewRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterDetailDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyInboundDeadLetterQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramAdminDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramClientBindingDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramReadinessDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyReconciliationQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardRedemptionDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardRedemptionQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierPolicyDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierRecalculateResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierStateQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointLotBackfillRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointLotBackfillResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsAdjustmentRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryDryRunRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryDryRunResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryExecutionRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryExecutionResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RedeemRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RecalculateLoyaltyTiersRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReviewLoyaltyAdjustmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RetryRewardFulfillmentRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RewardFulfillmentCallbackRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RewardFulfillmentRunResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitPointsAdjustmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitPointsExpiryApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitRewardFulfillmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitRewardRedemptionReversalApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateAccountStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateLoyaltyTierPolicyRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateLoyaltyTierPolicyStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateProgramRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateProgramStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardFulfillmentStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpsertClientBindingRequestDto;
import edu.courseflow.loyalty.service.LoyaltyAdminService;
import edu.courseflow.loyalty.service.LoyaltyBenefitReconciliationService;
import edu.courseflow.loyalty.service.LoyaltyInboundDeadLetterService;
import edu.courseflow.loyalty.service.LoyaltyRewardService;
import edu.courseflow.loyalty.service.LoyaltyService;
import edu.courseflow.loyalty.service.LoyaltyTierService;
import edu.courseflow.loyalty.service.LoyaltyWalletService;
import jakarta.validation.Valid;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/loyalty")
public class LoyaltyController {

    private final LoyaltyService loyaltyService;
    private final LoyaltyAdminService adminService;
    private final LoyaltyInboundDeadLetterService deadLetterService;
    private final LoyaltyRewardService rewardService;
    private final LoyaltyTierService tierService;
    private final LoyaltyWalletService walletService;
    private final LoyaltyBenefitReconciliationService benefitReconciliationService;

    public LoyaltyController(
            LoyaltyService loyaltyService,
            LoyaltyAdminService adminService,
            LoyaltyInboundDeadLetterService deadLetterService,
            LoyaltyRewardService rewardService,
            LoyaltyTierService tierService,
            LoyaltyWalletService walletService,
            LoyaltyBenefitReconciliationService benefitReconciliationService) {
        this.loyaltyService = loyaltyService;
        this.adminService = adminService;
        this.deadLetterService = deadLetterService;
        this.rewardService = rewardService;
        this.tierService = tierService;
        this.walletService = walletService;
        this.benefitReconciliationService = benefitReconciliationService;
    }

    @GetMapping("/programs")
    public List<LoyaltyProgramAdminDto> programs(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return adminService.listPrograms(tenantId, applicationId, programId, status, limit, user);
    }

    @GetMapping("/program-readiness")
    public LoyaltyProgramReadinessDto programReadiness(
            @RequestParam String tenantId,
            @RequestParam String applicationId,
            @RequestParam String programId,
            @RequestParam Optional<String> clientId,
            @RequestParam Optional<String> operation,
            CurrentUser user) {
        return adminService.programReadiness(tenantId, applicationId, programId, clientId, operation, user);
    }

    @PostMapping("/programs")
    public LoyaltyProgramDto createProgram(@Valid @RequestBody CreateProgramRequestDto request, CurrentUser user) {
        return loyaltyService.createProgram(request, user);
    }

    @GetMapping("/me/balances")
    public LearnerLoyaltyBalanceResponseDto learnerBalances(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            CurrentUser user) {
        return loyaltyService.learnerBalances(tenantId, applicationId, programId, user);
    }

    @GetMapping("/me/wallet")
    public LearnerLoyaltyWalletResponseDto learnerWallet(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return walletService.learnerWallet(tenantId, applicationId, programId, limit, user);
    }

    @GetMapping("/me/rewards")
    public LearnerRewardCatalogResponseDto learnerRewards(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            CurrentUser user) {
        return rewardService.learnerRewards(tenantId, applicationId, programId, user);
    }

    @PostMapping("/me/rewards/{rewardId}:redeem")
    public LoyaltyRewardRedemptionDto redeemReward(
            @PathVariable UUID rewardId,
            @Valid @RequestBody RedeemRewardRequestDto request,
            CurrentUser user) {
        return rewardService.redeemReward(rewardId, request, user);
    }

    @GetMapping("/programs/{programUuid}")
    public LoyaltyProgramAdminDto program(@PathVariable UUID programUuid, CurrentUser user) {
        return adminService.program(programUuid, user);
    }

    @PatchMapping("/programs/{programUuid}")
    public LoyaltyProgramAdminDto updateProgram(
            @PathVariable UUID programUuid,
            @Valid @RequestBody UpdateProgramRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return adminService.updateProgram(programUuid, request, correlationId, user);
    }

    @PatchMapping("/programs/{programUuid}/status")
    public LoyaltyProgramAdminDto updateProgramStatus(
            @PathVariable UUID programUuid,
            @Valid @RequestBody UpdateProgramStatusRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return adminService.updateProgramStatus(programUuid, request, correlationId, user);
    }

    @PostMapping("/programs/{programUuid}/client-bindings")
    public LoyaltyProgramClientBindingDto upsertProgramClientBinding(
            @PathVariable UUID programUuid,
            @Valid @RequestBody UpsertClientBindingRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return adminService.upsertClientBinding(programUuid, request, correlationId, user);
    }

    @GetMapping("/programs/{programUuid}/timeline")
    public LoyaltyAuditQueryResponseDto programTimeline(
            @PathVariable UUID programUuid,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return adminService.programTimeline(programUuid, limit, user);
    }

    @PostMapping("/accounts")
    public LoyaltyAccountDto createAccount(@Valid @RequestBody CreateAccountRequestDto request, CurrentUser user) {
        return loyaltyService.createAccount(request, user);
    }

    @GetMapping("/accounts/{accountId}")
    public LoyaltyAccountDto account(@PathVariable UUID accountId, CurrentUser user) {
        return loyaltyService.account(accountId, user);
    }

    @GetMapping("/accounts")
    public LoyaltyAccountDto account(
            @RequestParam String tenantId,
            @RequestParam String applicationId,
            @RequestParam String programId,
            @RequestParam String profileId,
            CurrentUser user) {
        return loyaltyService.account(tenantId, applicationId, programId, profileId, user);
    }

    @GetMapping("/accounts:search")
    public List<LoyaltyAccountDto> accounts(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> profileId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return adminService.listAccounts(tenantId, applicationId, programId, profileId, status, limit, user);
    }

    @PatchMapping("/accounts/{accountId}/status")
    public LoyaltyAccountDto updateAccountStatus(
            @PathVariable UUID accountId,
            @Valid @RequestBody UpdateAccountStatusRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return adminService.updateAccountStatus(accountId, request, correlationId, user);
    }

    @GetMapping("/accounts/{accountId}/timeline")
    public LoyaltyAuditQueryResponseDto accountTimeline(
            @PathVariable UUID accountId,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return adminService.accountTimeline(accountId, limit, user);
    }

    @GetMapping("/tier-policies")
    public List<LoyaltyTierPolicyDto> tierPolicies(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return tierService.listPolicies(tenantId, applicationId, programId, status, limit, user);
    }

    @PostMapping("/tier-policies")
    public LoyaltyTierPolicyDto createTierPolicy(
            @Valid @RequestBody CreateLoyaltyTierPolicyRequestDto request,
            CurrentUser user) {
        return tierService.createPolicy(request, user);
    }

    @PatchMapping("/tier-policies/{policyId}")
    public LoyaltyTierPolicyDto updateTierPolicy(
            @PathVariable UUID policyId,
            @Valid @RequestBody UpdateLoyaltyTierPolicyRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return tierService.updatePolicy(policyId, request, correlationId, user);
    }

    @PatchMapping("/tier-policies/{policyId}/status")
    public LoyaltyTierPolicyDto updateTierPolicyStatus(
            @PathVariable UUID policyId,
            @Valid @RequestBody UpdateLoyaltyTierPolicyStatusRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return tierService.updatePolicyStatus(policyId, request, correlationId, user);
    }

    @GetMapping("/tier-states")
    public LoyaltyTierStateQueryResponseDto tierStates(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> profileId,
            @RequestParam Optional<String> tierCode,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return tierService.listStates(tenantId, applicationId, programId, profileId, tierCode, limit, user);
    }

    @PostMapping("/tier-states:recalculate")
    public LoyaltyTierRecalculateResponseDto recalculateTierStates(
            @Valid @RequestBody RecalculateLoyaltyTiersRequestDto request,
            CurrentUser user) {
        return tierService.recalculate(request, user);
    }

    @GetMapping("/accounts/{accountId}/balance-buckets")
    public LoyaltyBalanceBucketResponseDto balanceBuckets(
            @PathVariable UUID accountId,
            @RequestParam Optional<Instant> asOf,
            CurrentUser user) {
        return adminService.balanceBuckets(accountId, asOf, user);
    }

    @PostMapping("/points:earn")
    public PointsMutationResponseDto earn(@Valid @RequestBody PointsMutationRequestDto request, CurrentUser user) {
        return loyaltyService.earn(request, user);
    }

    @PostMapping("/points:burn")
    public PointsMutationResponseDto burn(@Valid @RequestBody PointsMutationRequestDto request, CurrentUser user) {
        return loyaltyService.burn(request, user);
    }

    @PostMapping("/points/{entryId}:reverse")
    public PointsMutationResponseDto reverse(
            @PathVariable UUID entryId,
            @Valid @RequestBody ReversePointsRequestDto request,
            CurrentUser user) {
        return loyaltyService.reverse(entryId, request, user);
    }

    @PostMapping("/points:adjust")
    public PointsMutationResponseDto adjust(@Valid @RequestBody PointsAdjustmentRequestDto request, CurrentUser user) {
        return loyaltyService.adjust(request, user);
    }

    @PostMapping("/points:expire-dry-run")
    public PointsExpiryDryRunResponseDto expiryDryRun(
            @Valid @RequestBody PointsExpiryDryRunRequestDto request,
            CurrentUser user) {
        return loyaltyService.expiryDryRun(request, user);
    }

    @PostMapping("/points:expire")
    public PointsExpiryExecutionResponseDto executeExpiry(
            @Valid @RequestBody PointsExpiryExecutionRequestDto request,
            CurrentUser user) {
        return loyaltyService.executeExpiry(request, user);
    }

    @PostMapping("/point-lots:backfill")
    public PointLotBackfillResponseDto backfillPointLots(
            @Valid @RequestBody PointLotBackfillRequestDto request,
            CurrentUser user) {
        return adminService.backfillPointLots(request, user);
    }

    @GetMapping("/adjustment-approvals")
    public LoyaltyAdjustmentApprovalQueryResponseDto adjustmentApprovals(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> profileId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return adminService.adjustmentApprovals(
                tenantId, applicationId, programId, profileId, status, from, to, limit, user);
    }

    @PostMapping("/adjustment-approvals")
    public LoyaltyAdjustmentApprovalDto submitAdjustmentApproval(
            @Valid @RequestBody SubmitPointsAdjustmentApprovalRequestDto request,
            CurrentUser user) {
        return loyaltyService.submitAdjustmentApproval(request, user);
    }

    @PostMapping("/expiry-approvals")
    public LoyaltyAdjustmentApprovalDto submitExpiryApproval(
            @Valid @RequestBody SubmitPointsExpiryApprovalRequestDto request,
            CurrentUser user) {
        return loyaltyService.submitExpiryApproval(request, user);
    }

    @PostMapping("/adjustment-approvals/{approvalId}:approve")
    public LoyaltyAdjustmentApprovalDto approveAdjustmentApproval(
            @PathVariable UUID approvalId,
            @Valid @RequestBody ReviewLoyaltyAdjustmentApprovalRequestDto request,
            CurrentUser user) {
        return loyaltyService.approveAdjustmentApproval(approvalId, request, user);
    }

    @PostMapping("/adjustment-approvals/{approvalId}:reject")
    public LoyaltyAdjustmentApprovalDto rejectAdjustmentApproval(
            @PathVariable UUID approvalId,
            @Valid @RequestBody ReviewLoyaltyAdjustmentApprovalRequestDto request,
            CurrentUser user) {
        return loyaltyService.rejectAdjustmentApproval(approvalId, request, user);
    }

    @GetMapping("/approvals/{approvalId}/evidence-pack")
    public LoyaltyApprovalEvidencePackDto approvalEvidencePack(
            @PathVariable UUID approvalId,
            CurrentUser user) {
        return adminService.approvalEvidencePack(approvalId, user);
    }

    @GetMapping("/ledger")
    public LedgerQueryResponseDto ledger(@RequestParam UUID accountId, CurrentUser user) {
        return adminService.ledger(accountId, user);
    }

    @GetMapping("/reconciliation/entries")
    public LoyaltyReconciliationQueryResponseDto reconciliationEntries(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> profileId,
            @RequestParam Optional<UUID> accountId,
            @RequestParam Optional<String> entryType,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return adminService.reconciliationEntries(
                tenantId, applicationId, programId, profileId, accountId, entryType, from, to, limit, user);
    }

    @GetMapping("/benefit-reconciliation/entries")
    public LoyaltyBenefitReconciliationQueryResponseDto benefitReconciliationEntries(
            @RequestParam String tenantId,
            @RequestParam String applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> profileId,
            @RequestParam Optional<String> redemptionId,
            @RequestParam Optional<String> itemType,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Boolean> includeMatched,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return benefitReconciliationService.query(
                tenantId,
                applicationId,
                programId,
                profileId,
                redemptionId,
                itemType,
                status,
                includeMatched,
                from,
                to,
                limit,
                user);
    }

    @GetMapping("/finance/closeout")
    public LoyaltyFinanceCloseoutExportDto financeCloseout(
            @RequestParam String tenantId,
            @RequestParam String applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            @RequestParam Optional<String> cursor,
            CurrentUser user) {
        return adminService.financeCloseout(tenantId, applicationId, programId, from, to, limit, cursor, user);
    }

    @GetMapping("/rewards")
    public List<LoyaltyRewardDto> rewards(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Boolean> activeOnly,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return rewardService.listRewards(tenantId, applicationId, programId, status, activeOnly, limit, user);
    }

    @PostMapping("/rewards")
    public LoyaltyRewardDto createReward(
            @Valid @RequestBody CreateRewardRequestDto request,
            CurrentUser user) {
        return rewardService.createReward(request, user);
    }

    @GetMapping("/rewards/{rewardId}")
    public LoyaltyRewardDto reward(@PathVariable UUID rewardId, CurrentUser user) {
        return rewardService.reward(rewardId, user);
    }

    @PatchMapping("/rewards/{rewardId}")
    public LoyaltyRewardDto updateReward(
            @PathVariable UUID rewardId,
            @Valid @RequestBody UpdateRewardRequestDto request,
            CurrentUser user) {
        return rewardService.updateReward(rewardId, request, user);
    }

    @PatchMapping("/rewards/{rewardId}/status")
    public LoyaltyRewardDto updateRewardStatus(
            @PathVariable UUID rewardId,
            @Valid @RequestBody UpdateRewardStatusRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return rewardService.updateRewardStatus(rewardId, request, correlationId, user);
    }

    @GetMapping("/reward-redemptions")
    public LoyaltyRewardRedemptionQueryResponseDto rewardRedemptions(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> programId,
            @RequestParam Optional<String> profileId,
            @RequestParam Optional<UUID> rewardId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<String> fulfillmentStatus,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return rewardService.redemptions(
                tenantId, applicationId, programId, profileId, rewardId, status, fulfillmentStatus,
                from, to, limit, user);
    }

    @GetMapping("/reward-redemptions/{redemptionId}")
    public LoyaltyRewardRedemptionDto rewardRedemption(@PathVariable UUID redemptionId, CurrentUser user) {
        return rewardService.redemption(redemptionId, user);
    }

    @PostMapping("/reward-redemptions/{redemptionId}:reverse")
    public LoyaltyRewardRedemptionDto reverseRewardRedemption(
            @PathVariable UUID redemptionId,
            @Valid @RequestBody ReversePointsRequestDto request,
            CurrentUser user) {
        return rewardService.reverseRedemption(redemptionId, request, user);
    }

    @PostMapping("/reward-redemptions/{redemptionId}/reversal-approvals")
    public LoyaltyAdjustmentApprovalDto submitRewardRedemptionReversalApproval(
            @PathVariable UUID redemptionId,
            @Valid @RequestBody SubmitRewardRedemptionReversalApprovalRequestDto request,
            CurrentUser user) {
        return rewardService.submitReversalApproval(redemptionId, request, user);
    }

    @PostMapping("/reward-redemptions/{redemptionId}/fulfillment-approvals")
    public LoyaltyAdjustmentApprovalDto submitRewardFulfillmentApproval(
            @PathVariable UUID redemptionId,
            @Valid @RequestBody SubmitRewardFulfillmentApprovalRequestDto request,
            CurrentUser user) {
        return rewardService.submitFulfillmentApproval(redemptionId, request, user);
    }

    @PatchMapping("/reward-redemptions/{redemptionId}/fulfillment")
    public LoyaltyRewardRedemptionDto updateRewardRedemptionFulfillment(
            @PathVariable UUID redemptionId,
            @Valid @RequestBody UpdateRewardFulfillmentStatusRequestDto request,
            CurrentUser user) {
        return rewardService.updateFulfillment(redemptionId, request, user);
    }

    @PostMapping("/reward-redemptions/{redemptionId}/fulfillment:retry")
    public LoyaltyRewardRedemptionDto retryRewardRedemptionFulfillment(
            @PathVariable UUID redemptionId,
            @RequestBody(required = false) RetryRewardFulfillmentRequestDto request,
            CurrentUser user) {
        return rewardService.retryFulfillment(redemptionId, request, user);
    }

    @PostMapping("/reward-fulfillment:run-due")
    public RewardFulfillmentRunResponseDto runDueRewardFulfillments(
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return rewardService.runDueFulfillments(limit, user);
    }

    @PostMapping("/reward-fulfillment/{provider}/callbacks")
    public LoyaltyRewardRedemptionDto rewardFulfillmentCallback(
            @PathVariable String provider,
            @Valid @RequestBody RewardFulfillmentCallbackRequestDto request,
            CurrentUser user) {
        return rewardService.applyFulfillmentCallback(provider, request, user);
    }

    @GetMapping("/dead-letters")
    public LoyaltyInboundDeadLetterQueryResponseDto deadLetters(
            @RequestParam Optional<String> status,
            @RequestParam Optional<String> sourceTopic,
            @RequestParam Optional<String> dltTopic,
            @RequestParam Optional<String> payloadHash,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return deadLetterService.search(status, sourceTopic, dltTopic, payloadHash, from, to, limit, user);
    }

    @GetMapping("/dead-letters/{id}")
    public LoyaltyInboundDeadLetterDetailDto deadLetter(@PathVariable UUID id, CurrentUser user) {
        return deadLetterService.get(id, user);
    }

    @GetMapping("/dead-letters/{id}/approvals")
    public LoyaltyInboundDeadLetterApprovalQueryResponseDto deadLetterApprovals(
            @PathVariable UUID id,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return deadLetterService.approvals(id, status, limit, user);
    }

    @PostMapping("/dead-letters/{id}/approvals")
    public LoyaltyInboundDeadLetterApprovalDto requestDeadLetterApproval(
            @PathVariable UUID id,
            @Valid @RequestBody LoyaltyInboundDeadLetterApprovalRequestDto request,
            CurrentUser user) {
        return deadLetterService.requestApproval(id, request, user);
    }

    @PostMapping("/dead-letters/approvals/{approvalId}:approve")
    public LoyaltyInboundDeadLetterApprovalDto approveDeadLetterApproval(
            @PathVariable UUID approvalId,
            @Valid @RequestBody LoyaltyInboundDeadLetterApprovalReviewRequestDto request,
            CurrentUser user) {
        return deadLetterService.approveApproval(approvalId, request, user);
    }

    @PostMapping("/dead-letters/approvals/{approvalId}:reject")
    public LoyaltyInboundDeadLetterApprovalDto rejectDeadLetterApproval(
            @PathVariable UUID approvalId,
            @Valid @RequestBody LoyaltyInboundDeadLetterApprovalReviewRequestDto request,
            CurrentUser user) {
        return deadLetterService.rejectApproval(approvalId, request, user);
    }

    @PostMapping("/dead-letters/{id}:replay")
    public LoyaltyInboundDeadLetterActionResponseDto replayDeadLetter(
            @PathVariable UUID id,
            @RequestBody(required = false) LoyaltyInboundDeadLetterActionRequestDto request,
            CurrentUser user) {
        return deadLetterService.replay(id, request, user);
    }

    @PostMapping("/dead-letters/{id}:discard")
    public LoyaltyInboundDeadLetterActionResponseDto discardDeadLetter(
            @PathVariable UUID id,
            @RequestBody(required = false) LoyaltyInboundDeadLetterActionRequestDto request,
            CurrentUser user) {
        return deadLetterService.discard(id, request, user);
    }

    @GetMapping("/audit")
    public LoyaltyAuditQueryResponseDto audit(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> aggregateType,
            @RequestParam Optional<String> aggregateId,
            @RequestParam Optional<String> action,
            @RequestParam Optional<String> actorId,
            @RequestParam Optional<String> correlationId,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return adminService.audit(
                tenantId, applicationId, aggregateType, aggregateId, action, actorId, correlationId,
                from, to, limit, user);
    }
}
