package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_ALREADY_COMMITTED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_APPROVAL_ALREADY_EXISTS;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_APPROVAL_EXPIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_APPROVAL_NOT_APPROVED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_APPROVAL_NOT_FOUND;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_APPROVAL_NOT_PENDING;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_APPROVAL_SUBJECT_CHANGED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_DRY_RUN_EXPIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_DRY_RUN_NOT_COMMIT_READY;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_DRY_RUN_NOT_FOUND;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_OPERATOR_REQUIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_PAYLOAD_CHANGED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_RESULT_HASH_MISMATCH;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_SELF_APPROVAL_BLOCKED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_SELF_COMMIT_BLOCKED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveOperationApproval;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveOperationApprovalRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CouponImportApprovalService {

    private static final int MAX_QUEUE_LIMIT = 200;

    private final CouponImportDryRunService dryRuns;
    private final IncentiveCouponImportBatchRepository importBatches;
    private final IncentiveOperationApprovalRepository approvals;
    private final IncentiveAuditEventRepository auditEvents;
    private final CouponCodeFingerprintService couponFingerprints;
    private final AdminOperationRateGuard adminOperationRateGuard;
    private final IncentiveAccessService access;
    private final ObjectMapper objectMapper;
    private final Duration approvalTtl;

    public CouponImportApprovalService(CouponImportDryRunService dryRuns,
                                       IncentiveCouponImportBatchRepository importBatches,
                                       IncentiveOperationApprovalRepository approvals,
                                       IncentiveAuditEventRepository auditEvents,
                                       CouponCodeFingerprintService couponFingerprints,
                                       AdminOperationRateGuard adminOperationRateGuard,
                                       IncentiveAccessService access,
                                       ObjectMapper objectMapper,
                                       @Value("${courseflow.promotion.coupon.import-approval-ttl-minutes:60}")
                                       long approvalTtlMinutes) {
        this.dryRuns = dryRuns;
        this.importBatches = importBatches;
        this.approvals = approvals;
        this.auditEvents = auditEvents;
        this.couponFingerprints = couponFingerprints;
        this.adminOperationRateGuard = adminOperationRateGuard;
        this.access = access;
        this.objectMapper = objectMapper;
        this.approvalTtl = Duration.ofMinutes(Math.max(1, approvalTtlMinutes));
    }

    @Transactional
    public CouponImportApprovalResponseDto requestApproval(UUID dryRunId,
                                                           CouponImportCommitRequestDto request,
                                                           CurrentUser user,
                                                           String correlationId) {
        requireOperatorActor(user);
        if (request == null) {
            throw new BadRequestException("Coupon import approval request is required");
        }
        requireText(correlationId, "correlationId");
        requireText(request.csvContent(), "file");
        requireText(request.approvedResultHash(), "approvedResultHash");
        requireText(request.reason(), "reason");
        requireText(request.changeTicket(), "changeTicket");
        if (dryRunId == null) {
            throw new BadRequestException("dryRunId is required");
        }
        IncentiveCouponImportBatch batch = importBatches.lockById(dryRunId)
                .orElseThrow(() -> NotFoundException.coded(
                        COUPON_IMPORT_DRY_RUN_NOT_FOUND,
                        "Coupon import dry-run not found: " + dryRunId));
        requireAdmin(batch, user);
        if (request.campaignId() != null && !batch.getCampaignId().equals(request.campaignId())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import dry-run belongs to a different campaign");
        }
        requireBatchCommitReady(batch);
        String sourceClientId = access.sourceClientId(user);
        adminOperationRateGuard.requireAllowed(
                "coupon_import_approval_request",
                batch.getTenantId(),
                batch.getApplicationId(),
                batch.getCampaignId(),
                user,
                sourceClientId,
                batch.getContentHash());

        CouponImportDryRunService.DryRunEvaluation evaluation = dryRuns.evaluateForCommit(
                dryRuns.commitDryRunRequest(effectiveRequestFromBatch(request, batch)),
                user);
        if (!evaluation.campaign().getId().equals(batch.getCampaignId())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import approval payload campaign does not match dry-run");
        }
        if (!evaluation.resultHash().equals(batch.getResultHash())
                || !evaluation.resultHash().equals(request.approvedResultHash())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_RESULT_HASH_MISMATCH,
                    "Coupon import approval result hash no longer matches");
        }
        if (!evaluation.commitReady()) {
            throw ConflictException.coded(
                    COUPON_IMPORT_DRY_RUN_NOT_COMMIT_READY,
                    "Coupon import approval payload is no longer commit-ready");
        }

        String subjectHash = subjectHash(batch);
        approvals.findActiveForSubject(
                        IncentiveOperationApproval.OPERATION_COUPON_IMPORT_COMMIT,
                        IncentiveOperationApproval.TARGET_COUPON_IMPORT_DRY_RUN,
                        batch.getId(),
                        subjectHash)
                .ifPresent(existing -> {
                    throw ConflictException.coded(
                            COUPON_IMPORT_APPROVAL_ALREADY_EXISTS,
                            "An active coupon import approval already exists for this dry-run");
                });
        Instant expiresAt = approvalExpiresAt(batch, Instant.now());
        String actorId = actorId(user);
        IncentiveOperationApproval approval = new IncentiveOperationApproval(
                IncentiveOperationApproval.OPERATION_COUPON_IMPORT_COMMIT,
                IncentiveOperationApproval.TARGET_COUPON_IMPORT_DRY_RUN,
                batch.getId(),
                batch.getTenantId(),
                batch.getApplicationId(),
                batch.getCampaignId(),
                batch.getTenantId() + "/" + batch.getApplicationId(),
                batch.getRequestHash(),
                batch.getResultHash(),
                subjectHash,
                batch.getRequestedRows(),
                batch.getValidRows(),
                batch.getInvalidRows(),
                batch.getDuplicateInFileRows(),
                batch.getDuplicateExistingRows(),
                batch.isStorageInventoryReady(),
                batch.isCommitReady(),
                subjectJson(batch),
                request.reason().trim(),
                request.changeTicket().trim(),
                actorId,
                correlationId,
                sourceClientId,
                expiresAt);
        approvals.save(approval);
        auditApproval("coupon.import_approval_requested", approval, actorId, request.reason().trim(),
                correlationId, sourceClientId);
        return approvalDto(approval);
    }

    @Transactional(readOnly = true)
    public CouponImportApprovalResponseDto approval(UUID approvalId, CurrentUser user) {
        requireOperatorActor(user);
        IncentiveOperationApproval approval = approvals.findById(approvalId)
                .orElseThrow(() -> BadRequestException.coded(
                        COUPON_IMPORT_APPROVAL_NOT_FOUND,
                        "Coupon import approval not found"));
        requireRead(approval.getTenantId(), approval.getApplicationId(), user);
        return approvalDto(approval);
    }

    @Transactional(readOnly = true)
    public List<CouponImportApprovalResponseDto> queue(String tenantId,
                                                       String applicationId,
                                                       UUID campaignId,
                                                       String status,
                                                       Integer limit,
                                                       CurrentUser user) {
        requireOperatorActor(user);
        String tenant = requireText(tenantId, "tenantId");
        String application = requireText(applicationId, "applicationId");
        requireRead(tenant, application, user);
        String normalizedStatus = blankToNull(status);
        if (normalizedStatus != null && !List.of(
                IncentiveOperationApproval.STATUS_PENDING,
                IncentiveOperationApproval.STATUS_APPROVED,
                IncentiveOperationApproval.STATUS_REJECTED,
                IncentiveOperationApproval.STATUS_EXECUTED).contains(normalizedStatus)) {
            throw new BadRequestException("Unsupported coupon import approval status: " + status);
        }
        int pageSize = Math.min(MAX_QUEUE_LIMIT, Math.max(1, limit == null ? 50 : limit));
        return approvals.search(
                        IncentiveOperationApproval.OPERATION_COUPON_IMPORT_COMMIT,
                        tenant,
                        application,
                        campaignId,
                        normalizedStatus,
                        PageRequest.of(0, pageSize))
                .stream()
                .map(this::approvalDto)
                .toList();
    }

    @Transactional
    public CouponImportApprovalResponseDto approve(UUID approvalId,
                                                   CouponImportApprovalDecisionRequestDto request,
                                                   CurrentUser user,
                                                   String correlationId) {
        requireOperatorActor(user);
        requireText(correlationId, "correlationId");
        IncentiveOperationApproval approval = lockApproval(approvalId);
        requireReview(approval, user);
        String sourceClientId = access.sourceClientId(user);
        adminOperationRateGuard.requireAllowed(
                "coupon_import_approval_decision",
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getCampaignId(),
                user,
                sourceClientId,
                approval.getSubjectHash());
        String actorId = actorId(user);
        if (actorId.equals(approval.getRequestedBy())) {
            throw ForbiddenException.coded(
                    COUPON_IMPORT_SELF_APPROVAL_BLOCKED,
                    "Coupon import approval must be reviewed by a different operator");
        }
        if (!approval.pending()) {
            throw ConflictException.coded(
                    COUPON_IMPORT_APPROVAL_NOT_PENDING,
                    "Coupon import approval is not pending");
        }
        if (approval.expired(Instant.now())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_APPROVAL_EXPIRED,
                    "Coupon import approval is expired");
        }
        validateBatchStillCommitReady(approval);
        approval.approve(actorId, request == null ? null : request.note(), Instant.now());
        auditApproval("coupon.import_approval_approved", approval, actorId,
                request == null ? null : request.note(), correlationId, sourceClientId);
        return approvalDto(approval);
    }

    @Transactional
    public CouponImportApprovalResponseDto reject(UUID approvalId,
                                                  CouponImportApprovalDecisionRequestDto request,
                                                  CurrentUser user,
                                                  String correlationId) {
        requireOperatorActor(user);
        requireText(correlationId, "correlationId");
        String note = request == null ? null : requireText(request.note(), "note");
        IncentiveOperationApproval approval = lockApproval(approvalId);
        requireReview(approval, user);
        String sourceClientId = access.sourceClientId(user);
        adminOperationRateGuard.requireAllowed(
                "coupon_import_approval_decision",
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getCampaignId(),
                user,
                sourceClientId,
                approval.getSubjectHash());
        String actorId = actorId(user);
        if (actorId.equals(approval.getRequestedBy())) {
            throw ForbiddenException.coded(
                    COUPON_IMPORT_SELF_APPROVAL_BLOCKED,
                    "Coupon import approval must be rejected by a different operator");
        }
        if (!approval.pending()) {
            throw ConflictException.coded(
                    COUPON_IMPORT_APPROVAL_NOT_PENDING,
                    "Coupon import approval is not pending");
        }
        approval.reject(actorId, note, Instant.now());
        auditApproval("coupon.import_approval_rejected", approval, actorId, note, correlationId, sourceClientId);
        return approvalDto(approval);
    }

    @Transactional
    public IncentiveOperationApproval requireApprovedForCommit(UUID approvalId, CurrentUser user) {
        requireOperatorActor(user);
        if (approvalId == null) {
            throw new BadRequestException("approvalId is required");
        }
        IncentiveOperationApproval approval = lockApproval(approvalId);
        requireAdmin(approval, user);
        String actorId = actorId(user);
        if (approval.approved()) {
            if (actorId.equals(approval.getApprovedBy())) {
                throw ForbiddenException.coded(
                        COUPON_IMPORT_SELF_COMMIT_BLOCKED,
                        "Coupon import commit must be run by a different operator from approver");
            }
            if (approval.expired(Instant.now())) {
                throw ConflictException.coded(
                        COUPON_IMPORT_APPROVAL_EXPIRED,
                        "Coupon import approval is expired");
            }
            validateBatchStillCommitReady(approval);
            return approval;
        }
        if (approval.executed()) {
            return approval;
        }
        throw ConflictException.coded(
                COUPON_IMPORT_APPROVAL_NOT_APPROVED,
                "Coupon import approval is not approved");
    }

    public CouponImportCommitRequestDto effectiveCommitRequest(CouponImportCommitRequestDto request,
                                                               IncentiveOperationApproval approval) {
        if (request.dryRunId() != null && !approval.getTargetId().equals(request.dryRunId())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import approval belongs to a different dry-run");
        }
        if (request.campaignId() != null && !approval.getCampaignId().equals(request.campaignId())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import approval belongs to a different campaign");
        }
        if (request.approvedResultHash() != null && !request.approvedResultHash().isBlank()
                && !approval.getResultHash().equals(request.approvedResultHash())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_RESULT_HASH_MISMATCH,
                    "Coupon import approval result hash does not match commit request");
        }
        if (request.reason() != null && !request.reason().isBlank()
                && !approval.getReason().equals(request.reason().trim())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import approval reason does not match commit request");
        }
        if (request.changeTicket() != null && !request.changeTicket().isBlank()
                && !approval.getChangeTicket().equals(request.changeTicket().trim())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import approval change ticket does not match commit request");
        }
        return new CouponImportCommitRequestDto(
                approval.getId(),
                approval.getTargetId(),
                approval.getCampaignId(),
                request.csvContent(),
                request.maxRows(),
                request.holderProfileId(),
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                request.metadata(),
                approval.getReason(),
                approval.getChangeTicket(),
                approval.getResultHash(),
                request.idempotencyKey(),
                request.confirm());
    }

    @Transactional
    public void markCommitted(IncentiveOperationApproval approval,
                              String actorId,
                              Instant committedAt,
                              String correlationId,
                              String sourceClientId) {
        if (approval == null || approval.executed()) {
            return;
        }
        approval.markExecuted(actorId, committedAt);
        auditApproval("coupon.import_approval_executed", approval, actorId, approval.getReason(),
                correlationId, sourceClientId);
    }

    public CouponImportApprovalResponseDto approvalDto(IncentiveOperationApproval approval) {
        return new CouponImportApprovalResponseDto(
                approval.getId(),
                approval.getStatus(),
                approval.getTargetId(),
                approval.getCampaignId(),
                approval.getResultHash(),
                approval.getRequestedRows(),
                approval.getValidRows(),
                approval.getInvalidRows(),
                approval.getDuplicateInFileRows(),
                approval.getDuplicateExistingRows(),
                approval.isStorageInventoryReady(),
                approval.isCommitReady(),
                approval.getReason(),
                approval.getChangeTicket(),
                approval.getRequestedBy(),
                approval.getApprovedBy(),
                approval.getRejectedBy(),
                approval.getExecutedBy(),
                approval.getExpiresAt(),
                approval.getCreatedAt(),
                approval.getApprovedAt(),
                approval.getRejectedAt(),
                approval.getExecutedAt());
    }

    private IncentiveOperationApproval lockApproval(UUID approvalId) {
        return approvals.lockById(approvalId)
                .orElseThrow(() -> BadRequestException.coded(
                        COUPON_IMPORT_APPROVAL_NOT_FOUND,
                        "Coupon import approval not found"));
    }

    private void validateBatchStillCommitReady(IncentiveOperationApproval approval) {
        IncentiveCouponImportBatch batch = importBatches.lockById(approval.getTargetId())
                .orElseThrow(() -> ConflictException.coded(
                        COUPON_IMPORT_DRY_RUN_NOT_FOUND,
                        "Coupon import dry-run is no longer available"));
        requireBatchCommitReady(batch);
        if (!Objects.equals(batch.getResultHash(), approval.getResultHash())
                || !Objects.equals(batch.getRequestHash(), approval.getRequestHash())
                || !Objects.equals(subjectHash(batch), approval.getSubjectHash())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_APPROVAL_SUBJECT_CHANGED,
                    "Coupon import approval dry-run no longer matches current batch");
        }
    }

    private CouponImportCommitRequestDto effectiveRequestFromBatch(CouponImportCommitRequestDto request,
                                                                   IncentiveCouponImportBatch batch) {
        return new CouponImportCommitRequestDto(
                request.approvalId(),
                batch.getId(),
                batch.getCampaignId(),
                request.csvContent(),
                request.maxRows(),
                request.holderProfileId(),
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                request.metadata(),
                request.reason(),
                request.changeTicket(),
                request.approvedResultHash(),
                request.idempotencyKey(),
                request.confirm());
    }

    private void requireBatchCommitReady(IncentiveCouponImportBatch batch) {
        if (batch.getCommittedAt() != null) {
            throw ConflictException.coded(
                    COUPON_IMPORT_ALREADY_COMMITTED,
                    "Coupon import dry-run has already been committed");
        }
        if (batch.getExpiresAt() != null && !batch.getExpiresAt().isAfter(Instant.now())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_DRY_RUN_EXPIRED,
                    "Coupon import dry-run has expired");
        }
        if (!batch.isCommitReady()
                || batch.getInvalidRows() != 0
                || batch.getDuplicateInFileRows() != 0
                || batch.getDuplicateExistingRows() != 0
                || !batch.isStorageInventoryReady()) {
            throw ConflictException.coded(
                    COUPON_IMPORT_DRY_RUN_NOT_COMMIT_READY,
                    "Coupon import dry-run is not commit-ready");
        }
    }

    private void requireAdmin(IncentiveCouponImportBatch batch, CurrentUser user) {
        access.requireCouponImportManageAccess(batch.getTenantId(), batch.getApplicationId(), user);
        access.requireActiveApplication(batch.getTenantId(), batch.getApplicationId(), user, "admin");
    }

    private void requireAdmin(IncentiveOperationApproval approval, CurrentUser user) {
        access.requireCouponImportManageAccess(approval.getTenantId(), approval.getApplicationId(), user);
        access.requireActiveApplication(approval.getTenantId(), approval.getApplicationId(), user, "admin");
    }

    private void requireReview(IncentiveOperationApproval approval, CurrentUser user) {
        requireReview(approval.getTenantId(), approval.getApplicationId(), user);
    }

    private void requireReview(String tenantId, String applicationId, CurrentUser user) {
        access.requireCouponImportReviewAccess(tenantId, applicationId, user);
    }

    private void requireRead(String tenantId, String applicationId, CurrentUser user) {
        access.requireCouponImportReadAccess(tenantId, applicationId, user);
    }

    private void requireOperatorActor(CurrentUser user) {
        if (user == null) {
            throw ForbiddenException.coded(
                    COUPON_IMPORT_OPERATOR_REQUIRED,
                    "Coupon import approval requires an authenticated operator");
        }
        if ("service".equalsIgnoreCase(access.actorType(user))) {
            throw ForbiddenException.coded(
                    COUPON_IMPORT_OPERATOR_REQUIRED,
                    "Coupon import approval is not available to runtime service actors");
        }
    }

    private Instant approvalExpiresAt(IncentiveCouponImportBatch batch, Instant now) {
        Instant expiresAt = now.plus(approvalTtl);
        if (batch.getExpiresAt() != null && batch.getExpiresAt().isBefore(expiresAt)) {
            expiresAt = batch.getExpiresAt();
        }
        if (!expiresAt.isAfter(now)) {
            throw ConflictException.coded(
                    COUPON_IMPORT_APPROVAL_EXPIRED,
                    "Coupon import approval already expired");
        }
        return expiresAt;
    }

    private String subjectHash(IncentiveCouponImportBatch batch) {
        return couponFingerprints.integrityHash("coupon-import-approval-subject", String.join("|",
                batch.getId().toString(),
                batch.getCampaignId().toString(),
                batch.getRequestHash(),
                batch.getContentHash(),
                batch.getResultHash(),
                Integer.toString(batch.getRequestedRows()),
                Integer.toString(batch.getValidRows()),
                Integer.toString(batch.getInvalidRows()),
                Integer.toString(batch.getDuplicateInFileRows()),
                Integer.toString(batch.getDuplicateExistingRows()),
                Boolean.toString(batch.isStorageInventoryReady()),
                Boolean.toString(batch.isCommitReady())));
    }

    private String subjectJson(IncentiveCouponImportBatch batch) {
        Map<String, Object> subject = new LinkedHashMap<>();
        subject.put("dryRunId", batch.getId().toString());
        subject.put("campaignId", batch.getCampaignId().toString());
        subject.put("resultHash", batch.getResultHash());
        subject.put("requestedRows", batch.getRequestedRows());
        subject.put("validRows", batch.getValidRows());
        subject.put("invalidRows", batch.getInvalidRows());
        subject.put("duplicateInFileRows", batch.getDuplicateInFileRows());
        subject.put("duplicateExistingRows", batch.getDuplicateExistingRows());
        subject.put("storageInventoryReady", batch.isStorageInventoryReady());
        subject.put("commitReady", batch.isCommitReady());
        return toJson(subject);
    }

    private void auditApproval(String action,
                               IncentiveOperationApproval approval,
                               String actorId,
                               String note,
                               String correlationId,
                               String sourceClientId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("approvalId", approval.getId().toString());
        payload.put("operationType", approval.getOperationType());
        payload.put("status", approval.getStatus());
        payload.put("dryRunId", approval.getTargetId().toString());
        payload.put("campaignId", approval.getCampaignId().toString());
        payload.put("resultHash", approval.getResultHash());
        payload.put("requestedRows", approval.getRequestedRows());
        payload.put("validRows", approval.getValidRows());
        payload.put("reason", approval.getReason());
        payload.put("changeTicket", approval.getChangeTicket());
        auditEvents.save(new IncentiveAuditEvent(
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getId().toString(),
                "coupon-import-approval",
                action,
                actorId,
                note,
                toJson(payload),
                correlationId,
                sourceClientId));
    }

    private String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new BadRequestException(field + " is required");
        }
        return value.trim();
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize coupon import approval", ex);
        }
    }
}
