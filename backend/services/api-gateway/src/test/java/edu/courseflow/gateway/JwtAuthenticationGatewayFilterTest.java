package edu.courseflow.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Collectors;
import javax.crypto.SecretKey;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

class JwtAuthenticationGatewayFilterTest {

    private static final String SECRET = "test-secret-key-that-is-comfortably-over-32-bytes-long";
    private static final String INTERNAL_SECRET = "internal-test-secret-that-is-comfortably-over-32-bytes";

    private static JwtAuthenticationGatewayFilter newFilter() {
        return newFilter(converter(internalToken("4", "student@courseflow.local", "STUDENT")));
    }

    private static JwtAuthenticationGatewayFilter newFilter(InternalTokenConverterClient converter) {
        return new JwtAuthenticationGatewayFilter(token -> Mono.empty(), converter, internalJwt(), true);
    }

    private static InternalJwtService internalJwt() {
        return new InternalJwtService(new InternalJwtProperties(
                INTERNAL_SECRET,
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "api-gateway"));
    }

    private static InternalTokenConverterClient converter(String token) {
        return new InternalTokenConverterClient() {
            @Override
            public boolean enabled() {
                return true;
            }

            @Override
            public boolean required() {
                return true;
            }

            @Override
            public Mono<String> exchange(String subjectToken) {
                return Mono.just(token);
            }
        };
    }

