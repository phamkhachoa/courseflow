package edu.courseflow.commonlibrary.constants;

/**
 * Identity headers injected by the API gateway after it verifies the JWT. Downstream services
 * trust these because the gateway strips any client-supplied copies first and services are only
 * reachable through the gateway (network isolation). Downstream services require a short-lived
 * internal JWT before accepting gateway-propagated identity headers or internal endpoints.
 */
public final class GatewayHeaders {

    public static final String USER_ID = "X-User-Id";
    /** Primary (highest-ranked) role code, kept for backward compatibility with single-role callers. */
    public static final String USER_ROLE = "X-User-Role";
    /** Comma-separated list of all effective role codes the caller holds. */
    public static final String USER_ROLES = "X-User-Roles";
    /**
     * Comma-separated scoped role tuples. Each tuple is
     * {@code base64url(code).base64url(scopeType).base64url(scopeId-or-empty)}.
     */
    public static final String USER_ROLE_SCOPES = "X-User-Role-Scopes";
    public static final String USER_EMAIL = "X-User-Email";
    public static final String CORRELATION_ID = "X-Correlation-Id";
    /** Short-lived internal JWT minted by identity-token-converter-service. */
    public static final String INTERNAL_AUTHORIZATION = "X-Internal-Authorization";

    private GatewayHeaders() {
    }
}
