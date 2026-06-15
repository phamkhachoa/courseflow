package edu.courseflow.commonlibrary.web;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Defense-in-depth for gateway-propagated identity headers.
 *
 * <p>The API gateway is still the primary trust boundary: it strips client-supplied identity headers,
 * verifies JWTs, then injects {@code X-User-*}. This filter closes the direct-service access gap:
 * downstream services only accept propagated identity headers, {@code /internal/**} endpoints and
 * {@code /backoffice/**} endpoints when the request carries a valid short-lived internal JWT.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class TrustedGatewayHeaderFilter extends OncePerRequestFilter {

    private static final List<String> IDENTITY_HEADERS = List.of(
            GatewayHeaders.USER_ID,
            GatewayHeaders.USER_ROLE,
            GatewayHeaders.USER_ROLES,
            GatewayHeaders.USER_ROLE_SCOPES,
            GatewayHeaders.USER_EMAIL);
    private static final String REJECTION_METRIC = "courseflow.internal_jwt.rejections";

    private final InternalJwtService internalJwtService;
    private final MeterRegistry meterRegistry;

    public TrustedGatewayHeaderFilter(InternalJwtService internalJwtService) {
        this(internalJwtService, (MeterRegistry) null);
    }

    @Autowired
    public TrustedGatewayHeaderFilter(
            InternalJwtService internalJwtService, ObjectProvider<MeterRegistry> meterRegistryProvider) {
        this(internalJwtService, meterRegistryProvider.getIfAvailable());
    }

    TrustedGatewayHeaderFilter(InternalJwtService internalJwtService, MeterRegistry meterRegistry) {
        this.internalJwtService = internalJwtService;
        this.meterRegistry = meterRegistry;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if (!requiresInternalJwt(request)) {
            filterChain.doFilter(request, response);
            return;
        }

        RejectionReason rejectionReason = internalJwtRejectionReason(request);
        if (rejectionReason == null) {
            filterChain.doFilter(request, response);
            return;
        }

        recordRejection(rejectionReason, request);
        deny(response);
    }

    private boolean hasIdentityHeaders(HttpServletRequest request) {
        return IDENTITY_HEADERS.stream().anyMatch(header -> request.getHeader(header) != null);
    }

    private boolean requiresInternalJwt(HttpServletRequest request) {
        String path = request.getRequestURI();
        return path.startsWith("/internal/") || path.startsWith("/backoffice/") || hasIdentityHeaders(request);
    }

    private RejectionReason internalJwtRejectionReason(HttpServletRequest request) {
        String header = firstBearerHeader(request);
        if (header == null) {
            return RejectionReason.MISSING;
        }
        try {
            Claims claims = internalJwtService.verify(header);
            if (!"internal".equals(claims.get("token_use", String.class))) {
                return RejectionReason.WRONG_TOKEN_USE;
            }
            String actorType = claims.get("actor_type", String.class);
            if (!"user".equals(actorType) && !"service".equals(actorType)) {
                return RejectionReason.WRONG_ACTOR_TYPE;
            }
            if (hasIdentityHeaders(request) && !"user".equals(actorType)) {
                return RejectionReason.WRONG_ACTOR_TYPE;
            }
            if (requiresServiceActor(request) && !"service".equals(actorType)) {
                return RejectionReason.WRONG_ACTOR_TYPE;
            }
            if (hasIdentityHeaders(request) && !identityClaimsMatchHeaders(claims, request)) {
                return RejectionReason.IDENTITY_MISMATCH;
            }
            if (requiresGatewayIdentityHeaders(claims, request)) {
                return RejectionReason.MISSING_IDENTITY_HEADERS;
            }
            if (serviceScopeMissing(claims, request)) {
                return RejectionReason.INSUFFICIENT_SCOPE;
            }
            return null;
        } catch (JwtException | IllegalArgumentException | IllegalStateException ex) {
            return RejectionReason.INVALID;
        }
    }

    private boolean requiresGatewayIdentityHeaders(Claims claims, HttpServletRequest request) {
        if (!requiresInternalJwt(request) || "service".equals(claims.get("actor_type", String.class))) {
            return false;
        }
        return !hasIdentityHeaders(request);
    }

    private boolean serviceScopeMissing(Claims claims, HttpServletRequest request) {
        if (!"service".equals(claims.get("actor_type", String.class))) {
            return false;
        }
        Set<String> required = requiredServiceScopes(request);
        if (required.isEmpty()) {
            return false;
        }
        Set<String> granted = extractScopes(claims);
        return !granted.contains("*") && required.stream().noneMatch(granted::contains);
    }

    private boolean requiresServiceActor(HttpServletRequest request) {
        String path = request.getRequestURI();
        return path.startsWith("/internal/identities/")
                || path.startsWith("/internal/authz/check")
                || path.startsWith("/internal/users/provision-profile")
                || isCourseModuleServiceOnlyEndpoint(path)
                || isEnrollmentServiceOnlyEndpoint(path);
    }

    private boolean isCourseModuleServiceOnlyEndpoint(String path) {
        return path.matches("^/internal/courses/[^/]+/modules/[^/]+/items/[^/]+/progress/verified$")
                || path.matches("^/internal/courses/[^/]+/modules/items/progress/verified$")
                || path.matches("^/internal/courses/[^/]+/modules/progress/internal$");
    }

    private boolean isEnrollmentServiceOnlyEndpoint(String path) {
        return path.equals("/internal/enrollments/access")
                || path.equals("/internal/enrollments/roster")
                || path.equals("/internal/learner-memberships")
                || path.matches("^/internal/enrollments/orders/[^/]+:record-payment$");
    }

    private Set<String> requiredServiceScopes(HttpServletRequest request) {
        String path = request.getRequestURI();
        String method = request.getMethod();
        if (path.startsWith("/backoffice/")) {
            return Set.of(InternalScopes.BACKOFFICE);
        }
        if (path.startsWith("/internal/identities/resolve")) {
            return Set.of(InternalScopes.IDENTITY_RESOLVE);
        }
        if (path.startsWith("/internal/identities/provision")) {
            return Set.of(InternalScopes.IDENTITY_PROVISION);
        }
        if (path.startsWith("/internal/authz/check")) {
            return Set.of(InternalScopes.AUTHZ_CHECK);
        }
        if (path.equals("/internal/permissions") || path.startsWith("/internal/roles")) {
            return Set.of("GET".equalsIgnoreCase(method)
                    ? InternalScopes.ROLE_MANAGEMENT_READ
                    : InternalScopes.ROLE_MANAGEMENT_WRITE);
        }
        if (path.startsWith("/internal/users/provision-profile")) {
            return Set.of(InternalScopes.PROFILE_WRITE);
        }
        if (path.startsWith("/internal/profiles/")) {
            return Set.of("GET".equalsIgnoreCase(method) || path.endsWith(":batch")
                    ? InternalScopes.PROFILE_READ
                    : InternalScopes.PROFILE_WRITE);
        }
        if (path.equals("/internal/users") || path.startsWith("/internal/users/")) {
            return userDirectoryScopes(path, method);
        }
        if (path.equals("/internal/incentives") || path.startsWith("/internal/incentives/")) {
            return promotionScopes(path, method);
        }
        if (path.equals("/internal/loyalty") || path.startsWith("/internal/loyalty/")) {
            return loyaltyScopes(path, method);
        }
        if (path.equals("/internal/analytics/marketing/funnel/events")) {
            return Set.of(InternalScopes.ANALYTICS_FUNNEL_WRITE);
        }
        if (path.equals("/internal/analytics/warehouse/exports")) {
            return Set.of(InternalScopes.ANALYTICS_EXPORT_READ);
        }
        if (path.equals("/internal/analytics/recommendations/events")) {
            return Set.of(InternalScopes.ANALYTICS_EVENT_WRITE);
        }
        if (path.startsWith("/internal/analytics/recommendations/batch/")) {
            return Set.of(InternalScopes.ANALYTICS_MODEL_WRITE);
        }
        if (path.startsWith("/internal/recommendation-ml/")) {
            return recommendationMlScopes(path, method);
        }
        if (path.startsWith("/internal/")) {
            return Set.of(InternalScopes.SERVICE);
        }
        return Set.of();
    }

    private Set<String> recommendationMlScopes(String path, String method) {
        if (path.equals("/internal/recommendation-ml/related-courses:train")
                || path.equals("/internal/recommendation-ml/related-courses:enqueue")) {
            return Set.of(InternalScopes.RECOMMENDATION_ML_TRAIN);
        }
        if ("GET".equalsIgnoreCase(method)
                && path.matches("^/internal/recommendation-ml/training-runs/[^/]+$")) {
            return Set.of(InternalScopes.RECOMMENDATION_ML_TRAIN);
        }
        if ("GET".equalsIgnoreCase(method)
                && (path.equals("/internal/recommendation-ml/models/active")
                || path.matches("^/internal/recommendation-ml/courses/[^/]+/related$"))) {
            return Set.of(InternalScopes.RECOMMENDATION_ML_INFER);
        }
        return Set.of(InternalScopes.RECOMMENDATION_ML_OPS);
    }

    private Set<String> loyaltyScopes(String path, String method) {
        if ("GET".equalsIgnoreCase(method)) {
            return Set.of(InternalScopes.LOYALTY_READ);
        }
        if (path.equals("/internal/loyalty/points:earn")) {
            return Set.of(InternalScopes.LOYALTY_EARN);
        }
        if (path.equals("/internal/loyalty/points:burn")) {
            return Set.of(InternalScopes.LOYALTY_BURN);
        }
        if (path.matches("^/internal/loyalty/points/[^/]+:reverse$")) {
            return Set.of(InternalScopes.LOYALTY_REVERSE);
        }
        if (path.equals("/internal/loyalty/points:adjust")) {
            return Set.of(InternalScopes.LOYALTY_ADJUST);
        }
        if (path.equals("/internal/loyalty/points:expire")
                || path.equals("/internal/loyalty/points:expire-dry-run")) {
            return Set.of(InternalScopes.LOYALTY_EXPIRE);
        }
        return Set.of(InternalScopes.LOYALTY_ADMIN);
    }

    private Set<String> promotionScopes(String path, String method) {
        if (path.equals("/internal/incentives/evaluate")) {
            return Set.of(InternalScopes.PROMOTION_EVALUATE);
        }
        if (path.equals("/internal/incentives/reservations")
                && "POST".equalsIgnoreCase(method)) {
            return Set.of(InternalScopes.PROMOTION_RESERVE);
        }
        if (path.matches("^/internal/incentives/reservations/[^/]+/commit$")) {
            return Set.of(InternalScopes.PROMOTION_COMMIT);
        }
        if (path.matches("^/internal/incentives/reservations/[^/]+/cancel$")) {
            return Set.of(InternalScopes.PROMOTION_CANCEL);
        }
        if (path.matches("^/internal/incentives/redemptions/[^/]+/reverse$")) {
            return Set.of(InternalScopes.PROMOTION_REVERSE);
        }
        return Set.of(InternalScopes.PROMOTION_ADMIN);
    }

    private Set<String> userDirectoryScopes(String path, String method) {
        if (path.contains("/assignments")) {
            return Set.of("GET".equalsIgnoreCase(method)
                    ? InternalScopes.ROLE_ASSIGNMENT_READ
                    : InternalScopes.ROLE_ASSIGNMENT_WRITE);
        }
        if (path.endsWith("/deactivate")) {
            return Set.of(InternalScopes.USER_DIRECTORY_WRITE);
        }
        if (path.endsWith(":batch") || "GET".equalsIgnoreCase(method)) {
            return Set.of(InternalScopes.USER_DIRECTORY_READ);
        }
        return Set.of(InternalScopes.USER_DIRECTORY_WRITE);
    }

    @SuppressWarnings("unchecked")
    private Set<String> extractScopes(Claims claims) {
        Set<String> scopes = new LinkedHashSet<>();
        Object rawScope = claims.get("scope");
        if (rawScope != null) {
            Arrays.stream(rawScope.toString().split("\\s+"))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(scopes::add);
        }
        Object rawScp = claims.get("scp");
        if (rawScp instanceof List<?> list) {
            for (Object scope : list) {
                if (scope != null && !scope.toString().isBlank()) {
                    scopes.add(scope.toString().trim());
                }
            }
        }
        return scopes;
    }

    private String firstBearerHeader(HttpServletRequest request) {
        String internal = request.getHeader(GatewayHeaders.INTERNAL_AUTHORIZATION);
        if (isBearer(internal)) {
            return internal;
        }
        String authorization = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (isBearer(authorization)) {
            return authorization;
        }
        return null;
    }

    private boolean isBearer(String header) {
        return header != null && header.regionMatches(true, 0, "Bearer ", 0, 7);
    }

    private boolean identityClaimsMatchHeaders(Claims claims, HttpServletRequest request) {
        String uid = claims.get("uid", String.class);
        String userIdHeader = request.getHeader(GatewayHeaders.USER_ID);
        if (uid == null || userIdHeader == null || !uid.equals(userIdHeader)) {
            return false;
        }
        String emailHeader = request.getHeader(GatewayHeaders.USER_EMAIL);
        String emailClaim = claims.get("email", String.class);
        if (emailHeader != null && (emailClaim == null || !emailClaim.equals(emailHeader))) {
            return false;
        }

        Set<String> roles = extractRoleCodes(claims);
        String primaryRoleHeader = request.getHeader(GatewayHeaders.USER_ROLE);
        if (primaryRoleHeader != null && !primaryRoleHeader.isBlank()
                && !roles.contains(primaryRoleHeader.trim())) {
            return false;
        }

        String rolesHeader = request.getHeader(GatewayHeaders.USER_ROLES);
        if (rolesHeader != null && !rolesHeader.isBlank() && !roles.equals(parseCsv(rolesHeader))) {
            return false;
        }

        String roleScopesHeader = request.getHeader(GatewayHeaders.USER_ROLE_SCOPES);
        return roleScopesHeader == null
                || roleScopesHeader.isBlank()
                || encodedRoleScopes(claims).equals(parseCsv(roleScopesHeader));
    }

    @SuppressWarnings("unchecked")
    private Set<String> extractRoleCodes(Claims claims) {
        Set<String> roles = new LinkedHashSet<>();
        Object rawRoles = claims.get("roles");
        if (rawRoles instanceof List<?> list) {
            addRoleCodes(roles, list);
        }
        Object rawAssignments = claims.get("role_assignments");
        if (rawAssignments instanceof List<?> list) {
            addRoleCodes(roles, list);
        }
        return roles;
    }

    @SuppressWarnings("unchecked")
    private void addRoleCodes(Set<String> roles, List<?> list) {
        for (Object element : list) {
            if (element instanceof Map<?, ?> map) {
                Object code = ((Map<String, Object>) map).get("code");
                if (code != null && !code.toString().isBlank()) {
                    roles.add(code.toString());
                }
            } else if (element != null && !element.toString().isBlank()) {
                roles.add(element.toString());
            }
        }
    }

    @SuppressWarnings("unchecked")
    private Set<String> encodedRoleScopes(Claims claims) {
        Object rawAssignments = claims.get("role_assignments");
        if (!(rawAssignments instanceof List<?> assignments)) {
            return Set.of();
        }
        Set<String> encoded = new LinkedHashSet<>();
        for (Object element : assignments) {
            if (!(element instanceof Map<?, ?> raw)) {
                continue;
            }
            Map<String, Object> assignment = (Map<String, Object>) raw;
            Object code = assignment.get("code");
            if (code == null || code.toString().isBlank()) {
                continue;
            }
            Object scopeType = assignment.get("scopeType");
            Object scopeId = assignment.get("scopeId");
            encoded.add(encode(code.toString()) + "." + encode(scopeType) + "." + encode(scopeId));
        }
        return encoded;
    }

    private Set<String> parseCsv(String raw) {
        return Arrays.stream(raw.split(","))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private String encode(Object raw) {
        if (raw == null || raw.toString().isBlank()) {
            return "";
        }
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(raw.toString().getBytes(StandardCharsets.UTF_8));
    }

    private void recordRejection(RejectionReason reason, HttpServletRequest request) {
        if (meterRegistry == null) {
            return;
        }
        meterRegistry.counter(
                        REJECTION_METRIC,
                        "reason",
                        reason.metricValue,
                        "request_type",
                        requestType(request))
                .increment();
    }

    private String requestType(HttpServletRequest request) {
        if (request.getRequestURI().startsWith("/internal/")) {
            return "internal_endpoint";
        }
        if (request.getRequestURI().startsWith("/backoffice/")) {
            return "backoffice_endpoint";
        }
        if (hasIdentityHeaders(request)) {
            return "identity_headers";
        }
        return "unknown";
    }

    private void deny(HttpServletResponse response) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"statusCode\":\"401 UNAUTHORIZED\",\"title\":\"Unauthorized\","
                + "\"detail\":\"Trusted gateway internal token is required\"}");
    }

    private enum RejectionReason {
        MISSING("missing"),
        INVALID("invalid"),
        WRONG_TOKEN_USE("wrong_token_use"),
        WRONG_ACTOR_TYPE("wrong_actor_type"),
        IDENTITY_MISMATCH("identity_mismatch"),
        MISSING_IDENTITY_HEADERS("missing_identity_headers"),
        INSUFFICIENT_SCOPE("insufficient_scope");

        private final String metricValue;

        RejectionReason(String metricValue) {
            this.metricValue = metricValue;
        }
    }
}
