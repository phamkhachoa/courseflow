package edu.courseflow.tokenconverter.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import edu.courseflow.tokenconverter.dto.TokenExchangeResponse;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.time.Instant;
import java.util.Base64;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.crypto.SecretKey;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class TokenExchangeServiceTest {

    private static final String EXTERNAL_SECRET = "external-jwt-secret-that-is-at-least-32-bytes";
    private static final String INTERNAL_SECRET = "internal-jwt-secret-that-is-at-least-32-bytes";
    private static final String STS_SECRET = "sts-client-secret-that-is-at-least-32-bytes";
    private static final String USER_MANAGEMENT_STS_SECRET = "user-management-sts-secret-32-byte-value";
    private static final String CHECKOUT_STS_SECRET = "checkout-sts-secret-32-byte-value";
    private static final String PROMOTION_STS_SECRET = "promotion-sts-secret-32-byte-value";
    private static final String LOYALTY_STS_SECRET = "loyalty-sts-secret-32-byte-value";
    private static final String API_GATEWAY_CLIENT_ID = "api-gateway";
    private static final String KEYCLOAK_ISSUER = "https://sso.courseflow.example.com/realms/courseflow";
    private static final String KEYCLOAK_JWKS =
            "https://sso.courseflow.example.com/realms/courseflow/protocol/openid-connect/certs";

    private final TokenConverterProperties properties = new TokenConverterProperties(
            KEYCLOAK_ISSUER,
            KEYCLOAK_JWKS,
            "courseflow-api",
            "HS256",
            INTERNAL_SECRET,
            "",
            "",
            "courseflow-token-converter",
            "courseflow-services",
            "courseflow-services,course-service",
            "",
            API_GATEWAY_CLIENT_ID + "=" + STS_SECRET,
            API_GATEWAY_CLIENT_ID,
            "internal:service,internal:token-exchange",
            API_GATEWAY_CLIENT_ID + "=internal:service,internal:token-exchange",
            180,
            30);
    private final TokenExchangeService service = new TokenExchangeService(
            externalVerifier(properties),
            testIdentityResolver(),
            new InternalTokenIssuer(properties, new ScopeMapper()),
            properties);

    @Test
    void exchangesExternalJwtForShortLivedInternalJwt() {
        TokenExchangeResponse response = service.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "courseflow-services",
                "course:read learning:write admin:write",
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null);

        assertThat(response.token_type()).isEqualTo("Bearer");
        assertThat(response.expires_in()).isEqualTo(180);
        assertThat(response.scope()).contains("course:read").contains("learning:write");
        assertThat(response.scope()).doesNotContain("admin:write");

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();

        assertThat(claims.getIssuer()).isEqualTo("courseflow-token-converter");
        assertThat(claims.getSubject()).isEqualTo("4");
        assertThat(claims.get("uid")).isEqualTo("4");
        assertThat(claims.get("email")).isEqualTo("student@courseflow.local");
        assertThat(((Collection<?>) claims.get("aud")).stream().map(String::valueOf).toList())
                .contains("courseflow-services");
        assertThat(claims.get("roles", List.class)).contains("STUDENT");
        assertThat(claims.get("token_use")).isEqualTo("internal");
    }

    @Test
    void rejectsTokenExchangeWithoutClientCredentials() {
        assertThatThrownBy(() -> service.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "courseflow-services",
                "course:read"))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void rejectsAudienceOutsideAllowlist() {
        assertThatThrownBy(() -> service.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "gradebook-service",
                null,
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void rejectsInvalidExternalToken() {
        TokenExchangeService rejecting = new TokenExchangeService(
                rejectingExternalVerifier(properties),
                testIdentityResolver(),
                new InternalTokenIssuer(properties, new ScopeMapper()),
                properties);

        assertThatThrownBy(() -> rejecting.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                "bad-token",
                "courseflow-services",
                null,
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void canIssueRs256InternalJwt() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        var pair = generator.generateKeyPair();
        TokenConverterProperties rsProperties = new TokenConverterProperties(
                KEYCLOAK_ISSUER,
                KEYCLOAK_JWKS,
                "courseflow-api",
                "RS256",
                "",
                pem("PRIVATE KEY", pair.getPrivate()),
                "",
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                "",
                API_GATEWAY_CLIENT_ID + "=" + STS_SECRET,
                API_GATEWAY_CLIENT_ID,
                "internal:service,internal:token-exchange",
                API_GATEWAY_CLIENT_ID + "=internal:service,internal:token-exchange",
                180,
                30);
        TokenExchangeService rsService = new TokenExchangeService(
                externalVerifier(rsProperties),
                testIdentityResolver(),
                new InternalTokenIssuer(rsProperties, new ScopeMapper()),
                rsProperties);

        TokenExchangeResponse response = rsService.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "courseflow-services",
                null,
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null);

        Claims claims = Jwts.parser()
                .verifyWith(pair.getPublic())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();
        assertThat(claims.getIssuer()).isEqualTo("courseflow-token-converter");
        assertThat(claims.getSubject()).isEqualTo("4");
    }

    @Test
    void canIssueServiceTokenWithClientCredentials() {
        TokenConverterProperties stsProperties = stsProperties();
        TokenExchangeService stsService = service(stsProperties);

        TokenExchangeResponse response = stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:service",
                "course-service",
                STS_SECRET,
                null,
                null,
                null,
                null);

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();
        assertThat(claims.getSubject()).isEqualTo("service:course-service");
        assertThat(claims.get("actor_type")).isEqualTo("service");
        assertThat(claims.get("azp")).isEqualTo("course-service");
        assertThat(claims.get("scope")).isEqualTo("internal:service");
    }

    @Test
    void rejectsServiceScopeOutsidePerClientProfile() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:identity:provision",
                "course-service",
                STS_SECRET,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void acceptsPrivilegedScopeOnlyForMappedClient() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        TokenExchangeResponse response = stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:identity:provision",
                "user-management-service",
                USER_MANAGEMENT_STS_SECRET,
                null,
                null,
                null,
                null);

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();
        assertThat(claims.get("azp")).isEqualTo("user-management-service");
        assertThat(claims.get("scope")).isEqualTo("internal:identity:provision");
    }

    @Test
    void acceptsPromotionRuntimeOperationScopeOnlyForTrustedSourceClient() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        TokenExchangeResponse response = stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:promotion:evaluate internal:promotion:reserve",
                "checkout-service",
                CHECKOUT_STS_SECRET,
                null,
                null,
                null,
                null);

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();
        assertThat(claims.get("azp")).isEqualTo("checkout-service");
        assertThat(claims.get("scope").toString())
                .contains("internal:promotion:evaluate")
                .contains("internal:promotion:reserve");
    }

    @Test
    void rejectsPromotionOperationScopeForUnmappedClient() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:promotion:evaluate",
                "course-service",
                STS_SECRET,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void rejectsPromotionRuntimeOperationScopeForPromotionServiceItself() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:promotion:evaluate",
                "promotion-service",
                PROMOTION_STS_SECRET,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void acceptsLoyaltyRuntimeOperationScopesOnlyForCheckoutClient() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        TokenExchangeResponse response = stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:loyalty:earn internal:loyalty:burn internal:loyalty:reverse internal:loyalty:read",
                "checkout-service",
                CHECKOUT_STS_SECRET,
                null,
                null,
                null,
                null);

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();
        assertThat(claims.get("azp")).isEqualTo("checkout-service");
        assertThat(claims.get("scope").toString())
                .contains("internal:loyalty:earn")
                .contains("internal:loyalty:burn")
                .contains("internal:loyalty:reverse")
                .contains("internal:loyalty:read");
    }

    @Test
    void acceptsLoyaltyAdminReadScopesOnlyForLoyaltyService() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        TokenExchangeResponse response = stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:loyalty:admin internal:loyalty:read",
                "loyalty-service",
                LOYALTY_STS_SECRET,
                null,
                null,
                null,
                null);

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();
        assertThat(claims.get("azp")).isEqualTo("loyalty-service");
        assertThat(claims.get("scope").toString())
                .contains("internal:loyalty:admin")
                .contains("internal:loyalty:read");
    }

    @Test
    void rejectsLoyaltyOperationScopeForPromotionService() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:loyalty:earn",
                "promotion-service",
                PROMOTION_STS_SECRET,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void rejectsSecretFromAnotherClient() {
        TokenExchangeService stsService = service(stsPropertiesWithClientPolicy());

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.CLIENT_CREDENTIALS_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:service",
                "course-service",
                USER_MANAGEMENT_STS_SECRET,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void oidcModeRequiresPerClientStsSecretsAndScopes() {
        assertThatThrownBy(() -> new TokenConverterProperties(
                "https://sso.courseflow.example.com/realms/courseflow",
                "https://sso.courseflow.example.com/realms/courseflow/protocol/openid-connect/certs",
                "courseflow-api",
                "HS256",
                INTERNAL_SECRET,
                "",
                "",
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                STS_SECRET,
                "",
                "api-gateway",
                "internal:service,internal:token-exchange",
                "",
                180,
                30))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("COURSEFLOW_STS_CLIENT_SECRETS");
    }

    @Test
    void oidcModeRejectsPerClientSecretWithoutScopePolicy() {
        assertThatThrownBy(() -> new TokenConverterProperties(
                "https://sso.courseflow.example.com/realms/courseflow",
                "https://sso.courseflow.example.com/realms/courseflow/protocol/openid-connect/certs",
                "courseflow-api",
                "HS256",
                INTERNAL_SECRET,
                "",
                "",
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                "",
                "api-gateway=" + STS_SECRET,
                "api-gateway",
                "internal:service,internal:token-exchange",
                "",
                180,
                30))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("COURSEFLOW_STS_CLIENT_SCOPES");
    }

    @Test
    void oidcModeAcceptsPerClientStsPolicy() {
        TokenConverterProperties oidcProperties = new TokenConverterProperties(
                "https://sso.courseflow.example.com/realms/courseflow",
                "https://sso.courseflow.example.com/realms/courseflow/protocol/openid-connect/certs",
                "courseflow-api",
                "HS256",
                INTERNAL_SECRET,
                "",
                "",
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                "",
                "api-gateway=" + STS_SECRET,
                "api-gateway",
                "internal:service,internal:token-exchange",
                "api-gateway=internal:service,internal:token-exchange",
                180,
                30);

        assertThat(oidcProperties.serviceClientAllowed("api-gateway")).isTrue();
        assertThat(oidcProperties.serviceScopesForClient("api-gateway", "internal:token-exchange"))
                .containsExactly("internal:token-exchange");
    }

    @Test
    void canIssueTrustedUserTokenWithVerifiedActorToken() {
        TokenConverterProperties stsProperties = stsProperties();
        TokenExchangeService stsService = service(stsProperties);
        String actorToken = internalUserToken("42", "student@courseflow.local", "STUDENT");

        TokenExchangeResponse response = stsService.exchange(
                TokenExchangeService.TRUSTED_USER_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:user",
                "course-service",
                STS_SECRET,
                null,
                null,
                null,
                null,
                actorToken);

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();
        assertThat(claims.getSubject()).isEqualTo("42");
        assertThat(claims.get("actor_type")).isEqualTo("user");
        assertThat(claims.get("azp")).isEqualTo("course-service");
        assertThat(claims.get("roles", List.class)).contains("STUDENT");
        assertThat(claims.get("uid")).isEqualTo("42");
    }

    @Test
    void rejectsTrustedUserTokenWithSelfAssertedClaims() {
        TokenConverterProperties stsProperties = stsProperties();
        TokenExchangeService stsService = service(stsProperties);

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.TRUSTED_USER_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:user",
                "course-service",
                STS_SECRET,
                "42",
                "student@courseflow.local",
                "ADMIN",
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void rejectsTrustedUserTokenWithoutActorToken() {
        TokenConverterProperties stsProperties = stsProperties();
        TokenExchangeService stsService = service(stsProperties);

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.TRUSTED_USER_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:user",
                "course-service",
                STS_SECRET,
                null,
                null,
                null,
                null,
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void rejectsTrustedUserTokenWhenActorTypeIsMissing() {
        TokenConverterProperties stsProperties = stsProperties();
        TokenExchangeService stsService = service(stsProperties);
        String actorToken = internalUserTokenWithoutActorType("42", "student@courseflow.local", "STUDENT");

        assertThatThrownBy(() -> stsService.exchange(
                TokenExchangeService.TRUSTED_USER_GRANT,
                null,
                null,
                "courseflow-services",
                "internal:user",
                "course-service",
                STS_SECRET,
                null,
                null,
                null,
                null,
                actorToken))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void recordsTokenExchangeMetricsForSuccessAndFailure() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        TokenExchangeService metered = service(properties, registry);

        metered.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "courseflow-services",
                "course:read",
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null);

        assertThat(registry.find("courseflow.token_converter.requests")
                .tag("grant_type", "token_exchange")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.find("courseflow.token_converter.success")
                .tag("grant_type", "token_exchange")
                .tag("actor_type", "user")
                .counter()
                .count()).isEqualTo(1.0);

        assertThatThrownBy(() -> metered.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "gradebook-service",
                null,
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null)).isInstanceOf(ResponseStatusException.class);

        assertThat(registry.find("courseflow.token_converter.failure")
                .tag("grant_type", "token_exchange")
                .tag("reason", "audience_is_not_allowed")
                .tag("status", "400")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.find("courseflow.token_converter.duration")
                .tag("grant_type", "token_exchange")
                .tag("outcome", "success")
                .timer()
                .count()).isEqualTo(1);
        assertThat(registry.find("courseflow.token_converter.duration")
                .tag("grant_type", "token_exchange")
                .tag("outcome", "failure")
                .timer()
                .count()).isEqualTo(1);
    }

    @Test
    void auditsTokenExchangeSuccessAndFailure() {
        TokenConverterAudit audit = mock(TokenConverterAudit.class);
        TokenExchangeService audited = service(properties, audit);

        audited.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "courseflow-services",
                "course:read",
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null);

        verify(audit).success(argThat(event -> event != null
                && TokenExchangeService.TOKEN_EXCHANGE_GRANT.equals(event.grantType())
                && "user".equals(event.actorType())
                && "4".equals(event.actorId())
                && "courseflow-services".equals(event.audience())
                && event.scopes().contains("course:read")
                && KEYCLOAK_ISSUER.equals(event.externalIssuer())
                && "student@courseflow.local".equals(event.externalSubject())
                && "200".equals(event.status())));

        assertThatThrownBy(() -> audited.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "gradebook-service",
                null,
                API_GATEWAY_CLIENT_ID,
                STS_SECRET,
                null,
                null,
                null,
                null)).isInstanceOf(ResponseStatusException.class);

        verify(audit).failure(argThat(event -> event != null
                && TokenExchangeService.TOKEN_EXCHANGE_GRANT.equals(event.grantType())
                && "external_user".equals(event.actorType())
                && "gradebook-service".equals(event.audience())
                && "400".equals(event.status())
                && "Audience is not allowed".equals(event.reason())
                && event.scopes().isEmpty()));
    }

    private String externalToken(String subject, String userId, String... roleCodes) {
        return externalTokenWithIssuer(KEYCLOAK_ISSUER, subject, userId, roleCodes);
    }

    private String externalTokenWithIssuer(String issuer, String subject, String userId, String... roleCodes) {
        Instant now = Instant.now();
        List<Map<String, Object>> roles = java.util.Arrays.stream(roleCodes)
                .map(code -> {
                    Map<String, Object> claim = new HashMap<>();
                    claim.put("code", code);
                    claim.put("scopeType", "PLATFORM");
                    claim.put("scopeId", null);
                    return claim;
                })
                .toList();
        return Jwts.builder()
                .issuer(issuer)
                .subject(subject)
                .claim("uid", userId)
                .claim("roles", roles)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(3600)))
                .signWith(Keys.hmacShaKeyFor(EXTERNAL_SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }

    private SecretKey internalKey() {
        return Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8));
    }

    private SecretKey externalKey() {
        return Keys.hmacShaKeyFor(EXTERNAL_SECRET.getBytes(StandardCharsets.UTF_8));
    }

    private String internalUserToken(String userId, String email, String role) {
        return internalUserToken(userId, email, role, true);
    }

    private String internalUserTokenWithoutActorType(String userId, String email, String role) {
        return internalUserToken(userId, email, role, false);
    }

    private String internalUserToken(String userId, String email, String role, boolean includeActorType) {
        Instant now = Instant.now();
        var builder = Jwts.builder()
                .issuer("courseflow-token-converter")
                .subject(userId)
                .claim("aud", List.of("courseflow-services"))
                .claim("token_use", "internal")
                .claim("azp", "api-gateway")
                .claim("uid", userId)
                .claim("email", email)
                .claim("roles", List.of(role))
                .claim("role_assignments", List.of(Map.of(
                        "code", role,
                        "scopeType", "COURSE",
                        "scopeId", "100")))
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(180)));
        if (includeActorType) {
            builder.claim("actor_type", "user");
        }
        return builder.signWith(internalKey()).compact();
    }

    private TokenConverterProperties stsProperties() {
        return new TokenConverterProperties(
                KEYCLOAK_ISSUER,
                KEYCLOAK_JWKS,
                "courseflow-api",
                "HS256",
                INTERNAL_SECRET,
                "",
                "",
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                "",
                "course-service=" + STS_SECRET,
                "course-service",
                "internal:service,internal:user",
                "course-service=internal:service,internal:user",
                180,
                30);
    }

    private TokenConverterProperties stsPropertiesWithClientPolicy() {
        return new TokenConverterProperties(
                KEYCLOAK_ISSUER,
                KEYCLOAK_JWKS,
                "courseflow-api",
                "HS256",
                INTERNAL_SECRET,
                "",
                "",
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                "",
                "course-service=" + STS_SECRET
                        + ";user-management-service=" + USER_MANAGEMENT_STS_SECRET
                        + ";checkout-service=" + CHECKOUT_STS_SECRET
                        + ";promotion-service=" + PROMOTION_STS_SECRET
                        + ";loyalty-service=" + LOYALTY_STS_SECRET,
                "course-service,user-management-service,checkout-service,promotion-service,loyalty-service",
                "internal:service,internal:user,internal:identity:provision,internal:authz:check,"
                        + "internal:promotion:admin,internal:promotion:evaluate,internal:promotion:reserve,"
                        + "internal:promotion:commit,internal:promotion:cancel,internal:promotion:reverse,"
                        + "internal:loyalty:admin,internal:loyalty:read,internal:loyalty:earn,"
                        + "internal:loyalty:burn,internal:loyalty:reverse,internal:loyalty:adjust,"
                        + "internal:loyalty:expire",
                "course-service=internal:service,internal:user;"
                        + "user-management-service=internal:identity:provision,internal:authz:check;"
                        + "checkout-service=internal:service,internal:promotion:evaluate,internal:promotion:reserve,"
                        + "internal:promotion:commit,internal:promotion:cancel,internal:promotion:reverse,"
                        + "internal:loyalty:earn,internal:loyalty:burn,internal:loyalty:reverse,"
                        + "internal:loyalty:read;"
                        + "promotion-service=internal:service,internal:promotion:admin;"
                        + "loyalty-service=internal:service,internal:loyalty:admin,internal:loyalty:read",
                180,
                30);
    }

    private TokenExchangeService service(TokenConverterProperties customProperties) {
        return new TokenExchangeService(
                externalVerifier(customProperties),
                testIdentityResolver(),
                new InternalTokenIssuer(customProperties, new ScopeMapper()),
                customProperties);
    }

    private TokenExchangeService service(TokenConverterProperties customProperties, SimpleMeterRegistry registry) {
        return new TokenExchangeService(
                externalVerifier(customProperties),
                testIdentityResolver(),
                new InternalTokenIssuer(customProperties, new ScopeMapper()),
                customProperties,
                new TokenConverterMetrics(registry));
    }

    private TokenExchangeService service(TokenConverterProperties customProperties, TokenConverterAudit audit) {
        return new TokenExchangeService(
                externalVerifier(customProperties),
                testIdentityResolver(),
                new InternalTokenIssuer(customProperties, new ScopeMapper()),
                customProperties,
                TokenConverterMetrics.noop(),
                audit);
    }

    private ExternalTokenVerifier externalVerifier(TokenConverterProperties customProperties) {
        return new ExternalTokenVerifier(customProperties) {
            @Override
            public ExternalTokenClaims verify(String token) {
                Claims claims = Jwts.parser()
                        .verifyWith(externalKey())
                        .build()
                        .parseSignedClaims(token)
                        .getPayload();
                return new ExternalTokenClaims(claims.getIssuer(), claims.getSubject(), new HashMap<>(claims));
            }
        };
    }

    private ExternalTokenVerifier rejectingExternalVerifier(TokenConverterProperties customProperties) {
        return new ExternalTokenVerifier(customProperties) {
            @Override
            public ExternalTokenClaims verify(String token) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid external token");
            }
        };
    }

    private AccessControlIdentityResolver testIdentityResolver() {
        return externalClaims -> new ResolvedIdentity(
                String.valueOf(externalClaims.get("uid")),
                externalClaims.issuer(),
                externalClaims.subject(),
                externalClaims.stringClaim("email") == null ? externalClaims.subject() : externalClaims.stringClaim("email"),
                "ACTIVE",
                roleAssignments(externalClaims.get("roles")));
    }

    @SuppressWarnings("unchecked")
    private List<ResolvedIdentity.RoleAssignment> roleAssignments(Object rawRoles) {
        if (!(rawRoles instanceof Collection<?> roles)) {
            return List.of();
        }
        return roles.stream()
                .map(raw -> {
                    if (raw instanceof Map<?, ?> map) {
                        Object code = ((Map<String, Object>) map).get("code");
                        if (code == null || code.toString().isBlank()) {
                            return null;
                        }
                        return new ResolvedIdentity.RoleAssignment(
                                code.toString(),
                                stringValue(((Map<String, Object>) map).get("scopeType"), "PLATFORM"),
                                stringValue(((Map<String, Object>) map).get("scopeId"), null));
                    }
                    if (raw != null && !raw.toString().isBlank()) {
                        return new ResolvedIdentity.RoleAssignment(raw.toString(), "PLATFORM", null);
                    }
                    return null;
                })
                .filter(java.util.Objects::nonNull)
                .toList();
    }

    private String stringValue(Object value, String fallback) {
        return value == null || value.toString().isBlank() ? fallback : value.toString();
    }

    private String pem(String label, PrivateKey key) {
        return pem(label, key.getEncoded());
    }

    private String pem(String label, PublicKey key) {
        return pem(label, key.getEncoded());
    }

    private String pem(String label, byte[] encoded) {
        return "-----BEGIN " + label + "-----\n"
                + Base64.getMimeEncoder(64, "\n".getBytes()).encodeToString(encoded)
                + "\n-----END " + label + "-----";
    }
}
