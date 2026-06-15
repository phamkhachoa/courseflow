package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ExperimentPreviewRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ExperimentVariantPreviewRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class IncentiveExperimentServiceTest {

    @Mock
    private IncentiveAccessService access;
    @Mock
    private IncentiveAuditEventRepository auditEvents;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @Test
    void previewAssignsDeterministicVariantAndAuditsWithoutRawContextSecrets() {
        IncentiveExperimentService service = new IncentiveExperimentService(access, auditEvents, objectMapper);
        CurrentUser admin = new CurrentUser(7L, "admin@courseflow.local", "ADMIN", Set.of("ADMIN"));
        ExperimentPreviewRequestDto request = new ExperimentPreviewRequestDto(
                context("profile-1"),
                "checkout-price-test",
                "PROFILE",
                null,
                List.of(
                        new ExperimentVariantPreviewRequestDto(
                                "discount-10", 5000, false, "SAVE10", Map.of("owner", "growth")),
                        new ExperimentVariantPreviewRequestDto(
                                "holdout", 5000, true, null, Map.of())),
                "traffic review");

        var first = service.preview(request, admin, "corr-exp-1");
        var second = service.preview(request, admin, "corr-exp-2");

        assertThat(second.bucket()).isEqualTo(first.bucket());
        assertThat(second.selectedVariantKey()).isEqualTo(first.selectedVariantKey());
        assertThat(first.preview()).isTrue();
        assertThat(first.ledgerImpact()).isFalse();
        assertThat(first.assignmentKeyHash()).doesNotContain("profile-1");
        assertThat(first.variants()).hasSize(2);
        assertThat(first.variants()).filteredOn("selected", true)
                .singleElement()
                .extracting("key")
                .isEqualTo(first.selectedVariantKey());
        verify(access, times(2)).requireAdminAccess("courseflow", "lms", admin);
        verify(access, times(2)).requireActiveApplication("courseflow", "lms", admin, "experiment-preview");

        ArgumentCaptor<IncentiveAuditEvent> audit = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents, times(2)).save(audit.capture());
        IncentiveAuditEvent firstAudit = audit.getAllValues().getFirst();
        assertThat(firstAudit.getAction()).isEqualTo("experiment.previewed");
        assertThat(firstAudit.getAggregateType()).isEqualTo("experiment");
        assertThat(firstAudit.getAggregateId()).isEqualTo("checkout-price-test");
        assertThat(firstAudit.getCorrelationId()).isEqualTo("corr-exp-1");
        assertThat(firstAudit.getPayloadJson())
                .contains("promotion-experiment-preview-v1")
                .contains("assignmentKeyHash")
                .contains("discount-10")
                .doesNotContain("profile-1")
                .doesNotContain("SECRET-001");
    }

    @Test
    void previewAddsImplicitHoldoutWhenAllocationIsBelowFullTraffic() {
        IncentiveExperimentService service = new IncentiveExperimentService(access, auditEvents, objectMapper);
        CurrentUser admin = new CurrentUser(7L, "admin@courseflow.local", "ADMIN", Set.of("ADMIN"));

        var response = service.preview(new ExperimentPreviewRequestDto(
                context("profile-2"),
                "checkout-holdout-test",
                "PROFILE",
                null,
                List.of(new ExperimentVariantPreviewRequestDto(
                        "discount-5", 2500, false, "SAVE5", Map.of())),
                null), admin, "corr-exp");

        assertThat(response.reasonCodes()).contains("EXPERIMENT_IMPLICIT_HOLDOUT_CONFIGURED");
        assertThat(response.variants()).extracting("key").containsExactly("discount-5", "__HOLDOUT__");
        assertThat(response.variants()).extracting("weightBps").containsExactly(2500, 7500);
        assertThat(response.variants().getLast().holdout()).isTrue();
        assertThat(response.selectedVariantKey()).isIn("discount-5", "__HOLDOUT__");
    }

    @Test
    void previewRejectsDuplicateKeysAndWeightOverflow() {
        IncentiveExperimentService service = new IncentiveExperimentService(access, auditEvents, objectMapper);
        CurrentUser admin = new CurrentUser(7L, "admin@courseflow.local", "ADMIN", Set.of("ADMIN"));

        assertThatThrownBy(() -> service.preview(new ExperimentPreviewRequestDto(
                context("profile-3"),
                "duplicate-test",
                "PROFILE",
                null,
                List.of(
                        new ExperimentVariantPreviewRequestDto("A", 5000, false, null, Map.of()),
                        new ExperimentVariantPreviewRequestDto("a", 5000, false, null, Map.of())),
                null), admin, "corr-dup"))
                .hasMessageContaining("Duplicate experiment variant key");

        assertThatThrownBy(() -> service.preview(new ExperimentPreviewRequestDto(
                context("profile-3"),
                "overflow-test",
                "PROFILE",
                null,
                List.of(
                        new ExperimentVariantPreviewRequestDto("A", 6000, false, null, Map.of()),
                        new ExperimentVariantPreviewRequestDto("B", 5000, false, null, Map.of())),
                null), admin, "corr-overflow"))
                .hasMessageContaining("weights cannot exceed 10000");
    }

    private EvaluateIncentivesRequestDto context(String profileId) {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                profileId,
                "order-123",
                "WEB",
                "USD",
                List.of("SECRET-001"),
                List.of(),
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.ZERO),
                List.of(),
                Map.of("cohort", "spring-2026"));
    }
}
