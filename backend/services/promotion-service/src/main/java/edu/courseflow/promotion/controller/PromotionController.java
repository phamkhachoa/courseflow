package edu.courseflow.promotion.controller;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.AdminPreviewIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.AdminPreviewIncentivesResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ApplicationClientBindingDto;
import edu.courseflow.promotion.dto.PromotionDtos.ApplicationDto;
import edu.courseflow.promotion.dto.PromotionDtos.AuditQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDetailDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDiffDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionReviewQueueResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionTransitionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionValidationDto;
import edu.courseflow.promotion.dto.PromotionDtos.CancelReservationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CancelReservationResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CommitReservationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CommitReservationResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponStorageInventoryDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateApplicationClientBindingRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateApplicationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCampaignRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCouponRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.GenerateCouponsRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.GenerateCouponsResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveCatalogDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.LearnerCouponWalletDto;
import edu.courseflow.promotion.dto.PromotionDtos.RedemptionDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReservationDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionEvidencePackDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionEvidencePackExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionPolicyRegistryDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionRestoreDrillRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionRestoreDrillResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RollbackCampaignVersionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateApplicationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateApplicationStatusRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCampaignStatusRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCampaignVersionDraftRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCouponStatusRequestDto;
import edu.courseflow.promotion.service.CampaignVersionService;
import edu.courseflow.promotion.service.CouponImportApprovalService;
import edu.courseflow.promotion.service.CouponImportCommitService;
import edu.courseflow.promotion.service.CouponImportDryRunService;
import edu.courseflow.promotion.service.CouponImportQueryService;
import edu.courseflow.promotion.service.IncentiveAccessService;
import edu.courseflow.promotion.service.IncentiveAuditQueryService;
import edu.courseflow.promotion.service.IncentiveCatalogService;
import edu.courseflow.promotion.service.IncentiveReconciliationService;
import edu.courseflow.promotion.service.PromotionService;
import edu.courseflow.promotion.service.RetentionApprovalService;
import edu.courseflow.promotion.service.RetentionDryRunService;
import edu.courseflow.promotion.service.RetentionExecutionService;
import jakarta.validation.Valid;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.MediaType;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/internal/incentives")
public class PromotionController {

    private final PromotionService promotions;
    private final IncentiveAccessService access;
    private final CampaignVersionService campaignVersions;
    private final IncentiveAuditQueryService auditQueries;
    private final IncentiveReconciliationService reconciliation;
    private final IncentiveCatalogService catalog;
    private final RetentionDryRunService retention;
    private final RetentionExecutionService retentionExecutions;
    private final RetentionApprovalService retentionApprovals;
    private final CouponImportDryRunService couponImports;
    private final CouponImportApprovalService couponImportApprovals;
    private final CouponImportCommitService couponImportCommits;
    private final CouponImportQueryService couponImportQueries;

    public PromotionController(PromotionService promotions,
                               IncentiveAccessService access,
                               CampaignVersionService campaignVersions,
                               IncentiveAuditQueryService auditQueries,
                               IncentiveReconciliationService reconciliation,
                               IncentiveCatalogService catalog,
                               RetentionDryRunService retention,
                               RetentionExecutionService retentionExecutions,
                               RetentionApprovalService retentionApprovals,
                               CouponImportDryRunService couponImports,
                               CouponImportApprovalService couponImportApprovals,
                               CouponImportCommitService couponImportCommits,
                               CouponImportQueryService couponImportQueries) {
        this.promotions = promotions;
        this.access = access;
        this.campaignVersions = campaignVersions;
        this.auditQueries = auditQueries;
        this.reconciliation = reconciliation;
        this.catalog = catalog;
        this.retention = retention;
        this.retentionExecutions = retentionExecutions;
        this.retentionApprovals = retentionApprovals;
        this.couponImports = couponImports;
        this.couponImportApprovals = couponImportApprovals;
        this.couponImportCommits = couponImportCommits;
        this.couponImportQueries = couponImportQueries;
    }

    @GetMapping("/catalog")
    public IncentiveCatalogDto catalog(CurrentUser user) {
        return catalog.catalog();
    }

    @GetMapping("/applications")
    public List<ApplicationDto> listApplications(@RequestParam Optional<String> tenantId,
                                                 @RequestParam Optional<String> applicationId,
                                                 @RequestParam Optional<String> status,
                                                 CurrentUser user) {
        return access.listApplications(tenantId, applicationId, status, user);
    }

    @PostMapping("/applications")
    public ApplicationDto createApplication(@Valid @RequestBody CreateApplicationRequestDto request,
                                            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                            String correlationId,
                                            CurrentUser user) {
        return access.createApplication(request, user, correlationId);
    }