    @Test
    void stripsSpoofedHeadersAndInjectsVerifiedClaims() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/assignments")
                .header("Authorization", "Bearer " + accessToken("student@courseflow.local", "4", "STUDENT"))
                .header(GatewayHeaders.USER_ID, "999")
                .header(GatewayHeaders.USER_ROLE, "ADMIN")
                .header(GatewayHeaders.USER_ROLE_SCOPES, "spoofed.scope.header")
                .header(GatewayHeaders.USER_EMAIL, "spoofed@example.com")
                .header(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer spoofed-internal-token")
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ID)).isEqualTo("4");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE)).isEqualTo("STUDENT");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLES)).isEqualTo("STUDENT");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE_SCOPES))
                .doesNotContain("spoofed");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_EMAIL))
                .isEqualTo("student@courseflow.local");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.INTERNAL_AUTHORIZATION))
                .startsWith("Bearer ");
    }

    @Test
    void injectsInternalTokenWhenConverterIsEnabled() {
        String internalToken = internalToken("4", "student@courseflow.local", "STUDENT");
        InternalTokenConverterClient converter = new InternalTokenConverterClient() {
            @Override
            public boolean enabled() {
                return true;
            }

            @Override
            public boolean required() {
                return false;
            }

            @Override
            public Mono<String> exchange(String subjectToken) {
                return Mono.just(internalToken);
            }
        };
        JwtAuthenticationGatewayFilter filter = newFilter(converter);
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/assignments")
                .header("Authorization", "Bearer " + accessToken("student@courseflow.local", "4", "STUDENT"))
                .header(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer forged")
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        assertThat(forwarded.get().getRequest().getHeaders().getFirst("Authorization"))
                .isEqualTo("Bearer " + internalToken);
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.INTERNAL_AUTHORIZATION))
                .isEqualTo("Bearer " + internalToken);
    }

    @Test
    void failsClosedWhenRequiredConverterCannotIssueToken() {
        InternalTokenConverterClient converter = new InternalTokenConverterClient() {
            @Override
            public boolean enabled() {
                return true;
            }

            @Override
            public boolean required() {
                return true;
            }

            @Override
            public Mono<String> exchange(String subjectToken) {
                return Mono.error(new IllegalStateException("converter down"));
            }
        };
        JwtAuthenticationGatewayFilter filter = newFilter(converter);
        MockServerWebExchange exchange = MockServerWebExchange.from(MockServerHttpRequest.get("/api/v1/assignments")
                .header("Authorization", "Bearer " + accessToken("student@courseflow.local", "4", "STUDENT"))
                .build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.BAD_GATEWAY);
    }

    @Test
    void failsClosedWhenConverterReturnsNonUserInternalToken() {
        JwtAuthenticationGatewayFilter filter = newFilter(converter(internalTokenWithActorType(
                "service", "4", "student@courseflow.local", "STUDENT")));
        MockServerWebExchange exchange = MockServerWebExchange.from(MockServerHttpRequest.get("/api/v1/assignments")
                .header("Authorization", "Bearer " + accessToken("student@courseflow.local", "4", "STUDENT"))
                .build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.BAD_GATEWAY);
    }

    @Test
    void forwardsAllRoleCodesAndPicksHighestRankedPrimary() {
        JwtAuthenticationGatewayFilter filter = newFilter(converter(internalToken(
                "7", "ta@courseflow.local", "STUDENT", "TA")));
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        // A TA who is also a STUDENT in another course: both codes ride along, TA wins as primary.
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/assignments")
                .header("Authorization", "Bearer " + accessToken("ta@courseflow.local", "7", "STUDENT", "TA"))
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE)).isEqualTo("TA");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLES))
                .isEqualTo("STUDENT,TA");
    }

    @Test
    void rejectsProtectedRequestWithoutBearerToken() {
        JwtAuthenticationGatewayFilter filter = newFilter(converter(internalToken(
                "7", "ta@courseflow.local", "STUDENT", "TA")));
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/assignments").build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void allowsPublicCatalogReadWithoutBearerToken() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        filter.filter(MockServerWebExchange.from(MockServerHttpRequest.get("/api/v1/courses").build()), chain)
                .block();

        assertThat(forwarded.get()).isNotNull();
    }

    @Test
    void allowsPublicProfileReadWithoutBearerToken() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        filter.filter(MockServerWebExchange.from(MockServerHttpRequest.get("/api/v1/profiles/42").build()), chain)
                .block();

        assertThat(forwarded.get()).isNotNull();
    }

    @Test
    void keepsProfileSummaryBatchProtected() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.post("/api/v1/profiles/summary:batch").build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void blocksRemovedRegistrationEndpointWithoutBearerToken() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        filter.filter(MockServerWebExchange.from(MockServerHttpRequest.post("/api/v1/auth/register").build()), chain)
                .block();

        assertThat(forwarded.get()).isNull();
    }

    @Test
    void blocksRemovedAuthEndpoints() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.post("/api/v1/auth/login").build());

        filter.filter(exchange, chain).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.GONE);
        assertThat(forwarded.get()).isNull();
    }

    @Test
    void blocksAllRemovedAuthSubpaths() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.post("/api/v1/auth/logout")
                        .header("Authorization", "Bearer " + accessToken("admin@courseflow.local", "1", "ADMIN"))
                        .build());

        filter.filter(exchange, chain).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.GONE);
        assertThat(forwarded.get()).isNull();
    }

    @Test
    void blocksRemovedEmailVerificationEndpointWithoutBearerToken() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        filter.filter(MockServerWebExchange.from(
                        MockServerHttpRequest.post("/api/v1/auth/email/verify").build()),
                chain).block();

        assertThat(forwarded.get()).isNull();
    }

    @Test
    void rejectsCourseModuleReadWithoutBearerToken() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/courses/30000000-0000-0000-0000-000000000001/modules").build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    @Test
    void allowsAuthenticatedStudentThroughNonOperatorRoute() {
        // Learner/user API is authenticated but not operator-gated.
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/assignments")
                .header("Authorization", "Bearer " + accessToken("student@courseflow.local", "4", "STUDENT"))
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE)).isEqualTo("STUDENT");
    }

    @Test
    void rejectsStudentAccessToUserManagementRoute() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        MockServerWebExchange exchange = MockServerWebExchange.from(MockServerHttpRequest.get("/api/admin/v1/users")
                .header("Authorization", "Bearer " + accessToken("student@courseflow.local", "4", "STUDENT"))
                .build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
    }

    @Test
    void allowsOperatorWithMultipleRolesIntoUserManagement() {
        JwtAuthenticationGatewayFilter filter = newFilter(converter(internalToken(
                "7", "ta@courseflow.local", "STUDENT", "TA")));
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerHttpRequest request = MockServerHttpRequest.get("/api/admin/v1/users")
                .header("Authorization", "Bearer " + accessToken("ta@courseflow.local", "7", "STUDENT", "TA"))
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        // Primary role is the highest-ranked code; X-User-Roles carries the full set.
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE)).isEqualTo("TA");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLES))
                .contains("STUDENT").contains("TA");
    }

    @Test
    void allowsIncentiveOperatorIntoAdminApi() {
        JwtAuthenticationGatewayFilter filter = newFilter(converter(internalToken(
                "17", "ops@courseflow.local", "INCENTIVE_OPERATOR")));
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerHttpRequest request = MockServerHttpRequest.get("/api/admin/v1/incentives/ops-console")
                .header("Authorization", "Bearer " + accessToken("ops@courseflow.local", "17", "INCENTIVE_OPERATOR"))
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE))
                .isEqualTo("INCENTIVE_OPERATOR");
    }

    @Test
    void allowsLoyaltyOperatorIntoLoyaltyAdminApi() {
        JwtAuthenticationGatewayFilter filter = newFilter(converter(internalToken(
                "18", "loyalty-ops@courseflow.local", "STUDENT", "LOYALTY_OPERATOR")));
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        MockServerHttpRequest request = MockServerHttpRequest.get("/api/admin/v1/loyalty/dead-letters")
                .header("Authorization", "Bearer " + accessToken(
                        "loyalty-ops@courseflow.local", "18", "STUDENT", "LOYALTY_OPERATOR"))
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE))
                .isEqualTo("LOYALTY_OPERATOR");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLES))
                .isEqualTo("STUDENT,LOYALTY_OPERATOR");
    }

    /**
     * Mint a representative external token for tests. The verifier is stubbed here; identity is
     * derived from the exchanged internal token.
     */
    private String accessToken(String subject, String userId, String... roleCodes) {
        Instant now = Instant.now();
        SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
        List<Map<String, Object>> roles = Arrays.stream(roleCodes)
                .map(code -> {
                    Map<String, Object> claim = new HashMap<>();
                    claim.put("code", code);
                    claim.put("scopeType", "PLATFORM");
                    claim.put("scopeId", null);
                    return claim;
                })
                .collect(Collectors.toList());
        return Jwts.builder()
                .subject(subject)
                .claim("uid", userId)
                .claim("roles", roles)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(3600)))
                .signWith(key)
                .compact();
    }

    private static String internalToken(String userId, String email, String... roleCodes) {
        return internalTokenWithActorType("user", userId, email, roleCodes);
    }

    private static String internalTokenWithActorType(String actorType, String userId, String email,
                                                    String... roleCodes) {
        Instant now = Instant.now();
        SecretKey key = Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8));
        List<Map<String, Object>> roleAssignments = Arrays.stream(roleCodes)
                .map(code -> {
                    Map<String, Object> claim = new HashMap<>();
                    claim.put("code", code);
                    claim.put("scopeType", "PLATFORM");
                    claim.put("scopeId", null);
                    return claim;
                })
                .collect(Collectors.toList());
        return Jwts.builder()
                .issuer("courseflow-token-converter")
                .subject(userId)
                .claim("aud", List.of("courseflow-services"))
                .claim("token_use", "internal")
                .claim("actor_type", actorType)
                .claim("uid", userId)
                .claim("email", email)
                .claim("roles", Arrays.asList(roleCodes))
                .claim("role_assignments", roleAssignments)
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(180)))
                .signWith(key)
                .compact();
    }
}
