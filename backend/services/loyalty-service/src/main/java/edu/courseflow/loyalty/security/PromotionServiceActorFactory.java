package edu.courseflow.loyalty.security;

import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.time.Instant;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class PromotionServiceActorFactory {

    private static final String CLIENT_CREDENTIALS_GRANT = "client_credentials";
    private static final Set<String> PROMOTION_LOYALTY_SCOPES =
            Set.of(InternalScopes.LOYALTY_EARN, InternalScopes.LOYALTY_REVERSE);

    private final RestClient tokenConverter;
    private final String clientId;
    private final String clientSecret;
    private final String audience;
    private final long refreshSkewSeconds;
    private volatile CachedToken cachedToken;

    public PromotionServiceActorFactory(
            RestClient.Builder restClientBuilder,
            @Value("${courseflow.loyalty.promotion-service-actor.token-converter-uri:"
                    + "${TOKEN_CONVERTER_URI:http://identity-token-converter-service:8080}}")
            String tokenConverterUri,
            @Value("${courseflow.loyalty.promotion-service-actor.client-id:"
                    + "${LOYALTY_PROMOTION_SERVICE_ACTOR_CLIENT_ID:promotion-service}}")
            String clientId,
            @Value("${courseflow.loyalty.promotion-service-actor.client-secret:"
                    + "${LOYALTY_PROMOTION_SERVICE_ACTOR_CLIENT_SECRET:${COURSEFLOW_STS_CLIENT_SECRET:}}}")
            String clientSecret,
            @Value("${courseflow.loyalty.promotion-service-actor.audience:"
                    + "${COURSEFLOW_INTERNAL_JWT_AUDIENCE:courseflow-services}}")
            String audience,
            @Value("${courseflow.loyalty.promotion-service-actor.refresh-skew-seconds:30}")
            long refreshSkewSeconds) {
        this.tokenConverter = restClientBuilder.clone()
                .baseUrl(blankToDefault(tokenConverterUri, "http://identity-token-converter-service:8080"))
                .build();
        this.clientId = blankToDefault(clientId, "promotion-service");
        this.clientSecret = clientSecret == null ? "" : clientSecret.trim();
        this.audience = blankToDefault(audience, "courseflow-services");
        this.refreshSkewSeconds = Math.max(5, Math.min(refreshSkewSeconds, 120));
    }

    public CurrentUser currentUser() {
        return new CurrentUser(
                null,
                clientId + "@system",
                "SERVICE",
                Set.of(),
                Set.of(),
                serviceToken());
    }

    private String serviceToken() {
        CachedToken token = cachedToken;
        Instant now = Instant.now();
        if (token != null && token.refreshAfter().isAfter(now)) {
            return token.token();
        }
        synchronized (this) {
            token = cachedToken;
            now = Instant.now();
            if (token != null && token.refreshAfter().isAfter(now)) {
                return token.token();
            }
            TokenExchangeResponse response = requestServiceToken();
            long expiresIn = Math.max(30, response.expires_in());
            long usableSeconds = Math.max(5, expiresIn - Math.min(refreshSkewSeconds, expiresIn / 3));
            cachedToken = new CachedToken(response.access_token(), now.plusSeconds(usableSeconds));
            return cachedToken.token();
        }
    }

    private TokenExchangeResponse requestServiceToken() {
        if (clientSecret.isBlank()) {
            throw new IllegalStateException("LOYALTY_PROMOTION_SERVICE_ACTOR_CLIENT_SECRET or "
                    + "COURSEFLOW_STS_CLIENT_SECRET is required for promotion loyalty consumer");
        }
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", CLIENT_CREDENTIALS_GRANT);
        form.add("client_id", clientId);
        form.add("client_secret", clientSecret);
        form.add("audience", audience);
        form.add("scope", String.join(" ", PROMOTION_LOYALTY_SCOPES));
        try {
            TokenExchangeResponse response = tokenConverter.post()
                    .uri("/oauth/token")
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .body(form)
                    .retrieve()
                    .body(TokenExchangeResponse.class);
            if (response == null || response.access_token() == null || response.access_token().isBlank()) {
                throw new IllegalStateException("Token converter returned an empty promotion service actor token");
            }
            return response;
        } catch (RestClientException ex) {
            throw new IllegalStateException("Could not obtain promotion service actor token", ex);
        }
    }

    private static String blankToDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private record CachedToken(String token, Instant refreshAfter) {
    }

    private record TokenExchangeResponse(String access_token, String issued_token_type,
                                         String token_type, long expires_in, String scope) {
    }
}