    @PatchMapping("/applications/{applicationUuid}")
    public ApplicationDto updateApplication(@PathVariable UUID applicationUuid,
                                            @Valid @RequestBody UpdateApplicationRequestDto request,
                                            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                            String correlationId,
                                            CurrentUser user) {
        return access.updateApplication(applicationUuid, request, user, correlationId);
    }

    @PatchMapping("/applications/{applicationUuid}/status")
    public ApplicationDto updateApplicationStatus(@PathVariable UUID applicationUuid,
                                                  @Valid @RequestBody UpdateApplicationStatusRequestDto request,
                                                  @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                                  String correlationId,
                                                  CurrentUser user) {
        return access.updateApplicationStatus(applicationUuid, request, user, correlationId);
    }

    @PostMapping("/applications/{applicationUuid}/client-bindings")
    public ApplicationClientBindingDto upsertApplicationClientBinding(
            @PathVariable UUID applicationUuid,
            @Valid @RequestBody CreateApplicationClientBindingRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return access.upsertClientBinding(applicationUuid, request, user, correlationId);
    }

    @GetMapping("/campaigns")
    public List<CampaignDto> listCampaigns(@RequestParam Optional<String> tenantId,
                                           @RequestParam Optional<String> applicationId,
                                           CurrentUser user) {
        return promotions.listCampaigns(tenantId, applicationId, user);
    }

    @GetMapping("/campaigns/{campaignId}")
    public CampaignDto campaign(@PathVariable UUID campaignId, CurrentUser user) {
        return promotions.campaignDetail(campaignId, user);
    }

    @PostMapping("/campaigns")
    public CampaignDto createCampaign(@Valid @RequestBody CreateCampaignRequestDto request,
                                      @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                      String correlationId,
                                      CurrentUser user) {
        return promotions.createCampaign(request, user, correlationId);
    }

    @PatchMapping("/campaigns/{campaignId}/status")
    public CampaignDto updateCampaignStatus(@PathVariable UUID campaignId,
                                            @Valid @RequestBody UpdateCampaignStatusRequestDto request,
                                            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                            String correlationId,
                                            CurrentUser user) {
        return promotions.updateCampaignStatus(campaignId, request, user, correlationId);
    }

    @GetMapping("/campaigns/{campaignId}/versions")
    public List<CampaignVersionDto> campaignVersionList(@PathVariable UUID campaignId, CurrentUser user) {
        return campaignVersions.listVersions(campaignId, user);
    }

    @GetMapping("/campaign-versions/review-queue")
    public CampaignVersionReviewQueueResponseDto campaignVersionReviewQueue(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return campaignVersions.reviewQueue(
                tenantId.orElse(null),
                applicationId.orElse(null),
                status.orElse(null),
                limit.orElse(null),
                user);
    }

    @PostMapping("/campaigns/{campaignId}/versions")
    public CampaignVersionDto createCampaignVersion(
            @PathVariable UUID campaignId,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return campaignVersions.createDraftVersion(campaignId, user, correlationId);
    }

    @GetMapping("/campaigns/{campaignId}/versions/{versionNumber}")
    public CampaignVersionDetailDto campaignVersion(@PathVariable UUID campaignId,
                                                    @PathVariable int versionNumber,
                                                    CurrentUser user) {
        return campaignVersions.detail(campaignId, versionNumber, user);
    }

    @PatchMapping("/campaigns/{campaignId}/versions/{versionNumber}/draft")
    public CampaignVersionDetailDto updateCampaignVersionDraft(
            @PathVariable UUID campaignId,
            @PathVariable int versionNumber,
            @Valid @RequestBody UpdateCampaignVersionDraftRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return campaignVersions.updateDraft(campaignId, versionNumber, request, user, correlationId);
    }

    @GetMapping("/campaigns/{campaignId}/versions/{versionNumber}/validation")
    public CampaignVersionValidationDto campaignVersionValidation(@PathVariable UUID campaignId,
                                                                  @PathVariable int versionNumber,
                                                                  CurrentUser user) {
        return campaignVersions.validation(campaignId, versionNumber, user);
    }

    @GetMapping("/campaigns/{campaignId}/versions/{leftVersion}/diff")
    public CampaignVersionDiffDto campaignVersionDiff(@PathVariable UUID campaignId,
                                                      @PathVariable int leftVersion,
                                                      @RequestParam int rightVersion,
                                                      CurrentUser user) {
        return campaignVersions.diff(campaignId, leftVersion, rightVersion, user);
    }

