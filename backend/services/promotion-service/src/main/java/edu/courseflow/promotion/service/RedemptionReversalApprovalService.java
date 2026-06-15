package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_ALREADY_EXISTS;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_EXPIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_NOT_APPROVED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_NOT_FOUND;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_NOT_PENDING;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_PAYLOAD_CHANGED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_REQUIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_APPROVAL_SUBJECT_CHANGED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_OPERATOR_REQUIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_SELF_APPROVAL_BLOCKED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.REDEMPTION_REVERSAL_SELF_EXECUTION_BLOCKED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RedemptionReversalApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RedemptionReversalApprovalRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RedemptionReversalApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveOperationApproval;
import edu.courseflow.promotion.model.IncentiveRedemption;
import edu.courseflow.promotion.model.IncentiveReservation;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveOperationApprovalRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
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
public class RedemptionReversalApprovalService {

    private static final int MAX_QUEUE_LIMIT = 200;
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final IncentiveRedemptionRepository redemptions;
    private final IncentiveReservationRepository reservations;
    private final IncentiveOperationApprovalRepository approvals;
    private final IncentiveAuditEventRepository auditEvents;
    private final AdminOperationRateGuard adminOperationRateGuard;
    private final IncentiveAccessService access;
    private final ObjectMapper objectMapper;
    private final Duration approvalTtl;

    public RedemptionReversalApprovalService(
            IncentiveRedemptionRepository redemptions,
            IncentiveReservationRepository reservations,
            IncentiveOperationApprovalRepository approvals,
            IncentiveAuditEventRepository auditEvents,
            AdminOperationRateGuard adminOperationRateGuard,
            IncentiveAccessService access,
            ObjectMapper objectMapper,
            @Value("${courseflow.promotion.redemption-reversal.approval-ttl-minutes:60}")
            long approvalTtlMinutes) {
        this.redemptions = redemptions;
        this.reservations = reservations;
        this.approvals = approvals;
        this.auditEvents = auditEvents;
        this.adminOperationRateGuard = adminOperationRateGuard;
        this.access = access;
        this.objectMapper = objectMapper;
        this.approvalTtl = Duration.ofMinutes(Math.max(1, approvalTtlMinutes));
    }

    @Transactional
    public RedemptionReversalApprovalResponseDto requestApproval(UUID redemptionId,
                                                                  RedemptionReversalApprovalRequestDto request,
                                                                  CurrentUser user,
                                                                  String correlationId) {
        requireOperatorActor(user);
        if (redemptionId == null) {
            throw new BadRequestException("redemptionId is required");
        }
        if (request == null) {
            throw new BadRequestException("Redemption reversal approval request is required");
        }
        requireText(correlationId, "correlationId");
        String idempotencyKey = requireText(request.idempotencyKey(), "idempotencyKey");
        String reason = requireText(request.reason(), "reason");
        String changeTicket = requireText(request.changeTicket(), "changeTicket");
        IncentiveRedemption redemption = redemptions.lockById(redemptionId)
                .orElseThrow(() -> new NotFoundException("Redemption not found: " + redemptionId));
        requireAdmin(redemption, user);
        requireReversible(redemption);
        IncentiveReservation reservation = reservation(redemption);
        String sourceClientId = access.sourceClientId(user);
        String requestHash = requestHash(redemption.getId(), idempotencyKey, reason, changeTicket);
        String resultHash = resultHash(redemption);
        String subjectJson = subjectJson(redemption, reservation, idempotencyKey, requestHash, resultHash, changeTicket,
                request.metadata());
        String subjectHash = subjectHash(subjectJson);
        adminOperationRateGuard.requireAllowed(
                "redemption_reversal_approval_request",
                redemption.getTenantId(),
                redemption.getApplicationId(),
                redemption.getCampaignId(),
                user,
                sourceClientId,
                subjectHash);
        approvals.findActiveForSubject(
                        IncentiveOperationApproval.OPERATION_REDEMPTION_REVERSE,
                        IncentiveOperationApproval.TARGET_REDEMPTION,
                        redemption.getId(),
                        subjectHash)
                .ifPresent(existing -> {
                    throw ConflictException.coded(
                            REDEMPTION_REVERSAL_APPROVAL_ALREADY_EXISTS,
                            "An active redemption reversal approval already exists for this redemption");
                });
        String actorId = actorId(user);
        Instant now = Instant.now();
        IncentiveOperationApproval approval = new IncentiveOperationApproval(
                IncentiveOperationApproval.OPERATION_REDEMPTION_REVERSE,
                IncentiveOperationApproval.TARGET_REDEMPTION,
                redemption.getId(),
                redemption.getTenantId(),
                redemption.getApplicationId(),
                redemption.getCampaignId(),
                redemption.getTenantId() + "/" + redemption.getApplicationId() + "/redemption/"
                        + redemption.getId(),
                requestHash,
                resultHash,
                subjectHash,
                1,
                1,
                0,
                0,
                0,
                true,
                true,
                subjectJson,
                reason,
                changeTicket,
                actorId,
                correlationId,
                sourceClientId,
                now.plus(approvalTtl));
        approvals.save(approval);
        auditApproval("redemption.reversal_approval_requested", approval, actorId, reason, correlationId,
                sourceClientId);
        return approvalDto(approval);
    }

