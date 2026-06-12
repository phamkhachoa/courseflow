package edu.courseflow.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
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

    private static JwtAuthenticationGatewayFilter newFilter() {
        return new JwtAuthenticationGatewayFilter(new JwtSecretProperties(SECRET));
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
                .header(GatewayHeaders.USER_EMAIL, "spoofed@example.com")
                .build();

        filter.filter(MockServerWebExchange.from(request), chain).block();

        assertThat(forwarded.get()).isNotNull();
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ID)).isEqualTo("4");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLE)).isEqualTo("STUDENT");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_ROLES)).isEqualTo("STUDENT");
        assertThat(forwarded.get().getRequest().getHeaders().getFirst(GatewayHeaders.USER_EMAIL))
                .isEqualTo("student@courseflow.local");
    }

    @Test
    void forwardsAllRoleCodesAndPicksHighestRankedPrimary() {
        JwtAuthenticationGatewayFilter filter = newFilter();
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
        JwtAuthenticationGatewayFilter filter = newFilter();
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
    void allowsPublicRegistrationWithoutBearerToken() {
        JwtAuthenticationGatewayFilter filter = newFilter();
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        GatewayFilterChain chain = exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };

        filter.filter(MockServerWebExchange.from(MockServerHttpRequest.post("/api/v1/auth/register").build()), chain)
                .block();

        assertThat(forwarded.get()).isNotNull();
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
        JwtAuthenticationGatewayFilter filter = newFilter();
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

    /**
     * Mint a token the way identity-service does: a {@code roles} claim that is an array of
     * {@code {code, scopeType, scopeId}} maps (not a single {@code role} string).
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
}
