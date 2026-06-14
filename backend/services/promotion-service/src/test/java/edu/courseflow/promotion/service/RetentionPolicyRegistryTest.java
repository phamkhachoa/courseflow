package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import java.util.List;
import org.junit.jupiter.api.Test;

class RetentionPolicyRegistryTest {

    private final RetentionPolicyRegistry registry = new RetentionPolicyRegistry();

    @Test
    void listsRunnableAndNeverPurgePolicies() {
        var policies = registry.listPolicies().policies();

        assertThat(policies)
                .extracting(policy -> policy.policyId() + ":" + policy.actionType() + ":"
                        + policy.destructiveExecutionSupported())
                .contains(
                        "expired-idempotency-keys:PURGE_CANDIDATE:false",
                        "published-outbox-events:PURGE_CANDIDATE:false",
                        "terminal-reservation-request-snapshots:REDACT_CANDIDATE:true",
                        "immutable-ledger-entries:NEVER_PURGE:false",
                        "immutable-redemptions:NEVER_PURGE:false",
                        "immutable-audit-events:NEVER_PURGE:false",
                        "immutable-campaign-versions:NEVER_PURGE:false");
    }

    @Test
    void defaultSelectionOnlyIncludesRunnablePolicies() {
        assertThat(registry.select(List.of()))
                .extracting(RetentionPolicyRegistry.RetentionPolicy::policyId)
                .containsExactly(
                        "expired-idempotency-keys",
                        "published-outbox-events",
                        "terminal-reservation-request-snapshots");
    }

    @Test
    void rejectsUnknownPolicy() {
        assertThatThrownBy(() -> registry.select(List.of("unknown-policy")))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("Unknown retention policy");
    }
}
