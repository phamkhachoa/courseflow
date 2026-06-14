package edu.courseflow.promotion.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionPolicyDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionPolicyRegistryDto;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Component;

@Component
public class RetentionPolicyRegistry {

    static final String EXPIRED_IDEMPOTENCY_KEYS = "expired-idempotency-keys";
    static final String PUBLISHED_OUTBOX_EVENTS = "published-outbox-events";
    static final String TERMINAL_RESERVATION_REQUEST_SNAPSHOTS = "terminal-reservation-request-snapshots";

    private static final String VERSION = "v1";

    private final List<RetentionPolicy> policies = List.of(
            new RetentionPolicy(
                    EXPIRED_IDEMPOTENCY_KEYS,
                    VERSION,
                    "incentive_idempotency_keys",
                    "PURGE_CANDIDATE",
                    1,
                    0,
                    1_000,
                    List.of("GLOBAL", "APPLICATION"),
                    "expires_at <= asOf - retentionDays and status <> IN_PROGRESS",
                    List.of("unexpired rows", "IN_PROGRESS rows"),
                    true),
            new RetentionPolicy(
                    PUBLISHED_OUTBOX_EVENTS,
                    VERSION,
                    "outbox_events",
                    "PURGE_CANDIDATE",
                    14,
                    7,
                    1_000,
                    List.of("GLOBAL"),
                    "published_at is not null and published_at <= asOf - retentionDays",
                    List.of("unpublished rows", "recently published rows"),
                    true),
            new RetentionPolicy(
                    TERMINAL_RESERVATION_REQUEST_SNAPSHOTS,
                    VERSION,
                    "incentive_reservation_request_snapshots",
                    "REDACT_CANDIDATE",
                    30,
                    7,
                    500,
                    List.of("GLOBAL", "APPLICATION"),
                    "status in EXPIRED,CANCELLED and terminal_at <= asOf - retentionDays",
                    List.of("RESERVED rows", "REDEEMED rows", "recent terminal rows",
                            "already minimized/redacted snapshots"),
                    true),
            neverPurge("immutable-ledger-entries", "incentive_ledger_entries"),
            neverPurge("immutable-redemptions", "incentive_redemptions"),
            neverPurge("immutable-audit-events", "incentive_audit_events"),
            neverPurge("immutable-campaign-versions", "incentive_campaign_versions"));

    private final Map<String, RetentionPolicy> policiesById = policies.stream()
            .collect(java.util.stream.Collectors.toUnmodifiableMap(RetentionPolicy::policyId, policy -> policy));

    public RetentionPolicyRegistryDto listPolicies() {
        return new RetentionPolicyRegistryDto(policies.stream().map(RetentionPolicy::toDto).toList());
    }

    public List<RetentionPolicy> runnableDefaults() {
        return policies.stream().filter(RetentionPolicy::dryRunSupported).toList();
    }

    public List<RetentionPolicy> select(List<String> policyIds) {
        if (policyIds == null || policyIds.isEmpty()) {
            return runnableDefaults();
        }
        return policyIds.stream()
                .map(policyId -> policyId == null ? "" : policyId.trim())
                .distinct()
                .map(this::requirePolicy)
                .toList();
    }

    private RetentionPolicy requirePolicy(String policyId) {
        String normalized = policyId == null ? "" : policyId.trim();
        RetentionPolicy policy = policiesById.get(normalized);
        if (policy == null) {
            throw new BadRequestException("Unknown retention policy: " + policyId);
        }
        return policy;
    }

    private static RetentionPolicy neverPurge(String policyId, String targetDataset) {
        return new RetentionPolicy(
                policyId,
                VERSION,
                targetDataset,
                "NEVER_PURGE",
                0,
                0,
                0,
                List.of("GLOBAL", "APPLICATION"),
                "never eligible for purge",
                List.of("immutable business/audit evidence"),
                false);
    }

    public record RetentionPolicy(
            String policyId,
            String policyVersion,
            String targetDataset,
            String actionType,
            int defaultRetentionDays,
            int minimumRetentionDays,
            int defaultBatchLimit,
            List<String> scopeTypes,
            String eligibleWhen,
            List<String> blockerRules,
            boolean dryRunSupported
    ) {
        public RetentionPolicy {
            Objects.requireNonNull(policyId, "policyId");
            Objects.requireNonNull(targetDataset, "targetDataset");
        }

        public RetentionPolicyDto toDto() {
            return new RetentionPolicyDto(
                    policyId,
                    policyVersion,
                    targetDataset,
                    actionType,
                    defaultRetentionDays,
                    minimumRetentionDays,
                    defaultBatchLimit,
                    TERMINAL_RESERVATION_REQUEST_SNAPSHOTS.equals(policyId),
                    scopeTypes,
                    eligibleWhen,
                    blockerRules);
        }
    }
}
