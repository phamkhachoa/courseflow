package edu.courseflow.gateway;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
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
 *   <li>validates the external Bearer JWT (legacy HS256 or OAuth2/OIDC JWKS);</li>
 *   <li>exchanges the external JWT for a short-lived internal JWT;</li>
 *   <li>forwards identity derived from the verified internal JWT via legacy {@code X-User-*}
 *       headers, plus {@code X-Internal-Authorization}.</li>
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

    private final GatewayExternalTokenVerifier externalTokenVerifier;
    private final ExternalTokenProperties externalTokenProperties;
    private final InternalTokenConverterClient tokenConverter;
    private final InternalJwtService internalJwtService;

    @Autowired
    public JwtAuthenticationGatewayFilter(GatewayExternalTokenVerifier externalTokenVerifier,
            ExternalTokenProperties externalTokenProperties,
            InternalTokenConverterClient tokenConverter,
            InternalJwtService internalJwtService) {
        this.externalTokenVerifier = externalTokenVerifier;
        this.externalTokenProperties = externalTokenProperties;
        this.tokenConverter = tokenConverter == null ? InternalTokenConverterClient.disabled() : tokenConverter;
        this.internalJwtService = internalJwtService;
    }

    JwtAuthenticationGatewayFilter(GatewayExternalTokenVerifier externalTokenVerifier,
            ExternalTokenProperties externalTokenProperties,
            InternalTokenConverterClient tokenConverter,
            InternalJwtService internalJwtService,
            boolean testConstructor) {
        this(externalTokenVerifier, externalTokenProperties, tokenConverter, internalJwtService);
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

        if (isLegacyAuthPath(path) && !externalTokenProperties.legacyMode()) {
            return error(exchange, HttpStatus.GONE, "Gone", "Legacy auth endpoints are disabled in OIDC mode");
        }

        if (isPublic(path, request.getMethod().name())) {
            return chain.filter(exchange.mutate().request(builder.build()).build());
        }

        String authHeader = request.getHeaders().getFirst("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return unauthorized(exchange, "Missing bearer token");
        }

        String externalToken = authHeader.substring(7);
        return externalTokenVerifier.verify(externalToken)
                .then(forwardWithInternalToken(exchange, chain, builder, externalToken))
                .onErrorResume(ex -> unauthorized(exchange, "Invalid or expired token"));
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
                    IdentityHeaders identity;
                    try {
                        Claims internalClaims = internalJwtService.verify(internalToken);
                        identity = identityHeaders(internalClaims, exchange.getRequest().getURI().getPath());
                    } catch (OperatorForbiddenException ex) {
                        return forbidden(exchange, "Admin API requires an operator role");
                    } catch (JwtException | IllegalArgumentException | IllegalStateException ex) {
                        return conversionFailure;
                    }
                    ServerHttpRequest converted = builder.headers(headers ->
                            writeInternalIdentityHeaders(headers, internalToken, identity)).build();
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

    private boolean isLegacyAuthPath(String path) {
        return path.startsWith("/api/v1/auth/");
    }

    private boolean isPublicReadPath(String path) {
        if (path.equals("/api/v1/courses") || path.matches("/api/v1/courses/[^/]+")
                || path.matches("/api/v1/courses/[^/]+/related")) {
            return true;
        }
        return path.startsWith("/api/v1/search")
                || path.matches("/api/v1/profiles/[^/]+")
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
     * Pull role assignment tuples out of the verified internal JWT. The converter writes
     * `role_assignments` as an array of `{code, scopeType, scopeId}` maps; older/legacy internal
     * tokens may only have `roles`, so we tolerate both shapes.
     */
    @SuppressWarnings("unchecked")
    private List<RoleClaim> extractRoleClaims(Claims claims) {
        Object rawAssignments = claims.get("role_assignments");
        if (rawAssignments instanceof List<?> assignments && !assignments.isEmpty()) {
            return roleClaims(assignments);
        }
        Object rawRoles = claims.get("roles");
        if (rawRoles instanceof List<?> roles) {
            return roleClaims(roles);
        }
        return List.of();
    }

    @SuppressWarnings("unchecked")
    private List<RoleClaim> roleClaims(List<?> list) {
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

    private IdentityHeaders identityHeaders(Claims claims, String path) {
        String userId = requireClaim(claims, "uid");
        String email = claims.get("email", String.class);
        List<RoleClaim> roleClaims = extractRoleClaims(claims);
        Set<String> roleCodes = roleClaims.stream()
                .map(RoleClaim::code)
                .collect(java.util.stream.Collectors.toCollection(LinkedHashSet::new));
        if (roleCodes.isEmpty()) {
            throw new IllegalArgumentException("Internal token carries no roles");
        }
        if (isOperatorPath(path) && roleCodes.stream().noneMatch(OPERATOR_ROLES::contains)) {
            throw new OperatorForbiddenException();
        }
        return new IdentityHeaders(userId, email, primaryRole(roleCodes), roleCodes, roleClaims);
    }

    private void writeInternalIdentityHeaders(org.springframework.http.HttpHeaders headers,
                                              String internalToken,
                                              IdentityHeaders identity) {
        String bearer = "Bearer " + internalToken;
        headers.set("Authorization", bearer);
        headers.set(GatewayHeaders.INTERNAL_AUTHORIZATION, bearer);
        headers.set(GatewayHeaders.USER_ID, identity.userId());
        headers.set(GatewayHeaders.USER_ROLE, identity.primaryRole());
        headers.set(GatewayHeaders.USER_ROLES, String.join(",", identity.roleCodes()));
        headers.set(GatewayHeaders.USER_ROLE_SCOPES, encodeRoleScopes(identity.roleClaims()));
        if (identity.email() != null && !identity.email().isBlank()) {
            headers.set(GatewayHeaders.USER_EMAIL, identity.email());
        }
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

    private record IdentityHeaders(String userId, String email, String primaryRole, Set<String> roleCodes,
                                   List<RoleClaim> roleClaims) {
    }

    private static final class OperatorForbiddenException extends RuntimeException {
    }
}
