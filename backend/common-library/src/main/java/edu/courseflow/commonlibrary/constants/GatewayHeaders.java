package edu.courseflow.commonlibrary.constants;

/**
 * Identity headers injected by the API gateway after it verifies the JWT. Downstream services
 * trust these because the gateway strips any client-supplied copies first and services are only
 * reachable through the gateway (network isolation).
 */
public final class GatewayHeaders {

    public static final String USER_ID = "X-User-Id";
    /** Primary (highest-ranked) role code, kept for backward compatibility with single-role callers. */
    public static final String USER_ROLE = "X-User-Role";
    /** Comma-separated list of all effective role codes the caller holds. */
    public static final String USER_ROLES = "X-User-Roles";
    public static final String USER_EMAIL = "X-User-Email";
    public static final String CORRELATION_ID = "X-Correlation-Id";

    private GatewayHeaders() {
    }
}