    @Transactional(readOnly = true)
    public RedemptionReversalApprovalResponseDto approval(UUID approvalId, CurrentUser user) {
        requireOperatorActor(user);
        IncentiveOperationApproval approval = approvals.findById(approvalId)
                .orElseThrow(() -> BadRequestException.coded(
                        REDEMPTION_REVERSAL_APPROVAL_NOT_FOUND,
                        "Redemption reversal approval not found"));
        requireOperation(approval);
        requireRead(approval, user);
        return approvalDto(approval);
    }

    @Transactional(readOnly = true)
    public List<RedemptionReversalApprovalResponseDto> queue(String tenantId,
                                                             String applicationId,
                                                             UUID campaignId,
                                                             String status,
                                                             Integer limit,
                                                             CurrentUser user) {
        requireOperatorActor(user);
        String tenant = requireText(tenantId, "tenantId");
        String application = requireText(applicationId, "applicationId");
        access.requireReviewAccess(tenant, application, user);
        String normalizedStatus = blankToNull(status);
        if (normalizedStatus != null && !List.of(
                IncentiveOperationApproval.STATUS_PENDING,
                IncentiveOperationApproval.STATUS_APPROVED,
                IncentiveOperationApproval.STATUS_REJECTED,
                IncentiveOperationApproval.STATUS_EXECUTED).contains(normalizedStatus)) {
            throw new BadRequestException("Unsupported redemption reversal approval status: " + status);
        }
        int pageSize = Math.min(MAX_QUEUE_LIMIT, Math.max(1, limit == null ? 50 : limit));
        return approvals.search(
                        IncentiveOperationApproval.OPERATION_REDEMPTION_REVERSE,
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
    public RedemptionReversalApprovalResponseDto approve(UUID approvalId,
                                                         RedemptionReversalApprovalDecisionRequestDto request,
                                                         CurrentUser user,
                                                         String correlationId) {
        requireOperatorActor(user);
        requireText(correlationId, "correlationId");
        IncentiveOperationApproval approval = lockApproval(approvalId);
        requireReview(approval, user);
        String sourceClientId = access.sourceClientId(user);
        adminOperationRateGuard.requireAllowed(
                "redemption_reversal_approval_decision",
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getCampaignId(),
                user,
                sourceClientId,
                approval.getSubjectHash());
        String actorId = actorId(user);
        if (actorId.equals(approval.getRequestedBy())) {
            throw ForbiddenException.coded(
                    REDEMPTION_REVERSAL_SELF_APPROVAL_BLOCKED,
                    "Redemption reversal approval must be reviewed by a different operator");
        }
        if (!approval.pending()) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_NOT_PENDING,
                    "Redemption reversal approval is not pending");
        }
        if (approval.expired(Instant.now())) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_EXPIRED,
                    "Redemption reversal approval is expired");
        }
        validateSubjectStillMatches(approval);
        approval.approve(actorId, request == null ? null : request.note(), Instant.now());
        auditApproval("redemption.reversal_approval_approved", approval, actorId,
                request == null ? null : request.note(), correlationId, sourceClientId);
        return approvalDto(approval);
    }

    @Transactional
    public RedemptionReversalApprovalResponseDto reject(UUID approvalId,
                                                        RedemptionReversalApprovalDecisionRequestDto request,
                                                        CurrentUser user,
                                                        String correlationId) {
        requireOperatorActor(user);
        requireText(correlationId, "correlationId");
        String note = request == null ? null : requireText(request.note(), "note");
        IncentiveOperationApproval approval = lockApproval(approvalId);
        requireReview(approval, user);
        String sourceClientId = access.sourceClientId(user);
        adminOperationRateGuard.requireAllowed(
                "redemption_reversal_approval_decision",
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getCampaignId(),
                user,
                sourceClientId,
                approval.getSubjectHash());
        String actorId = actorId(user);
        if (actorId.equals(approval.getRequestedBy())) {
            throw ForbiddenException.coded(
                    REDEMPTION_REVERSAL_SELF_APPROVAL_BLOCKED,
                    "Redemption reversal approval must be rejected by a different operator");
        }
        if (!approval.pending()) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_NOT_PENDING,
                    "Redemption reversal approval is not pending");
        }
        approval.reject(actorId, note, Instant.now());
        auditApproval("redemption.reversal_approval_rejected", approval, actorId, note, correlationId, sourceClientId);
        return approvalDto(approval);
    }

    @Transactional
    public IncentiveOperationApproval requireApprovedForReverse(IncentiveRedemption redemption,
                                                                ReverseRedemptionRequestDto request,
                                                                CurrentUser user) {
        requireOperatorActor(user);
        if (request == null || request.approvalId() == null) {
            throw BadRequestException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_REQUIRED,
                    "approvalId is required for operator redemption reversal");
        }
        IncentiveOperationApproval approval = lockApproval(request.approvalId());
        requireAdmin(approval, user);
        if (!approval.getTargetId().equals(redemption.getId())
                || !Objects.equals(approval.getTenantId(), redemption.getTenantId())
                || !Objects.equals(approval.getApplicationId(), redemption.getApplicationId())
                || !Objects.equals(approval.getCampaignId(), redemption.getCampaignId())) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_PAYLOAD_CHANGED,
                    "Redemption reversal approval belongs to a different redemption scope");
        }
        String reason = requireText(request.reason(), "reason");
        String changeTicket = effectiveChangeTicket(request, approval);
        String requestHash = requestHash(redemption.getId(),
                requireText(request.idempotencyKey(), "idempotencyKey"), reason, changeTicket);
        if (!Objects.equals(approval.getRequestHash(), requestHash)) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_PAYLOAD_CHANGED,
                    "Redemption reversal request does not match the approved payload");
        }
        if (approval.executed()) {
            return approval;
        }
        if (!approval.approved()) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_NOT_APPROVED,
                    "Redemption reversal approval is not approved");
        }
        String actorId = actorId(user);
        if (actorId.equals(approval.getApprovedBy())) {
            throw ForbiddenException.coded(
                    REDEMPTION_REVERSAL_SELF_EXECUTION_BLOCKED,
                    "Redemption reversal must be executed by a different operator from approver");
        }
        if (approval.expired(Instant.now())) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_EXPIRED,
                    "Redemption reversal approval is expired");
        }
        validateSubjectStillMatches(approval, redemption);
        return approval;
    }

    @Transactional
    public void markExecuted(IncentiveOperationApproval approval,
                             String actorId,
                             Instant executedAt,
                             String correlationId,
                             String sourceClientId) {
        if (approval == null || approval.executed()) {
            return;
        }
        approval.markExecuted(actorId, executedAt);
        auditApproval("redemption.reversal_approval_executed", approval, actorId, approval.getReason(),
                correlationId, sourceClientId);
    }

    public RedemptionReversalApprovalResponseDto approvalDto(IncentiveOperationApproval approval) {
        Map<String, Object> subject = readSubject(approval.getSubjectJson());
        return new RedemptionReversalApprovalResponseDto(
                approval.getId(),
                approval.getStatus(),
                approval.getTargetId(),
                uuidValue(subject.get("reservationId")),
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getCampaignId(),
                integerValue(subject.get("campaignVersion")),
                uuidValue(subject.get("couponId")),
                stringValue(subject.get("profileId")),
                stringValue(subject.get("externalReference")),
                stringValue(subject.get("idempotencyKey")),
                approval.getRequestHash(),
                approval.getResultHash(),
                approval.getSubjectHash(),
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
                approval.getExecutedAt(),
                subject);
    }

    private IncentiveOperationApproval lockApproval(UUID approvalId) {
        return approvals.lockById(approvalId)
                .map(approval -> {
                    requireOperation(approval);
                    return approval;
                })
                .orElseThrow(() -> BadRequestException.coded(
                        REDEMPTION_REVERSAL_APPROVAL_NOT_FOUND,
                        "Redemption reversal approval not found"));
    }

    private void requireOperation(IncentiveOperationApproval approval) {
        if (!IncentiveOperationApproval.OPERATION_REDEMPTION_REVERSE.equals(approval.getOperationType())
                || !IncentiveOperationApproval.TARGET_REDEMPTION.equals(approval.getTargetType())) {
            throw BadRequestException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_NOT_FOUND,
                    "Redemption reversal approval not found");
        }
    }

    private void validateSubjectStillMatches(IncentiveOperationApproval approval) {
        IncentiveRedemption redemption = redemptions.lockById(approval.getTargetId())
                .orElseThrow(() -> ConflictException.coded(
                        REDEMPTION_REVERSAL_APPROVAL_SUBJECT_CHANGED,
                        "Redemption reversal approval target is no longer available"));
        validateSubjectStillMatches(approval, redemption);
    }

    private void validateSubjectStillMatches(IncentiveOperationApproval approval, IncentiveRedemption redemption) {
        requireReversible(redemption);
        IncentiveReservation reservation = reservation(redemption);
        Map<String, Object> originalSubject = readSubject(approval.getSubjectJson());
        String subjectJson = subjectJson(redemption, reservation, stringValue(originalSubject.get("idempotencyKey")),
                approval.getRequestHash(), approval.getResultHash(), approval.getChangeTicket(),
                originalSubject.get("metadata"));
        if (!Objects.equals(approval.getSubjectHash(), subjectHash(subjectJson))) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_SUBJECT_CHANGED,
                    "Redemption reversal approval no longer matches the current redemption");
        }
    }

    private void requireReversible(IncentiveRedemption redemption) {
        if (!"REDEEMED".equals(redemption.getStatus())) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_SUBJECT_CHANGED,
                    "Only redeemed incentives can be reversed through approval");
        }
    }

    private IncentiveReservation reservation(IncentiveRedemption redemption) {
        if (redemption.getReservationId() == null) {
            throw ConflictException.coded(
                    REDEMPTION_REVERSAL_APPROVAL_SUBJECT_CHANGED,
                    "Redemption is missing its reservation");
        }
        return reservations.lockById(redemption.getReservationId())
                .orElseThrow(() -> ConflictException.coded(
                        REDEMPTION_REVERSAL_APPROVAL_SUBJECT_CHANGED,
                        "Redemption is missing its reservation: " + redemption.getReservationId()));
    }

    private String requestHash(UUID redemptionId, String idempotencyKey, String reason, String changeTicket) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("redemptionId", redemptionId.toString());
        payload.put("idempotencyKey", idempotencyKey);
        payload.put("reason", reason);
        payload.put("changeTicket", changeTicket);
        return hash(payload);
    }

    private String resultHash(IncentiveRedemption redemption) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("redemptionId", redemption.getId().toString());
        payload.put("reservationId", Objects.toString(redemption.getReservationId(), null));
        payload.put("redemptionRequestHash", redemption.getRequestHash());
        payload.put("effectsHash", hash(redemption.getEffectsJson()));
        payload.put("quotaPolicy", "NO_RELEASE_ON_COMMITTED_REVERSAL");
        return hash(payload);
    }

    private String subjectJson(IncentiveRedemption redemption,
                               IncentiveReservation reservation,
                               String idempotencyKey,
                               String requestHash,
                               String resultHash,
                               String changeTicket,
                               Object metadata) {
        Map<String, Object> subject = new LinkedHashMap<>();
        subject.put("redemptionId", redemption.getId().toString());
        subject.put("reservationId", redemption.getReservationId().toString());
        subject.put("tenantId", redemption.getTenantId());
        subject.put("applicationId", redemption.getApplicationId());
        subject.put("campaignId", redemption.getCampaignId().toString());
        subject.put("campaignVersion", redemption.getCampaignVersion());
        subject.put("couponId", redemption.getCouponId() == null ? null : redemption.getCouponId().toString());
        subject.put("profileId", redemption.getProfileId());
        subject.put("externalReference", redemption.getExternalReference());
        subject.put("idempotencyKey", idempotencyKey);
        subject.put("currentStatus", redemption.getStatus());
        subject.put("reservationStatus", reservation.getStatus());
        subject.put("redemptionRequestHash", redemption.getRequestHash());
        subject.put("effectsHash", hash(redemption.getEffectsJson()));
        subject.put("requestHash", requestHash);
        subject.put("resultHash", resultHash);
        subject.put("changeTicket", changeTicket);
        subject.put("quotaPolicy", "NO_RELEASE_ON_COMMITTED_REVERSAL");
        subject.put("quotaReleased", false);
        if (metadata != null) {
            subject.put("metadata", metadata);
        }
        return toJson(subject);
    }

    private String subjectHash(String subjectJson) {
        return hash(subjectJson);
    }

    private void requireAdmin(IncentiveRedemption redemption, CurrentUser user) {
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        access.requireKnownApplication(redemption.getTenantId(), redemption.getApplicationId(), user, "reverse");
    }

    private void requireAdmin(IncentiveOperationApproval approval, CurrentUser user) {
        access.requireAdminAccess(approval.getTenantId(), approval.getApplicationId(), user);
        access.requireKnownApplication(approval.getTenantId(), approval.getApplicationId(), user, "reverse");
    }

    private void requireReview(IncentiveOperationApproval approval, CurrentUser user) {
        access.requireReviewAccess(approval.getTenantId(), approval.getApplicationId(), user);
    }

    private void requireRead(IncentiveOperationApproval approval, CurrentUser user) {
        access.requireReviewAccess(approval.getTenantId(), approval.getApplicationId(), user);
    }

    private void requireOperatorActor(CurrentUser user) {
        if (user == null) {
            throw ForbiddenException.coded(
                    REDEMPTION_REVERSAL_OPERATOR_REQUIRED,
                    "Redemption reversal approval requires an authenticated operator");
        }
        if ("service".equalsIgnoreCase(access.actorType(user))) {
            throw ForbiddenException.coded(
                    REDEMPTION_REVERSAL_OPERATOR_REQUIRED,
                    "Redemption reversal approval is not available to runtime service actors");
        }
    }

    private String effectiveChangeTicket(ReverseRedemptionRequestDto request, IncentiveOperationApproval approval) {
        String value = blankToNull(request.changeTicket());
        if (value != null) {
            return value;
        }
        return approval.getChangeTicket();
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
        payload.put("redemptionId", approval.getTargetId().toString());
        payload.put("campaignId", approval.getCampaignId() == null ? null : approval.getCampaignId().toString());
        payload.put("requestHash", approval.getRequestHash());
        payload.put("resultHash", approval.getResultHash());
        payload.put("subjectHash", approval.getSubjectHash());
        payload.put("reason", approval.getReason());
        payload.put("changeTicket", approval.getChangeTicket());
        auditEvents.save(new IncentiveAuditEvent(
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getId().toString(),
                "redemption-reversal-approval",
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

    private Map<String, Object> readSubject(String subjectJson) {
        try {
            Map<String, Object> value = objectMapper.readValue(subjectJson, MAP_TYPE);
            return value == null ? Map.of() : value;
        } catch (JsonProcessingException ex) {
            return Map.of();
        }
    }

    private Integer integerValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Integer.parseInt(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    private UUID uuidValue(Object value) {
        String text = stringValue(value);
        if (text == null || text.isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(text);
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private String stringValue(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize redemption reversal approval", ex);
        }
    }

    private String hash(Object value) {
        try {
            byte[] bytes;
            if (value instanceof String text) {
                bytes = text.getBytes(StandardCharsets.UTF_8);
            } else {
                bytes = objectMapper.writer()
                        .with(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS)
                        .writeValueAsBytes(value);
            }
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(bytes));
        } catch (JsonProcessingException | NoSuchAlgorithmException ex) {
            throw new IllegalStateException("Unable to hash redemption reversal approval", ex);
        }
    }
}
