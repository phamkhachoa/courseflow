package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveEffectDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationEffectDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationEntryDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationQueryResponseDto;
import edu.courseflow.promotion.repository.IncentiveLedgerEntryRepository;
import edu.courseflow.promotion.repository.IncentiveLedgerEntryRepository.ReconciliationLedgerRow;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IncentiveReconciliationService {

    private static final int DEFAULT_LIMIT = 50;
    private static final int MAX_LIMIT = 200;
    private static final String COMMITTED_REVERSAL_QUOTA_POLICY = "NO_RELEASE_ON_COMMITTED_REVERSAL";
    private static final Set<String> ENTRY_TYPES = Set.of("RESERVE", "COMMIT", "CANCEL", "EXPIRE", "REVERSE");
    private static final TypeReference<List<IncentiveEffectDto>> EFFECT_LIST = new TypeReference<>() {
    };

    private final IncentiveLedgerEntryRepository ledgerEntries;
    private final IncentiveAccessService access;
    private final ObjectMapper objectMapper;
    private final IncentiveMetrics metrics;

    public IncentiveReconciliationService(IncentiveLedgerEntryRepository ledgerEntries,
                                          IncentiveAccessService access,
                                          ObjectMapper objectMapper,
                                          IncentiveMetrics metrics) {
        this.ledgerEntries = ledgerEntries;
        this.access = access;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
    }

    @Transactional(readOnly = true)
    public IncentiveReconciliationQueryResponseDto query(Optional<String> tenantId,
                                                         Optional<String> applicationId,
                                                         Optional<String> profileId,
                                                         Optional<String> externalReference,
                                                         Optional<UUID> campaignId,
                                                         Optional<UUID> couponId,
                                                         Optional<UUID> redemptionId,
                                                         Optional<UUID> reservationId,
                                                         Optional<String> entryType,
                                                         Optional<Instant> from,
                                                         Optional<Instant> to,
                                                         Optional<Integer> limit,
                                                         CurrentUser user) {
        long started = System.nanoTime();
        String result = "success";
        try {
            String tenant = blankToNull(tenantId.orElse(null));
            String application = blankToNull(applicationId.orElse(null));
            requireListAccess(tenant, application, user);
            String normalizedEntryType = entryType.map(this::normalizeEntryType).orElse(null);
            Instant fromCreatedAt = from.orElse(null);
            Instant toCreatedAt = to.orElse(null);
            if (fromCreatedAt != null && toCreatedAt != null && !fromCreatedAt.isBefore(toCreatedAt)) {
                throw new BadRequestException("Reconciliation from timestamp must be before to timestamp");
            }
            int pageSize = Math.max(1, Math.min(limit.orElse(DEFAULT_LIMIT), MAX_LIMIT));
            List<ReconciliationLedgerRow> rows = ledgerEntries.searchReconciliationRows(
                    tenant,
                    application,
                    blankToNull(profileId.orElse(null)),
                    blankToNull(externalReference.orElse(null)),
                    campaignId.orElse(null),
                    couponId.orElse(null),
                    redemptionId.orElse(null),
                    reservationId.orElse(null),
                    normalizedEntryType,
                    fromCreatedAt,
                    toCreatedAt,
                    pageSize + 1);
            boolean hasMore = rows.size() > pageSize;
            List<IncentiveReconciliationEntryDto> items = rows.stream()
                    .limit(pageSize)
                    .flatMap(row -> entries(row).stream())
                    .toList();
            return new IncentiveReconciliationQueryResponseDto(items, pageSize, hasMore, Instant.now());
        } catch (RuntimeException ex) {
            result = "error";
            throw ex;
        } finally {
            metrics.reconciliationQuery(result, Duration.ofNanos(System.nanoTime() - started));
        }
    }

    private List<IncentiveReconciliationEntryDto> entries(ReconciliationLedgerRow row) {
        List<IncentiveEffectDto> effects = effects(row.getEffectJson());
        if (effects.isEmpty()) {
            return List.of(entry(row, null, "MISSING_EFFECT", List.of("MISSING_EFFECT")));
        }
        List<IncentiveReconciliationEntryDto> items = new ArrayList<>();
        for (IncentiveEffectDto effect : effects) {
            items.add(entry(row, effect, status(row, effect), reasonCodes(row, effect)));
        }
        return List.copyOf(items);
    }

    private IncentiveReconciliationEntryDto entry(ReconciliationLedgerRow row,
                                                 IncentiveEffectDto effect,
                                                 String status,
                                                 List<String> reasonCodes) {
        return new IncentiveReconciliationEntryDto(
                row.getLedgerEntryId(),
                reconciliationKey(row, effect),
                status,
                reasonCodes,
                direction(row.getEntryType()),
                row.getEntryType(),
                row.getRedemptionId(),
                row.getReservationId(),
                row.getTenantId(),
                row.getApplicationId(),
                row.getCampaignId(),
                row.getCampaignVersion(),
                row.getCouponId(),
                row.getProfileId(),
                row.getExternalReference(),
                row.getRedemptionStatus(),
                quotaPolicy(row.getEntryType()),
                quotaReleased(row.getEntryType()),
                outboxStatus(row),
                row.getOutboxEventType(),
                row.getOutboxPublishedAt(),
                row.getCorrelationId(),
                row.getSourceClientId(),
                row.getLedgerCreatedAt(),
                row.getRedeemedAt(),
                row.getReversedAt(),
                effect == null ? null : effect(effect));
    }

    private String status(ReconciliationLedgerRow row, IncentiveEffectDto effect) {
        if (effectId(effect).isBlank()) {
            return "MISSING_EFFECT";
        }
        if (row.getRedemptionId() != null && requiresOutbox(row.getEntryType())
                && ledgerEntries.countByRedemptionIdAndEntryType(row.getRedemptionId(), row.getEntryType()) > 1) {
            return "DUPLICATE";
        }
        if (requiresOutbox(row.getEntryType()) && row.getOutboxEventType() == null) {
            return "MISSING_OUTBOX";
        }
        if ("RESERVE".equals(row.getEntryType())) {
            return "PENDING";
        }
        if ("COMMIT".equals(row.getEntryType()) && "REVERSED".equals(row.getRedemptionStatus())) {
            return "REVERSED";
        }
        return "MATCHED";
    }

    private List<String> reasonCodes(ReconciliationLedgerRow row, IncentiveEffectDto effect) {
        String status = status(row, effect);
        if ("MATCHED".equals(status)) {
            return List.of();
        }
        return List.of(status);
    }

    private IncentiveReconciliationEffectDto effect(IncentiveEffectDto effect) {
        return new IncentiveReconciliationEffectDto(
                effectId(effect),
                effect.type(),
                firstNonBlank(effect.benefitType(), effect.amount() == null ? effect.type() : "DISCOUNT"),
                firstNonBlank(effect.actionType(), effect.type()),
                effect.targetType(),
                effect.targetId(),
                effect.amount(),
                effect.currency(),
                firstNonBlank(effect.unit(), effect.currency() == null ? null : "MONEY"),
                effect.quantity() == null ? effect.amount() : effect.quantity(),
                effect.campaignVersion(),
                effect.metadata() == null ? Map.of() : effect.metadata());
    }

    private List<IncentiveEffectDto> effects(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<IncentiveEffectDto> result = objectMapper.readValue(json, EFFECT_LIST);
            return result == null ? List.of() : result;
        } catch (JsonProcessingException ex) {
            return List.of();
        }
    }

    private String reconciliationKey(ReconciliationLedgerRow row, IncentiveEffectDto effect) {
        String effectId = effect == null ? "missing-effect" : effectId(effect);
        String operationId = row.getRedemptionId() == null
                ? Objects.toString(row.getReservationId(), row.getLedgerEntryId().toString())
                : row.getRedemptionId().toString();
        return String.join(":", operationId, row.getEntryType(), effectId);
    }

    private String effectId(IncentiveEffectDto effect) {
        if (effect == null) {
            return "";
        }
        if (effect.effectId() != null && !effect.effectId().isBlank()) {
            return effect.effectId();
        }
        Map<String, Object> metadata = effect.metadata() == null ? Map.of() : effect.metadata();
        String campaignId = Objects.toString(metadata.get("campaignId"), "");
        String campaignVersion = Objects.toString(
                effect.campaignVersion() == null ? metadata.get("campaignVersion") : effect.campaignVersion(), "");
        String actionType = firstNonBlank(effect.actionType(), effect.type());
        String targetType = firstNonBlank(effect.targetType(), "TARGET");
        String targetId = firstNonBlank(effect.targetId(), "order");
        if (campaignId.isBlank() || campaignVersion.isBlank() || actionType == null || actionType.isBlank()) {
            return "";
        }
        return String.join(":", campaignId, campaignVersion, actionType, targetType, targetId);
    }

    private String direction(String entryType) {
        return switch (entryType) {
            case "COMMIT" -> "APPLY";
            case "REVERSE" -> "COMPENSATE";
            case "CANCEL", "EXPIRE" -> "RELEASE";
            case "RESERVE" -> "PENDING";
            default -> "UNKNOWN";
        };
    }

    private String quotaPolicy(String entryType) {
        return switch (entryType) {
            case "RESERVE" -> "HOLD_RESERVED_QUOTA";
            case "CANCEL", "EXPIRE" -> "RELEASE_RESERVED_QUOTA";
            case "REVERSE" -> COMMITTED_REVERSAL_QUOTA_POLICY;
            default -> "NO_QUOTA_CHANGE";
        };
    }

    private Boolean quotaReleased(String entryType) {
        return switch (entryType) {
            case "CANCEL", "EXPIRE" -> true;
            case "REVERSE" -> false;
            default -> null;
        };
    }

    private String outboxStatus(ReconciliationLedgerRow row) {
        if (!requiresOutbox(row.getEntryType())) {
            return "NOT_REQUIRED";
        }
        if (row.getOutboxEventType() == null) {
            return "MISSING";
        }
        return row.getOutboxPublishedAt() == null ? "PENDING" : "PUBLISHED";
    }

    private boolean requiresOutbox(String entryType) {
        return "COMMIT".equals(entryType) || "REVERSE".equals(entryType);
    }

    private String normalizeEntryType(String value) {
        String normalized = value == null ? "" : value.trim().toUpperCase();
        if (normalized.isBlank()) {
            return null;
        }
        if (!ENTRY_TYPES.contains(normalized)) {
            throw new BadRequestException("Unsupported reconciliation entryType: " + value);
        }
        return normalized;
    }

    private void requireListAccess(String tenantId, String applicationId, CurrentUser user) {
        if (tenantId == null || applicationId == null) {
            throw new BadRequestException("tenantId and applicationId are required for reconciliation queries");
        }
        access.requireAdminAccess(tenantId, applicationId, user);
    }

    private String firstNonBlank(String first, String fallback) {
        return first == null || first.isBlank() ? fallback : first;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
