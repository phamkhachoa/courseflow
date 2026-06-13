package edu.courseflow.gateway;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * The gateway is the single trust boundary. For every inbound request it:
 * <ol>
 *   <li>strips any client-supplied {@code X-User-*} headers so identity cannot be spoofed;</li>
 *   <li>validates the Bearer JWT (HS256, shared secret with identity-service);</li>
 *   <li>exchanges the external JWT for a short-lived internal JWT;</li>
 *   <li>forwards a verified identity to downstream services via legacy {@code X-User-*} headers,
 *       plus {@code X-Internal-Authorization}.</li>
 * </ol>
 * Downstream services are only reachable through the gateway (network isolation) and may read
 * these headers as trusted, e.g. via {@code CurrentUserArgumentResolver} in common-library.
 */
@Component
public class JwtAuthenticationGatewayFilter implements GlobalFilter, Ordered {

    private static final Set<String> PUBLIC_AUTH_PATHS = Set.of(
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/email/verify",
            "/api/v1/auth/email/resend"
    );

    /** Roles allowed through the operator-gated edge (user administration). */
    private static final Set<String> OPERATOR_ROLES = Set.of("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA");

    /** Most-privileged first; used to pick the single {@code X-User-Role} value for legacy callers. */
    private static final List<String> ROLE_RANK =
            List.of("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA", "STUDENT");

    private final SecretKey secretKey;
    private final InternalTokenConverterClient tokenConverter;

    @Autowired
    public JwtAuthenticationGatewayFilter(JwtSecretProperties jwtSecretProperties,
            InternalTokenConverterClient tokenConverter) {
        this.secretKey = jwtSecretProperties.secretKey();
        this.tokenConverter = tokenConverter == null ? InternalTokenConverterClient.disabled() : tokenConverter;
    }

    JwtAuthenticationGatewayFilter(JwtSecretProperties jwtSecretProperties) {
        this(jwtSecretProperties, InternalTokenConverterClient.disabled());
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        // Always strip identity headers — only the gateway may set them.
        ServerHttpRequest.Builder builder = request.mutate().headers(headers -> {
            headers.remove(GatewayHeaders.USER_ID);
            headers.remove(GatewayHeaders.USER_ROLE);
            headers.remove(GatewayHeaders.USER_ROLES);
            headers.remove(GatewayHeaders.USER_ROLE_SCOPES);
            headers.remove(GatewayHeaders.USER_EMAIL);
            headers.remove(GatewayHeaders.INTERNAL_AUTHORIZATION);
        });

        if (isPublic(path, request.getMethod().name())) {
            return chain.filter(exchange.mutate().request(builder.build()).build());
        }

        String authHeader = request.getHeaders().getFirst("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return unauthorized(exchange, "Missing bearer token");
        }

        try {
            String externalToken = authHeader.substring(7);
            Claims claims = Jwts.parser()
                    .verifyWith(secretKey)
                    .build()
                    .parseSignedClaims(externalToken)
                    .getPayload();

            String userId = requireClaim(claims, "uid");
            String email = claims.getSubject();
            if (email == null || email.isBlank()) {
                return unauthorized(exchange, "Token subject is missing");
            }

            // identity-service issues a `roles` claim: an array of {code, scopeType, scopeId}.
            List<RoleClaim> roleClaims = extractRoleClaims(claims);
            Set<String> roleCodes = roleClaims.stream()
                    .map(RoleClaim::code)
                    .collect(java.util.stream.Collectors.toCollection(LinkedHashSet::new));
            if (roleCodes.isEmpty()) {
                return unauthorized(exchange, "Token carries no roles");
            }
            String primaryRole = primaryRole(roleCodes);

            if (isOperatorPath(path) && roleCodes.stream().noneMatch(OPERATOR_ROLES::contains)) {
                return forbidden(exchange, "Admin API requires an operator role");
            }

            builder.header(GatewayHeaders.USER_ID, userId)
                    .header(GatewayHeaders.USER_ROLE, primaryRole)
                    .header(GatewayHeaders.USER_ROLES, String.join(",", roleCodes))
                    .header(GatewayHeaders.USER_ROLE_SCOPES, encodeRoleScopes(roleClaims))
                    .header(GatewayHeaders.USER_EMAIL, email);

            return forwardWithInternalToken(exchange, chain, builder, externalToken);
        } catch (JwtException | IllegalArgumentException ex) {
            return unauthorized(exchange, "Invalid or expired token");
        }
    }

