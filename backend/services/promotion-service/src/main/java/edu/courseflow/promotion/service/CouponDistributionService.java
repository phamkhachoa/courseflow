package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionActionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionPreviewRecipientDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionPreviewResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionRecipientDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionRecipientInputDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCouponDistributionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.PreviewCouponDistributionRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveCouponDistribution;
import edu.courseflow.promotion.model.IncentiveCouponDistributionRecipient;
import edu.courseflow.promotion.model.OutboxEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCouponDistributionRecipientRepository;
import edu.courseflow.promotion.repository.IncentiveCouponDistributionRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CouponDistributionService {

    private static final Set<String> SOURCE_TYPES = Set.of("COHORT", "SECTION", "COURSE", "SEGMENT", "MANUAL");
    private static final String COUPON_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final IncentiveCampaignRepository campaigns;
    private final IncentiveCouponRepository coupons;
    private final IncentiveCouponDistributionRepository distributions;
    private final IncentiveCouponDistributionRecipientRepository recipients;
    private final IncentiveAuditEventRepository auditEvents;
    private final OutboxEventRepository outboxEvents;
    private final IncentiveAccessService access;
    private final CouponCodeFingerprintService couponFingerprints;
    private final CouponStorageCutoverGuard couponStorageCutoverGuard;
    private final AdminOperationRateGuard adminOperationRateGuard;
    private final ObjectMapper objectMapper;
    private final SecureRandom secureRandom = new SecureRandom();

    public CouponDistributionService(IncentiveCampaignRepository campaigns,
                                     IncentiveCouponRepository coupons,
                                     IncentiveCouponDistributionRepository distributions,
                                     IncentiveCouponDistributionRecipientRepository recipients,
                                     IncentiveAuditEventRepository auditEvents,
                                     OutboxEventRepository outboxEvents,
                                     IncentiveAccessService access,
                                     CouponCodeFingerprintService couponFingerprints,
                                     CouponStorageCutoverGuard couponStorageCutoverGuard,
                                     AdminOperationRateGuard adminOperationRateGuard,
                                     ObjectMapper objectMapper) {
        this.campaigns = campaigns;
        this.coupons = coupons;
        this.distributions = distributions;
        this.recipients = recipients;
        this.auditEvents = auditEvents;
        this.outboxEvents = outboxEvents;
        this.access = access;
        this.couponFingerprints = couponFingerprints;
        this.couponStorageCutoverGuard = couponStorageCutoverGuard;
        this.adminOperationRateGuard = adminOperationRateGuard;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public CouponDistributionPreviewResponseDto preview(PreviewCouponDistributionRequestDto request,
                                                        CurrentUser user,
                                                        String correlationId) {
        IncentiveCampaign campaign = campaign(request.campaignId());
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireActiveApplication(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        CouponValidationSupport.validateWindowAndLimits(
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile());
        String sourceType = normalizeSourceType(request.sourceType());
        List<RecipientDraft> drafts = recipientDrafts(request.recipients());
        String previewHash = previewHash(
                campaign.getId(),
                sourceType,
                blankToNull(request.sourceReference()),
                Boolean.TRUE.equals(request.notifyLearners()),
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                request.metadata(),
                drafts);
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        audit(campaign.getTenantId(), campaign.getApplicationId(), campaign.getId().toString(),
                "coupon-distribution-preview", "coupon.distribution_previewed", actorId(user), null, Map.of(
                        "campaignId", campaign.getId().toString(),
                        "sourceType", sourceType,
                        "sourceReference", blankToNull(request.sourceReference()) == null
                                ? ""
                                : blankToNull(request.sourceReference()),
                        "requestedRecipients", request.recipients().size(),
                        "uniqueRecipients", drafts.size(),
                        "duplicateRecipients", request.recipients().size() - drafts.size(),
                        "previewHash", previewHash), auditMetadata);
        return new CouponDistributionPreviewResponseDto(
                campaign.getId(),
                sourceType,
                blankToNull(request.sourceReference()),
                Boolean.TRUE.equals(request.notifyLearners()),
                request.recipients().size(),
                drafts.size(),
                request.recipients().size() - drafts.size(),
                previewHash,
                previewSample(request.recipients()));
    }

    @Transactional
    public CouponDistributionDto create(CreateCouponDistributionRequestDto request,
                                        CurrentUser user,
                                        String correlationId) {
        IncentiveCampaign campaign = campaign(request.campaignId());
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireActiveApplication(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        CouponValidationSupport.validateWindowAndLimits(
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile());
        String sourceType = normalizeSourceType(request.sourceType());
        String name = requireText(request.name(), "distribution name");
        List<RecipientDraft> drafts = recipientDrafts(request.recipients());
        String expectedHash = previewHash(
                campaign.getId(),
                sourceType,
                blankToNull(request.sourceReference()),
                Boolean.TRUE.equals(request.notifyLearners()),
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                request.metadata(),
                drafts);
        if (!expectedHash.equals(blankToNull(request.previewHash()))) {
            throw new ConflictException("Coupon distribution preview hash does not match current recipients");
        }
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        IncentiveCouponDistribution distribution = distributions.save(new IncentiveCouponDistribution(
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                name,
                sourceType,
                blankToNull(request.sourceReference()),
                Boolean.TRUE.equals(request.notifyLearners()),
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                drafts.size(),
                expectedHash,
                blankToNull(request.reason()),
                toJson(request.metadata() == null ? Map.of() : request.metadata()),
                actorId(user)));
        List<IncentiveCouponDistributionRecipient> savedRecipients = drafts.stream()
                .map(draft -> new IncentiveCouponDistributionRecipient(
                        distribution.getId(),
                        distribution.getTenantId(),
                        distribution.getApplicationId(),
                        distribution.getCampaignId(),
                        draft.profileId(),
                        toJson(draft.metadata())))
                .toList();
        recipients.saveAll(savedRecipients);
        audit(distribution.getTenantId(), distribution.getApplicationId(), distribution.getId().toString(),
                "coupon-distribution", "coupon.distribution_created", actorId(user), request.reason(), Map.of(
                        "campaignId", campaign.getId().toString(),
                        "sourceType", distribution.getSourceType(),
                        "sourceReference", distribution.getSourceReference() == null
                                ? ""
                                : distribution.getSourceReference(),
                        "recipientCount", distribution.getRecipientCount(),
                        "notifyLearners", distribution.isNotifyLearners(),
                        "previewHash", distribution.getPreviewHash()), auditMetadata);
        return distributionDto(distribution, savedRecipients);
    }

    @Transactional(readOnly = true)
    public CouponDistributionQueryResponseDto list(Optional<String> tenantId,
                                                   Optional<String> applicationId,
                                                   Optional<UUID> campaignId,
                                                   Optional<String> status,
                                                   Optional<Integer> limit,
                                                   CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        UUID campaignFilter = campaignId.orElse(null);
        if (tenant != null && application != null) {
            access.requireReviewAccess(tenant, application, user);
        } else if (campaignFilter != null) {
            IncentiveCampaign campaign = campaign(campaignFilter);
            access.requireReviewAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        } else {
            access.requirePlatformAdmin(user);
        }
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 200));
        List<CouponDistributionDto> items = distributions.search(
                        tenant,
                        application,
                        campaignFilter,
                        normalizeStatusOrNull(status.orElse(null)),
                        PageRequest.of(0, pageSize))
                .stream()
                .map(distribution -> distributionDto(distribution, List.of()))
                .toList();
        return new CouponDistributionQueryResponseDto(items, pageSize);
    }

    @Transactional(readOnly = true)
    public CouponDistributionDto get(UUID distributionId, CurrentUser user) {
        IncentiveCouponDistribution distribution = distribution(distributionId);
        access.requireReviewAccess(distribution.getTenantId(), distribution.getApplicationId(), user);
        return distributionDto(distribution, recipients.findByDistributionIdOrderByCreatedAtAsc(distributionId));
    }

    @Transactional
    public CouponDistributionDto approve(UUID distributionId,
                                         CouponDistributionActionRequestDto request,
                                         CurrentUser user,
                                         String correlationId) {
        IncentiveCouponDistribution distribution = lockDistribution(distributionId);
        access.requireAdminAccess(distribution.getTenantId(), distribution.getApplicationId(), user);
        access.requireClientOperation(distribution.getTenantId(), distribution.getApplicationId(), user, "admin");
        if ("APPROVED".equals(distribution.getStatus()) || "ISSUED".equals(distribution.getStatus())) {
            return distributionDto(distribution, recipients.findByDistributionIdOrderByCreatedAtAsc(distributionId));
        }
        try {
            distribution.approve(actorId(user));
        } catch (IllegalStateException ex) {
            throw new ConflictException(ex.getMessage());
        }
        IncentiveCouponDistribution saved = distributions.save(distribution);
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "coupon-distribution",
                "coupon.distribution_approved", actorId(user), request == null ? null : request.reason(), Map.of(
                        "campaignId", saved.getCampaignId().toString(),
                        "recipientCount", saved.getRecipientCount()), auditMetadata);
        return distributionDto(saved, recipients.findByDistributionIdOrderByCreatedAtAsc(distributionId));
    }

    @Transactional
    public CouponDistributionDto issue(UUID distributionId,
                                       CouponDistributionActionRequestDto request,
                                       CurrentUser user,
                                       String correlationId) {
        IncentiveCouponDistribution distribution = lockDistribution(distributionId);
        access.requireAdminAccess(distribution.getTenantId(), distribution.getApplicationId(), user);
        access.requireActiveApplication(distribution.getTenantId(), distribution.getApplicationId(), user, "admin");
        if ("ISSUED".equals(distribution.getStatus())) {
            return distributionDto(distribution, recipients.findByDistributionIdOrderByCreatedAtAsc(distributionId));
        }
        if (!"APPROVED".equals(distribution.getStatus())) {
            throw new ConflictException("Coupon distribution must be approved before issue");
        }
        couponStorageCutoverGuard.requireCouponWriteAllowed(
                distribution.getTenantId(),
                distribution.getApplicationId(),
                distribution.getCampaignId());
        adminOperationRateGuard.requireAllowed(
                "coupon_distribution_issue",
                distribution.getTenantId(),
                distribution.getApplicationId(),
                distribution.getCampaignId(),
                user,
                access.sourceClientId(user),
                distribution.getPreviewHash());
        List<IncentiveCouponDistributionRecipient> rows =
                recipients.findByDistributionIdOrderByCreatedAtAsc(distributionId);
        List<IncentiveCouponDistributionRecipient> changed = new ArrayList<>();
        List<IncentiveCoupon> createdCoupons = new ArrayList<>();
        for (IncentiveCouponDistributionRecipient recipient : rows) {
            if (!"PENDING".equals(recipient.getStatus())) {
                continue;
            }
            CouponCodeDraft code = uniqueCouponCode(distribution.getCampaignId());
            IncentiveCoupon coupon = coupons.save(new IncentiveCoupon(
                    distribution.getCampaignId(),
                    code.codeMask(),
                    couponFingerprints.primaryFingerprint(code.normalizedCode()),
                    code.codeMask(),
                    recipient.getProfileId(),
                    distribution.getStartsAt(),
                    distribution.getExpiresAt(),
                    distribution.getMaxRedemptions(),
                    distribution.getMaxRedemptionsPerProfile(),
                    toJson(couponMetadata(distribution, recipient))));
            recipient.issue(coupon.getId(), distribution.isNotifyLearners());
            changed.add(recipient);
            createdCoupons.add(coupon);
            if (distribution.isNotifyLearners()) {
                outboxEvents.save(new OutboxEvent(
                        recipient.getId(),
                        "coupon-distribution-recipient",
                        "coupon.distribution.recipient_issued",
                        toJson(notificationPayload(distribution, recipient, coupon))));
            }
        }
        if (!changed.isEmpty()) {
            recipients.saveAll(changed);
        }
        int issuedCount = (int) rows.stream()
                .filter(row -> "ISSUED".equals(row.getStatus()))
                .count();
        distribution.markIssued(actorId(user), issuedCount);
        IncentiveCouponDistribution saved = distributions.save(distribution);
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "coupon-distribution",
                "coupon.distribution_issued", actorId(user), request == null ? null : request.reason(), Map.of(
                        "campaignId", saved.getCampaignId().toString(),
                        "issuedCount", issuedCount,
                        "createdCoupons", createdCoupons.size(),
                        "notifyLearners", saved.isNotifyLearners()), auditMetadata);
        return distributionDto(saved, rows);
    }

    @Transactional
    public CouponDistributionDto revoke(UUID distributionId,
                                        CouponDistributionActionRequestDto request,
                                        CurrentUser user,
                                        String correlationId) {
        String reason = requireText(request == null ? null : request.reason(), "revoke reason");
        IncentiveCouponDistribution distribution = lockDistribution(distributionId);
        access.requireAdminAccess(distribution.getTenantId(), distribution.getApplicationId(), user);
        access.requireClientOperation(distribution.getTenantId(), distribution.getApplicationId(), user, "admin");
        if ("REVOKED".equals(distribution.getStatus())) {
            return distributionDto(distribution, recipients.findByDistributionIdOrderByCreatedAtAsc(distributionId));
        }
        List<IncentiveCouponDistributionRecipient> rows =
                recipients.findByDistributionIdOrderByCreatedAtAsc(distributionId);
        List<IncentiveCouponDistributionRecipient> changed = new ArrayList<>();
        int voidedCoupons = 0;
        for (IncentiveCouponDistributionRecipient recipient : rows) {
            if ("REVOKED".equals(recipient.getStatus())) {
                continue;
            }
            if (recipient.getCouponId() != null) {
                IncentiveCoupon coupon = coupons.lockById(recipient.getCouponId())
                        .orElseThrow(() -> new NotFoundException("Coupon not found: " + recipient.getCouponId()));
                if (!"VOID".equals(coupon.getStatus())) {
                    coupon.changeStatus("VOID");
                    coupons.save(coupon);
                    voidedCoupons += 1;
                }
            }
            recipient.revoke(reason);
            changed.add(recipient);
        }
        if (!changed.isEmpty()) {
            recipients.saveAll(changed);
        }
        int revokedCount = (int) rows.stream()
                .filter(row -> "REVOKED".equals(row.getStatus()))
                .count();
        try {
            distribution.revoke(actorId(user), revokedCount);
        } catch (IllegalStateException ex) {
            throw new ConflictException(ex.getMessage());
        }
        IncentiveCouponDistribution saved = distributions.save(distribution);
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "coupon-distribution",
                "coupon.distribution_revoked", actorId(user), reason, Map.of(
                        "campaignId", saved.getCampaignId().toString(),
                        "revokedCount", revokedCount,
                        "voidedCoupons", voidedCoupons), auditMetadata);
        outboxEvents.save(new OutboxEvent(
                saved.getId(),
                "coupon-distribution",
                "coupon.distribution.revoked",
                toJson(Map.of(
                        "distributionId", saved.getId().toString(),
                        "tenantId", saved.getTenantId(),
                        "applicationId", saved.getApplicationId(),
                        "campaignId", saved.getCampaignId().toString(),
                        "revokedCount", revokedCount,
                        "reason", reason,
                        "correlationId", auditMetadata.correlationId() == null ? "" : auditMetadata.correlationId()))));
        return distributionDto(saved, rows);
    }

    private List<CouponDistributionPreviewRecipientDto> previewSample(
            List<CouponDistributionRecipientInputDto> inputs) {
        LinkedHashSet<String> seen = new LinkedHashSet<>();
        List<CouponDistributionPreviewRecipientDto> sample = new ArrayList<>();
        for (CouponDistributionRecipientInputDto input : inputs) {
            if (sample.size() >= 20) {
                break;
            }
            String profileId = requireText(input.profileId(), "profileId");
            boolean duplicate = !seen.add(profileId);
            sample.add(new CouponDistributionPreviewRecipientDto(
                    profileId,
                    duplicate ? "DUPLICATE" : "READY",
                    duplicate ? "Profile already appears in this distribution payload" : null,
                    input.metadata() == null ? Map.of() : input.metadata()));
        }
        return sample;
    }

    private List<RecipientDraft> recipientDrafts(List<CouponDistributionRecipientInputDto> inputs) {
        if (inputs == null || inputs.isEmpty()) {
            throw new BadRequestException("Coupon distribution recipients are required");
        }
        LinkedHashMap<String, Map<String, Object>> unique = new LinkedHashMap<>();
        for (CouponDistributionRecipientInputDto input : inputs) {
            String profileId = requireText(input.profileId(), "profileId");
            unique.putIfAbsent(profileId, input.metadata() == null ? Map.of() : input.metadata());
        }
        if (unique.isEmpty()) {
            throw new BadRequestException("Coupon distribution recipients are required");
        }
        return unique.entrySet().stream()
                .map(entry -> new RecipientDraft(entry.getKey(), entry.getValue()))
                .toList();
    }

    private Map<String, Object> couponMetadata(IncentiveCouponDistribution distribution,
                                               IncentiveCouponDistributionRecipient recipient) {
        Map<String, Object> metadata = new LinkedHashMap<>(readMap(distribution.getMetadataJson()));
        metadata.put("distributionId", distribution.getId().toString());
        metadata.put("distributionName", distribution.getName());
        metadata.put("sourceType", distribution.getSourceType());
        metadata.put("sourceReference", distribution.getSourceReference());
        metadata.put("recipientMetadata", readMap(recipient.getMetadataJson()));
        return metadata;
    }

    private Map<String, Object> notificationPayload(IncentiveCouponDistribution distribution,
                                                    IncentiveCouponDistributionRecipient recipient,
                                                    IncentiveCoupon coupon) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("distributionId", distribution.getId().toString());
        payload.put("tenantId", distribution.getTenantId());
        payload.put("applicationId", distribution.getApplicationId());
        payload.put("campaignId", distribution.getCampaignId().toString());
        payload.put("sourceType", distribution.getSourceType());
        payload.put("sourceReference", distribution.getSourceReference());
        payload.put("profileId", recipient.getProfileId());
        payload.put("couponId", coupon.getId().toString());
        payload.put("codeMask", coupon.getCodeMask());
        payload.put("startsAt", coupon.getStartsAt());
        payload.put("expiresAt", coupon.getExpiresAt());
        return payload;
    }

    private CouponCodeDraft uniqueCouponCode(UUID campaignId) {
        for (int attempt = 0; attempt < 100; attempt += 1) {
            String normalized = "D" + randomCouponSuffix(13);
            if (!couponExistsForCode(campaignId, normalized)) {
                return new CouponCodeDraft(normalized, CouponCodeNormalizer.mask(normalized));
            }
        }
        throw new ConflictException("Could not generate a unique coupon code for distribution");
    }

    private boolean couponExistsForCode(UUID campaignId, String normalizedCode) {
        for (CouponCodeFingerprintService.CouponLookupCandidate lookup : couponFingerprints.lookupCandidates(normalizedCode)) {
            if (coupons.findByCampaignIdAndNormalizedCode(campaignId, lookup.fingerprint()).isPresent()) {
                return true;
            }
        }
        return false;
    }

    private String previewHash(UUID campaignId,
                               String sourceType,
                               String sourceReference,
                               boolean notifyLearners,
                               Instant startsAt,
                               Instant expiresAt,
                               Integer maxRedemptions,
                               Integer maxRedemptionsPerProfile,
                               Map<String, Object> metadata,
                               List<RecipientDraft> drafts) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("campaignId", campaignId.toString());
        payload.put("sourceType", sourceType);
        payload.put("sourceReference", sourceReference);
        payload.put("notifyLearners", notifyLearners);
        payload.put("startsAt", startsAt == null ? null : startsAt.toString());
        payload.put("expiresAt", expiresAt == null ? null : expiresAt.toString());
        payload.put("maxRedemptions", maxRedemptions);
        payload.put("maxRedemptionsPerProfile", maxRedemptionsPerProfile);
        payload.put("metadata", metadata == null ? Map.of() : metadata);
        payload.put("recipients", drafts.stream()
                .map(draft -> Map.of(
                        "profileId", draft.profileId(),
                        "metadata", draft.metadata()))
                .toList());
        return "sha256:" + sha256(toJson(canonicalValue(payload)));
    }

    @SuppressWarnings("unchecked")
    private Object canonicalValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            LinkedHashMap<String, Object> sorted = new LinkedHashMap<>();
            map.entrySet().stream()
                    .filter(entry -> entry.getKey() != null)
                    .sorted(Comparator.comparing(entry -> String.valueOf(entry.getKey())))
                    .forEach(entry -> sorted.put(String.valueOf(entry.getKey()), canonicalValue(entry.getValue())));
            return sorted;
        }
        if (value instanceof List<?> list) {
            return list.stream().map(this::canonicalValue).toList();
        }
        return value;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private String randomCouponSuffix(int length) {
        StringBuilder builder = new StringBuilder(length);
        for (int i = 0; i < length; i += 1) {
            builder.append(COUPON_ALPHABET.charAt(secureRandom.nextInt(COUPON_ALPHABET.length())));
        }
        return builder.toString();
    }

    private IncentiveCampaign campaign(UUID campaignId) {
        return campaigns.findById(campaignId)
                .orElseThrow(() -> new NotFoundException("Campaign not found: " + campaignId));
    }

    private IncentiveCouponDistribution distribution(UUID distributionId) {
        return distributions.findById(distributionId)
                .orElseThrow(() -> new NotFoundException("Coupon distribution not found: " + distributionId));
    }

    private IncentiveCouponDistribution lockDistribution(UUID distributionId) {
        return distributions.lockById(distributionId)
                .orElseThrow(() -> new NotFoundException("Coupon distribution not found: " + distributionId));
    }

    private CouponDistributionDto distributionDto(IncentiveCouponDistribution distribution,
                                                  List<IncentiveCouponDistributionRecipient> recipientRows) {
        return new CouponDistributionDto(
                distribution.getId(),
                distribution.getTenantId(),
                distribution.getApplicationId(),
                distribution.getCampaignId(),
                distribution.getName(),
                distribution.getSourceType(),
                distribution.getSourceReference(),
                distribution.getStatus(),
                distribution.isNotifyLearners(),
                distribution.getStartsAt(),
                distribution.getExpiresAt(),
                distribution.getMaxRedemptions(),
                distribution.getMaxRedemptionsPerProfile(),
                distribution.getRecipientCount(),
                distribution.getIssuedCount(),
                distribution.getRevokedCount(),
                distribution.getPreviewHash(),
                distribution.getReason(),
                readMap(distribution.getMetadataJson()),
                distribution.getCreatedBy(),
                distribution.getApprovedBy(),
                distribution.getIssuedBy(),
                distribution.getRevokedBy(),
                distribution.getCreatedAt(),
                distribution.getApprovedAt(),
                distribution.getIssuedAt(),
                distribution.getRevokedAt(),
                distribution.getUpdatedAt(),
                recipientRows.stream().map(this::recipientDto).toList());
    }

    private CouponDistributionRecipientDto recipientDto(IncentiveCouponDistributionRecipient recipient) {
        return new CouponDistributionRecipientDto(
                recipient.getId(),
                recipient.getDistributionId(),
                recipient.getProfileId(),
                recipient.getStatus(),
                recipient.getCouponId(),
                recipient.getNotificationStatus(),
                recipient.getFailureReason(),
                readMap(recipient.getMetadataJson()),
                recipient.getCreatedAt(),
                recipient.getIssuedAt(),
                recipient.getRevokedAt());
    }

    private String normalizeSourceType(String sourceType) {
        String normalized = requireText(sourceType, "sourceType").toUpperCase();
        if (!SOURCE_TYPES.contains(normalized)) {
            throw new BadRequestException("Unsupported coupon distribution sourceType: " + sourceType);
        }
        return normalized;
    }

    private String normalizeStatusOrNull(String status) {
        String normalized = blankToNull(status);
        if (normalized == null) {
            return null;
        }
        String upper = normalized.toUpperCase();
        if (Set.of("PENDING_APPROVAL", "APPROVED", "ISSUED", "REVOKED").contains(upper)) {
            return upper;
        }
        throw new BadRequestException("Unsupported coupon distribution status: " + status);
    }

    private String requireText(String value, String field) {
        String text = blankToNull(value);
        if (text == null) {
            throw new BadRequestException("Coupon distribution " + field + " is required");
        }
        return text;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }

    private Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> result = objectMapper.readValue(json, MAP_TYPE);
            return result == null ? Map.of() : result;
        } catch (JsonProcessingException ex) {
            return Map.of();
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new BadRequestException("Invalid coupon distribution payload");
        }
    }

    private void audit(String tenantId,
                       String applicationId,
                       String aggregateId,
                       String aggregateType,
                       String action,
                       String actorId,
                       String note,
                       Object payload,
                       AuditMetadata metadata) {
        auditEvents.save(new IncentiveAuditEvent(
                tenantId,
                applicationId,
                aggregateId,
                aggregateType,
                action,
                actorId,
                note,
                toJson(payload),
                metadata == null ? null : metadata.correlationId(),
                metadata == null ? null : metadata.sourceClientId()));
    }

    private record RecipientDraft(String profileId, Map<String, Object> metadata) {
    }

    private record CouponCodeDraft(String normalizedCode, String codeMask) {
    }
}