    @PostMapping("/campaigns/{campaignId}/versions/{versionNumber}/rollback")
    public CampaignVersionDetailDto rollbackCampaignVersion(@PathVariable UUID campaignId,
                                                            @PathVariable int versionNumber,
                                                            @RequestBody(required = false)
                                                            RollbackCampaignVersionRequestDto request,
                                                            @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                                    required = false)
                                                            String correlationId,
                                                            CurrentUser user) {
        return campaignVersions.rollback(campaignId, versionNumber, request, user, correlationId);
    }

    @PostMapping("/campaigns/{campaignId}/versions/{versionNumber}/submit")
    public CampaignVersionDto submitCampaignVersion(@PathVariable UUID campaignId,
                                                    @PathVariable int versionNumber,
                                                    @RequestBody(required = false)
                                                    CampaignVersionTransitionRequestDto request,
                                                    @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                            required = false)
                                                    String correlationId,
                                                    CurrentUser user) {
        return campaignVersions.submit(campaignId, versionNumber, request, user, correlationId);
    }

    @PostMapping("/campaigns/{campaignId}/versions/{versionNumber}/approve")
    public CampaignVersionDto approveCampaignVersion(@PathVariable UUID campaignId,
                                                     @PathVariable int versionNumber,
                                                     @RequestBody(required = false)
                                                     CampaignVersionTransitionRequestDto request,
                                                     @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                             required = false)
                                                     String correlationId,
                                                     CurrentUser user) {
        return campaignVersions.approve(campaignId, versionNumber, request, user, correlationId);
    }

    @PostMapping("/campaigns/{campaignId}/versions/{versionNumber}/reject")
    public CampaignVersionDto rejectCampaignVersion(@PathVariable UUID campaignId,
                                                    @PathVariable int versionNumber,
                                                    @RequestBody(required = false)
                                                    CampaignVersionTransitionRequestDto request,
                                                    @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                            required = false)
                                                    String correlationId,
                                                    CurrentUser user) {
        return campaignVersions.reject(campaignId, versionNumber, request, user, correlationId);
    }

    @PostMapping("/campaigns/{campaignId}/versions/{versionNumber}/publish")
    public CampaignVersionDto publishCampaignVersion(@PathVariable UUID campaignId,
                                                     @PathVariable int versionNumber,
                                                     @RequestBody(required = false)
                                                     CampaignVersionTransitionRequestDto request,
                                                     @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                             required = false)
                                                     String correlationId,
                                                     CurrentUser user) {
        return campaignVersions.publish(campaignId, versionNumber, request, user, correlationId);
    }

    @PostMapping("/coupons")
    public CouponDto createCoupon(@Valid @RequestBody CreateCouponRequestDto request,
                                  @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                  String correlationId,
                                  CurrentUser user) {
        return promotions.createCoupon(request, user, correlationId);
    }

    @GetMapping("/coupons")
    public List<CouponDto> coupons(@RequestParam Optional<String> tenantId,
                                   @RequestParam Optional<String> applicationId,
                                   @RequestParam Optional<UUID> campaignId,
                                   @RequestParam Optional<String> status,
                                   @RequestParam Optional<String> holderProfileId,
                                   @RequestParam Optional<String> code,
                                   @RequestParam Optional<Integer> limit,
                                   CurrentUser user) {
        return promotions.listCoupons(
                tenantId,
                applicationId,
                campaignId,
                status,
                holderProfileId,
                code,
                limit,
                user);
    }

    @GetMapping("/learner/coupons")
    public LearnerCouponWalletDto learnerCoupons(@RequestParam String tenantId,
                                                 @RequestParam String applicationId,
                                                 @RequestParam String profileId,
                                                 @RequestParam Optional<Integer> limit,
                                                 CurrentUser user) {
        return promotions.learnerCoupons(tenantId, applicationId, profileId, limit, user);
    }

    @GetMapping("/coupons/storage-inventory")
    public CouponStorageInventoryDto couponStorageInventory(@RequestParam Optional<String> tenantId,
                                                            @RequestParam Optional<String> applicationId,
                                                            @RequestParam Optional<UUID> campaignId,
                                                            @RequestParam Optional<Boolean> activeOnly,
                                                            CurrentUser user) {
        return promotions.couponStorageInventory(tenantId, applicationId, campaignId, activeOnly, user);
    }

    @PostMapping(value = "/coupons:import-dry-run", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public CouponImportDryRunResponseDto couponImportDryRun(@RequestParam UUID campaignId,
                                                            @RequestParam Optional<Integer> maxRows,
                                                            @RequestParam Optional<String> holderProfileId,
                                                            @RequestParam Optional<Instant> startsAt,
                                                            @RequestParam Optional<Instant> expiresAt,
                                                            @RequestParam Optional<Integer> maxRedemptions,
                                                            @RequestParam Optional<Integer> maxRedemptionsPerProfile,
                                                            @RequestParam Optional<String> idempotencyKey,
                                                            @RequestParam("file") MultipartFile file,
                                                            @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                                    required = false)
                                                            String correlationId,
                                                            @RequestHeader(value = "Idempotency-Key", required = false)
                                                            String idempotencyKeyHeader,
                                                            CurrentUser user) {
        return couponImports.dryRun(new CouponImportDryRunRequestDto(
                campaignId,
                csvContent(file),
                maxRows.orElse(null),
                holderProfileId.orElse(null),
                startsAt.orElse(null),
                expiresAt.orElse(null),
                maxRedemptions.orElse(null),
                maxRedemptionsPerProfile.orElse(null),
                null,
                firstNonBlank(idempotencyKey.orElse(null), idempotencyKeyHeader)), user, correlationId);
    }

    @GetMapping("/coupons/import-dry-runs")
    public CouponImportDryRunQueryResponseDto couponImportDryRuns(@RequestParam Optional<String> tenantId,
                                                                  @RequestParam Optional<String> applicationId,
                                                                  @RequestParam Optional<UUID> campaignId,
                                                                  @RequestParam Optional<String> status,
                                                                  @RequestParam Optional<Instant> from,
                                                                  @RequestParam Optional<Instant> to,
                                                                  @RequestParam Optional<Integer> limit,
                                                                  CurrentUser user) {
        return couponImportQueries.dryRuns(
                tenantId,
                applicationId,
                campaignId,
                status,
                from,
                to,
                limit,
                user);
    }

    @GetMapping("/coupons/import-dry-runs/{dryRunId}")
    public CouponImportDryRunResponseDto couponImportDryRun(@PathVariable UUID dryRunId,
                                                            CurrentUser user) {
        return couponImports.dryRun(dryRunId, user);
    }

    @GetMapping("/coupons/import-dry-runs/{dryRunId}/issue-export")
    public edu.courseflow.promotion.dto.PromotionDtos.CouponImportIssueExportDto couponImportIssueExport(
            @PathVariable UUID dryRunId,
            @RequestParam Optional<String> rowStatus,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
            String correlationId,
            CurrentUser user) {
        return couponImportQueries.dryRunIssueExport(dryRunId, rowStatus, user, correlationId);
    }

    @PostMapping(value = "/coupons/import-dry-runs/{dryRunId}/approvals",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public CouponImportApprovalResponseDto requestCouponImportApproval(
            @PathVariable UUID dryRunId,
            @RequestParam UUID campaignId,
            @RequestParam String approvedResultHash,
            @RequestParam String reason,
            @RequestParam String changeTicket,
            @RequestParam Optional<Integer> maxRows,
            @RequestParam Optional<String> holderProfileId,
            @RequestParam Optional<Instant> startsAt,
            @RequestParam Optional<Instant> expiresAt,
            @RequestParam Optional<Integer> maxRedemptions,
            @RequestParam Optional<Integer> maxRedemptionsPerProfile,
            @RequestParam("file") MultipartFile file,
            @RequestHeader(GatewayHeaders.CORRELATION_ID)
            String correlationId,
            CurrentUser user) {
        return couponImportApprovals.requestApproval(dryRunId, new CouponImportCommitRequestDto(
                null,
                dryRunId,
                campaignId,
                csvContent(file),
                maxRows.orElse(null),
                holderProfileId.orElse(null),
                startsAt.orElse(null),
                expiresAt.orElse(null),
                maxRedemptions.orElse(null),
                maxRedemptionsPerProfile.orElse(null),
                null,
                reason,
                changeTicket,
                approvedResultHash,
                null,
                true), user, correlationId);
    }

    @GetMapping("/coupons/import-approvals")
    public List<CouponImportApprovalResponseDto> couponImportApprovals(
            @RequestParam String tenantId,
            @RequestParam String applicationId,
            @RequestParam Optional<UUID> campaignId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return couponImportApprovals.queue(
                tenantId,
                applicationId,
                campaignId.orElse(null),
                status.orElse(null),
                limit.orElse(null),
                user);
    }

    @GetMapping("/coupons/import-approvals/{approvalId}")
    public CouponImportApprovalResponseDto couponImportApproval(@PathVariable UUID approvalId,
                                                                CurrentUser user) {
        return couponImportApprovals.approval(approvalId, user);
    }

    @GetMapping("/coupons/import-operations")
    public CouponImportOperationQueryResponseDto couponImportOperations(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<UUID> campaignId,
            @RequestParam Optional<UUID> approvalId,
            @RequestParam Optional<UUID> dryRunId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return couponImportQueries.operations(
                tenantId,
                applicationId,
                campaignId,
                approvalId,
                dryRunId,
                status,
                from,
                to,
                limit,
                user);
    }

    @GetMapping("/coupons/import-operations/{importId}")
    public CouponImportOperationDto couponImportOperation(@PathVariable UUID importId,
                                                          CurrentUser user) {
        return couponImportQueries.operation(importId, user);
    }

    @GetMapping("/coupons/import-operations/{importId}/export")
    public CouponImportOperationExportDto couponImportOperationExport(
            @PathVariable UUID importId,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
            String correlationId,
            CurrentUser user) {
        return couponImportQueries.operationExport(importId, user, correlationId);
    }

    @PostMapping("/coupons/import-approvals/{approvalId}:approve")
    public CouponImportApprovalResponseDto approveCouponImport(@PathVariable UUID approvalId,
                                                               @RequestBody(required = false)
                                                               CouponImportApprovalDecisionRequestDto request,
                                                               @RequestHeader(GatewayHeaders.CORRELATION_ID)
                                                               String correlationId,
                                                               CurrentUser user) {
        return couponImportApprovals.approve(approvalId, request, user, correlationId);
    }

    @PostMapping("/coupons/import-approvals/{approvalId}:reject")
    public CouponImportApprovalResponseDto rejectCouponImport(@PathVariable UUID approvalId,
                                                              @RequestBody(required = false)
                                                              CouponImportApprovalDecisionRequestDto request,
                                                              @RequestHeader(GatewayHeaders.CORRELATION_ID)
                                                              String correlationId,
                                                              CurrentUser user) {
        return couponImportApprovals.reject(approvalId, request, user, correlationId);
    }

    @PostMapping(value = "/coupons/import-approvals/{approvalId}:commit",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public CouponImportCommitResponseDto couponImportApprovalCommit(
            @PathVariable UUID approvalId,
            @RequestParam Optional<UUID> dryRunId,
            @RequestParam Optional<UUID> campaignId,
            @RequestParam Optional<String> approvedResultHash,
            @RequestParam Optional<String> reason,
            @RequestParam Optional<String> changeTicket,
            @RequestParam Optional<String> idempotencyKey,
            @RequestParam boolean confirm,
            @RequestParam Optional<Integer> maxRows,
            @RequestParam Optional<String> holderProfileId,
            @RequestParam Optional<Instant> startsAt,
            @RequestParam Optional<Instant> expiresAt,
            @RequestParam Optional<Integer> maxRedemptions,
            @RequestParam Optional<Integer> maxRedemptionsPerProfile,
            @RequestParam("file") MultipartFile file,
            @RequestHeader(GatewayHeaders.CORRELATION_ID)
            String correlationId,
            @RequestHeader(value = "Idempotency-Key", required = false)
            String idempotencyKeyHeader,
            CurrentUser user) {
        return couponImportCommits.commit(new CouponImportCommitRequestDto(
                approvalId,
                dryRunId.orElse(null),
                campaignId.orElse(null),
                csvContent(file),
                maxRows.orElse(null),
                holderProfileId.orElse(null),
                startsAt.orElse(null),
                expiresAt.orElse(null),
                maxRedemptions.orElse(null),
                maxRedemptionsPerProfile.orElse(null),
                null,
                reason.orElse(null),
                changeTicket.orElse(null),
                approvedResultHash.orElse(null),
                firstNonBlank(idempotencyKey.orElse(null), idempotencyKeyHeader),
                confirm), user, correlationId);
    }

    @PostMapping(value = "/coupons/import-dry-runs/{dryRunId}:commit",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public CouponImportCommitResponseDto couponImportCommit(@PathVariable UUID dryRunId,
                                                            @RequestParam UUID approvalId,
                                                            @RequestParam UUID campaignId,
                                                            @RequestParam String approvedResultHash,
                                                            @RequestParam Optional<String> idempotencyKey,
                                                            @RequestParam String reason,
                                                            @RequestParam String changeTicket,
                                                            @RequestParam boolean confirm,
                                                            @RequestParam Optional<Integer> maxRows,
                                                            @RequestParam Optional<String> holderProfileId,
                                                            @RequestParam Optional<Instant> startsAt,
                                                            @RequestParam Optional<Instant> expiresAt,
                                                            @RequestParam Optional<Integer> maxRedemptions,
                                                            @RequestParam Optional<Integer> maxRedemptionsPerProfile,
                                                            @RequestParam("file") MultipartFile file,
                                                            @RequestHeader(GatewayHeaders.CORRELATION_ID)
                                                            String correlationId,
                                                            @RequestHeader(value = "Idempotency-Key", required = false)
                                                            String idempotencyKeyHeader,
                                                            CurrentUser user) {
        return couponImportCommits.commit(new CouponImportCommitRequestDto(
                approvalId,
                dryRunId,
                campaignId,
                csvContent(file),
                maxRows.orElse(null),
                holderProfileId.orElse(null),
                startsAt.orElse(null),
                expiresAt.orElse(null),
                maxRedemptions.orElse(null),
                maxRedemptionsPerProfile.orElse(null),
                null,
                reason,
                changeTicket,
                approvedResultHash,
                firstNonBlank(idempotencyKey.orElse(null), idempotencyKeyHeader),
                confirm), user, correlationId);
    }

    @GetMapping("/retention/policies")
    public RetentionPolicyRegistryDto retentionPolicies(CurrentUser user) {
        return retention.policies(user);
    }

    private String csvContent(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BadRequestException("Coupon CSV file is required");
        }
        try {
            return new String(file.getBytes(), StandardCharsets.UTF_8);
        } catch (IOException ex) {
            throw new BadRequestException("Unable to read coupon CSV file");
        }
    }

    private String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first.trim();
        }
        return second == null || second.isBlank() ? null : second.trim();
    }

    @PostMapping("/retention/dry-runs")
    public RetentionDryRunResponseDto retentionDryRun(@RequestBody(required = false) RetentionDryRunRequestDto request,
                                                      @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                              required = false)
                                                      String correlationId,
                                                      CurrentUser user) {
        return retention.dryRun(request, user, correlationId);
    }

    @PostMapping("/retention/restore-drills")
    public RetentionRestoreDrillResponseDto registerRestoreDrill(
            @Valid @RequestBody RetentionRestoreDrillRequestDto request,
            @RequestHeader(GatewayHeaders.CORRELATION_ID) String correlationId,
            CurrentUser user) {
        return retentionApprovals.registerRestoreDrill(request, user, correlationId);
    }

    @GetMapping("/retention/restore-drills/{restoreDrillRef}")
    public RetentionRestoreDrillResponseDto restoreDrill(@PathVariable String restoreDrillRef,
                                                         CurrentUser user) {
        return retentionApprovals.restoreDrill(restoreDrillRef, user);
    }

    @PostMapping("/retention/approvals")
    public RetentionApprovalResponseDto requestRetentionApproval(
            @Valid @RequestBody RetentionApprovalRequestDto request,
            @RequestHeader(GatewayHeaders.CORRELATION_ID) String correlationId,
            CurrentUser user) {
        return retentionApprovals.requestApproval(request, user, correlationId);
    }

    @GetMapping("/retention/approvals/{approvalId}")
    public RetentionApprovalResponseDto retentionApproval(@PathVariable UUID approvalId,
                                                          CurrentUser user) {
        return retentionApprovals.approval(approvalId, user);
    }

    @GetMapping("/retention/approvals/{approvalId}/evidence-pack")
    public RetentionEvidencePackDto retentionEvidencePack(
            @PathVariable UUID approvalId,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
            String correlationId,
            CurrentUser user) {
        return retentionApprovals.evidencePack(approvalId, user, correlationId);
    }

    @GetMapping("/retention/approvals/{approvalId}/evidence-pack/export")
    public RetentionEvidencePackExportDto retentionEvidencePackExport(
            @PathVariable UUID approvalId,
            @RequestParam Optional<String> format,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
            String correlationId,
            CurrentUser user) {
        return retentionApprovals.evidencePackExport(approvalId, format.orElse(null), user, correlationId);
    }

    @GetMapping("/retention/approvals")
    public RetentionApprovalQueryResponseDto retentionApprovals(
            @RequestParam Optional<String> scopeType,
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<UUID> approvalId,
            @RequestParam Optional<UUID> dryRunId,
            @RequestParam Optional<String> status,
            @RequestParam Optional<String> policyId,
            @RequestParam Optional<String> changeTicket,
            @RequestParam Optional<String> requestedBy,
            @RequestParam Optional<String> approvedBy,
            @RequestParam Optional<String> executedBy,
            @RequestParam Optional<Boolean> expired,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return retentionApprovals.queue(
                scopeType.orElse(null),
                tenantId.orElse(null),
                applicationId.orElse(null),
                approvalId.orElse(null),
                dryRunId.orElse(null),
                status.orElse(null),
                policyId.orElse(null),
                changeTicket.orElse(null),
                requestedBy.orElse(null),
                approvedBy.orElse(null),
                executedBy.orElse(null),
                expired.orElse(null),
                from.orElse(null),
                to.orElse(null),
                limit.orElse(null),
                user);
    }

    @PostMapping("/retention/approvals/{approvalId}:approve")
    public RetentionApprovalResponseDto approveRetention(@PathVariable UUID approvalId,
                                                         @RequestBody(required = false)
                                                         RetentionApprovalDecisionRequestDto request,
                                                         @RequestHeader(GatewayHeaders.CORRELATION_ID)
                                                         String correlationId,
                                                         CurrentUser user) {
        return retentionApprovals.approve(approvalId, request, user, correlationId);
    }

    @PostMapping("/retention/approvals/{approvalId}:reject")
    public RetentionApprovalResponseDto rejectRetention(@PathVariable UUID approvalId,
                                                        @RequestBody(required = false)
                                                        RetentionApprovalDecisionRequestDto request,
                                                        @RequestHeader(GatewayHeaders.CORRELATION_ID)
                                                        String correlationId,
                                                        CurrentUser user) {
        return retentionApprovals.reject(approvalId, request, user, correlationId);
    }

    @PostMapping("/retention/executions")
    public RetentionExecutionResponseDto retentionExecution(@Valid @RequestBody RetentionExecutionRequestDto request,
                                                            @RequestHeader(GatewayHeaders.CORRELATION_ID)
                                                            String correlationId,
                                                            CurrentUser user) {
        return retentionExecutions.execute(request, user, correlationId);
    }

    @GetMapping("/coupons/{couponId}")
    public CouponDto coupon(@PathVariable UUID couponId, CurrentUser user) {
        return promotions.coupon(couponId, user);
    }

    @PatchMapping("/coupons/{couponId}/status")
    public CouponDto updateCouponStatus(@PathVariable UUID couponId,
                                        @Valid @RequestBody UpdateCouponStatusRequestDto request,
                                        @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                        String correlationId,
                                        CurrentUser user) {
        return promotions.updateCouponStatus(couponId, request, user, correlationId);
    }

    @PostMapping("/coupons:generate")
    public GenerateCouponsResponseDto generateCoupons(@Valid @RequestBody GenerateCouponsRequestDto request,
                                                      @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                              required = false)
                                                      String correlationId,
                                                      CurrentUser user) {
        return promotions.generateCoupons(request, user, correlationId);
    }

    @PostMapping("/admin/preview")
    public AdminPreviewIncentivesResponseDto adminPreview(
            @Valid @RequestBody AdminPreviewIncentivesRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        return promotions.preview(request, user, correlationId);
    }

    @GetMapping("/reservations")
    public List<ReservationDto> reservations(@RequestParam Optional<String> tenantId,
                                             @RequestParam Optional<String> applicationId,
                                             @RequestParam Optional<String> profileId,
                                             @RequestParam Optional<String> externalReference,
                                             @RequestParam Optional<UUID> campaignId,
                                             @RequestParam Optional<UUID> couponId,
                                             @RequestParam Optional<String> status,
                                             @RequestParam Optional<Boolean> expiredOnly,
                                             @RequestParam Optional<Integer> limit,
                                             CurrentUser user) {
        return promotions.listReservations(
                tenantId,
                applicationId,
                profileId,
                externalReference,
                campaignId,
                couponId,
                status,
                expiredOnly,
                limit,
                user);
    }

    @GetMapping("/reservations/{reservationId}")
    public ReservationDto reservation(@PathVariable UUID reservationId, CurrentUser user) {
        return promotions.reservation(reservationId, user);
    }

    @PostMapping("/evaluate")
    public EvaluateIncentivesResponseDto evaluate(@Valid @RequestBody EvaluateIncentivesRequestDto request,
                                                  CurrentUser user) {
        return promotions.evaluate(request, user);
    }

    @PostMapping("/reservations")
    public ReserveIncentiveResponseDto reserve(@Valid @RequestBody ReserveIncentiveRequestDto request,
                                               @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                               String correlationId,
                                               @RequestHeader(value = "Idempotency-Key", required = false)
                                               String idempotencyKeyHeader,
                                               CurrentUser user) {
        return promotions.reserve(new ReserveIncentiveRequestDto(
                firstNonBlank(idempotencyKeyHeader, request.idempotencyKey()),
                request.context()), user, correlationId);
    }

    @PostMapping("/reservations/{reservationId}/commit")
    public CommitReservationResponseDto commit(@PathVariable UUID reservationId,
                                               @Valid @RequestBody CommitReservationRequestDto request,
                                               @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                               String correlationId,
                                               @RequestHeader(value = "Idempotency-Key", required = false)
                                               String idempotencyKeyHeader,
                                               CurrentUser user) {
        return promotions.commit(reservationId, new CommitReservationRequestDto(
                firstNonBlank(idempotencyKeyHeader, request.idempotencyKey()),
                request.externalReference()), user, correlationId);
    }

    @PostMapping("/reservations/{reservationId}/cancel")
    public CancelReservationResponseDto cancel(@PathVariable UUID reservationId,
                                               @Valid @RequestBody CancelReservationRequestDto request,
                                               @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false)
                                               String correlationId,
                                               @RequestHeader(value = "Idempotency-Key", required = false)
                                               String idempotencyKeyHeader,
                                               CurrentUser user) {
        return promotions.cancel(reservationId, new CancelReservationRequestDto(
                firstNonBlank(idempotencyKeyHeader, request.idempotencyKey()),
                request.reason()), user, correlationId);
    }

    @GetMapping("/redemptions")
    public List<RedemptionDto> redemptions(@RequestParam Optional<String> tenantId,
                                           @RequestParam Optional<String> applicationId,
                                           @RequestParam Optional<String> profileId,
                                           @RequestParam Optional<String> externalReference,
                                           @RequestParam Optional<UUID> campaignId,
                                           @RequestParam Optional<UUID> couponId,
                                           @RequestParam Optional<Integer> limit,
                                           CurrentUser user) {
        return promotions.listRedemptions(
                tenantId,
                applicationId,
                profileId,
                externalReference,
                campaignId,
                couponId,
                limit,
                user);
    }

    @GetMapping("/redemptions/{redemptionId}")
    public RedemptionDto redemption(@PathVariable UUID redemptionId, CurrentUser user) {
        return promotions.redemption(redemptionId, user);
    }

    @GetMapping("/reconciliation/entries")
    public IncentiveReconciliationQueryResponseDto reconciliationEntries(
            @RequestParam Optional<String> tenantId,
            @RequestParam Optional<String> applicationId,
            @RequestParam Optional<String> profileId,
            @RequestParam Optional<String> externalReference,
            @RequestParam Optional<UUID> campaignId,
            @RequestParam Optional<UUID> couponId,
            @RequestParam Optional<UUID> redemptionId,
            @RequestParam Optional<UUID> reservationId,
            @RequestParam Optional<String> entryType,
            @RequestParam Optional<Instant> from,
            @RequestParam Optional<Instant> to,
            @RequestParam Optional<Integer> limit,
            CurrentUser user) {
        return reconciliation.query(
                tenantId,
                applicationId,
                profileId,
                externalReference,
                campaignId,
                couponId,
                redemptionId,
                reservationId,
                entryType,
                from,
                to,
                limit,
                user);
    }

    @PostMapping("/redemptions/{redemptionId}/reverse")
    public ReverseRedemptionResponseDto reverseRedemption(@PathVariable UUID redemptionId,
                                                          @Valid @RequestBody
                                                          ReverseRedemptionRequestDto request,
                                                          @RequestHeader(value = GatewayHeaders.CORRELATION_ID,
                                                                  required = false)
                                                          String correlationId,
                                                          @RequestHeader(value = "Idempotency-Key", required = false)
                                                          String idempotencyKeyHeader,
                                                          CurrentUser user) {
        return promotions.reverse(redemptionId, new ReverseRedemptionRequestDto(
                firstNonBlank(idempotencyKeyHeader, request.idempotencyKey()),
                request.reason()), user, correlationId);
    }

    @GetMapping("/audit")
    public AuditQueryResponseDto audit(@RequestParam Optional<String> tenantId,
                                       @RequestParam Optional<String> applicationId,
                                       @RequestParam Optional<String> aggregateType,
                                       @RequestParam Optional<String> aggregateId,
                                       @RequestParam Optional<String> action,
                                       @RequestParam Optional<String> actorId,
                                       @RequestParam Optional<String> correlationId,
                                       @RequestParam Optional<String> sourceClientId,
                                       @RequestParam Optional<Instant> from,
                                       @RequestParam Optional<Instant> to,
                                       @RequestParam Optional<Integer> limit,
                                       CurrentUser user) {
        return auditQueries.query(
                tenantId, applicationId, aggregateType, aggregateId, action, actorId, correlationId, sourceClientId,
                from, to, limit, user);
    }

    @GetMapping("/campaigns/{campaignId}/timeline")
    public AuditQueryResponseDto campaignTimeline(@PathVariable UUID campaignId,
                                                  @RequestParam Optional<Integer> limit,
                                                  CurrentUser user) {
        return auditQueries.campaignTimeline(campaignId, limit, user);
    }

    @GetMapping("/applications/{applicationUuid}/timeline")
    public AuditQueryResponseDto applicationTimeline(@PathVariable UUID applicationUuid,
                                                     @RequestParam Optional<Integer> limit,
                                                     CurrentUser user) {
        return auditQueries.applicationTimeline(applicationUuid, limit, user);
    }

    @GetMapping("/redemptions/{redemptionId}/timeline")
    public AuditQueryResponseDto redemptionTimeline(@PathVariable UUID redemptionId,
                                                    @RequestParam Optional<Integer> limit,
                                                    CurrentUser user) {
        return auditQueries.redemptionTimeline(redemptionId, limit, user);
    }
}
