package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.AuditEventDto;
import edu.courseflow.promotion.dto.PromotionDtos.AuditQueryResponseDto;
import edu.courseflow.promotion.model.IncentiveApplication;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveRedemption;
import edu.courseflow.promotion.repository.IncentiveApplicationRepository;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IncentiveAuditQueryService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final IncentiveAuditEventRepository auditEvents;
    private final IncentiveCampaignRepository campaigns;
    private final IncentiveApplicationRepository applications;
    private final IncentiveRedemptionRepository redemptions;
    private final IncentiveAccessService access;
    private final ObjectMapper objectMapper;
    private final IncentiveMetrics metrics;

    public IncentiveAuditQueryService(IncentiveAuditEventRepository auditEvents,
                                      IncentiveCampaignRepository campaigns,
                                      IncentiveApplicationRepository applications,
                                      IncentiveRedemptionRepository redemptions,
                                      IncentiveAccessService access,
                                      ObjectMapper objectMapper,
                                      IncentiveMetrics metrics) {
        this.auditEvents = auditEvents;
        this.campaigns = campaigns;
        this.applications = applications;
        this.redemptions = redemptions;
        this.access = access;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
    }

    @Transactional(readOnly = true)
    public AuditQueryResponseDto query(Optional<String> tenantId,
                                       Optional<String> applicationId,
                                       Optional<String> aggregateType,
                                       Optional<String> aggregateId,
                                       Optional<String> action,
                                       Optional<String> actorId,
                                       Optional<String> correlationId,
                                       Optional<String> sourceClientId,
                                       Optional<Instant> from,
                                       Optional<Instant> to,
                                       Optional<Integer> limit,
                                       CurrentUser user) {
        long started = System.nanoTime();
        try {
            String tenant = blankToNull(tenantId.orElse(null));
            String application = blankToNull(applicationId.orElse(null));
            if (tenant != null && application != null) {
                access.requireReviewAccess(tenant, application, user);
            } else {
                access.requirePlatformAdmin(user);
            }
            int pageSize = boundedLimit(limit.orElse(50));
            List<IncentiveAuditEvent> rows = auditEvents.search(
                    tenant,
                    application,
                    blankToNull(aggregateType.orElse(null)),
                    blankToNull(aggregateId.orElse(null)),
                    blankToNull(action.orElse(null)),
                    blankToNull(actorId.orElse(null)),
                    blankToNull(correlationId.orElse(null)),
                    blankToNull(sourceClientId.orElse(null)),
                    from.orElse(Instant.EPOCH),
                    to.orElse(Instant.parse("9999-12-31T23:59:59Z")),
                    PageRequest.of(0, pageSize + 1));
            return response(rows, pageSize);
        } finally {
            metrics.auditQuery("explorer", Duration.ofNanos(System.nanoTime() - started));
        }
    }

    @Transactional(readOnly = true)
    public AuditQueryResponseDto campaignTimeline(UUID campaignId, Optional<Integer> limit, CurrentUser user) {
        long started = System.nanoTime();
        try {
            IncentiveCampaign campaign = campaigns.findById(campaignId)
                    .orElseThrow(() -> new NotFoundException("Campaign not found: " + campaignId));
            access.requireReviewAccess(campaign.getTenantId(), campaign.getApplicationId(), user);
            return timeline(campaign.getTenantId(), campaign.getApplicationId(),
                    List.of(campaign.getId().toString()), limit);
        } finally {
            metrics.auditQuery("campaign_timeline", Duration.ofNanos(System.nanoTime() - started));
        }
    }

    @Transactional(readOnly = true)
    public AuditQueryResponseDto applicationTimeline(UUID applicationUuid, Optional<Integer> limit, CurrentUser user) {
        long started = System.nanoTime();
        try {
            IncentiveApplication application = applications.findById(applicationUuid)
                    .orElseThrow(() -> new NotFoundException("Incentive application not found: " + applicationUuid));
            access.requireReviewAccess(application.getTenantId(), application.getApplicationId(), user);
            return timeline(application.getTenantId(), application.getApplicationId(),
                    List.of(application.getId().toString()), limit);
        } finally {
            metrics.auditQuery("application_timeline", Duration.ofNanos(System.nanoTime() - started));
        }
    }

    @Transactional(readOnly = true)
    public AuditQueryResponseDto redemptionTimeline(UUID redemptionId, Optional<Integer> limit, CurrentUser user) {
        long started = System.nanoTime();
        try {
            IncentiveRedemption redemption = redemptions.findById(redemptionId)
                    .orElseThrow(() -> new NotFoundException("Redemption not found: " + redemptionId));
            access.requireReviewAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
            List<String> aggregateIds = new ArrayList<>();
            aggregateIds.add(redemption.getId().toString());
            if (redemption.getReservationId() != null) {
                aggregateIds.add(redemption.getReservationId().toString());
            }
            return timeline(redemption.getTenantId(), redemption.getApplicationId(), aggregateIds, limit);
        } finally {
            metrics.auditQuery("redemption_timeline", Duration.ofNanos(System.nanoTime() - started));
        }
    }

    private AuditQueryResponseDto timeline(String tenantId, String applicationId,
                                           List<String> aggregateIds, Optional<Integer> limit) {
        int pageSize = boundedLimit(limit.orElse(100));
        List<IncentiveAuditEvent> rows = auditEvents.timeline(
                tenantId,
                applicationId,
                aggregateIds,
                PageRequest.of(0, pageSize + 1));
        return response(rows, pageSize);
    }

    private AuditQueryResponseDto response(List<IncentiveAuditEvent> rows, int limit) {
        boolean hasMore = rows.size() > limit;
        List<AuditEventDto> items = rows.stream()
                .limit(limit)
                .map(this::auditDto)
                .toList();
        return new AuditQueryResponseDto(items, limit, hasMore);
    }

    private AuditEventDto auditDto(IncentiveAuditEvent event) {
        return new AuditEventDto(
                event.getId(),
                event.getTenantId(),
                event.getApplicationId(),
                event.getAggregateId(),
                event.getAggregateType(),
                event.getAction(),
                event.getActorId(),
                event.getNote(),
                readMap(event.getPayloadJson()),
                event.getCorrelationId(),
                event.getSourceClientId(),
                event.getCreatedAt());
    }

    private Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> result = objectMapper.readValue(json, MAP_TYPE);
            return result == null ? Map.of() : result;
        } catch (JsonProcessingException ex) {
            return Map.of("raw", json);
        }
    }

    private int boundedLimit(int requested) {
        return Math.max(1, Math.min(requested, 200));
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
