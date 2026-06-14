package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDetailDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDiffDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDiffEntryDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionReviewQueueItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionReviewQueueResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionTransitionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionValidationDto;
import edu.courseflow.promotion.dto.PromotionDtos.RollbackCampaignVersionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCampaignVersionDraftRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ValidationMessageDto;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCampaignVersion;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignVersionRepository;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CampaignVersionService {

    private final IncentiveCampaignRepository campaigns;
    private final IncentiveCampaignVersionRepository campaignVersions;
    private final IncentiveAuditEventRepository auditEvents;
    private final IncentiveAccessService access;
    private final IncentiveDecisionEngine decisions;
    private final PromotionLoyaltyReadinessClient loyaltyReadiness;
    private final ObjectMapper objectMapper;
    private final IncentiveMetrics metrics;

    public CampaignVersionService(IncentiveCampaignRepository campaigns,
                                  IncentiveCampaignVersionRepository campaignVersions,
                                  IncentiveAuditEventRepository auditEvents,
                                  IncentiveAccessService access,
                                  IncentiveDecisionEngine decisions,
                                  PromotionLoyaltyReadinessClient loyaltyReadiness,
                                  ObjectMapper objectMapper,
                                  IncentiveMetrics metrics) {
        this.campaigns = campaigns;
        this.campaignVersions = campaignVersions;
        this.auditEvents = auditEvents;
        this.access = access;
        this.decisions = decisions;
        this.loyaltyReadiness = loyaltyReadiness;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
    }

    @Transactional(readOnly = true)
    public List<CampaignVersionDto> listVersions(UUID campaignId, CurrentUser user) {
        IncentiveCampaign campaign = campaign(campaignId);
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        return campaignVersions.findByCampaignIdOrderByVersionNumberDesc(campaignId)
                .stream()
                .map(this::versionDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public CampaignVersionDetailDto detail(UUID campaignId, int versionNumber, CurrentUser user) {
        IncentiveCampaignVersion version = version(campaignId, versionNumber);
        access.requireReviewAccess(version.getTenantId(), version.getApplicationId(), user);
        return detailDto(version);
    }

    @Transactional(readOnly = true)
    public CampaignVersionReviewQueueResponseDto reviewQueue(String tenantId,
                                                             String applicationId,
                                                             String status,
                                                             Integer limit,
                                                             CurrentUser user) {
        String normalizedTenant = trimToNull(tenantId);
        String normalizedApplication = trimToNull(applicationId);
        if (normalizedTenant != null && normalizedApplication != null) {
            access.requireReviewAccess(normalizedTenant, normalizedApplication, user);
        } else {
            access.requirePlatformAdmin(user);
        }
        String normalizedStatus = trimToNull(status);
        if (normalizedStatus != null) {
            normalizedStatus = normalizedStatus.toUpperCase();
        }
        int pageSize = Math.max(1, Math.min(limit == null ? 50 : limit, 200));
        List<IncentiveCampaignVersion> rows = campaignVersions.reviewQueue(
                normalizedTenant,
                normalizedApplication,
                normalizedStatus,
                org.springframework.data.domain.PageRequest.of(0, pageSize + 1));
        boolean hasMore = rows.size() > pageSize;
        List<CampaignVersionReviewQueueItemDto> items = rows.stream()
                .limit(pageSize)
                .map(this::reviewQueueItem)
                .toList();
        return new CampaignVersionReviewQueueResponseDto(items, pageSize, hasMore);
    }

    @Transactional
    public CampaignVersionDto createDraftVersion(UUID campaignId, CurrentUser user) {
        return createDraftVersion(campaignId, user, null);
    }

    @Transactional
    public CampaignVersionDto createDraftVersion(UUID campaignId, CurrentUser user, String correlationId) {
        IncentiveCampaign campaign = campaign(campaignId);
        access.requireAdminAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
        access.requireClientOperation(campaign.getTenantId(), campaign.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        IncentiveCampaignVersion saved = campaignVersions.save(createDraftVersion(campaign, actorId(user)));
        audit(saved, "campaign_version.created", actorId(user), null, auditMetadata);
        metrics.versionTransition("created", "success");
        return versionDto(saved);
    }

    @Transactional
    public IncentiveCampaignVersion createInitialDraft(IncentiveCampaign campaign, String actorId) {
        return campaignVersions.save(createDraftVersion(campaign, actorId));
    }

    @Transactional
    public CampaignVersionDetailDto updateDraft(UUID campaignId, int versionNumber,
                                                UpdateCampaignVersionDraftRequestDto request,
                                                CurrentUser user) {
        return updateDraft(campaignId, versionNumber, request, user, null);
    }

    @Transactional
    public CampaignVersionDetailDto updateDraft(UUID campaignId, int versionNumber,
                                                UpdateCampaignVersionDraftRequestDto request,
                                                CurrentUser user,
                                                String correlationId) {
        if (request == null) {
            throw new BadRequestException("Campaign version patch is required");
        }
        IncentiveCampaignVersion version = lockVersion(campaignId, versionNumber);
        access.requireAdminAccess(version.getTenantId(), version.getApplicationId(), user);
        access.requireClientOperation(version.getTenantId(), version.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        validatePatch(version, request);
        String rulesJson = request.rules() == null ? null : toRulesJson(request.rules());
        String actionsJson = request.actions() == null ? null : toActionsJson(request.actions());
        try {
            version.updateDraft(
                    trimToNull(request.code()),
                    trimToNull(request.name()),
                    request.description(),
                    trimToNull(request.incentiveType()),
                    request.startsAt(),
                    request.endsAt(),
                    request.priority(),
                    request.exclusive(),
                    request.stackable(),
                    request.couponRequired(),
                    normalizeMatchPolicy(request.matchPolicy()),
                    trimToNull(request.currency()),
                    rulesJson,
                    actionsJson,
                    request.maxRedemptions(),
                    request.maxRedemptionsPerProfile());
        } catch (IllegalStateException ex) {
            throw new ConflictException(ex.getMessage());
        }
        IncentiveCampaignVersion saved = campaignVersions.save(version);
        audit(saved, "campaign_version.draft_updated", actorId(user), null, Map.of(
                "campaignId", saved.getCampaignId().toString(),
                "campaignVersion", saved.getVersionNumber()), auditMetadata);
        metrics.versionTransition("draft_updated", "success");
        return detailDto(saved);
    }

    @Transactional(readOnly = true)
    public CampaignVersionValidationDto validation(UUID campaignId, int versionNumber, CurrentUser user) {
        IncentiveCampaignVersion version = version(campaignId, versionNumber);
        access.requireReviewAccess(version.getTenantId(), version.getApplicationId(), user);
        return validationDto(version);
    }

    @Transactional(readOnly = true)
    public CampaignVersionDiffDto diff(UUID campaignId, int leftVersion, int rightVersion, CurrentUser user) {
        IncentiveCampaignVersion left = version(campaignId, leftVersion);
        IncentiveCampaignVersion right = version(campaignId, rightVersion);
        access.requireReviewAccess(left.getTenantId(), left.getApplicationId(), user);
        if (!Objects.equals(left.getTenantId(), right.getTenantId())
                || !Objects.equals(left.getApplicationId(), right.getApplicationId())) {
            throw new ConflictException("Campaign versions are not in the same tenant/application scope");
        }
        List<CampaignVersionDiffEntryDto> changes = new ArrayList<>();
        diff(changes, "code", left.getCode(), right.getCode());
        diff(changes, "name", left.getName(), right.getName());
        diff(changes, "description", left.getDescription(), right.getDescription());
        diff(changes, "incentiveType", left.getIncentiveType(), right.getIncentiveType());
        diff(changes, "startsAt", left.getStartsAt(), right.getStartsAt());
        diff(changes, "endsAt", left.getEndsAt(), right.getEndsAt());
        diff(changes, "priority", left.getPriority(), right.getPriority());
        diff(changes, "exclusive", left.isExclusive(), right.isExclusive());
        diff(changes, "stackable", left.isStackable(), right.isStackable());
        diff(changes, "couponRequired", left.isCouponRequired(), right.isCouponRequired());
        diff(changes, "matchPolicy", left.getMatchPolicy(), right.getMatchPolicy());
        diff(changes, "currency", left.getCurrency(), right.getCurrency());
        diff(changes, "rules", canonicalJson(left.getRulesJson()), canonicalJson(right.getRulesJson()));
        diff(changes, "actions", canonicalJson(left.getActionsJson()), canonicalJson(right.getActionsJson()));
        diff(changes, "maxRedemptions", left.getMaxRedemptions(), right.getMaxRedemptions());
        diff(changes, "maxRedemptionsPerProfile",
                left.getMaxRedemptionsPerProfile(), right.getMaxRedemptionsPerProfile());
        return new CampaignVersionDiffDto(campaignId, leftVersion, rightVersion, List.copyOf(changes));
    }

    @Transactional
    public CampaignVersionDetailDto rollback(UUID campaignId, int versionNumber,
                                             RollbackCampaignVersionRequestDto request,
                                             CurrentUser user) {
        return rollback(campaignId, versionNumber, request, user, null);
    }

    @Transactional
    public CampaignVersionDetailDto rollback(UUID campaignId, int versionNumber,
                                             RollbackCampaignVersionRequestDto request,
                                             CurrentUser user,
        String correlationId) {
        IncentiveCampaignVersion source = version(campaignId, versionNumber);
        access.requireAdminAccess(source.getTenantId(), source.getApplicationId(), user);
        access.requireClientOperation(source.getTenantId(), source.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        if (!"PUBLISHED".equals(source.getVersionStatus()) && !"SUPERSEDED".equals(source.getVersionStatus())) {
            throw new ConflictException("Only published or superseded campaign versions can be rolled back");
        }
        int nextVersion = nextVersionNumber(campaignId);
        IncentiveCampaignVersion rollbackDraft = new IncentiveCampaignVersion(source, nextVersion, actorId(user));
        IncentiveCampaignVersion saved = campaignVersions.save(rollbackDraft);
        audit(saved, "campaign_version.rollback_draft_created", actorId(user),
                request == null ? null : request.note(), Map.of(
                        "campaignId", saved.getCampaignId().toString(),
                        "campaignVersion", saved.getVersionNumber(),
                        "rollbackSourceVersion", source.getVersionNumber()), auditMetadata);
        metrics.versionTransition("rollback_draft_created", "success");
        return detailDto(saved);
    }

    @Transactional
    public CampaignVersionDto submit(UUID campaignId, int versionNumber,
                                     CampaignVersionTransitionRequestDto request,
                                     CurrentUser user) {
        return submit(campaignId, versionNumber, request, user, null);
    }

    @Transactional
    public CampaignVersionDto submit(UUID campaignId, int versionNumber,
                                     CampaignVersionTransitionRequestDto request,
                                     CurrentUser user,
        String correlationId) {
        IncentiveCampaignVersion version = version(campaignId, versionNumber);
        access.requireAdminAccess(version.getTenantId(), version.getApplicationId(), user);
        access.requireClientOperation(version.getTenantId(), version.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        try {
            version.submit(actorId(user), request == null ? null : request.note());
        } catch (IllegalStateException ex) {
            throw new ConflictException(ex.getMessage());
        }
        IncentiveCampaignVersion saved = campaignVersions.save(version);
        audit(saved, "campaign_version.submitted", actorId(user), request == null ? null : request.note(),
                auditMetadata);
        metrics.versionTransition("submitted", "success");
        return versionDto(saved);
    }

    @Transactional
    public CampaignVersionDto approve(UUID campaignId, int versionNumber,
                                      CampaignVersionTransitionRequestDto request,
                                      CurrentUser user) {
        return approve(campaignId, versionNumber, request, user, null);
    }

    @Transactional
    public CampaignVersionDto approve(UUID campaignId, int versionNumber,
                                      CampaignVersionTransitionRequestDto request,
                                      CurrentUser user,
        String correlationId) {
        IncentiveCampaignVersion version = version(campaignId, versionNumber);
        access.requireReviewAccess(version.getTenantId(), version.getApplicationId(), user);
        access.requireClientOperation(version.getTenantId(), version.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        try {
            version.approve(actorId(user), request == null ? null : request.note());
        } catch (IllegalStateException ex) {
            throw new ConflictException(ex.getMessage());
        }
        IncentiveCampaignVersion saved = campaignVersions.save(version);
        audit(saved, "campaign_version.approved", actorId(user), request == null ? null : request.note(),
                auditMetadata);
        metrics.versionTransition("approved", "success");
        return versionDto(saved);
    }

    @Transactional
    public CampaignVersionDto reject(UUID campaignId, int versionNumber,
                                     CampaignVersionTransitionRequestDto request,
                                     CurrentUser user) {
        return reject(campaignId, versionNumber, request, user, null);
    }

    @Transactional
    public CampaignVersionDto reject(UUID campaignId, int versionNumber,
                                     CampaignVersionTransitionRequestDto request,
                                     CurrentUser user,
        String correlationId) {
        IncentiveCampaignVersion version = version(campaignId, versionNumber);
        access.requireReviewAccess(version.getTenantId(), version.getApplicationId(), user);
        access.requireClientOperation(version.getTenantId(), version.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        try {
            version.reject(actorId(user), request == null ? null : request.note());
        } catch (IllegalStateException ex) {
            throw new ConflictException(ex.getMessage());
        }
        IncentiveCampaignVersion saved = campaignVersions.save(version);
        audit(saved, "campaign_version.rejected", actorId(user), request == null ? null : request.note(),
                auditMetadata);
        metrics.versionTransition("rejected", "success");
        return versionDto(saved);
    }

    @Transactional
    public CampaignVersionDto publish(UUID campaignId, int versionNumber,
                                      CampaignVersionTransitionRequestDto request,
                                      CurrentUser user) {
        return publish(campaignId, versionNumber, request, user, null);
    }

    @Transactional
    public CampaignVersionDto publish(UUID campaignId, int versionNumber,
                                      CampaignVersionTransitionRequestDto request,
                                      CurrentUser user,
                                      String correlationId) {
        IncentiveCampaignVersion version = lockVersion(campaignId, versionNumber);
        IncentiveCampaign campaign = campaign(campaignId);
        access.requireAdminAccess(version.getTenantId(), version.getApplicationId(), user);
        access.requireClientOperation(version.getTenantId(), version.getApplicationId(), user, "admin");
        AuditMetadata auditMetadata = AuditMetadata.from(user, access, correlationId);
        enforcePublishable(version);
        try {
            campaignVersions.deactivateActiveSnapshots(campaignId);
            version.publish(actorId(user));
        } catch (IllegalStateException ex) {
            throw new ConflictException(ex.getMessage());
        }
        campaign.publishFrom(version);
        campaigns.save(campaign);
        IncentiveCampaignVersion saved = campaignVersions.save(version);
        audit(saved, "campaign_version.published", actorId(user), request == null ? null : request.note(),
                auditMetadata);
        metrics.versionTransition("published", "success");
        return versionDto(saved);
    }

    @Transactional
    public void deactivateActiveSnapshot(UUID campaignId) {
        campaignVersions.deactivateActiveSnapshotOnly(campaignId);
    }

    @Transactional(readOnly = true)
    public Integer latestVersionNumber(UUID campaignId) {
        return campaignVersions.findByCampaignIdOrderByVersionNumberDesc(campaignId)
                .stream()
                .findFirst()
                .map(IncentiveCampaignVersion::getVersionNumber)
                .orElse(null);
    }

    @Transactional(readOnly = true)
    public Integer publishedVersionNumber(UUID campaignId) {
        return campaignVersions.findFirstByCampaignIdAndActiveSnapshotTrue(campaignId)
                .map(IncentiveCampaignVersion::getVersionNumber)
                .orElse(null);
    }

    private IncentiveCampaignVersion createDraftVersion(IncentiveCampaign campaign, String actorId) {
        return new IncentiveCampaignVersion(campaign, nextVersionNumber(campaign.getId()), actorId);
    }

    private int nextVersionNumber(UUID campaignId) {
        Integer latest = latestVersionNumber(campaignId);
        return latest == null ? 1 : latest + 1;
    }

    private void enforcePublishable(IncentiveCampaignVersion version) {
        List<ValidationMessageDto> blockers = validateSnapshot(version);
        if (!blockers.isEmpty()) {
            throw new BadRequestException("Campaign version is not publishable: " + blockers.getFirst().message());
        }
    }

    private List<ValidationMessageDto> validateSnapshot(IncentiveCampaignVersion version) {
        List<ValidationMessageDto> blockers = new ArrayList<>();
        if (version.getStartsAt() != null && version.getEndsAt() != null
                && !version.getStartsAt().isBefore(version.getEndsAt())) {
            blockers.add(blocker("INVALID_DATE_WINDOW", "startsAt", "Campaign startsAt must be before endsAt"));
        }
        if (version.getMaxRedemptions() != null && version.getMaxRedemptions() < 0) {
            blockers.add(blocker("INVALID_QUOTA", "maxRedemptions", "Campaign maxRedemptions must not be negative"));
        }
        if (version.getMaxRedemptionsPerProfile() != null && version.getMaxRedemptionsPerProfile() < 0) {
            blockers.add(blocker("INVALID_QUOTA", "maxRedemptionsPerProfile",
                    "Campaign maxRedemptionsPerProfile must not be negative"));
        }
        if (!"ALL".equalsIgnoreCase(version.getMatchPolicy()) && !"ANY".equalsIgnoreCase(version.getMatchPolicy())) {
            blockers.add(blocker("INVALID_MATCH_POLICY", "matchPolicy", "Campaign matchPolicy must be ALL or ANY"));
        }
        try {
            decisions.validateRules(decisions.rules(version.getRulesJson()));
        } catch (IllegalArgumentException ex) {
            blockers.add(blocker("INVALID_RULES", "rules", ex.getMessage()));
        }
        List<ActionSpecDto> actions = List.of();
        boolean validActions = true;
        try {
            actions = decisions.actions(version.getActionsJson());
            decisions.validateActions(actions);
        } catch (IllegalArgumentException ex) {
            blockers.add(blocker("INVALID_ACTIONS", "actions", ex.getMessage()));
            validActions = false;
        }
        if (validActions) {
            validateLoyaltyReadiness(version, actions, blockers);
        }
        return List.copyOf(blockers);
    }

    private void validateLoyaltyReadiness(
            IncentiveCampaignVersion version,
            List<ActionSpecDto> actions,
            List<ValidationMessageDto> blockers) {
        for (int index = 0; index < actions.size(); index++) {
            ActionSpecDto action = actions.get(index);
            if (!"LOYALTY_POINTS_EARN".equalsIgnoreCase(action.type())) {
                continue;
            }
            String programId = actionParameter(action, "programId");
            PromotionLoyaltyReadinessClient.LoyaltyReadinessResult readiness =
                    loyaltyReadiness.checkEarnReadiness(version.getTenantId(), version.getApplicationId(), programId);
            if (!readiness.ready()) {
                String reason = readiness.blockers().isEmpty()
                        ? "LOYALTY_PROGRAM_NOT_READY"
                        : String.join(",", readiness.blockers());
                blockers.add(blocker(
                        "LOYALTY_PROGRAM_NOT_READY",
                        "actions[" + index + "].parameters.programId",
                        "Loyalty program " + programId + " is not ready for earn: " + reason));
            }
        }
    }

    private CampaignVersionValidationDto validationDto(IncentiveCampaignVersion version) {
        List<ValidationMessageDto> blockers = validateSnapshot(version);
        List<ValidationMessageDto> warnings = new ArrayList<>();
        if (version.getStartsAt() == null) {
            warnings.add(warning("MISSING_START_WINDOW", "startsAt", "Campaign has no start window"));
        }
        if (version.getEndsAt() == null) {
            warnings.add(warning("MISSING_END_WINDOW", "endsAt", "Campaign has no end window"));
        }
        if (version.getMaxRedemptions() == null && version.getMaxRedemptionsPerProfile() == null) {
            warnings.add(warning("UNBOUNDED_CAMPAIGN_QUOTA", "maxRedemptions",
                    "Campaign has no campaign quota limit"));
        }
        return new CampaignVersionValidationDto(
                version.getCampaignId(),
                version.getVersionNumber(),
                blockers.isEmpty(),
                blockers,
                List.copyOf(warnings));
    }

    private CampaignVersionReviewQueueItemDto reviewQueueItem(IncentiveCampaignVersion version) {
        CampaignVersionValidationDto validation = validationDto(version);
        return new CampaignVersionReviewQueueItemDto(
                versionDto(version),
                version.getTenantId(),
                version.getApplicationId(),
                version.getCode(),
                version.getName(),
                validation.blockers().size(),
                validation.warnings().size(),
                validation.publishable());
    }

    private void validatePatch(IncentiveCampaignVersion version, UpdateCampaignVersionDraftRequestDto request) {
        Instant startsAt = request.startsAt() == null ? version.getStartsAt() : request.startsAt();
        Instant endsAt = request.endsAt() == null ? version.getEndsAt() : request.endsAt();
        if (startsAt != null && endsAt != null && !startsAt.isBefore(endsAt)) {
            throw new BadRequestException("Campaign startsAt must be before endsAt");
        }
        if (request.code() != null && trimToNull(request.code()) == null) {
            throw new BadRequestException("Campaign code must not be blank");
        }
        if (request.name() != null && trimToNull(request.name()) == null) {
            throw new BadRequestException("Campaign name must not be blank");
        }
        if (request.maxRedemptions() != null && request.maxRedemptions() < 0) {
            throw new BadRequestException("Campaign maxRedemptions must not be negative");
        }
        if (request.maxRedemptionsPerProfile() != null && request.maxRedemptionsPerProfile() < 0) {
            throw new BadRequestException("Campaign maxRedemptionsPerProfile must not be negative");
        }
        normalizeMatchPolicy(request.matchPolicy());
    }

    private String toRulesJson(List<edu.courseflow.promotion.dto.PromotionDtos.RuleSpecDto> rules) {
        try {
            return decisions.toRulesJson(rules);
        } catch (IllegalArgumentException ex) {
            throw new BadRequestException(ex.getMessage());
        }
    }

    private String toActionsJson(List<edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto> actions) {
        try {
            return decisions.toActionsJson(actions);
        } catch (IllegalArgumentException ex) {
            throw new BadRequestException(ex.getMessage());
        }
    }

    private IncentiveCampaign campaign(UUID campaignId) {
        return campaigns.findById(campaignId)
                .orElseThrow(() -> new NotFoundException("Campaign not found: " + campaignId));
    }

    private IncentiveCampaignVersion version(UUID campaignId, int versionNumber) {
        return campaignVersions.findByCampaignIdAndVersionNumber(campaignId, versionNumber)
                .orElseThrow(() -> new NotFoundException(
                        "Campaign version not found: " + campaignId + "/" + versionNumber));
    }

    private IncentiveCampaignVersion lockVersion(UUID campaignId, int versionNumber) {
        return campaignVersions.lockByCampaignIdAndVersionNumber(campaignId, versionNumber)
                .orElseThrow(() -> new NotFoundException(
                        "Campaign version not found: " + campaignId + "/" + versionNumber));
    }

    private void audit(IncentiveCampaignVersion version, String action, String actorId, String note) {
        audit(version, action, actorId, note, Map.of(
                "campaignId", version.getCampaignId().toString(),
                "campaignVersion", version.getVersionNumber(),
                "versionStatus", version.getVersionStatus()), null);
    }

    private void audit(IncentiveCampaignVersion version, String action, String actorId, String note,
                       AuditMetadata metadata) {
        audit(version, action, actorId, note, Map.of(
                "campaignId", version.getCampaignId().toString(),
                "campaignVersion", version.getVersionNumber(),
                "versionStatus", version.getVersionStatus()), metadata);
    }

    private void audit(IncentiveCampaignVersion version, String action, String actorId, String note,
                       Object payload) {
        audit(version, action, actorId, note, payload, null);
    }

    private void audit(IncentiveCampaignVersion version, String action, String actorId, String note,
                       Object payload, AuditMetadata metadata) {
        auditEvents.save(new IncentiveAuditEvent(
                version.getTenantId(),
                version.getApplicationId(),
                version.getCampaignId().toString(),
                "campaign-version",
                action,
                actorId,
                note,
                toJson(payload),
                metadata == null ? null : metadata.correlationId(),
                metadata == null ? null : metadata.sourceClientId()));
    }

    public CampaignVersionDto versionDto(IncentiveCampaignVersion version) {
        return new CampaignVersionDto(
                version.getId(),
                version.getCampaignId(),
                version.getVersionNumber(),
                version.getVersionStatus(),
                version.isActiveSnapshot(),
                version.getCreatedBy(),
                version.getSubmittedBy(),
                version.getReviewedBy(),
                version.getPublishedBy(),
                version.getReviewNote(),
                version.getCreatedAt(),
                version.getSubmittedAt(),
                version.getReviewedAt(),
                version.getPublishedAt());
    }

    public CampaignVersionDetailDto detailDto(IncentiveCampaignVersion version) {
        return new CampaignVersionDetailDto(
                version.getId(),
                version.getCampaignId(),
                version.getVersionNumber(),
                version.getVersionStatus(),
                version.isActiveSnapshot(),
                version.getTenantId(),
                version.getApplicationId(),
                version.getCode(),
                version.getName(),
                version.getDescription(),
                version.getIncentiveType(),
                version.getStartsAt(),
                version.getEndsAt(),
                version.getPriority(),
                version.isExclusive(),
                version.isStackable(),
                version.isCouponRequired(),
                version.getMatchPolicy(),
                version.getCurrency(),
                decisions.rules(version.getRulesJson()),
                decisions.actions(version.getActionsJson()),
                version.getMaxRedemptions(),
                version.getMaxRedemptionsPerProfile(),
                version.getRollbackSourceVersion(),
                version.getCreatedBy(),
                version.getSubmittedBy(),
                version.getReviewedBy(),
                version.getPublishedBy(),
                version.getReviewNote(),
                version.getCreatedAt(),
                version.getSubmittedAt(),
                version.getReviewedAt(),
                version.getPublishedAt());
    }

    private void diff(List<CampaignVersionDiffEntryDto> changes, String field, Object left, Object right) {
        if (!Objects.equals(left, right)) {
            changes.add(new CampaignVersionDiffEntryDto(field, left, right));
        }
    }

    private Object canonicalJson(String json) {
        try {
            return objectMapper.readTree(json == null || json.isBlank() ? "null" : json);
        } catch (JsonProcessingException ex) {
            return json;
        }
    }

    private String actionParameter(ActionSpecDto action, String key) {
        Object value = action.parameters() == null ? null : action.parameters().get(key);
        return value == null ? "" : String.valueOf(value).trim();
    }

    private ValidationMessageDto blocker(String code, String field, String message) {
        return new ValidationMessageDto("BLOCKER", code, field, message);
    }

    private ValidationMessageDto warning(String code, String field, String message) {
        return new ValidationMessageDto("WARNING", code, field, message);
    }

    private String normalizeMatchPolicy(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim().toUpperCase();
        if (!"ALL".equals(normalized) && !"ANY".equals(normalized)) {
            throw new BadRequestException("Campaign matchPolicy must be ALL or ANY");
        }
        return normalized;
    }

    private String trimToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize campaign version audit payload", ex);
        }
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }
}