    private Mono<Void> forwardWithInternalToken(ServerWebExchange exchange, GatewayFilterChain chain,
                                                ServerHttpRequest.Builder builder, String externalToken) {
        if (!tokenConverter.enabled()) {
            return error(exchange, HttpStatus.BAD_GATEWAY, "Bad Gateway", "Internal token converter is disabled");
        }
        Mono<Void> conversionFailure =
                error(exchange, HttpStatus.BAD_GATEWAY, "Bad Gateway", "Internal token conversion failed");

        return tokenConverter.exchange(externalToken)
                .flatMap(internalToken -> {
                    ServerHttpRequest converted = builder.headers(headers -> {
                        String bearer = "Bearer " + internalToken;
                        headers.set("Authorization", bearer);
                        headers.set(GatewayHeaders.INTERNAL_AUTHORIZATION, bearer);
                    }).build();
                    return chain.filter(exchange.mutate().request(converted).build());
                })
                .switchIfEmpty(conversionFailure)
                .onErrorResume(ex -> conversionFailure);
    }

    private boolean isPublic(String path, String method) {
        // WebSocket handshake authenticates inside the STOMP CONNECT frame at notification-service.
        if (path.startsWith("/ws")) {
            return true;
        }
        if ("/actuator/health".equals(path) || PUBLIC_AUTH_PATHS.contains(path)) {
            return true;
        }
        return "GET".equalsIgnoreCase(method) && isPublicReadPath(path);
    }

    private boolean isPublicReadPath(String path) {
        if (path.equals("/api/v1/courses") || path.matches("/api/v1/courses/[^/]+")
                || path.matches("/api/v1/courses/[^/]+/related")) {
            return true;
        }
        return path.startsWith("/api/v1/search")
                || path.startsWith("/api/v1/certificates/verify")
                || path.startsWith("/api/v1/reviews/courses");
    }

    private boolean isOperatorPath(String path) {
        return path.startsWith("/api/admin/");
    }

    private String requireClaim(Claims claims, String name) {
        Object value = claims.get(name);
        if (value == null || value.toString().isBlank()) {
            throw new IllegalArgumentException("Missing JWT claim: " + name);
        }
        return value.toString();
    }

    /**
     * Pull the distinct role codes out of the {@code roles} claim. The claim is an array of
     * {@code {code, scopeType, scopeId}} maps; we only need the codes at the edge — scope-aware
     * decisions are delegated to identity-service's {@code /internal/authz/check}. Order is
     * preserved so {@link #primaryRole} can pick deterministically.
     */
    @SuppressWarnings("unchecked")
    private List<RoleClaim> extractRoleClaims(Claims claims) {
        Object raw = claims.get("roles");
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        List<RoleClaim> roles = new java.util.ArrayList<>();
        for (Object element : list) {
            if (element instanceof Map<?, ?> map) {
                Object code = ((Map<String, Object>) map).get("code");
                if (code != null && !code.toString().isBlank()) {
                    Object scopeType = ((Map<String, Object>) map).get("scopeType");
                    Object scopeId = ((Map<String, Object>) map).get("scopeId");
                    roles.add(new RoleClaim(
                            code.toString(),
                            scopeType == null ? "PLATFORM" : scopeType.toString(),
                            scopeId == null ? null : scopeId.toString()));
                }
            } else if (element != null && !element.toString().isBlank()) {
                // Tolerate a plain array of code strings.
                roles.add(new RoleClaim(element.toString(), "PLATFORM", null));
            }
        }
        return roles;
    }

    private String encodeRoleScopes(List<RoleClaim> roleClaims) {
        return roleClaims.stream()
                .map(claim -> encode(claim.code()) + "." + encode(claim.scopeType()) + "." + encode(claim.scopeId()))
                .collect(java.util.stream.Collectors.joining(","));
    }

    private String encode(String raw) {
        if (raw == null || raw.isBlank()) {
            return "";
        }
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Choose the highest-ranked role as the single {@code X-User-Role} value (backward compat).
     * Operator roles outrank STUDENT; among operators we keep the most privileged first.
     */
    private String primaryRole(Set<String> roleCodes) {
        return ROLE_RANK.stream()
                .filter(roleCodes::contains)
                .findFirst()
                .orElse(roleCodes.iterator().next());
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange, String message) {
        return error(exchange, HttpStatus.UNAUTHORIZED, "Unauthorized", message);
    }

    private Mono<Void> forbidden(ServerWebExchange exchange, String message) {
        return error(exchange, HttpStatus.FORBIDDEN, "Forbidden", message);
    }

    private Mono<Void> error(ServerWebExchange exchange, HttpStatus status, String title, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(status);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] body = ("{\"statusCode\":\"" + status + "\",\"title\":\"" + title + "\",\"detail\":\""
                + message + "\"}").getBytes(StandardCharsets.UTF_8);
        return response.writeWith(Mono.just(response.bufferFactory().wrap(body)));
    }

    @Override
    public int getOrder() {
        // Right after correlation-id propagation.
        return Ordered.HIGHEST_PRECEDENCE + 1;
    }

    private record RoleClaim(String code, String scopeType, String scopeId) {
    }
}
