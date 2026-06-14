package edu.courseflow.promotion.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class PromotionLoyaltyReadinessClient {

    private final RestClient loyaltyClient;
    private final InternalJwtService internalJwt;
    private final String clientId;
    private final boolean enabled;

    public PromotionLoyaltyReadinessClient(
            RestClient.Builder restClientBuilder,
            InternalJwtService internalJwt,
            @Value("${courseflow.promotion.loyalty-service-url:http://loyalty-service:8080}") String loyaltyServiceUrl,
            @Value("${courseflow.promotion.loyalty.client-id:promotion-service}") String clientId,
            @Value("${courseflow.promotion.loyalty.readiness-timeout-ms:1500}") long readinessTimeoutMs,
            @Value("${courseflow.promotion.loyalty.readiness-enabled:true}") boolean enabled) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int timeoutMs = (int) Math.max(250, Math.min(readinessTimeoutMs, 5000));
        requestFactory.setConnectTimeout(timeoutMs);
        requestFactory.setReadTimeout(timeoutMs);
        this.loyaltyClient = restClientBuilder.clone()
                .baseUrl(loyaltyServiceUrl)
                .requestFactory(requestFactory)
                .build();
        this.internalJwt = internalJwt;
        this.clientId = clientId == null || clientId.isBlank() ? "promotion-service" : clientId.trim();
        this.enabled = enabled;
    }

    public LoyaltyReadinessResult checkEarnReadiness(String tenantId, String applicationId, String programId) {
        if (!enabled) {
            return new LoyaltyReadinessResult(
                    true,
                    List.of(),
                    List.of("LOYALTY_READINESS_CHECK_DISABLED"),
                    "DISABLED");
        }
        try {
            LoyaltyProgramReadiness response = loyaltyClient.get()
                    .uri(uri -> uri.path("/internal/loyalty/program-readiness")
                            .queryParam("tenantId", tenantId)
                            .queryParam("applicationId", applicationId)
                            .queryParam("programId", programId)
                            .queryParam("clientId", clientId)
                            .queryParam("operation", "earn")
                            .build())
                    .headers(headers -> internalJwt.applyServiceToken(headers, List.of(InternalScopes.LOYALTY_EARN)))
                    .retrieve()
                    .body(LoyaltyProgramReadiness.class);
            if (response == null) {
                return unavailable("LOYALTY_READINESS_EMPTY_RESPONSE");
            }
            return new LoyaltyReadinessResult(
                    response.ready(),
                    safe(response.blockers()),
                    safe(response.warnings()),
                    response.programStatus());
        } catch (RestClientResponseException ex) {
            return unavailable("LOYALTY_READINESS_REJECTED_" + ex.getStatusCode().value());
        } catch (RestClientException ex) {
            return unavailable("LOYALTY_READINESS_UNAVAILABLE");
        }
    }

    private LoyaltyReadinessResult unavailable(String reason) {
        return new LoyaltyReadinessResult(false, List.of(reason), List.of(), "UNKNOWN");
    }

    private List<String> safe(List<String> values) {
        return values == null ? List.of() : values;
    }

    public record LoyaltyReadinessResult(
            boolean ready,
            List<String> blockers,
            List<String> warnings,
            String programStatus
    ) {
    }

    public record LoyaltyProgramReadiness(
            boolean ready,
            String programStatus,
            List<String> blockers,
            List<String> warnings
    ) {
    }
}
