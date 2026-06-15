package edu.courseflow.outboxrelay.controller;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import edu.courseflow.commonlibrary.exception.ApiExceptionHandler;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.commonlibrary.web.CurrentUserArgumentResolver;
import edu.courseflow.commonlibrary.web.TrustedGatewayHeaderFilter;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterQueryResponseDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterSummaryDto;
import edu.courseflow.outboxrelay.relay.DeadLetterService;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class DeadLetterAdminControllerSecurityTest {

    private static final String INTERNAL_SECRET = "test-internal-jwt-secret-32-byte-value-001";

    private final DeadLetterService deadLetters = org.mockito.Mockito.mock(DeadLetterService.class);
    private final InternalJwtService internalJwtService = new InternalJwtService(new InternalJwtProperties(
            INTERNAL_SECRET,
            "courseflow-token-converter",
            "courseflow-services",
            180,
            30,
            "api-gateway"));
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders
                .standaloneSetup(new DeadLetterAdminController(deadLetters))
                .setControllerAdvice(new ApiExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .addFilters(new TrustedGatewayHeaderFilter(internalJwtService))
                .build();
    }

    @Test
    void deadLetterSearchRequiresInternalJwtBeforeController() throws Exception {
        mvc.perform(get("/internal/outbox/dead-letters")
                        .header("X-User-Id", "1")
                        .header("X-User-Role", "ADMIN")
                        .header("X-User-Roles", "ADMIN"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(deadLetters);
    }

    @Test
    void deadLetterSearchRequiresPlatformAdminRole() throws Exception {
        mvc.perform(get("/internal/outbox/dead-letters")
                        .headers(userHeaders("OPS", Set.of("OPS"))))
                .andExpect(status().isForbidden());

        verifyNoInteractions(deadLetters);
    }

    @Test
    void deadLetterSearchAllowsPlatformAdmin() throws Exception {
        UUID id = UUID.randomUUID();
        UUID sourceEventId = UUID.randomUUID();
        when(deadLetters.search(
                        eq("OPEN"),
                        eq("promotion-service"),
                        eq("incentive.redemption.committed"),
                        eq("enrollment-1"),
                        eq("sha256:payload"),
                        eq(10)))
                .thenReturn(new DeadLetterQueryResponseDto(
                        List.of(summary(id, sourceEventId)),
                        10,
                        false));

        mvc.perform(get("/internal/outbox/dead-letters")
                        .headers(userHeaders("ADMIN", Set.of("ADMIN")))
                        .param("status", "OPEN")
                        .param("service", "promotion-service")
                        .param("eventType", "incentive.redemption.committed")
                        .param("aggregateId", "enrollment-1")
                        .param("payloadHash", "sha256:payload")
                        .param("limit", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].id").value(id.toString()))
                .andExpect(jsonPath("$.items[0].sourceEventId").value(sourceEventId.toString()))
                .andExpect(jsonPath("$.items[0].serviceName").value("promotion-service"))
                .andExpect(jsonPath("$.items[0].payloadHash").value("sha256:payload"));

        verify(deadLetters).search(
                "OPEN",
                "promotion-service",
                "incentive.redemption.committed",
                "enrollment-1",
                "sha256:payload",
                10);
    }

    private HttpHeaders userHeaders(String primaryRole, Set<String> roles) {
        HttpHeaders headers = new HttpHeaders();
        internalJwtService.applyUserToken(headers, new CurrentUser(
                1L,
                "operator@example.com",
                primaryRole,
                roles,
                Set.of()));
        return headers;
    }

    private DeadLetterSummaryDto summary(UUID id, UUID sourceEventId) {
        Instant now = Instant.parse("2026-06-15T00:00:00Z");
        return new DeadLetterSummaryDto(
                id,
                "promotion-service",
                sourceEventId,
                "incentive.redemption.committed",
                "incentive.redemption.committed",
                1,
                42L,
                "enrollment-1",
                "OPEN",
                5,
                0,
                "sha256:payload",
                "TimeoutException",
                "broker timeout",
                now,
                now,
                null,
                null,
                null);
    }
}
