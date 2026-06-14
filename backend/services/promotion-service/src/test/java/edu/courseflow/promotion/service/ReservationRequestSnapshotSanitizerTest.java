package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ReservationRequestSnapshotSanitizerTest {

    private final ReservationRequestSnapshotSanitizer sanitizer =
            new ReservationRequestSnapshotSanitizer("test-request-snapshot-secret-32-byte-value");
    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @Test
    void storageSnapshotKeepsSafeAggregatesAndRemovesRawSensitiveValues() throws Exception {
        EvaluateIncentivesRequestDto request = request();

        String json = objectMapper.writeValueAsString(sanitizer.storageSnapshot(request));

        assertThat(json).contains("reservation-request-snapshot.v2");
        assertThat(json).contains("\"requestSnapshotMinimized\":true");
        assertThat(json).contains("\"coupons\"");
        assertThat(json).contains("SA****26");
        assertThat(json).contains("\"profileHash\":\"hmac-sha256:");
        assertThat(json).contains("\"externalReferenceHash\":\"hmac-sha256:");
        assertThat(json).contains("\"count\":1").doesNotContain("\"raw\"");
        assertThat(json)
                .doesNotContain("profile-private-123")
                .doesNotContain("order-private-456")
                .doesNotContain("SAVE-SUPERSECRET-2026")
                .doesNotContain("item-private-789")
                .doesNotContain("alice@example.com")
                .doesNotContain("token-secret-value")
                .doesNotContain("vip-sensitive-value");
    }

    @Test
    void auditFactsAreDeterministicAndDoNotIncludeGeneratedAt() {
        EvaluateIncentivesRequestDto request = request();

        Map<String, Object> first = sanitizer.auditFacts(request);
        Map<String, Object> second = sanitizer.auditFacts(request);

        assertThat(first).isEqualTo(second);
        assertThat(first).doesNotContainKey("generatedAt");
    }

    private EvaluateIncentivesRequestDto request() {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                "profile-private-123",
                "order-private-456",
                "WEB",
                "USD",
                List.of("SAVE-SUPERSECRET-2026"),
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.TEN),
                List.of(new IncentiveItemDto(
                        "item-private-789",
                        "COURSE",
                        1,
                        BigDecimal.valueOf(120),
                        Map.of("email", "alice@example.com", "category", "spring"))),
                Map.of("token", "token-secret-value", "segment", "vip-sensitive-value"));
    }
}
