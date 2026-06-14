package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_ALREADY_COMMITTED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_DRY_RUN_EXPIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_DRY_RUN_NOT_COMMIT_READY;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_DRY_RUN_NOT_FOUND;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_DUPLICATE_CODE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_PAYLOAD_CHANGED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_RESULT_HASH_MISMATCH;
import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_ACQUIRE_FAILED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_EXPIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_NOT_REPLAYABLE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.IDEMPOTENCY_KEY_REUSED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveCouponImportOperation;
import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import edu.courseflow.promotion.model.IncentiveOperationApproval;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportOperationRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CouponImportCommitService {

    private static final String OPERATION = "COUPON_IMPORT_COMMIT";
    private static final Duration IDEMPOTENCY_TTL = Duration.ofDays(7);

    private final CouponImportDryRunService dryRuns;
    private final CouponImportApprovalService importApprovals;
    private final IncentiveCouponImportBatchRepository importBatches;
    private final IncentiveCouponImportOperationRepository operations;
    private final IncentiveCouponRepository coupons;
    private final IncentiveIdempotencyKeyRepository idempotencyKeys;
    private final IncentiveAuditEventRepository auditEvents;
    private final CouponCodeFingerprintService couponFingerprints;
    private final CouponStorageCutoverGuard couponStorageCutoverGuard;
    private final AdminOperationRateGuard adminOperationRateGuard;
    private final IncentiveAccessService access;
    private final IncentiveMetrics metrics;
    private final ObjectMapper objectMapper;

    public CouponImportCommitService(CouponImportDryRunService dryRuns,
                                     CouponImportApprovalService importApprovals,
                                     IncentiveCouponImportBatchRepository importBatches,
                                     IncentiveCouponImportOperationRepository operations,
                                     IncentiveCouponRepository coupons,
                                     IncentiveIdempotencyKeyRepository idempotencyKeys,
                                     IncentiveAuditEventRepository auditEvents,
                                     CouponCodeFingerprintService couponFingerprints,
                                     CouponStorageCutoverGuard couponStorageCutoverGuard,
                                     AdminOperationRateGuard adminOperationRateGuard,
                                     IncentiveAccessService access,
                                     IncentiveMetrics metrics,
                                     ObjectMapper objectMapper) {
        this.dryRuns = dryRuns;
        this.importApprovals = importApprovals;
        this.importBatches = importBatches;
        this.operations = operations;
        this.coupons = coupons;
        this.idempotencyKeys = idempotencyKeys;
        this.auditEvents = auditEvents;
        this.couponFingerprints = couponFingerprints;
        this.couponStorageCutoverGuard = couponStorageCutoverGuard;
        this.adminOperationRateGuard = adminOperationRateGuard;
        this.access = access;
        this.metrics = metrics;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public CouponImportCommitResponseDto commit(CouponImportCommitRequestDto request,
                                                CurrentUser user,
                                                String correlationId) {
        long startedNanos = System.nanoTime();
        try {
            requireText(correlationId, "correlationId");
            requireCommitEnvelope(request);
            IncentiveOperationApproval approval = importApprovals.requireApprovedForCommit(request.approvalId(), user);
            CouponImportCommitRequestDto effectiveRequest = importApprovals.effectiveCommitRequest(request, approval);
            CouponImportCommitResponseDto response = commitInternal(
                    effectiveRequest,
                    approval,
                    user,
                    correlationId,
                    startedNanos);
            metrics.couponImportCommit(response.idempotencyReplay() ? "replay" : "success",
                    response.importedRows(),
                    elapsed(startedNanos));
            return response;
        } catch (ConflictException ex) {
            metrics.couponImportCommit("conflict", 0, elapsed(startedNanos));
            throw ex;
        } catch (RuntimeException ex) {
            metrics.couponImportCommit("error", 0, elapsed(startedNanos));
            throw ex;
        }
    }

    private CouponImportCommitResponseDto commitInternal(CouponImportCommitRequestDto request,
                                                        IncentiveOperationApproval approval,
                                                        CurrentUser user,
                                                        String correlationId,
                                                        long startedNanos) {
        requireRequest(request);
        IncentiveCouponImportBatch batch = importBatches.lockById(request.dryRunId())
                .orElseThrow(() -> NotFoundException.coded(
                        COUPON_IMPORT_DRY_RUN_NOT_FOUND,
                        "Coupon import dry-run not found: " + request.dryRunId()));
        if (!batch.getCampaignId().equals(request.campaignId())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import dry-run belongs to a different campaign");
        }
        access.requireCouponImportManageAccess(batch.getTenantId(), batch.getApplicationId(), user);
        access.requireActiveApplication(batch.getTenantId(), batch.getApplicationId(), user, "admin");
        String requestHash = commitRequestHash(request);
        if (batch.getCommittedAt() != null) {
            IdempotencySlot existing = replayExistingIdempotency(
                    batch.getTenantId(),
                    batch.getApplicationId(),
                    request.idempotencyKey().trim(),
                    requestHash);
            if (existing != null && existing.replay() != null) {
                return withReplay(existing.replay());
            }
            CouponImportCommitResponseDto durableReplay = replayCommittedOperation(
                    batch,
                    approval,
                    requestHash,
                    idempotencyKeyHash(request.idempotencyKey()),
                    existing == null ? null : existing.key());
            if (durableReplay != null) {
                return withReplay(durableReplay);
            }
            throw ConflictException.coded(
                    COUPON_IMPORT_ALREADY_COMMITTED,
                    "Coupon import dry-run has already been committed");
        }
        couponStorageCutoverGuard.requireCouponWriteAllowed(
                batch.getTenantId(),
                batch.getApplicationId(),
                batch.getCampaignId());
        adminOperationRateGuard.requireAllowed(
                "coupon_import_commit",
                batch.getTenantId(),
                batch.getApplicationId(),
                batch.getCampaignId(),
                user,
                access.sourceClientId(user),
                batch.getContentHash());
        if (batch.getExpiresAt() != null && !batch.getExpiresAt().isAfter(Instant.now())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_DRY_RUN_EXPIRED,
                    "Coupon import dry-run has expired");
        }
        requireCommitReady(batch);

        CouponImportDryRunService.DryRunEvaluation evaluation = dryRuns.evaluateForCommit(
                dryRuns.commitDryRunRequest(request),
                user);
        if (!evaluation.campaign().getId().equals(batch.getCampaignId())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_PAYLOAD_CHANGED,
                    "Coupon import payload campaign does not match dry-run");
        }
        if (!evaluation.resultHash().equals(batch.getResultHash())
                || !evaluation.resultHash().equals(request.approvedResultHash())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_RESULT_HASH_MISMATCH,
                    "Coupon import dry-run result hash no longer matches");
        }
        if (!evaluation.commitReady()) {
            throw ConflictException.coded(
                    COUPON_IMPORT_DRY_RUN_NOT_COMMIT_READY,
                    "Coupon import payload is no longer commit-ready");
        }
        IdempotencySlot idempotency = acquireIdempotency(
                batch.getTenantId(),
                batch.getApplicationId(),
                request.idempotencyKey().trim(),
                requestHash);
        if (idempotency.replay() != null) {
            return withReplay(idempotency.replay());
        }

        List<IncentiveCoupon> created = evaluation.rows().stream()
                .map(row -> new IncentiveCoupon(
                        batch.getCampaignId(),
                        row.codeMask(),
                        couponFingerprints.primaryFingerprint(row.normalizedCode()),
                        row.codeMask(),
                        row.holderProfileId(),
                        row.startsAt(),
                        row.expiresAt(),
                        row.maxRedemptions(),
                        row.maxRedemptionsPerProfile(),
                        toJson(row.metadata())))
                .toList();
        try {
            coupons.saveAll(created);
            coupons.flush();
        } catch (DataIntegrityViolationException ex) {
            throw ConflictException.coded(
                    COUPON_IMPORT_DUPLICATE_CODE,
                    "Coupon import contains codes that already exist for campaign");
        }

        Instant committedAt = Instant.now();
        UUID importId = UUID.randomUUID();
        CouponImportCommitResponseDto response = new CouponImportCommitResponseDto(
                importId,
                approval.getId(),
                batch.getId(),
                batch.getCampaignId(),
                IncentiveCouponImportOperation.STATUS_SUCCEEDED,
                evaluation.requestedRows(),
                created.size(),
                evaluation.resultHash(),
                false,
                committedAt,
                List.of());
        String actorId = actorId(user);
        String sourceClientId = access.sourceClientId(user);
        String idempotencyKeyHash = idempotencyKeyHash(request.idempotencyKey());
        operations.save(new IncentiveCouponImportOperation(
                importId,
                batch.getId(),
                approval.getId(),
                batch.getTenantId(),
                batch.getApplicationId(),
                batch.getCampaignId(),
                evaluation.resultHash(),
                requestHash,
                idempotencyKeyHash,
                response.requestedRows(),
                response.importedRows(),
                request.reason().trim(),
                request.changeTicket().trim(),
                toJson(response),
                actorId,
                correlationId,
                sourceClientId));
        batch.markCommitted(importId, response.importedRows(), actorId, committedAt);
        importBatches.save(batch);
        importApprovals.markCommitted(approval, actorId, committedAt, correlationId, sourceClientId);
        auditEvents.save(new IncentiveAuditEvent(
                batch.getTenantId(),
                batch.getApplicationId(),
                importId.toString(),
                "coupon-import",
                "coupon.import_committed",
                actorId,
                request.reason().trim(),
                toJson(Map.of(
                        "campaignId", batch.getCampaignId().toString(),
                        "approvalId", approval.getId().toString(),
                        "dryRunId", batch.getId().toString(),
                        "resultHash", response.resultHash(),
                        "requestedRows", response.requestedRows(),
                        "importedRows", response.importedRows(),
                        "reason", request.reason().trim(),
                        "idempotencyKeyHash", idempotencyKeyHash,
                        "changeTicket", request.changeTicket())),
                correlationId,
                sourceClientId));
        completeIdempotency(idempotency.key(), response);
        return response;
    }

    private void requireCommitEnvelope(CouponImportCommitRequestDto request) {
        if (request == null) {
            throw new BadRequestException("Coupon import commit request is required");
        }
        if (!request.confirm()) {
            throw new BadRequestException("confirm must be true");
        }
        if (request.approvalId() == null) {
            throw new BadRequestException("approvalId is required");
        }
        requireText(request.csvContent(), "file");
        requireText(request.idempotencyKey(), "idempotencyKey");
    }

    private void requireRequest(CouponImportCommitRequestDto request) {
        if (request.dryRunId() == null) {
            throw new BadRequestException("dryRunId is required");
        }
        if (request.campaignId() == null) {
            throw new BadRequestException("campaignId is required");
        }
        requireText(request.csvContent(), "file");
        requireText(request.approvedResultHash(), "approvedResultHash");
        requireText(request.idempotencyKey(), "idempotencyKey");
        requireText(request.reason(), "reason");
        requireText(request.changeTicket(), "changeTicket");
        if (request.idempotencyKey().trim().length() > 160) {
            throw new BadRequestException("idempotencyKey must be at most 160 characters");
        }
    }

    private void requireCommitReady(IncentiveCouponImportBatch batch) {
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

    private IdempotencySlot acquireIdempotency(String tenantId,
                                               String applicationId,
                                               String idempotencyKey,
                                               String requestHash) {
        Instant expiresAt = Instant.now().plus(IDEMPOTENCY_TTL);
        idempotencyKeys.insertInProgressIfAbsent(
                UUID.randomUUID(),
                tenantId,
                applicationId,
                OPERATION,
                idempotencyKey,
                requestHash,
                expiresAt);
        Optional<IncentiveIdempotencyKey> locked = idempotencyKeys.lockByScope(
                tenantId,
                applicationId,
                OPERATION,
                idempotencyKey);
        if (locked.isEmpty()) {
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_ACQUIRE_FAILED,
                    "Could not acquire idempotency key");
        }
        IncentiveIdempotencyKey key = locked.get();
        if (!key.getRequestHash().equals(requestHash)) {
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_REUSED,
                    "Idempotency key was reused with a different payload");
        }
        if (key.expired(Instant.now())) {
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_EXPIRED,
                    "Idempotency key has expired; use a new key");
        }
        if (key.succeeded()) {
            return new IdempotencySlot(key, readResponse(key.getResponseJson()));
        }
        if (!key.inProgress()) {
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_NOT_REPLAYABLE,
                    "Idempotency key is not replayable");
        }
        return new IdempotencySlot(key, null);
    }

    private IdempotencySlot replayExistingIdempotency(String tenantId,
                                                      String applicationId,
                                                      String idempotencyKey,
                                                      String requestHash) {
        Optional<IncentiveIdempotencyKey> locked = idempotencyKeys.lockByScope(
                tenantId,
                applicationId,
                OPERATION,
                idempotencyKey);
        if (locked.isEmpty()) {
            return null;
        }
        IncentiveIdempotencyKey key = locked.get();
        if (!key.getRequestHash().equals(requestHash)) {
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_REUSED,
                    "Idempotency key was reused with a different payload");
        }
        if (key.expired(Instant.now())) {
            throw ConflictException.coded(
                    IDEMPOTENCY_KEY_EXPIRED,
                    "Idempotency key has expired; use a new key");
        }
        if (key.succeeded()) {
            return new IdempotencySlot(key, readResponse(key.getResponseJson()));
        }
        if (key.inProgress()) {
            return new IdempotencySlot(key, null);
        }
        throw ConflictException.coded(
                IDEMPOTENCY_KEY_NOT_REPLAYABLE,
                "Idempotency key is not replayable");
    }

    private void completeIdempotency(IncentiveIdempotencyKey key, CouponImportCommitResponseDto response) {
        key.complete(toJson(response), Instant.now().plus(IDEMPOTENCY_TTL));
        idempotencyKeys.save(key);
    }

    private CouponImportCommitResponseDto replayCommittedOperation(IncentiveCouponImportBatch batch,
                                                                   IncentiveOperationApproval approval,
                                                                   String requestHash,
                                                                   String idempotencyKeyHash,
                                                                   IncentiveIdempotencyKey idempotencyKey) {
        Optional<IncentiveCouponImportOperation> existing = batch.getCommittedOperationId() == null
                ? Optional.empty()
                : operations.findById(batch.getCommittedOperationId());
        if (existing.isEmpty()) {
            existing = operations.findByDryRunId(batch.getId());
        }
        if (existing.isEmpty()) {
            return null;
        }
        IncentiveCouponImportOperation operation = existing.get();
        if (approval != null
                && operation.getApprovalId() != null
                && !operation.getApprovalId().equals(approval.getId())) {
            throw ConflictException.coded(
                    COUPON_IMPORT_ALREADY_COMMITTED,
                    "Coupon import dry-run has already been committed");
        }
        if (!operation.getRequestHash().equals(requestHash)
                || !operation.getIdempotencyKeyHash().equals(idempotencyKeyHash)) {
            throw ConflictException.coded(
                    COUPON_IMPORT_ALREADY_COMMITTED,
                    "Coupon import dry-run has already been committed");
        }
        CouponImportCommitResponseDto response = readResponse(operation.getResponseJson());
        if (idempotencyKey != null && idempotencyKey.inProgress()) {
            completeIdempotency(idempotencyKey, response);
        }
        return response;
    }

    private CouponImportCommitResponseDto readResponse(String json) {
        try {
            return objectMapper.readValue(json, CouponImportCommitResponseDto.class);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to deserialize coupon import commit response", ex);
        }
    }

    private CouponImportCommitResponseDto withReplay(CouponImportCommitResponseDto response) {
        return new CouponImportCommitResponseDto(
                response.importId(),
                response.approvalId(),
                response.dryRunId(),
                response.campaignId(),
                response.status(),
                response.requestedRows(),
                response.importedRows(),
                response.resultHash(),
                true,
                response.committedAt(),
                response.warnings());
    }

    private String commitRequestHash(CouponImportCommitRequestDto request) {
        Map<String, Object> identity = new LinkedHashMap<>();
        identity.put("approvalId", request.approvalId() == null ? null : request.approvalId().toString());
        identity.put("dryRunId", request.dryRunId().toString());
        identity.put("campaignId", request.campaignId().toString());
        identity.put("approvedResultHash", request.approvedResultHash());
        identity.put("csvContent", request.csvContent() == null ? "" : request.csvContent());
        identity.put("maxRows", request.maxRows());
        identity.put("holderProfileId", request.holderProfileId());
        identity.put("startsAt", request.startsAt() == null ? null : request.startsAt().toString());
        identity.put("expiresAt", request.expiresAt() == null ? null : request.expiresAt().toString());
        identity.put("maxRedemptions", request.maxRedemptions());
        identity.put("maxRedemptionsPerProfile", request.maxRedemptionsPerProfile());
        identity.put("metadata", request.metadata() == null ? Map.of() : request.metadata());
        identity.put("reason", request.reason());
        identity.put("changeTicket", request.changeTicket());
        identity.put("confirm", request.confirm());
        return couponFingerprints.integrityHash("coupon-import-commit", toJson(identity));
    }

    private String idempotencyKeyHash(String idempotencyKey) {
        return couponFingerprints.integrityHash("coupon-import-idempotency-key", idempotencyKey);
    }

    private String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new BadRequestException(field + " is required");
        }
        return value.trim();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize coupon import commit", ex);
        }
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }

    private Duration elapsed(long startedNanos) {
        return Duration.ofNanos(System.nanoTime() - startedNanos);
    }

    private record IdempotencySlot(IncentiveIdempotencyKey key, CouponImportCommitResponseDto replay) {
    }
}
