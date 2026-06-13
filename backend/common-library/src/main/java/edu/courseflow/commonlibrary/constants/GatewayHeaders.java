package edu.courseflow.commonlibrary.constants;

/**
 * Identity headers injected by the API gateway after it verifies the JWT. Downstream services
 * trust these because the gateway strips any client-supplied copies first and services are only
 * reachable through the gateway (network isolation). When {@link #SERVICE_TOKEN} is configured,
 * downstream services also require it before accepting any propagated identity header.
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
    /** Shared gateway-to-service attestation header. Clients must never be allowed to supply it. */
    public static final String SERVICE_TOKEN = "X-Service-Token";

    private GatewayHeaders() {
    }
}
