package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.events.common.EventMetadata;
import edu.courseflow.events.incentive.IncentiveEffectPayload;
import edu.courseflow.events.incentive.IncentiveRedemptionCommittedEvent;
import edu.courseflow.events.incentive.IncentiveRedemptionReversedEvent;
import edu.courseflow.promotion.dto.PromotionDtos.AdminPreviewIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.AdminPreviewIncentivesResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.AdminSimulationCandidateDto;
import edu.courseflow.promotion.dto.PromotionDtos.AdminSimulationQuotaExposureDto;
import edu.courseflow.promotion.dto.PromotionDtos.AdminSimulationTotalsDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignDto;
import edu.courseflow.promotion.dto.PromotionDtos.CancelReservationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CancelReservationResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CommitReservationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CommitReservationResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponStorageInventoryDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponStorageInventoryItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCampaignRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCouponRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.GenerateCouponsRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.GenerateCouponsResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveEffectDto;
import edu.courseflow.promotion.dto.PromotionDtos.LearnerCouponDto;
import edu.courseflow.promotion.dto.PromotionDtos.LearnerCouponWalletDto;
import edu.courseflow.promotion.dto.PromotionDtos.RedemptionDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReservationDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReservationQuotaSnapshotDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCampaignStatusRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCouponStatusRequestDto;
import edu.courseflow.promotion.model.CampaignDefinitionSnapshot;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import edu.courseflow.promotion.model.IncentiveLedgerEntry;
import edu.courseflow.promotion.model.IncentiveOperationApproval;
import edu.courseflow.promotion.model.IncentiveQuotaCounter;
import edu.courseflow.promotion.model.IncentiveRedemption;
import edu.courseflow.promotion.model.IncentiveReservation;
import edu.courseflow.promotion.model.OutboxEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignVersionRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import edu.courseflow.promotion.repository.IncentiveLedgerEntryRepository;
import edu.courseflow.promotion.repository.IncentiveQuotaCounterRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PromotionService {

    private static final Duration RESERVATION_TTL = Duration.ofMinutes(15);
    private static final Duration IDEMPOTENCY_TTL = Duration.ofDays(7);
    private static final String COMMITTED_REVERSAL_QUOTA_POLICY = "NO_RELEASE_ON_COMMITTED_REVERSAL";
    private static final boolean COMMITTED_REVERSAL_RELEASES_QUOTA = false;
    private static final String COUPON_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    private static final List<String> COUPON_STORAGE_FORMAT_ORDER = List.of(
            "current_hmac",
            "previous_hmac",
            "legacy_sha",
            "legacy_raw",
            "malformed");
    private static final TypeReference<List<IncentiveEffectDto>> EFFECT_LIST = new TypeReference<>() {
    };
    private static final TypeReference<List<QuotaSnapshotEntry>> QUOTA_SNAPSHOT_LIST = new TypeReference<>() {
    };

    private final IncentiveCampaignRepository campaigns;
    private final IncentiveCampaignVersionRepository campaignVersions;
    private final IncentiveCouponRepository coupons;
    private final IncentiveQuotaCounterRepository quotaCounters;
    private final IncentiveReservationRepository reservations;
    private final IncentiveRedemptionRepository redemptions;
    private final IncentiveLedgerEntryRepository ledgerEntries;
    private final IncentiveIdempotencyKeyRepository idempotencyKeys;
    private final IncentiveAuditEventRepository auditEvents;
    private final OutboxEventRepository outboxEvents;
    private final IncentiveDecisionEngine decisions;
    private final IncentiveAccessService access;
    private final CampaignVersionService campaignVersionService;
    private final RedemptionReversalApprovalService reversalApprovals;
    private final ObjectMapper objectMapper;
    private final IncentiveMetrics metrics;
    private final CouponCodeFingerprintService couponFingerprints;
    private final CouponStorageCutoverGuard couponStorageCutoverGuard;
    private final CouponAbuseGuard couponAbuseGuard;
    private final AdminOperationRateGuard adminOperationRateGuard;
    private final ReservationRequestSnapshotSanitizer requestSnapshotSanitizer;
    private final SecureRandom secureRandom = new SecureRandom();

    public PromotionService(IncentiveCampaignRepository campaigns,
                            IncentiveCampaignVersionRepository campaignVersions,
                            IncentiveCouponRepository coupons,
                            IncentiveQuotaCounterRepository quotaCounters,
                            IncentiveReservationRepository reservations,
                            IncentiveRedemptionRepository redemptions,
                            IncentiveLedgerEntryRepository ledgerEntries,
                            IncentiveIdempotencyKeyRepository idempotencyKeys,
                            IncentiveAuditEventRepository auditEvents,
                            OutboxEventRepository outboxEvents,
                            IncentiveDecisionEngine decisions,
                            IncentiveAccessService access,
                            CampaignVersionService campaignVersionService,
                            RedemptionReversalApprovalService reversalApprovals,
                            ObjectMapper objectMapper,
                            IncentiveMetrics metrics,
                            CouponCodeFingerprintService couponFingerprints,
                            CouponStorageCutoverGuard couponStorageCutoverGuard,
                            CouponAbuseGuard couponAbuseGuard,
                            AdminOperationRateGuard adminOperationRateGuard,
                            ReservationRequestSnapshotSanitizer requestSnapshotSanitizer) {
        this.campaigns = campaigns;
        this.campaignVersions = campaignVersions;
        this.coupons = coupons;
        this.quotaCounters = quotaCounters;
        this.reservations = reservations;
        this.redemptions = redemptions;
        this.ledgerEntries = ledgerEntries;
        this.idempotencyKeys = idempotencyKeys;
        this.auditEvents = auditEvents;
        this.outboxEvents = outboxEvents;
        this.decisions = decisions;
        this.access = access;
        this.campaignVersionService = campaignVersionService;
        this.reversalApprovals = reversalApprovals;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
        this.couponFingerprints = couponFingerprints;
        this.couponStorageCutoverGuard = couponStorageCutoverGuard;
        this.couponAbuseGuard = couponAbuseGuard;
        this.adminOperationRateGuard = adminOperationRateGuard;
        this.requestSnapshotSanitizer = requestSnapshotSanitizer;
    }

    @Transactional(readOnly = true)
    public List<CampaignDto> listCampaigns(Optional<String> tenantId, Optional<String> applicationId,
                                           CurrentUser user) {
        requireListAccess(tenantId, applicationId, user);
        return campaigns.listFiltered(blankToNull(tenantId.orElse(null)), blankToNull(applicationId.orElse(null)))
                .stream()
                .map(this::campaignDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public CampaignDto campaignDetail(UUID campaignId, CurrentUser user) {
        IncentiveCampaign campaign = campaign(campaignId);
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        return campaignDto(campaign);
    }

    @Transactional
    public CampaignDto createCampaign(CreateCampaignRequestDto request, CurrentUser user) {
        return createCampaign(request, user, null);
    }

    @Transactional
    public CampaignDto createCampaign(CreateCampaignRequestDto request, CurrentUser user, String correlationId) {
        validateCampaignRequest(request);
        access.requireAdminAccess(request.tenantId().trim(), request.applicationId().trim(), user);
        access.requireActiveApplication(request.tenantId().trim(), request.applicationId().trim(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        IncentiveCampaign campaign = new IncentiveCampaign(
                request.tenantId().trim(),
                request.applicationId().trim(),
                request.code().trim(),
                request.name().trim(),
                request.description(),
                defaultString(request.incentiveType(), "PROMOTION"),
                request.startsAt(),
                request.endsAt(),
                request.priority() == null ? 0 : request.priority(),
                Boolean.TRUE.equals(request.exclusive()),
                request.stackable() == null || request.stackable(),
                Boolean.TRUE.equals(request.couponRequired()),
                defaultString(request.matchPolicy(), "ALL").trim().toUpperCase(),
                request.currency(),
                decisions.toRulesJson(request.rules()),
                decisions.toActionsJson(request.actions()),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                actorId(user));
        IncentiveCampaign saved = campaigns.save(campaign);
        campaignVersionService.createInitialDraft(saved, actorId(user));
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "campaign",
                "campaign.created", actorId(user), null, saved, auditMetadata);
        return campaignDto(saved);
    }

    @Transactional
    public CampaignDto updateCampaignStatus(UUID campaignId, UpdateCampaignStatusRequestDto request, CurrentUser user) {
        return updateCampaignStatus(campaignId, request, user, null);
    }

    @Transactional
    public CampaignDto updateCampaignStatus(UUID campaignId, UpdateCampaignStatusRequestDto request, CurrentUser user,
                                            String correlationId) {
        IncentiveCampaign campaign = campaign(campaignId);
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireClientOperation(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        String requestedStatus = request.status() == null ? "" : request.status().trim().toUpperCase();
        if ("PUBLISHED".equals(requestedStatus)) {
            throw new BadRequestException("Publish campaign versions via the approval workflow");
        }
        campaign.changeStatus(request.status());
        if ("PAUSED".equals(campaign.getStatus()) || "ARCHIVED".equals(campaign.getStatus())
                || "DRAFT".equals(campaign.getStatus())) {
            campaignVersionService.deactivateActiveSnapshot(campaign.getId());
        }
        IncentiveCampaign saved = campaigns.save(campaign);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "campaign",
                "campaign.status_changed", actorId(user), request.note(), Map.of("status", saved.getStatus()),
                auditMetadata);
        return campaignDto(saved);
    }

    @Transactional
    public CouponDto createCoupon(CreateCouponRequestDto request, CurrentUser user) {
        return createCoupon(request, user, null);
    }

    @Transactional
    public CouponDto createCoupon(CreateCouponRequestDto request, CurrentUser user, String correlationId) {
        IncentiveCampaign campaign = campaign(request.campaignId());
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireActiveApplication(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        CouponValidationSupport.validateWindowAndLimits(
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile());
        String normalized = CouponCodeNormalizer.normalize(request.code());
        if (normalized.isBlank()) {
            throw new BadRequestException("Coupon code is required");
        }
        couponStorageCutoverGuard.requireCouponWriteAllowed(
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId());
        if (couponExistsForCode(campaign.getId(), normalized)) {
            throw new ConflictException("Coupon code already exists for campaign");
        }
        String codeMask = CouponCodeNormalizer.mask(normalized);
        IncentiveCoupon coupon = new IncentiveCoupon(
                campaign.getId(),
                codeMask,
                couponFingerprints.primaryFingerprint(normalized),
                codeMask,
                blankToNull(request.holderProfileId()),
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile(),
                toJson(request.metadata() == null ? Map.of() : request.metadata()));
        IncentiveCoupon saved = coupons.save(coupon);
        audit(campaign.getTenantId(), campaign.getApplicationId(), saved.getId().toString(), "coupon",
                "coupon.created", actorId(user), null, Map.of(
                        "campaignId", campaign.getId().toString(),
                        "codeMask", saved.getCodeMask()), auditMetadata);
        return couponDto(saved);
    }

    @Transactional(readOnly = true)
    public List<CouponDto> listCoupons(Optional<String> tenantId,
                                       Optional<String> applicationId,
                                       Optional<UUID> campaignId,
                                       Optional<String> status,
                                       Optional<String> holderProfileId,
                                       Optional<String> code,
                                       Optional<Integer> limit,
                                       CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant != null && application != null) {
            access.requireReviewAccess(tenant, application, user);
        } else if (campaignId.isPresent()) {
            IncentiveCampaign campaign = campaign(campaignId.get());
            access.requireReviewAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        } else {
            access.requirePlatformAdmin(user);
        }
        String normalizedCode = CouponCodeNormalizer.normalize(code.orElse(null));
        List<String> codeLookups = normalizedCode.isBlank()
                ? List.of("__no_coupon_lookup__")
                : couponFingerprints.lookupFingerprints(normalizedCode);
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 200));
        return coupons.listFiltered(
                        tenant,
                        application,
                        campaignId.orElse(null),
                        CouponValidationSupport.normalizeStatusOrNull(status.orElse(null)),
                        blankToNull(holderProfileId.orElse(null)),
                        !normalizedCode.isBlank(),
                        codeLookups,
                        normalizedCode.isBlank() ? "" : normalizedCode,
                        PageRequest.of(0, pageSize))
                .stream()
                .map(this::couponDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public LearnerCouponWalletDto learnerCoupons(String tenantId,
                                                 String applicationId,
                                                 String profileId,
                                                 Optional<Integer> limit,
                                                 CurrentUser user) {
        String tenant = defaultString(tenantId, "courseflow");
        String application = defaultString(applicationId, "lms");
        String profile = blankToNull(profileId);
        if (profile == null) {
            throw new BadRequestException("profileId is required");
        }
        access.requireClientOperation(tenant, application, user, "evaluate");
        access.requireTrustedRuntimeCaller(tenant, application, user, "evaluate");
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 100));
        Instant now = Instant.now();
        List<LearnerCouponDto> items = coupons.listFiltered(
                        tenant,
                        application,
                        null,
                        null,
                        profile,
                        false,
                        List.of("__no_coupon_lookup__"),
                        "",
                        PageRequest.of(0, pageSize))
                .stream()
                .map(coupon -> learnerCouponDto(coupon, profile, now))
                .toList();
        int available = (int) items.stream().filter(item -> "AVAILABLE".equals(item.walletStatus())).count();
        int expiringSoon = (int) items.stream()
                .filter(item -> "AVAILABLE".equals(item.walletStatus()))
                .filter(item -> item.expiresAt() != null && !item.expiresAt().isAfter(now.plus(Duration.ofDays(30))))
                .count();
        int used = (int) items.stream().filter(item -> "USED".equals(item.walletStatus())).count();
        int expired = (int) items.stream().filter(item -> "EXPIRED".equals(item.walletStatus())).count();
        return new LearnerCouponWalletDto(
                tenant,
                application,
                profile,
                now,
                available,
                expiringSoon,
                used,
                expired,
                items);
    }

    @Transactional(readOnly = true)
    public CouponStorageInventoryDto couponStorageInventory(Optional<String> tenantId,
                                                            Optional<String> applicationId,
                                                            Optional<UUID> campaignId,
                                                            Optional<Boolean> activeOnly,
                                                            CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        UUID campaignFilter = campaignId.orElse(null);
        if (tenant != null && application != null) {
            access.requireAdminAccess(tenant, application, user);
        } else if (campaignFilter != null) {
            IncentiveCampaign campaign = campaign(campaignFilter);
            access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
            tenant = campaign.getTenantId();
            application = campaign.getApplicationId();
        } else {
            access.requirePlatformAdmin(user);
        }
        boolean onlyActive = activeOnly.orElse(true);
        Map<String, Long> counts = new LinkedHashMap<>();
        COUPON_STORAGE_FORMAT_ORDER.forEach(storageFormat -> counts.put(storageFormat, 0L));
        coupons.countByStorageFormat(
                tenant,
                application,
                campaignFilter,
                onlyActive,
                couponFingerprints.currentStoragePrefix()).forEach(row ->
                counts.merge(row.getStorageFormat(), row.getCouponCount(), Long::sum));
        List<CouponStorageInventoryItemDto> items = counts.entrySet()
                .stream()
                .map(entry -> new CouponStorageInventoryItemDto(entry.getKey(), entry.getValue()))
                .toList();
        long total = items.stream().mapToLong(CouponStorageInventoryItemDto::count).sum();
        long legacy = items.stream()
                .filter(item -> "legacy_sha".equals(item.storageFormat()) || "legacy_raw".equals(item.storageFormat()))
                .mapToLong(CouponStorageInventoryItemDto::count)
                .sum();
        long malformed = items.stream()
                .filter(item -> "malformed".equals(item.storageFormat()))
                .mapToLong(CouponStorageInventoryItemDto::count)
                .sum();
        return new CouponStorageInventoryDto(
                tenant,
                application,
                campaignFilter,
                onlyActive,
                couponFingerprints.legacyFallbackEnabled(),
                legacy == 0 && malformed == 0,
                total,
                legacy,
                malformed,
                Instant.now(),
                items);
    }

    @Transactional(readOnly = true)
    public CouponDto coupon(UUID couponId, CurrentUser user) {
        IncentiveCoupon coupon = coupons.findById(couponId)
                .orElseThrow(() -> new NotFoundException("Coupon not found: " + couponId));
        IncentiveCampaign campaign = campaign(coupon.getCampaignId());
        access.requireReviewAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        return couponDto(coupon);
    }

    @Transactional
    public CouponDto updateCouponStatus(UUID couponId, UpdateCouponStatusRequestDto request, CurrentUser user) {
        return updateCouponStatus(couponId, request, user, null);
    }

    @Transactional
    public CouponDto updateCouponStatus(UUID couponId, UpdateCouponStatusRequestDto request, CurrentUser user,
                                        String correlationId) {
        if (request == null) {
            throw new BadRequestException("Coupon status request is required");
        }
        IncentiveCoupon coupon = coupons.lockById(couponId)
                .orElseThrow(() -> new NotFoundException("Coupon not found: " + couponId));
        IncentiveCampaign campaign = campaign(coupon.getCampaignId());
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireClientOperation(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        String nextStatus = CouponValidationSupport.normalizeStatusOrThrow(request.status());
        if (("VOID".equals(nextStatus) || "EXPIRED".equals(nextStatus))
                && blankToNull(request.reason()) == null) {
            throw new BadRequestException("Coupon status reason is required for " + nextStatus);
        }
        try {
            coupon.changeStatus(nextStatus);
        } catch (IllegalArgumentException ex) {
            throw new BadRequestException(ex.getMessage());
        }
        IncentiveCoupon saved = coupons.save(coupon);
        audit(campaign.getTenantId(), campaign.getApplicationId(), saved.getId().toString(), "coupon",
                "coupon.status_changed", actorId(user), request.reason(), Map.of(
                        "campaignId", campaign.getId().toString(),
                        "status", saved.getStatus(),
                        "codeMask", saved.getCodeMask()), auditMetadata);
        return couponDto(saved);
    }

    @Transactional
    public GenerateCouponsResponseDto generateCoupons(GenerateCouponsRequestDto request, CurrentUser user) {
        return generateCoupons(request, user, null);
    }

    @Transactional
    public GenerateCouponsResponseDto generateCoupons(GenerateCouponsRequestDto request, CurrentUser user,
                                                      String correlationId) {
        if (request == null) {
            throw new BadRequestException("Generate coupons request is required");
        }
        IncentiveCampaign campaign = campaign(request.campaignId());
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireActiveApplication(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        couponStorageCutoverGuard.requireCouponWriteAllowed(
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId());
        adminOperationRateGuard.requireAllowed(
                "coupon_generate",
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                user,
                access.sourceClientId(user),
                null);
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        CouponValidationSupport.validateWindowAndLimits(
                request.startsAt(),
                request.expiresAt(),
                request.maxRedemptions(),
                request.maxRedemptionsPerProfile());
        int quantity = Math.max(1, Math.min(request.quantity(), 500));
        int codeLength = Math.max(6, Math.min(request.codeLength() == null ? 10 : request.codeLength(), 32));
        String prefix = normalizeCouponPrefix(request.prefix());
        List<CouponDto> created = new ArrayList<>();
        int duplicateRetries = 0;
        int attempts = 0;
        int maxAttempts = quantity * 10;
        while (created.size() < quantity && attempts < maxAttempts) {
            attempts += 1;
            String normalized = prefix + randomCouponSuffix(codeLength);
            String fingerprint = couponFingerprints.primaryFingerprint(normalized);
            if (couponExistsForCode(campaign.getId(), normalized)) {
                duplicateRetries += 1;
                continue;
            }
            IncentiveCoupon coupon = new IncentiveCoupon(
                    campaign.getId(),
                    CouponCodeNormalizer.mask(normalized),
                    fingerprint,
                    CouponCodeNormalizer.mask(normalized),
                    blankToNull(request.holderProfileId()),
                    request.startsAt(),
                    request.expiresAt(),
                    request.maxRedemptions(),
                    request.maxRedemptionsPerProfile(),
                    toJson(request.metadata() == null ? Map.of() : request.metadata()));
            created.add(couponDto(coupons.save(coupon)));
        }
        if (created.size() < quantity) {
            throw new ConflictException("Could not generate enough unique coupon codes");
        }
        audit(campaign.getTenantId(), campaign.getApplicationId(), campaign.getId().toString(), "coupon-batch",
                "coupon.batch_generated", actorId(user), null, Map.of(
                        "campaignId", campaign.getId().toString(),
                        "requested", request.quantity(),
                        "created", created.size(),
                        "duplicateRetries", duplicateRetries,
                        "prefix", prefix), auditMetadata);
        return new GenerateCouponsResponseDto(campaign.getId(), request.quantity(), created.size(),
                duplicateRetries, created);
    }

    @Transactional(readOnly = true)
    public EvaluateIncentivesResponseDto evaluate(EvaluateIncentivesRequestDto request) {
        return evaluate(request, null);
    }

    @Transactional(readOnly = true)
    public EvaluateIncentivesResponseDto evaluate(EvaluateIncentivesRequestDto request, CurrentUser user) {
        long started = System.nanoTime();
        RuntimeMetric metric = RuntimeMetric.error();
        try {
            access.requireActiveApplication(request.tenantId(), request.applicationId(), user, "evaluate");
            access.requireTrustedRuntimeCaller(request.tenantId(), request.applicationId(), user, "evaluate");
            requireProfileAccess(user, request.profileId(), request.tenantId(), request.applicationId());
            EvaluateIncentivesResponseDto response = evaluateDecision(
                    request,
                    "evaluate",
                    access.sourceClientId(user),
                    true);
            metric = runtimeMetric(response.eligible(), response.reasonCodes(), hasCouponSelectors(request), "eligible");
            return response;
        } catch (RuntimeException ex) {
            metric = runtimeExceptionMetric(ex);
            throw ex;
        } finally {
            metrics.runtimeOperation("evaluate", metric.result(), metric.reason(), elapsed(started));
        }
    }

    @Transactional
    public AdminPreviewIncentivesResponseDto preview(AdminPreviewIncentivesRequestDto request, CurrentUser user,
                                                     String correlationId) {
        long started = System.nanoTime();
        RuntimeMetric metric = RuntimeMetric.error();
        try {
            if (request == null || request.context() == null) {
                throw new BadRequestException("Admin incentive preview context is required");
            }
            EvaluateIncentivesRequestDto context = request.context();
            access.requireAdminAccess(context.tenantId(), context.applicationId(), user);
            access.requireActiveApplication(context.tenantId(), context.applicationId(), user, "admin");
            Map<String, Object> auditFacts = requestSnapshotSanitizer.auditFacts(context);
            String contextHash = hash(auditFacts);
            String sourceClientId = access.sourceClientId(user);
            adminOperationRateGuard.requireAllowed(
                    "admin_preview",
                    context.tenantId(),
                    context.applicationId(),
                    null,
                    user,
                    sourceClientId,
                    contextHash);
            PreviewSimulation simulation = previewSimulation(context, "preview");
            EvaluateIncentivesResponseDto decision = simulation.decision();
            audit(
                    context.tenantId(),
                    context.applicationId(),
                    contextHash,
                    "incentive-preview",
                    "incentive.previewed",
                    actorId(user),
                    request.note(),
                    previewAuditPayload(auditFacts, simulation, contextHash),
                    correlationId,
                    sourceClientId);
            metric = runtimeMetric(decision.eligible(), decision.reasonCodes(), hasCouponSelectors(context), "previewed");
            return new AdminPreviewIncentivesResponseDto(
                    true,
                    false,
                    contextHash,
                    decision,
                    decision.campaignId(),
                    decision.campaignVersion(),
                    decision.campaignCode(),
                    decision.couponId(),
                    simulation.totals(),
                    simulation.quotaExposure(),
                    simulation.candidates(),
                    Instant.now());
        } catch (RuntimeException ex) {
            metric = runtimeExceptionMetric(ex);
            throw ex;
        } finally {
            metrics.runtimeOperation("preview", metric.result(), metric.reason(), elapsed(started));
        }
    }

    private PreviewSimulation previewSimulation(EvaluateIncentivesRequestDto request, String operation) {
        CouponMatchDiagnostics couponDiagnostics = CouponMatchDiagnostics.forRequest(request);
        try {
            List<Selection> candidates = selectCandidates(request, couponDiagnostics);
            Selection selected = candidates.stream()
                    .filter(candidate -> quotasAvailable(candidate, request.profileId()))
                    .findFirst()
                    .orElse(null);
            EvaluateIncentivesResponseDto decision;
            if (selected == null) {
                if (!candidates.isEmpty()) {
                    Selection first = candidates.getFirst();
                    decision = new EvaluateIncentivesResponseDto(
                            false,
                            first.campaign().getCampaignId(),
                            first.campaign().getCampaignVersion(),
                            first.campaign().getCode(),
                            first.coupon() == null ? null : first.coupon().getId(),
                            List.of(),
                            List.of("QUOTA_EXHAUSTED"));
                } else {
                    decision = new EvaluateIncentivesResponseDto(
                            false, null, null, null, null, List.of(), List.of("NO_ELIGIBLE_INCENTIVE"));
                }
            } else {
                decision = new EvaluateIncentivesResponseDto(
                        true,
                        selected.campaign().getCampaignId(),
                        selected.campaign().getCampaignVersion(),
                        selected.campaign().getCode(),
                        selected.coupon() == null ? null : selected.coupon().getId(),
                        selected.decision().effects(),
                        selected.decision().reasonCodes());
            }
            StackingAnalysis stackingAnalysis = stackingAnalysis(candidates, selected, request.profileId());
            List<AdminSimulationCandidateDto> candidateDtos = candidates.stream()
                    .map(candidate -> simulationCandidateDto(
                            candidate,
                            request.profileId(),
                            stackingAnalysis.result(candidate)))
                    .toList();
            List<AdminSimulationQuotaExposureDto> quotaExposure = selected == null
                    ? List.of()
                    : quotaExposure(selected, request.profileId());
            return new PreviewSimulation(
                    decision,
                    simulationTotals(request, decision.effects()),
                    quotaExposure,
                    candidateDtos);
        } finally {
            recordCouponMatch(operation, couponDiagnostics);
        }
    }

    private EvaluateIncentivesResponseDto evaluateDecision(EvaluateIncentivesRequestDto request, String operation) {
        return evaluateDecision(request, operation, null, false);
    }

    private EvaluateIncentivesResponseDto evaluateDecision(EvaluateIncentivesRequestDto request,
                                                          String operation,
                                                          String sourceClientId,
                                                          boolean applyAbuseGuard) {
        CouponMatchDiagnostics couponDiagnostics = CouponMatchDiagnostics.forRequest(request);
        try {
            List<Selection> candidates = selectCandidates(request, couponDiagnostics);
            Selection selection = candidates.stream()
                    .filter(candidate -> quotasAvailable(candidate, request.profileId()))
                    .findFirst()
                    .orElse(null);
            if (selection == null) {
                CouponAbuseGuard.Decision guard = applyAbuseGuard
                        ? couponAbuseGuard.check(
                        operation,
                        request,
                        sourceClientId,
                        couponDiagnostics.result(),
                        couponDiagnostics.couponRequired())
                        : CouponAbuseGuard.Decision.allowed();
                if (guard.blocked()) {
                    return new EvaluateIncentivesResponseDto(
                            false, null, null, null, null, List.of(), List.of(guard.reasonCode()));
                }
                if (!candidates.isEmpty()) {
                    return new EvaluateIncentivesResponseDto(
                            false,
                            candidates.getFirst().campaign().getCampaignId(),
                            candidates.getFirst().campaign().getCampaignVersion(),
                            candidates.getFirst().campaign().getCode(),
                            candidates.getFirst().coupon() == null ? null : candidates.getFirst().coupon().getId(),
                            List.of(),
                            List.of("QUOTA_EXHAUSTED"));
                }
                return new EvaluateIncentivesResponseDto(
                        false, null, null, null, null, List.of(), List.of("NO_ELIGIBLE_INCENTIVE"));
            }
            return new EvaluateIncentivesResponseDto(
                    true,
                    selection.campaign().getCampaignId(),
                    selection.campaign().getCampaignVersion(),
                    selection.campaign().getCode(),
                    selection.coupon() == null ? null : selection.coupon().getId(),
                    selection.decision().effects(),
                    selection.decision().reasonCodes());
        } finally {
            recordCouponMatch(operation, couponDiagnostics);
        }
    }

    @Transactional
    public ReserveIncentiveResponseDto reserve(ReserveIncentiveRequestDto request) {
        return reserve(request, null);
    }

    @Transactional
    public ReserveIncentiveResponseDto reserve(ReserveIncentiveRequestDto request, CurrentUser user) {
        return reserve(request, user, null);
    }

    @Transactional
    public ReserveIncentiveResponseDto reserve(ReserveIncentiveRequestDto request, CurrentUser user,
                                               String correlationId) {
        long started = System.nanoTime();
        RuntimeMetric metric = RuntimeMetric.error();
        try {
            access.requireActiveApplication(
                    request.context().tenantId(), request.context().applicationId(), user, "reserve");
            access.requireTrustedRuntimeCaller(
                    request.context().tenantId(), request.context().applicationId(), user, "reserve");
            requireProfileAccess(
                    user,
                    request.context().profileId(),
                    request.context().tenantId(),
                    request.context().applicationId());
            String sourceClientId = access.sourceClientId(user);
            AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
            String requestHash = hash(request);
            IdempotencySlot<ReserveIncentiveResponseDto> slot = acquireIdempotency(
                    request.context().tenantId(),
                    request.context().applicationId(),
                    "RESERVE",
                    request.idempotencyKey(),
                    requestHash,
                    ReserveIncentiveResponseDto.class);
            if (slot.replay() != null) {
                metric = new RuntimeMetric("replay", "idempotency_replay");
                return reserveReplay(slot.replay());
            }

            CouponMatchDiagnostics couponDiagnostics = CouponMatchDiagnostics.forRequest(request.context());
            try {
                List<Selection> candidates = selectCandidates(request.context(), couponDiagnostics);
                CouponAbuseGuard.Decision guard = couponAbuseGuard.check(
                        "reserve",
                        request.context(),
                        sourceClientId,
                        couponDiagnostics.result(),
                        couponDiagnostics.couponRequired());
                if (guard.blocked()) {
                    ReserveIncentiveResponseDto response = new ReserveIncentiveResponseDto(
                            false, null, null, null, null, null, List.of(), List.of(guard.reasonCode()), false);
                    completeIdempotency(slot.key(), response);
                    metric = runtimeMetric(false, response.reasonCodes(), hasCouponSelectors(request.context()), "reserved");
                    return response;
                }
                ReserveCandidate reservedCandidate = reserveFirstAvailableCandidate(candidates, request.context().profileId());
                if (reservedCandidate.selection() == null) {
                    List<String> reasons = candidates.isEmpty()
                            ? List.of("NO_ELIGIBLE_INCENTIVE")
                            : List.of("QUOTA_EXHAUSTED");
                    ReserveIncentiveResponseDto response = new ReserveIncentiveResponseDto(
                            false, null, null, null, null, null, List.of(), reasons, false);
                    completeIdempotency(slot.key(), response);
                    metric = runtimeMetric(false, reasons, hasCouponSelectors(request.context()), "reserved");
                    return response;
                }

                Selection selection = reservedCandidate.selection();
                List<QuotaSnapshotEntry> quotaSnapshot = reservedCandidate.quotaSnapshot();
                String effectsJson = toJson(selection.decision().effects());
                IncentiveReservation reservation = new IncentiveReservation(
                        request.context().tenantId(),
                        request.context().applicationId(),
                        selection.campaign().getCampaignId(),
                        selection.campaign().getCampaignVersion(),
                        selection.coupon() == null ? null : selection.coupon().getId(),
                        request.context().profileId(),
                        request.context().externalReference(),
                        effectsJson,
                        toJson(requestSnapshotSanitizer.storageSnapshot(request.context())),
                        requestHash,
                        toJson(quotaSnapshot),
                        Instant.now().plus(RESERVATION_TTL));
                reservations.save(reservation);
                ledgerEntries.save(new IncentiveLedgerEntry("RESERVE", reservation, null, effectsJson));
                audit(reservation.getTenantId(), reservation.getApplicationId(), reservation.getId().toString(), "reservation",
                        "reservation.created", actorId(user), null, Map.of(
                                "campaignId", reservation.getCampaignId().toString(),
                                "campaignVersion", reservation.getCampaignVersion(),
                                "couponId", reservation.getCouponId() == null ? "" : reservation.getCouponId().toString()),
                        auditMetadata);

                ReserveIncentiveResponseDto response = new ReserveIncentiveResponseDto(
                        true,
                        reservation.getId(),
                        reservation.getCampaignId(),
                        reservation.getCampaignVersion(),
                        reservation.getCouponId(),
                        reservation.getExpiresAt(),
                        selection.decision().effects(),
                        selection.decision().reasonCodes(),
                        false);
                completeIdempotency(slot.key(), response);
                metric = runtimeMetric(true, response.reasonCodes(), hasCouponSelectors(request.context()), "reserved");
                return response;
            } finally {
                recordCouponMatch("reserve", couponDiagnostics);
            }
        } catch (RuntimeException ex) {
            metric = runtimeExceptionMetric(ex);
            throw ex;
        } finally {
            metrics.runtimeOperation("reserve", metric.result(), metric.reason(), elapsed(started));
        }
    }

    @Transactional
    public CommitReservationResponseDto commit(UUID reservationId, CommitReservationRequestDto request) {
        return commit(reservationId, request, null);
    }

    @Transactional
    public CommitReservationResponseDto commit(UUID reservationId, CommitReservationRequestDto request, CurrentUser user) {
        return commit(reservationId, request, user, null);
    }

    @Transactional
    public CommitReservationResponseDto commit(UUID reservationId, CommitReservationRequestDto request,
                                               CurrentUser user, String correlationId) {
        long started = System.nanoTime();
        RuntimeMetric metric = RuntimeMetric.error();
        try {
            IncentiveReservation reservation = lockReservation(reservationId);
            access.requireKnownApplication(reservation.getTenantId(), reservation.getApplicationId(), user, "commit");
            access.requireTrustedRuntimeCaller(reservation.getTenantId(), reservation.getApplicationId(), user, "commit");
            requireProfileAccess(user, reservation.getProfileId(), reservation.getTenantId(), reservation.getApplicationId());
            AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
            String requestHash = hash(Map.of("reservationId", reservationId.toString(), "request", request));
            IdempotencySlot<CommitReservationResponseDto> slot = acquireIdempotency(
                    reservation.getTenantId(),
                    reservation.getApplicationId(),
                    "COMMIT",
                    request.idempotencyKey(),
                    requestHash,
                    CommitReservationResponseDto.class);
            if (slot.replay() != null) {
                metric = new RuntimeMetric("replay", "idempotency_replay");
                return commitReplay(slot.replay());
            }
            if (reservation.isExpired(Instant.now()) && "RESERVED".equals(reservation.getStatus())) {
                expireReservation(reservation, "reservation expired before commit", auditMetadata);
                CommitReservationResponseDto response = new CommitReservationResponseDto(
                        false,
                        reservation.getId(),
                        null,
                        reservation.getCampaignId(),
                        reservation.getCampaignVersion(),
                        reservation.getStatus(),
                        effects(reservation.getEffectsJson()),
                        List.of("RESERVATION_EXPIRED"),
                        false);
                completeIdempotency(slot.key(), response);
                metric = runtimeMetric(false, response.reasonCodes(), false, "committed");
                return response;
            }
            if ("REDEEMED".equals(reservation.getStatus())) {
                IncentiveRedemption existing = redemptions.findByReservationId(reservationId)
                        .orElseThrow(() -> new ConflictException("Reservation is redeemed without a redemption record"));
                CommitReservationResponseDto response = committedResponse(reservation, existing, false, "ALREADY_COMMITTED");
                completeIdempotency(slot.key(), response);
                metric = runtimeMetric(true, response.reasonCodes(), false, "already_committed");
                return response;
            }
            if ("EXPIRED".equals(reservation.getStatus()) || "CANCELLED".equals(reservation.getStatus())) {
                CommitReservationResponseDto response = new CommitReservationResponseDto(
                        false,
                        reservation.getId(),
                        null,
                        reservation.getCampaignId(),
                        reservation.getCampaignVersion(),
                        reservation.getStatus(),
                        effects(reservation.getEffectsJson()),
                        List.of("EXPIRED".equals(reservation.getStatus())
                                ? "ALREADY_EXPIRED"
                                : "RESERVATION_CANCELLED"),
                        false);
                completeIdempotency(slot.key(), response);
                metric = runtimeMetric(false, response.reasonCodes(), false, "committed");
                return response;
            }
            if (!"RESERVED".equals(reservation.getStatus())) {
                throw new ConflictException("Reservation is not committable: " + reservation.getStatus());
            }
            reservation.commit(request.externalReference());
            IncentiveReservation savedReservation = reservations.save(reservation);
            IncentiveRedemption redemption = redemptions.save(new IncentiveRedemption(savedReservation));
            ledgerEntries.save(new IncentiveLedgerEntry("COMMIT", savedReservation, redemption.getId(),
                    savedReservation.getEffectsJson()));
            audit(savedReservation.getTenantId(), savedReservation.getApplicationId(), redemption.getId().toString(),
                    "redemption", "redemption.committed", actorId(user), null, Map.of(
                            "reservationId", savedReservation.getId().toString(),
                            "campaignId", savedReservation.getCampaignId().toString(),
                            "campaignVersion", savedReservation.getCampaignVersion()), auditMetadata);
            outboxEvents.save(new OutboxEvent(redemption.getId(), "incentive-redemption",
                    "incentive.redemption.committed", toJson(new IncentiveRedemptionCommittedEvent(
                    UUID.randomUUID().toString(),
                    1,
                    redemption.getTenantId(),
                    redemption.getApplicationId(),
                    savedReservation.getId().toString(),
                    redemption.getId().toString(),
                    redemption.getCampaignId().toString(),
                    redemption.getCampaignVersion(),
                    redemption.getCouponId() == null ? null : redemption.getCouponId().toString(),
                    redemption.getProfileId(),
                    redemption.getExternalReference(),
                    auditMetadata.correlationId(),
                    auditMetadata.sourceClientId(),
                    eventEffects(redemption.getEffectsJson()),
                    redemption.getRedeemedAt(),
                    eventMetadata(auditMetadata, user)))));
            CommitReservationResponseDto response = committedResponse(savedReservation, redemption, false, "COMMITTED");
            completeIdempotency(slot.key(), response);
            metric = runtimeMetric(true, response.reasonCodes(), false, "committed");
            return response;
        } catch (RuntimeException ex) {
            metric = runtimeExceptionMetric(ex);
            throw ex;
        } finally {
            metrics.runtimeOperation("commit", metric.result(), metric.reason(), elapsed(started));
        }
    }

    @Transactional
    public CancelReservationResponseDto cancel(UUID reservationId, CancelReservationRequestDto request) {
        return cancel(reservationId, request, null);
    }

    @Transactional
    public CancelReservationResponseDto cancel(UUID reservationId, CancelReservationRequestDto request, CurrentUser user) {
        return cancel(reservationId, request, user, null);
    }

    @Transactional
    public CancelReservationResponseDto cancel(UUID reservationId, CancelReservationRequestDto request,
                                               CurrentUser user, String correlationId) {
        long started = System.nanoTime();
        RuntimeMetric metric = RuntimeMetric.error();
        try {
            IncentiveReservation reservation = lockReservation(reservationId);
            access.requireKnownApplication(reservation.getTenantId(), reservation.getApplicationId(), user, "cancel");
            access.requireTrustedRuntimeCaller(reservation.getTenantId(), reservation.getApplicationId(), user, "cancel");
            requireProfileAccess(user, reservation.getProfileId(), reservation.getTenantId(), reservation.getApplicationId());
            AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
            String requestHash = hash(Map.of("reservationId", reservationId.toString(), "request", request));
            IdempotencySlot<CancelReservationResponseDto> slot = acquireIdempotency(
                    reservation.getTenantId(),
                    reservation.getApplicationId(),
                    "CANCEL",
                    request.idempotencyKey(),
                    requestHash,
                    CancelReservationResponseDto.class);
            if (slot.replay() != null) {
                metric = new RuntimeMetric("replay", "idempotency_replay");
                return cancelReplay(slot.replay());
            }
            if (reservation.isExpired(Instant.now()) && "RESERVED".equals(reservation.getStatus())) {
                expireReservation(reservation, "reservation expired before cancel", auditMetadata);
                CancelReservationResponseDto response = new CancelReservationResponseDto(
                        false, reservation.getId(), reservation.getStatus(), List.of("RESERVATION_EXPIRED"), false);
                completeIdempotency(slot.key(), response);
                metric = runtimeMetric(false, response.reasonCodes(), false, "cancelled");
                return response;
            }
            if ("CANCELLED".equals(reservation.getStatus()) || "EXPIRED".equals(reservation.getStatus())) {
                CancelReservationResponseDto response = new CancelReservationResponseDto(
                        "CANCELLED".equals(reservation.getStatus()),
                        reservation.getId(),
                        reservation.getStatus(),
                        List.of("CANCELLED".equals(reservation.getStatus()) ? "ALREADY_CANCELLED" : "ALREADY_EXPIRED"),
                        false);
                completeIdempotency(slot.key(), response);
                metric = runtimeMetric(response.cancelled(), response.reasonCodes(), false, "cancelled");
                return response;
            }
            if (!"RESERVED".equals(reservation.getStatus())) {
                throw new ConflictException("Only reserved incentives can be cancelled in Sprint 1");
            }
            releaseQuotas(reservation);
            reservation.cancel(request.reason());
            reservations.save(reservation);
            ledgerEntries.save(new IncentiveLedgerEntry("CANCEL", reservation, null, reservation.getEffectsJson()));
            audit(reservation.getTenantId(), reservation.getApplicationId(), reservation.getId().toString(), "reservation",
                    "reservation.cancelled", actorId(user), request.reason(), Map.of("status", reservation.getStatus()),
                    auditMetadata);
            CancelReservationResponseDto response = new CancelReservationResponseDto(
                    true, reservation.getId(), reservation.getStatus(), List.of("CANCELLED"), false);
            completeIdempotency(slot.key(), response);
            metric = runtimeMetric(true, response.reasonCodes(), false, "cancelled");
            return response;
        } catch (RuntimeException ex) {
            metric = runtimeExceptionMetric(ex);
            throw ex;
        } finally {
            metrics.runtimeOperation("cancel", metric.result(), metric.reason(), elapsed(started));
        }
    }

    @Transactional(readOnly = true)
    public RedemptionDto redemption(UUID redemptionId) {
        return redemption(redemptionId, null);
    }

    @Transactional(readOnly = true)
    public RedemptionDto redemption(UUID redemptionId, CurrentUser user) {
        RedemptionDto redemption = redemptions.findById(redemptionId)
                .map(this::redemptionDto)
                .orElseThrow(() -> new NotFoundException("Redemption not found: " + redemptionId));
        requireProfileAccess(user, redemption.profileId(), redemption.tenantId(), redemption.applicationId());
        return redemption;
    }

    @Transactional(readOnly = true)
    public List<RedemptionDto> listRedemptions(Optional<String> tenantId,
                                               Optional<String> applicationId,
                                               Optional<String> profileId,
                                               Optional<String> externalReference,
                                               Optional<UUID> campaignId,
                                               Optional<UUID> couponId,
                                               Optional<Integer> limit,
                                               CurrentUser user) {
        requireListAccess(tenantId, applicationId, user);
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 200));
        return redemptions.listFiltered(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(profileId.orElse(null)),
                        blankToNull(externalReference.orElse(null)),
                        campaignId.orElse(null),
                        couponId.orElse(null),
                        PageRequest.of(0, pageSize))
                .stream()
                .map(this::redemptionDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public ReservationDto reservation(UUID reservationId, CurrentUser user) {
        Instant now = Instant.now();
        ReservationDto reservation = reservations.findById(reservationId)
                .map(row -> reservationDto(row, now))
                .orElseThrow(() -> new NotFoundException("Reservation not found: " + reservationId));
        access.requireAdminAccess(reservation.tenantId(), reservation.applicationId(), user);
        return reservation;
    }

    @Transactional(readOnly = true)
    public List<ReservationDto> listReservations(Optional<String> tenantId,
                                                 Optional<String> applicationId,
                                                 Optional<String> profileId,
                                                 Optional<String> externalReference,
                                                 Optional<UUID> campaignId,
                                                 Optional<UUID> couponId,
                                                 Optional<String> status,
                                                 Optional<Boolean> expiredOnly,
                                                 Optional<Integer> limit,
                                                 CurrentUser user) {
        requireListAccess(tenantId, applicationId, user);
        int pageSize = Math.max(1, Math.min(limit.orElse(50), 200));
        Instant now = Instant.now();
        return reservations.listFiltered(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(profileId.orElse(null)),
                        blankToNull(externalReference.orElse(null)),
                        campaignId.orElse(null),
                        couponId.orElse(null),
                        normalizeStatus(status.orElse(null)),
                        expiredOnly.orElse(false),
                        now,
                        PageRequest.of(0, pageSize))
                .stream()
                .map(row -> reservationDto(row, now))
                .toList();
    }

    @Transactional
    public ReverseRedemptionResponseDto reverse(UUID redemptionId, ReverseRedemptionRequestDto request,
                                                CurrentUser user) {
        return reverse(redemptionId, request, user, null);
    }

    @Transactional
    public ReverseRedemptionResponseDto reverse(UUID redemptionId, ReverseRedemptionRequestDto request,
                                                CurrentUser user, String correlationId) {
        long started = System.nanoTime();
        RuntimeMetric metric = RuntimeMetric.error();
        try {
            if (request == null) {
                throw new BadRequestException("Reverse redemption request is required");
            }
            IncentiveRedemption redemption = redemptions.lockById(redemptionId)
                    .orElseThrow(() -> new NotFoundException("Redemption not found: " + redemptionId));
            requireReverseAccess(redemption, user);
            access.requireKnownApplication(redemption.getTenantId(), redemption.getApplicationId(), user, "reverse");
            AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
            boolean serviceActor = "service".equalsIgnoreCase(access.actorType(user));
            IncentiveOperationApproval approval = null;
            if (!serviceActor) {
                approval = reversalApprovals.requireApprovedForReverse(redemption, request, user);
            }
            String requestHash = hash(Map.of("redemptionId", redemptionId.toString(), "request", request));
            IdempotencySlot<ReverseRedemptionResponseDto> slot = acquireIdempotency(
                    redemption.getTenantId(),
                    redemption.getApplicationId(),
                    "REVERSE",
                    request.idempotencyKey(),
                    requestHash,
                    ReverseRedemptionResponseDto.class);
            if (slot.replay() != null) {
                metrics.reversal("replay", "IDEMPOTENCY_REPLAY");
                metric = new RuntimeMetric("replay", "idempotency_replay");
                return reverseReplay(slot.replay());
            }
            if ("REVERSED".equals(redemption.getStatus())) {
                ReverseRedemptionResponseDto response = reverseResponse(redemption, false, "ALREADY_REVERSED");
                completeIdempotency(slot.key(), response);
                metrics.reversal("success", "ALREADY_REVERSED");
                metric = runtimeMetric(true, response.reasonCodes(), false, "already_reversed");
                return response;
            }
            if (!"REDEEMED".equals(redemption.getStatus())) {
                throw new ConflictException("Only redeemed incentives can be reversed");
            }
            IncentiveReservation reservation = redemption.getReservationId() == null ? null
                    : reservations.findById(redemption.getReservationId())
                    .orElseThrow(() -> new ConflictException(
                            "Redemption is missing its reservation: " + redemption.getReservationId()));
            if (reservation == null) {
                throw new ConflictException("Redemption is missing its reservation");
            }
            try {
                redemption.reverse(actorId(user));
            } catch (IllegalStateException ex) {
                throw new ConflictException(ex.getMessage());
            }
            IncentiveRedemption saved = redemptions.save(redemption);
            ledgerEntries.save(new IncentiveLedgerEntry("REVERSE", reservation, saved.getId(), saved.getEffectsJson()));
            Map<String, Object> auditPayload = new LinkedHashMap<>();
            auditPayload.put("reservationId", reservation.getId().toString());
            auditPayload.put("campaignId", saved.getCampaignId().toString());
            auditPayload.put("campaignVersion", saved.getCampaignVersion());
            auditPayload.put("quotaPolicy", COMMITTED_REVERSAL_QUOTA_POLICY);
            auditPayload.put("quotaReleased", COMMITTED_REVERSAL_RELEASES_QUOTA);
            if (approval != null) {
                auditPayload.put("approvalId", approval.getId().toString());
                auditPayload.put("approvalStatus", approval.getStatus());
                auditPayload.put("approvalSubjectHash", approval.getSubjectHash());
                auditPayload.put("approvedBy", approval.getApprovedBy());
                auditPayload.put("changeTicket", approval.getChangeTicket());
            }
            audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "redemption",
                    "redemption.reversed", actorId(user), request.reason(), auditPayload, auditMetadata);
            outboxEvents.save(new OutboxEvent(saved.getId(), "incentive-redemption",
                    "incentive.redemption.reversed", toJson(new IncentiveRedemptionReversedEvent(
                    UUID.randomUUID().toString(),
                    1,
                    saved.getTenantId(),
                    saved.getApplicationId(),
                    reservation.getId().toString(),
                    saved.getId().toString(),
                    saved.getCampaignId().toString(),
                    saved.getCampaignVersion(),
                    saved.getCouponId() == null ? null : saved.getCouponId().toString(),
                    saved.getProfileId(),
                    saved.getExternalReference(),
                    auditMetadata.correlationId(),
                    auditMetadata.sourceClientId(),
                    request.reason(),
                    COMMITTED_REVERSAL_RELEASES_QUOTA,
                    eventEffects(saved.getEffectsJson()),
                    saved.getReversedAt(),
                    eventMetadata(auditMetadata, user)))));
            reversalApprovals.markExecuted(approval, actorId(user), saved.getReversedAt(),
                    auditMetadata.correlationId(), auditMetadata.sourceClientId());
            ReverseRedemptionResponseDto response = reverseResponse(saved, false, "REVERSED");
            completeIdempotency(slot.key(), response);
            metrics.reversal("success", "REVERSED");
            metric = runtimeMetric(true, response.reasonCodes(), false, "reversed");
            return response;
        } catch (RuntimeException ex) {
            metric = runtimeExceptionMetric(ex);
            throw ex;
        } finally {
            metrics.runtimeOperation("reverse", metric.result(), metric.reason(), elapsed(started));
        }
    }

    private void requireReverseAccess(IncentiveRedemption redemption, CurrentUser user) {
        if ("service".equalsIgnoreCase(access.actorType(user))) {
            access.requireTrustedRuntimeCaller(redemption.getTenantId(), redemption.getApplicationId(), user, "reverse");
            return;
        }
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
    }

    @Transactional
    public int expireReservedReservations(int batchSize) {
        long started = System.nanoTime();
        String result = "success";
        int count = 0;
        try {
            int limit = Math.max(1, Math.min(batchSize, 500));
            List<IncentiveReservation> expired = reservations.lockExpiredReservedForExpiry(Instant.now(), limit);
            AuditMetadata auditMetadata = AuditMetadata.system("promotion-service/reservation-expiry", "reservation-expiry");
            for (IncentiveReservation reservation : expired) {
                if (expireReservation(reservation, "reservation ttl elapsed", auditMetadata)) {
                    count += 1;
                }
            }
            return count;
        } catch (RuntimeException ex) {
            result = "error";
            throw ex;
        } finally {
            Duration duration = elapsed(started);
            metrics.reservationExpiry(result, count, duration);
            metrics.runtimeOperation("reservation_expiry", result, result, duration);
        }
    }

    private List<Selection> selectCandidates(EvaluateIncentivesRequestDto request,
                                             CouponMatchDiagnostics couponDiagnostics) {
        Instant now = Instant.now();
        List<String> normalizedCodes = request.couponCodes() == null ? List.of() : request.couponCodes().stream()
                .map(CouponCodeNormalizer::normalize)
                .filter(code -> !code.isBlank())
                .distinct()
                .toList();
        List<UUID> couponIds = request.couponIds() == null ? List.of() : request.couponIds().stream()
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        List<Selection> candidates = new ArrayList<>();
        List<? extends CampaignDefinitionSnapshot> activeCampaigns =
                campaignVersions.findActivePublished(request.tenantId(), request.applicationId(), now);
        if (activeCampaigns.isEmpty()) {
            couponDiagnostics.record("no_active_campaign", false);
            couponDiagnostics.recordLookup("no_active_campaign", false);
        }
        for (CampaignDefinitionSnapshot campaign : activeCampaigns) {
            Optional<IncentiveCoupon> coupon = matchCoupon(
                    campaign,
                    normalizedCodes,
                    couponIds,
                    request.profileId(),
                    now,
                    couponDiagnostics);
            if (campaign.isCouponRequired() && coupon.isEmpty()) {
                continue;
            }
            IncentiveDecisionEngine.Decision decision;
            try {
                decision = decisions.decide(campaign, request);
            } catch (IllegalArgumentException ex) {
                continue;
            }
            if (decision.eligible()) {
                candidates.add(new Selection(campaign, coupon.orElse(null), decision));
            }
        }
        return List.copyOf(candidates);
    }

    private Optional<IncentiveCoupon> matchCoupon(CampaignDefinitionSnapshot campaign,
                                                  List<String> normalizedCodes,
                                                  List<UUID> couponIds,
                                                  String profileId,
                                                  Instant now,
                                                  CouponMatchDiagnostics couponDiagnostics) {
        if (normalizedCodes.isEmpty() && couponIds.isEmpty()) {
            couponDiagnostics.record("not_supplied", campaign.isCouponRequired());
            couponDiagnostics.recordLookup("not_supplied", campaign.isCouponRequired());
            return Optional.empty();
        }
        for (UUID couponId : couponIds) {
            Optional<IncentiveCoupon> coupon = coupons.findById(couponId)
                    .filter(found -> campaign.getCampaignId().equals(found.getCampaignId()));
            couponDiagnostics.recordLookup(coupon.isPresent() ? "coupon_id" : "miss", campaign.isCouponRequired());
            if (coupon.isEmpty()) {
                continue;
            }
            String result = couponMatchResult(coupon.get(), profileId, now);
            couponDiagnostics.record(result, campaign.isCouponRequired());
            if ("matched".equals(result)) {
                return coupon;
            }
        }
        boolean foundCodeForCampaign = false;
        for (String code : normalizedCodes) {
            CouponLookup lookup = findCouponByCode(campaign.getCampaignId(), code);
            couponDiagnostics.recordLookup(lookup.storagePath(), campaign.isCouponRequired());
            if (lookup.coupon().isEmpty()) {
                continue;
            }
            foundCodeForCampaign = true;
            String result = couponMatchResult(lookup.coupon().get(), profileId, now);
            couponDiagnostics.record(result, campaign.isCouponRequired());
            if ("matched".equals(result)) {
                return lookup.coupon();
            }
        }
        if (!foundCodeForCampaign) {
            couponDiagnostics.record("not_found", campaign.isCouponRequired());
            couponDiagnostics.recordLookup("miss", campaign.isCouponRequired());
        }
        return Optional.empty();
    }

    private CouponLookup findCouponByCode(UUID campaignId, String normalizedCode) {
        for (CouponCodeFingerprintService.CouponLookupCandidate candidate
                : couponFingerprints.lookupCandidates(normalizedCode)) {
            Optional<IncentiveCoupon> coupon = coupons.findByCampaignIdAndNormalizedCode(
                    campaignId,
                    candidate.fingerprint());
            if (coupon.isPresent()) {
                return new CouponLookup(coupon, candidate.storagePath());
            }
        }
        return new CouponLookup(Optional.empty(), "miss");
    }

    private boolean couponExistsForCode(UUID campaignId, String normalizedCode) {
        return findCouponByCode(campaignId, normalizedCode).coupon().isPresent();
    }

    private String couponMatchResult(IncentiveCoupon coupon, String profileId, Instant now) {
        if (!"ACTIVE".equals(coupon.getStatus())) {
            return "inactive";
        }
        if (coupon.getStartsAt() != null && coupon.getStartsAt().isAfter(now)) {
            return "not_started";
        }
        if (coupon.getExpiresAt() != null && coupon.getExpiresAt().isBefore(now)) {
            return "expired";
        }
        if (coupon.getHolderProfileId() != null && !coupon.getHolderProfileId().equals(profileId)) {
            return "holder_mismatch";
        }
        return "matched";
    }

    private List<QuotaSnapshotEntry> quotaSnapshot(Selection selection, String profileId) {
        CampaignDefinitionSnapshot campaign = selection.campaign();
        List<QuotaSnapshotEntry> snapshot = new ArrayList<>();
        if (campaign.getMaxRedemptions() != null) {
            snapshot.add(new QuotaSnapshotEntry("CAMPAIGN", campaign.getCampaignId().toString(),
                    IncentiveQuotaCounter.WILDCARD_PROFILE, campaign.getMaxRedemptions()));
        }
        if (campaign.getMaxRedemptionsPerProfile() != null) {
            snapshot.add(new QuotaSnapshotEntry("CAMPAIGN_PROFILE", campaign.getCampaignId().toString(),
                    profileId, campaign.getMaxRedemptionsPerProfile()));
        }
        if (selection.coupon() != null && selection.coupon().getMaxRedemptions() != null) {
            snapshot.add(new QuotaSnapshotEntry("COUPON", selection.coupon().getId().toString(),
                    IncentiveQuotaCounter.WILDCARD_PROFILE, selection.coupon().getMaxRedemptions()));
        }
        if (selection.coupon() != null && selection.coupon().getMaxRedemptionsPerProfile() != null) {
            snapshot.add(new QuotaSnapshotEntry("COUPON_PROFILE", selection.coupon().getId().toString(),
                    profileId, selection.coupon().getMaxRedemptionsPerProfile()));
        }
        return List.copyOf(snapshot);
    }

    private StackingAnalysis stackingAnalysis(List<Selection> candidates, Selection selected, String profileId) {
        if (candidates.isEmpty()) {
            return new StackingAnalysis(Map.of());
        }
        Map<Selection, StackingPolicyResult> results = new LinkedHashMap<>();
        for (Selection candidate : candidates) {
            boolean quotaAvailable = quotasAvailable(candidate, profileId);
            StackingPolicyResult result;
            if (!quotaAvailable) {
                result = new StackingPolicyResult(
                        "QUOTA_EXHAUSTED",
                        List.of("QUOTA_EXHAUSTED"),
                        false);
            } else if (candidate == selected) {
                result = new StackingPolicyResult(
                        "SELECTED_PRIMARY",
                        List.of("RUNTIME_SINGLE_WINNER", "STACKING_PRIMARY"),
                        true);
            } else if (selected == null) {
                result = new StackingPolicyResult(
                        "NOT_SELECTED",
                        List.of("NO_PRIMARY_SELECTION"),
                        false);
            } else if (selected.campaign().isExclusive()) {
                result = new StackingPolicyResult(
                        "BLOCKED_BY_EXCLUSIVE_WINNER",
                        List.of("WINNER_EXCLUSIVE"),
                        false);
            } else if (!selected.campaign().isStackable()) {
                result = new StackingPolicyResult(
                        "BLOCKED_BY_PRIMARY_NON_STACKABLE",
                        List.of("WINNER_NOT_STACKABLE"),
                        false);
            } else if (candidate.campaign().isExclusive()) {
                result = new StackingPolicyResult(
                        "BLOCKED_BY_CANDIDATE_EXCLUSIVE",
                        List.of("CANDIDATE_EXCLUSIVE"),
                        false);
            } else if (!candidate.campaign().isStackable()) {
                result = new StackingPolicyResult(
                        "BLOCKED_BY_CANDIDATE_NON_STACKABLE",
                        List.of("CANDIDATE_NOT_STACKABLE"),
                        false);
            } else {
                result = new StackingPolicyResult(
                        "WOULD_STACK",
                        List.of("STACKING_COMPATIBLE", "SIMULATION_ONLY"),
                        true);
            }
            results.put(candidate, result);
        }
        return new StackingAnalysis(results);
    }

    private AdminSimulationCandidateDto simulationCandidateDto(Selection selection,
                                                               String profileId,
                                                               StackingPolicyResult stacking) {
        return new AdminSimulationCandidateDto(
                selection.campaign().getCampaignId(),
                selection.campaign().getCampaignVersion(),
                selection.campaign().getCode(),
                selection.coupon() == null ? null : selection.coupon().getId(),
                true,
                "SELECTED_PRIMARY".equals(stacking.status()),
                selection.campaign().isExclusive(),
                selection.campaign().isStackable(),
                stacking.status(),
                stacking.reasonCodes(),
                selection.decision().effects(),
                selection.decision().reasonCodes(),
                quotaExposure(selection, profileId, stacking.wouldConsumeQuota()));
    }

    private List<AdminSimulationQuotaExposureDto> quotaExposure(Selection selection, String profileId) {
        return quotaExposure(selection, profileId, true);
    }

    private List<AdminSimulationQuotaExposureDto> quotaExposure(Selection selection,
                                                                String profileId,
                                                                boolean wouldConsume) {
        CampaignDefinitionSnapshot campaign = selection.campaign();
        return quotaSnapshot(selection, profileId).stream()
                .map(entry -> quotaExposure(
                        campaign.getTenantId(),
                        campaign.getApplicationId(),
                        entry,
                        wouldConsume))
                .toList();
    }

    private AdminSimulationQuotaExposureDto quotaExposure(String tenantId,
                                                          String applicationId,
                                                          QuotaSnapshotEntry entry,
                                                          boolean wouldConsume) {
        String profileId = entry.profileId() == null || entry.profileId().isBlank()
                ? IncentiveQuotaCounter.WILDCARD_PROFILE
                : entry.profileId();
        int used = quotaCounters.findByTenantIdAndApplicationIdAndScopeTypeAndScopeIdAndProfileId(
                        tenantId,
                        applicationId,
                        entry.scopeType(),
                        entry.scopeId(),
                        profileId)
                .map(IncentiveQuotaCounter::getUsedCount)
                .orElse(0);
        int remaining = Math.max(0, entry.limit() - used);
        boolean available = entry.limit() > 0 && remaining > 0;
        return new AdminSimulationQuotaExposureDto(
                entry.scopeType(),
                entry.scopeId(),
                profileId,
                entry.limit(),
                used,
                remaining,
                available,
                wouldConsume && available);
    }

    private AdminSimulationTotalsDto simulationTotals(EvaluateIncentivesRequestDto request,
                                                      List<IncentiveEffectDto> effects) {
        BigDecimal subtotal = request.transaction() == null || request.transaction().subtotal() == null
                ? BigDecimal.ZERO
                : request.transaction().subtotal();
        BigDecimal shipping = request.transaction() == null || request.transaction().shippingAmount() == null
                ? BigDecimal.ZERO
                : request.transaction().shippingAmount();
        BigDecimal totalDiscount = safeEffects(effects).stream()
                .filter(this::discountEffect)
                .map(effect -> effect.amount() == null ? BigDecimal.ZERO : effect.amount())
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal totalPoints = safeEffects(effects).stream()
                .filter(this::pointsEffect)
                .map(effect -> effect.quantity() == null
                        ? effect.amount() == null ? BigDecimal.ZERO : effect.amount()
                        : effect.quantity())
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal finalAmount = subtotal.add(shipping).subtract(totalDiscount).max(BigDecimal.ZERO);
        return new AdminSimulationTotalsDto(
                money(subtotal),
                money(totalDiscount),
                money(finalAmount),
                request.currency(),
                totalPoints);
    }

    private List<IncentiveEffectDto> safeEffects(List<IncentiveEffectDto> effects) {
        return effects == null ? List.of() : effects;
    }

    private boolean discountEffect(IncentiveEffectDto effect) {
        return "DISCOUNT".equalsIgnoreCase(effect.benefitType())
                || "MONEY".equalsIgnoreCase(effect.unit())
                || effect.currency() != null;
    }

    private boolean pointsEffect(IncentiveEffectDto effect) {
        return "POINTS_EARN_INTENT".equalsIgnoreCase(effect.benefitType())
                || "POINT".equalsIgnoreCase(effect.unit());
    }

    private BigDecimal money(BigDecimal value) {
        return (value == null ? BigDecimal.ZERO : value).setScale(2, java.math.RoundingMode.HALF_UP);
    }

    private ReserveCandidate reserveFirstAvailableCandidate(List<Selection> candidates, String profileId) {
        boolean fallbackAttempted = false;
        for (Selection candidate : candidates) {
            List<QuotaSnapshotEntry> snapshot = quotaSnapshot(candidate, profileId);
            if (tryConsumeQuotas(candidate.campaign(), snapshot)) {
                if (fallbackAttempted) {
                    metrics.quotaReserveFallback("success");
                }
                return new ReserveCandidate(candidate, snapshot);
            }
            fallbackAttempted = true;
            metrics.quotaReserveFallback("candidate_conflict");
        }
        if (fallbackAttempted) {
            metrics.quotaReserveFallback("exhausted");
        }
        return new ReserveCandidate(null, List.of());
    }

    private boolean tryConsumeQuotas(CampaignDefinitionSnapshot campaign, List<QuotaSnapshotEntry> quotaSnapshot) {
        List<QuotaSnapshotEntry> consumed = new ArrayList<>();
        try {
            for (QuotaSnapshotEntry entry : quotaSnapshot) {
                consumeQuota(campaign.getTenantId(), campaign.getApplicationId(), entry.scopeType(),
                        entry.scopeId(), entry.profileId(), entry.limit());
                consumed.add(entry);
            }
            return true;
        } catch (ConflictException ex) {
            releaseQuotas(campaign.getTenantId(), campaign.getApplicationId(), consumed);
            return false;
        }
    }

    private void releaseQuotas(String tenantId, String applicationId, List<QuotaSnapshotEntry> quotaSnapshot) {
        for (QuotaSnapshotEntry entry : quotaSnapshot) {
            releaseQuota(tenantId, applicationId, entry.scopeType(), entry.scopeId(), entry.profileId());
        }
    }

    private boolean quotasAvailable(Selection selection, String profileId) {
        CampaignDefinitionSnapshot campaign = selection.campaign();
        for (QuotaSnapshotEntry entry : quotaSnapshot(selection, profileId)) {
            if (!quotaAvailable(campaign.getTenantId(), campaign.getApplicationId(), entry.scopeType(),
                    entry.scopeId(), entry.profileId(), entry.limit())) {
                return false;
            }
        }
        return true;
    }

    private boolean quotaAvailable(String tenantId, String applicationId, String scopeType, String scopeId,
                                   String profileId, int limit) {
        if (limit <= 0) {
            metrics.quota("exhausted", scopeType);
            return false;
        }
        String normalizedProfileId = profileId == null || profileId.isBlank()
                ? IncentiveQuotaCounter.WILDCARD_PROFILE
                : profileId;
        boolean available = quotaCounters.findByTenantIdAndApplicationIdAndScopeTypeAndScopeIdAndProfileId(
                        tenantId, applicationId, scopeType, scopeId, normalizedProfileId)
                .map(counter -> counter.hasAvailableCapacity(limit))
                .orElse(true);
        metrics.quota(available ? "available" : "exhausted", scopeType);
        return available;
    }

    private void releaseQuotas(IncentiveReservation reservation) {
        List<QuotaSnapshotEntry> snapshot = quotaSnapshot(reservation.getQuotaSnapshotJson());
        if (!snapshot.isEmpty()) {
            for (QuotaSnapshotEntry entry : snapshot) {
                releaseQuota(reservation.getTenantId(), reservation.getApplicationId(), entry.scopeType(),
                        entry.scopeId(), entry.profileId());
            }
            return;
        }
        IncentiveCampaign campaign = campaign(reservation.getCampaignId());
        if (campaign.getMaxRedemptions() != null) {
            releaseQuota(reservation.getTenantId(), reservation.getApplicationId(), "CAMPAIGN",
                    campaign.getId().toString(), IncentiveQuotaCounter.WILDCARD_PROFILE);
        }
        if (campaign.getMaxRedemptionsPerProfile() != null) {
            releaseQuota(reservation.getTenantId(), reservation.getApplicationId(), "CAMPAIGN_PROFILE",
                    campaign.getId().toString(), reservation.getProfileId());
        }
        if (reservation.getCouponId() != null) {
            IncentiveCoupon coupon = coupons.findById(reservation.getCouponId()).orElse(null);
            if (coupon != null && coupon.getMaxRedemptions() != null) {
                releaseQuota(reservation.getTenantId(), reservation.getApplicationId(), "COUPON",
                        coupon.getId().toString(), IncentiveQuotaCounter.WILDCARD_PROFILE);
            }
            if (coupon != null && coupon.getMaxRedemptionsPerProfile() != null) {
                releaseQuota(reservation.getTenantId(), reservation.getApplicationId(), "COUPON_PROFILE",
                        coupon.getId().toString(), reservation.getProfileId());
            }
        }
    }

    private void consumeQuota(String tenantId, String applicationId, String scopeType, String scopeId,
                              String profileId, int limit) {
        if (limit <= 0) {
            metrics.quota("exhausted", scopeType);
            throw new ConflictException("Quota exhausted for " + scopeType);
        }
        String normalizedProfileId = profileId == null || profileId.isBlank()
                ? IncentiveQuotaCounter.WILDCARD_PROFILE
                : profileId;
        quotaCounters.insertIfAbsent(UUID.randomUUID(), tenantId, applicationId, scopeType, scopeId,
                normalizedProfileId, limit);
        int consumed = quotaCounters.tryConsumeIfAvailable(
                tenantId, applicationId, scopeType, scopeId, normalizedProfileId, limit);
        if (consumed != 1) {
            metrics.quota("exhausted", scopeType);
            throw new ConflictException("Quota exhausted for " + scopeType);
        }
        metrics.quota("consumed", scopeType);
    }

    private void releaseQuota(String tenantId, String applicationId, String scopeType, String scopeId,
                              String profileId) {
        Optional<IncentiveQuotaCounter> counter = quotaCounters.lockByScope(
                tenantId, applicationId, scopeType, scopeId, profileId);
        if (counter.isEmpty()) {
            metrics.quota("release_missing", scopeType);
            return;
        }
        counter.ifPresent(value -> {
            value.release();
            quotaCounters.save(value);
            metrics.quota("released", scopeType);
        });
    }

    private boolean expireReservation(IncentiveReservation reservation, String reason, AuditMetadata auditMetadata) {
        if (!"RESERVED".equals(reservation.getStatus())) {
            return false;
        }
        releaseQuotas(reservation);
        reservation.expire(reason);
        reservations.save(reservation);
        ledgerEntries.save(new IncentiveLedgerEntry("EXPIRE", reservation, null, reservation.getEffectsJson()));
        audit(reservation.getTenantId(), reservation.getApplicationId(), reservation.getId().toString(), "reservation",
                "reservation.expired", null, reason, Map.of("status", reservation.getStatus()), auditMetadata);
        return true;
    }

    private <T> IdempotencySlot<T> acquireIdempotency(String tenantId, String applicationId, String operation,
                                                      String idempotencyKey, String requestHash,
                                                      Class<T> responseType) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            metrics.idempotency(operation, "missing_key");
            throw new BadRequestException("Idempotency key is required");
        }
        Instant expiresAt = Instant.now().plus(IDEMPOTENCY_TTL);
        idempotencyKeys.insertInProgressIfAbsent(UUID.randomUUID(), tenantId, applicationId, operation,
                idempotencyKey, requestHash, expiresAt);
        Optional<IncentiveIdempotencyKey> lockedKey = idempotencyKeys.lockByScope(
                tenantId, applicationId, operation, idempotencyKey);
        if (lockedKey.isEmpty()) {
            metrics.idempotency(operation, "acquire_failed");
            throw new ConflictException("Could not acquire idempotency key");
        }
        IncentiveIdempotencyKey key = lockedKey.get();
        if (!key.getRequestHash().equals(requestHash)) {
            metrics.idempotency(operation, "payload_conflict");
            throw new ConflictException("Idempotency key was reused with a different payload");
        }
        if (key.expired(Instant.now())) {
            metrics.idempotency(operation, "expired");
            throw new ConflictException("Idempotency key has expired; use a new key");
        }
        if (key.succeeded()) {
            metrics.idempotency(operation, "replay");
            return new IdempotencySlot<>(key, read(key.getResponseJson(), responseType));
        }
        if (!key.inProgress()) {
            metrics.idempotency(operation, "not_replayable");
            throw new ConflictException("Idempotency key is not replayable");
        }
        metrics.idempotency(operation, "acquired");
        return new IdempotencySlot<>(key, null);
    }

    private void completeIdempotency(IncentiveIdempotencyKey key, Object response) {
        key.complete(toJson(response), Instant.now().plus(IDEMPOTENCY_TTL));
        idempotencyKeys.save(key);
    }

    private ReserveIncentiveResponseDto reserveReplay(ReserveIncentiveResponseDto response) {
        return new ReserveIncentiveResponseDto(
                response.reserved(),
                response.reservationId(),
                response.campaignId(),
                response.campaignVersion(),
                response.couponId(),
                response.expiresAt(),
                response.effects(),
                response.reasonCodes(),
                true);
    }

    private CommitReservationResponseDto commitReplay(CommitReservationResponseDto response) {
        return new CommitReservationResponseDto(
                response.committed(),
                response.reservationId(),
                response.redemptionId(),
                response.campaignId(),
                response.campaignVersion(),
                response.status(),
                response.effects(),
                response.reasonCodes(),
                true);
    }

    private CancelReservationResponseDto cancelReplay(CancelReservationResponseDto response) {
        return new CancelReservationResponseDto(
                response.cancelled(),
                response.reservationId(),
                response.status(),
                response.reasonCodes(),
                true);
    }

    private ReverseRedemptionResponseDto reverseReplay(ReverseRedemptionResponseDto response) {
        return new ReverseRedemptionResponseDto(
                response.reversed(),
                response.redemptionId(),
                response.status(),
                response.effects(),
                response.reasonCodes(),
                true);
    }

    private CommitReservationResponseDto committedResponse(IncentiveReservation reservation, IncentiveRedemption redemption,
                                                           boolean idempotencyReplay, String reasonCode) {
        return new CommitReservationResponseDto(
                true,
                reservation.getId(),
                redemption.getId(),
                reservation.getCampaignId(),
                reservation.getCampaignVersion(),
                redemption.getStatus(),
                effects(redemption.getEffectsJson()),
                List.of(reasonCode),
                idempotencyReplay);
    }

    private ReverseRedemptionResponseDto reverseResponse(IncentiveRedemption redemption,
                                                         boolean idempotencyReplay,
                                                         String reasonCode) {
        return new ReverseRedemptionResponseDto(
                true,
                redemption.getId(),
                redemption.getStatus(),
                effects(redemption.getEffectsJson()),
                List.of(reasonCode),
                idempotencyReplay);
    }

    private String normalizeCouponPrefix(String prefix) {
        String normalized = CouponCodeNormalizer.normalize(prefix);
        if (normalized.length() > 24) {
            throw new BadRequestException("Coupon prefix must be at most 24 characters");
        }
        return normalized;
    }

    private String randomCouponSuffix(int length) {
        StringBuilder builder = new StringBuilder(length);
        for (int i = 0; i < length; i += 1) {
            builder.append(COUPON_ALPHABET.charAt(secureRandom.nextInt(COUPON_ALPHABET.length())));
        }
        return builder.toString();
    }

    private RuntimeMetric runtimeMetric(boolean success, List<String> reasonCodes, boolean couponSupplied,
                                        String successReason) {
        String reason = primaryReason(reasonCodes, successReason);
        if (success) {
            return new RuntimeMetric("success", reason);
        }
        return switch (reason) {
            case "quota_exhausted" -> new RuntimeMetric("quota_exhausted", reason);
            case "reservation_expired", "already_expired" -> new RuntimeMetric("expired", reason);
            case "reservation_cancelled", "already_cancelled", "cancelled" -> new RuntimeMetric("cancelled", reason);
            case "no_eligible_incentive" -> new RuntimeMetric(couponSupplied ? "invalid_coupon" : "no_eligible",
                    couponSupplied ? "invalid_coupon" : reason);
            default -> new RuntimeMetric("conflict", reason);
        };
    }

    private RuntimeMetric runtimeExceptionMetric(RuntimeException ex) {
        if (ex instanceof ForbiddenException) {
            return new RuntimeMetric("forbidden", "forbidden");
        }
        if (ex instanceof BadRequestException) {
            return new RuntimeMetric("bad_request", "bad_request");
        }
        if (ex instanceof ConflictException) {
            return new RuntimeMetric("conflict", "conflict");
        }
        if (ex instanceof NotFoundException) {
            return new RuntimeMetric("not_found", "not_found");
        }
        return RuntimeMetric.error();
    }

    private String primaryReason(List<String> reasonCodes, String fallback) {
        String reason = reasonCodes == null || reasonCodes.isEmpty() ? fallback : reasonCodes.getFirst();
        if (reason == null || reason.isBlank()) {
            return "none";
        }
        return reason.trim().toLowerCase().replaceAll("[^a-z0-9_\\-]", "_");
    }

    private boolean hasCouponSelectors(EvaluateIncentivesRequestDto request) {
        boolean hasCodes = request != null && request.couponCodes() != null
                && request.couponCodes().stream().anyMatch(code -> code != null && !code.isBlank());
        boolean hasIds = request != null && request.couponIds() != null
                && request.couponIds().stream().anyMatch(Objects::nonNull);
        return hasCodes || hasIds;
    }

    private void recordCouponMatch(String operation, CouponMatchDiagnostics diagnostics) {
        metrics.couponMatch(operation, diagnostics.result(), diagnostics.couponSupplied(), diagnostics.couponRequired());
        metrics.couponLookup(
                operation,
                diagnostics.lookupStoragePath(),
                diagnostics.couponSupplied(),
                diagnostics.couponRequired());
    }

    private Duration elapsed(long startedNanos) {
        return Duration.ofNanos(System.nanoTime() - startedNanos);
    }

    private Map<String, Object> previewAuditPayload(Map<String, Object> auditFacts,
                                                    PreviewSimulation simulation,
                                                    String contextHash) {
        EvaluateIncentivesResponseDto decision = simulation.decision();
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("preview", true);
        payload.put("ledgerImpact", false);
        payload.put("contextHash", contextHash);
        payload.put("snapshotVersion", auditFacts.get("snapshotVersion"));
        payload.put("policyId", auditFacts.get("policyId"));
        payload.put("subject", auditFacts.get("subject"));
        payload.put("context", auditFacts.get("context"));
        payload.put("transaction", auditFacts.get("transaction"));
        payload.put("items", auditFacts.get("items"));
        payload.put("attributes", auditFacts.get("attributes"));
        payload.put("coupons", auditFacts.get("coupons"));
        payload.put("eligible", decision.eligible());
        payload.put("campaignId", decision.campaignId() == null ? "" : decision.campaignId().toString());
        payload.put("campaignVersion", decision.campaignVersion() == null ? "" : decision.campaignVersion());
        payload.put("campaignCode", Objects.toString(decision.campaignCode(), ""));
        payload.put("couponId", decision.couponId() == null ? "" : decision.couponId().toString());
        payload.put("reasonCodes", decision.reasonCodes());
        payload.put("totals", simulation.totals());
        payload.put("quotaExposure", simulation.quotaExposure());
        payload.put("candidateCount", simulation.candidates().size());
        return payload;
    }

    private void validateCampaignRequest(CreateCampaignRequestDto request) {
        if (request.startsAt() != null && request.endsAt() != null && !request.startsAt().isBefore(request.endsAt())) {
            throw new BadRequestException("Campaign startsAt must be before endsAt");
        }
        if (request.maxRedemptions() != null && request.maxRedemptions() < 0) {
            throw new BadRequestException("Campaign maxRedemptions must not be negative");
        }
        if (request.maxRedemptionsPerProfile() != null && request.maxRedemptionsPerProfile() < 0) {
            throw new BadRequestException("Campaign maxRedemptionsPerProfile must not be negative");
        }
        if (!"ALL".equalsIgnoreCase(defaultString(request.matchPolicy(), "ALL"))
                && !"ANY".equalsIgnoreCase(request.matchPolicy())) {
            throw new BadRequestException("Campaign matchPolicy must be ALL or ANY");
        }
    }

    private IncentiveCampaign campaign(UUID campaignId) {
        return campaigns.findById(campaignId)
                .orElseThrow(() -> new NotFoundException("Campaign not found: " + campaignId));
    }

    private IncentiveReservation lockReservation(UUID reservationId) {
        return reservations.lockById(reservationId)
                .orElseThrow(() -> new NotFoundException("Reservation not found: " + reservationId));
    }

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, Object payload) {
        audit(tenantId, applicationId, aggregateId, aggregateType, action, actorId, note, payload,
                (AuditMetadata) null);
    }

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, Object payload, AuditMetadata metadata) {
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

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, Object payload,
                       String correlationId, String sourceClientId) {
        audit(tenantId, applicationId, aggregateId, aggregateType, action, actorId, note, payload,
                new AuditMetadata(correlationId, sourceClientId));
    }

    private CampaignDto campaignDto(IncentiveCampaign campaign) {
        return new CampaignDto(
                campaign.getId(),
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getCode(),
                campaign.getName(),
                campaign.getDescription(),
                campaign.getIncentiveType(),
                campaign.getStatus(),
                campaign.getStartsAt(),
                campaign.getEndsAt(),
                campaign.getPriority(),
                campaign.isExclusive(),
                campaign.isStackable(),
                campaign.isCouponRequired(),
                campaign.getMatchPolicy(),
                campaign.getCurrency(),
                decisions.rules(campaign.getRulesJson()),
                decisions.actions(campaign.getActionsJson()),
                campaign.getMaxRedemptions(),
                campaign.getMaxRedemptionsPerProfile(),
                campaign.getCreatedAt(),
                campaign.getUpdatedAt(),
                campaign.getPublishedAt(),
                campaignVersionService.latestVersionNumber(campaign.getId()),
                campaignVersionService.publishedVersionNumber(campaign.getId()));
    }

    private CouponDto couponDto(IncentiveCoupon coupon) {
        return new CouponDto(
                coupon.getId(),
                coupon.getCampaignId(),
                coupon.getCodeMask(),
                null,
                coupon.getCodeMask(),
                coupon.getStatus(),
                coupon.getHolderProfileId(),
                coupon.getStartsAt(),
                coupon.getExpiresAt(),
                coupon.getMaxRedemptions(),
                coupon.getMaxRedemptionsPerProfile(),
                readMap(coupon.getMetadataJson()),
                coupon.getCreatedAt(),
                coupon.getUpdatedAt());
    }

    private LearnerCouponDto learnerCouponDto(IncentiveCoupon coupon, String profileId, Instant now) {
        IncentiveCampaign campaign = campaign(coupon.getCampaignId());
        Optional<IncentiveRedemption> usedRedemption = redemptions.listFiltered(
                        campaign.getTenantId(),
                        campaign.getApplicationId(),
                        profileId,
                        null,
                        campaign.getId(),
                        coupon.getId(),
                        PageRequest.of(0, 5))
                .stream()
                .filter(redemption -> !"REVERSED".equals(redemption.getStatus()))
                .findFirst();
        String walletStatus = learnerCouponStatus(coupon, campaign, usedRedemption.isPresent(), now);
        return new LearnerCouponDto(
                coupon.getId(),
                campaign.getId(),
                campaign.getCode(),
                campaign.getName(),
                coupon.getCodeMask(),
                coupon.getStatus(),
                walletStatus,
                coupon.getStartsAt(),
                coupon.getExpiresAt(),
                usedRedemption.map(IncentiveRedemption::getId).orElse(null),
                usedRedemption.map(IncentiveRedemption::getRedeemedAt).orElse(null),
                learnerCouponMessage(walletStatus));
    }

    private String learnerCouponStatus(IncentiveCoupon coupon,
                                       IncentiveCampaign campaign,
                                       boolean used,
                                       Instant now) {
        if (used) {
            return "USED";
        }
        if (!"ACTIVE".equals(coupon.getStatus())) {
            if ("EXPIRED".equals(coupon.getStatus())) {
                return "EXPIRED";
            }
            return coupon.getStatus();
        }
        if (!"PUBLISHED".equals(campaign.getStatus())) {
            return "UNAVAILABLE";
        }
        if (coupon.getStartsAt() != null && now.isBefore(coupon.getStartsAt())) {
            return "UPCOMING";
        }
        if (campaign.getStartsAt() != null && now.isBefore(campaign.getStartsAt())) {
            return "UPCOMING";
        }
        if (coupon.getExpiresAt() != null && !now.isBefore(coupon.getExpiresAt())) {
            return "EXPIRED";
        }
        if (campaign.getEndsAt() != null && !now.isBefore(campaign.getEndsAt())) {
            return "EXPIRED";
        }
        return "AVAILABLE";
    }

    private String learnerCouponMessage(String walletStatus) {
        return switch (walletStatus) {
            case "AVAILABLE" -> "Coupon can be used for eligible enrollments";
            case "UPCOMING" -> "Coupon is not active yet";
            case "USED" -> "Coupon has already been used";
            case "EXPIRED" -> "Coupon has expired";
            case "PAUSED" -> "Coupon is paused";
            case "VOID" -> "Coupon is void";
            default -> "Coupon is not currently available";
        };
    }

    private RedemptionDto redemptionDto(IncentiveRedemption redemption) {
        return new RedemptionDto(
                redemption.getId(),
                redemption.getReservationId(),
                redemption.getTenantId(),
                redemption.getApplicationId(),
                redemption.getCampaignId(),
                redemption.getCampaignVersion(),
                redemption.getCouponId(),
                redemption.getProfileId(),
                redemption.getExternalReference(),
                redemption.getStatus(),
                effects(redemption.getEffectsJson()),
                redemption.getRedeemedAt(),
                redemption.getReversedAt());
    }

    private ReservationDto reservationDto(IncentiveReservation reservation, Instant now) {
        return new ReservationDto(
                reservation.getId(),
                reservation.getTenantId(),
                reservation.getApplicationId(),
                reservation.getCampaignId(),
                reservation.getCampaignVersion(),
                reservation.getCouponId(),
                reservation.getProfileId(),
                reservation.getExternalReference(),
                reservation.getStatus(),
                effects(reservation.getEffectsJson()),
                quotaSnapshot(reservation.getQuotaSnapshotJson()).stream()
                        .map(this::reservationQuotaSnapshotDto)
                        .toList(),
                reservation.getRequestHash(),
                reservation.getReservedAt(),
                reservation.getExpiresAt(),
                reservation.getCommittedAt(),
                reservation.getCancelledAt(),
                reservation.getFailureReason(),
                "RESERVED".equals(reservation.getStatus())
                        && reservation.getExpiresAt() != null
                        && !reservation.getExpiresAt().isAfter(now));
    }

    private ReservationQuotaSnapshotDto reservationQuotaSnapshotDto(QuotaSnapshotEntry entry) {
        return new ReservationQuotaSnapshotDto(
                entry.scopeType(),
                entry.scopeId(),
                entry.profileId(),
                entry.limit());
    }

    private List<IncentiveEffectDto> effects(String json) {
        try {
            List<IncentiveEffectDto> result = objectMapper.readValue(json, EFFECT_LIST);
            return result == null ? List.of() : result;
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Invalid stored incentive effects", ex);
        }
    }

    private List<IncentiveEffectPayload> eventEffects(String json) {
        return effects(json).stream()
                .map(this::eventEffect)
                .toList();
    }

    private IncentiveEffectPayload eventEffect(IncentiveEffectDto effect) {
        String actionType = firstNonBlank(effect.actionType(), effect.type());
        String benefitType = firstNonBlank(effect.benefitType(), effect.amount() == null ? effect.type() : "DISCOUNT");
        String unit = firstNonBlank(effect.unit(), effect.currency() == null ? null : "MONEY");
        BigDecimal quantity = effect.quantity() == null ? effect.amount() : effect.quantity();
        return new IncentiveEffectPayload(
                firstNonBlank(effect.effectId(), legacyEffectId(effect, actionType)),
                effect.type(),
                benefitType,
                actionType,
                effect.targetType(),
                effect.targetId(),
                effect.amount(),
                effect.currency(),
                unit,
                quantity,
                effect.campaignVersion(),
                effect.metadata());
    }

    private String legacyEffectId(IncentiveEffectDto effect, String actionType) {
        Map<String, Object> metadata = effect.metadata() == null ? Map.of() : effect.metadata();
        String campaignId = Objects.toString(metadata.get("campaignId"), "");
        String campaignVersion = effect.campaignVersion() == null ? Objects.toString(metadata.get("campaignVersion"), "")
                : effect.campaignVersion().toString();
        String targetId = firstNonBlank(effect.targetId(), "order");
        if (!campaignId.isBlank() && !campaignVersion.isBlank()) {
            return String.join(":", campaignId, campaignVersion, firstNonBlank(actionType, effect.type()),
                    firstNonBlank(effect.targetType(), "TARGET"), targetId);
        }
        return String.join(":", "legacy", firstNonBlank(actionType, effect.type()),
                firstNonBlank(effect.targetType(), "TARGET"), targetId);
    }

    private String firstNonBlank(String first, String fallback) {
        return first == null || first.isBlank() ? fallback : first;
    }

    private EventMetadata eventMetadata(AuditMetadata auditMetadata, CurrentUser user) {
        return new EventMetadata(
                auditMetadata.correlationId(),
                null,
                actorId(user),
                Map.of("sourceClientId", Objects.toString(auditMetadata.sourceClientId(), "")));
    }

    private List<QuotaSnapshotEntry> quotaSnapshot(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<QuotaSnapshotEntry> result = objectMapper.readValue(json, QUOTA_SNAPSHOT_LIST);
            return result == null ? List.of() : result;
        } catch (JsonProcessingException ex) {
            return List.of();
        }
    }

    private Map<String, Object> readMap(String json) {
        try {
            return objectMapper.readValue(json, new TypeReference<>() {
            });
        } catch (JsonProcessingException ex) {
            return Map.of();
        }
    }

    private <T> T read(String json, Class<T> type) {
        try {
            return objectMapper.readValue(json, type);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Invalid idempotency response snapshot", ex);
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize incentive payload", ex);
        }
    }

    private String hash(Object value) {
        try {
            byte[] bytes = objectMapper.writer()
                    .with(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS)
                    .writeValueAsBytes(value);
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(bytes));
        } catch (JsonProcessingException | NoSuchAlgorithmException ex) {
            throw new IllegalStateException("Unable to hash incentive request", ex);
        }
    }

    private String hash(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("Unable to hash incentive request", ex);
        }
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }

    private void requireProfileAccess(CurrentUser user, String profileId, String tenantId, String applicationId) {
        if (user == null || user.id() == null) {
            return;
        }
        if (user.hasPlatformRole("ADMIN") || access.canAdminAccess(tenantId, applicationId, user)) {
            return;
        }
        if (profileId != null && profileId.equals(String.valueOf(user.id()))) {
            return;
        }
        throw new ForbiddenException("Not allowed to access another incentive profile");
    }

    private void requireListAccess(Optional<String> tenantId, Optional<String> applicationId, CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant != null && application != null) {
            access.requireAdminAccess(tenant, application, user);
            return;
        }
        access.requirePlatformAdmin(user);
    }

    private String defaultString(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String normalizeStatus(String status) {
        String value = blankToNull(status);
        return value == null ? null : value.toUpperCase();
    }

    private static int couponMatchPriority(String result) {
        return switch (result) {
            case "matched" -> 100;
            case "holder_mismatch" -> 90;
            case "expired" -> 80;
            case "not_started" -> 70;
            case "inactive" -> 60;
            case "not_found" -> 50;
            case "not_supplied" -> 40;
            case "no_active_campaign" -> 30;
            default -> 0;
        };
    }

    private static int couponLookupPriority(String storagePath) {
        return switch (storagePath) {
            case "current_hmac" -> 100;
            case "previous_hmac" -> 90;
            case "legacy_sha" -> 80;
            case "legacy_raw" -> 70;
            case "coupon_id" -> 65;
            case "miss" -> 50;
            case "not_supplied" -> 40;
            case "no_active_campaign" -> 30;
            default -> 0;
        };
    }

    private static final class CouponMatchDiagnostics {
        private final boolean couponSupplied;
        private String result;
        private boolean couponRequired;
        private String lookupStoragePath;

        private CouponMatchDiagnostics(boolean couponSupplied) {
            this.couponSupplied = couponSupplied;
        }

        static CouponMatchDiagnostics forRequest(EvaluateIncentivesRequestDto request) {
            boolean suppliedByCode = request != null
                    && request.couponCodes() != null
                    && request.couponCodes().stream().anyMatch(code -> code != null && !code.isBlank());
            boolean suppliedById = request != null
                    && request.couponIds() != null
                    && request.couponIds().stream().anyMatch(Objects::nonNull);
            return new CouponMatchDiagnostics(suppliedByCode || suppliedById);
        }

        void record(String nextResult, boolean nextCouponRequired) {
            if (nextResult == null || nextResult.isBlank()) {
                return;
            }
            if (result == null || couponMatchPriority(nextResult) > couponMatchPriority(result)
                    || (couponMatchPriority(nextResult) == couponMatchPriority(result) && nextCouponRequired)) {
                result = nextResult;
                couponRequired = nextCouponRequired;
            }
        }

        void recordLookup(String nextStoragePath, boolean nextCouponRequired) {
            if (nextStoragePath == null || nextStoragePath.isBlank()) {
                return;
            }
            if (lookupStoragePath == null
                    || couponLookupPriority(nextStoragePath) > couponLookupPriority(lookupStoragePath)
                    || (couponLookupPriority(nextStoragePath) == couponLookupPriority(lookupStoragePath)
                    && nextCouponRequired)) {
                lookupStoragePath = nextStoragePath;
                couponRequired = nextCouponRequired;
            }
        }

        String result() {
            if (result != null) {
                return result;
            }
            return couponSupplied ? "not_found" : "not_supplied";
        }

        String lookupStoragePath() {
            if (lookupStoragePath != null) {
                return lookupStoragePath;
            }
            return couponSupplied ? "miss" : "not_supplied";
        }

        boolean couponSupplied() {
            return couponSupplied;
        }

        boolean couponRequired() {
            return couponRequired;
        }
    }

    private record Selection(CampaignDefinitionSnapshot campaign, IncentiveCoupon coupon,
                             IncentiveDecisionEngine.Decision decision) {
    }

    private record ReserveCandidate(Selection selection, List<QuotaSnapshotEntry> quotaSnapshot) {
    }

    private record CouponLookup(Optional<IncentiveCoupon> coupon, String storagePath) {
    }

    private record IdempotencySlot<T>(IncentiveIdempotencyKey key, T replay) {
    }

    private record RuntimeMetric(String result, String reason) {
        static RuntimeMetric error() {
            return new RuntimeMetric("error", "error");
        }
    }

    private record StackingPolicyResult(String status, List<String> reasonCodes, boolean wouldConsumeQuota) {
    }

    private record StackingAnalysis(Map<Selection, StackingPolicyResult> results) {
        StackingPolicyResult result(Selection selection) {
            return results.getOrDefault(
                    selection,
                    new StackingPolicyResult("NOT_SELECTED", List.of("NO_STACKING_ANALYSIS"), false));
        }
    }

    private record PreviewSimulation(EvaluateIncentivesResponseDto decision,
                                     AdminSimulationTotalsDto totals,
                                     List<AdminSimulationQuotaExposureDto> quotaExposure,
                                     List<AdminSimulationCandidateDto> candidates) {
    }

    private record QuotaSnapshotEntry(String scopeType, String scopeId, String profileId, int limit) {
    }
}
