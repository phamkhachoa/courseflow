package edu.courseflow.identity.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.identity.service.AccessTokenRevocationService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Base64;
import java.util.Deque;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.util.UriUtils;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Defense-in-depth identity filter. Even though the gateway is the primary
 * trust boundary, this
 * service re-verifies the signed JWT itself instead of blindly trusting the
 * forwarded
 * {@code X-User-*} headers.
 *
 * <p>
 * Operator and primary-role decisions are driven entirely by the per-claim
 * {@code isOperator}
 * and {@code rank} fields, so this filter never needs to know the catalogue of
 * role codes — admins
 * can add new operator roles via {@code POST /internal/roles} without
 * redeploying.
 */
public class JwtIdentityFilter extends OncePerRequestFilter {

    public static final String ACCESS_TOKEN_JTI_ATTRIBUTE = JwtIdentityFilter.class.getName() + ".jti";
    public static final String ACCESS_TOKEN_EXPIRES_AT_ATTRIBUTE =
            JwtIdentityFilter.class.getName() + ".expiresAt";

    // Logout is intentionally NOT public: it needs the caller identity to revoke
    // that user's tokens.
    private static final List<String> PUBLIC_PATHS = List.of(
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/email/verify",
            "/auth/email/resend",
            "/actuator/health",
            "/actuator/info",
            "/actuator/prometheus");

    private final SecretKey secretKey;
    private final String issuer;
    private final long clockSkewSeconds;
    private final AccessTokenRevocationService accessTokenRevocations;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public JwtIdentityFilter(JwtProperties jwtProperties, AccessTokenRevocationService accessTokenRevocations) {
        this.secretKey = jwtProperties.secretKey();
        this.issuer = jwtProperties.getIssuer();
        this.clockSkewSeconds = jwtProperties.getClockSkewSeconds();
        this.accessTokenRevocations = accessTokenRevocations;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {
        String path = normalizedPath(request);
        if (path == null) {
            deny(response, HttpStatus.BAD_REQUEST, "Malformed request path");
            return;
        }

        if (isPublic(path)) {
            chain.doFilter(blankIdentity(request), response);
            return;
        }

        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            deny(response, HttpStatus.UNAUTHORIZED, "Missing bearer token");
            return;
        }

        Claims claims;
        try {
            claims = Jwts.parser()
                    .verifyWith(secretKey)
                    .requireIssuer(issuer)
                    .clockSkewSeconds(clockSkewSeconds)
                    .build()
                    .parseSignedClaims(authHeader.substring(7))
                    .getPayload();
        } catch (JwtException | IllegalArgumentException ex) {
            deny(response, HttpStatus.UNAUTHORIZED, "Invalid or expired token");
            return;
        }

        Object uid = claims.get("uid");
        String userId = uid == null ? null : uid.toString();
        String email = claims.getSubject();
        if (userId == null || userId.isBlank() || email == null || email.isBlank()) {
            deny(response, HttpStatus.UNAUTHORIZED, "Token is missing identity claims");
            return;
        }
        Long parsedUserId;
        try {
            parsedUserId = Long.valueOf(userId);
        } catch (NumberFormatException ex) {
            deny(response, HttpStatus.UNAUTHORIZED, "Token is missing identity claims");
            return;
        }

        Instant issuedAt = claims.getIssuedAt() == null ? null : claims.getIssuedAt().toInstant();
        Instant expiresAt = claims.getExpiration() == null ? null : claims.getExpiration().toInstant();
        String jti = claims.getId();
        if (expiresAt == null || !accessTokenRevocations.isAccepted(parsedUserId, jti, issuedAt)) {
            deny(response, HttpStatus.UNAUTHORIZED, "Token has been revoked");
            return;
        }

        List<RoleClaim> roleClaims = extractRoleClaims(claims);
        Set<String> roleCodes = new LinkedHashSet<>();
        boolean isOperator = false;
        boolean isAdmin = false;
        RoleClaim primary = null;
        for (RoleClaim rc : roleClaims) {
            roleCodes.add(rc.code);
            if (rc.isOperator)
                isOperator = true;
            if ("ADMIN".equals(rc.code))
                isAdmin = true;
            if (primary == null || rc.rank > primary.rank)
                primary = rc;
        }

        if (requiresAdmin(path, request.getMethod()) && !isAdmin) {
            deny(response, HttpStatus.FORBIDDEN, "This operation requires the ADMIN role");
            return;
        }
        if (requiresOperator(path) && !isOperator) {
            deny(response, HttpStatus.FORBIDDEN, "This operation requires an operator role");
            return;
        }

        String rolesCsv = String.join(",", roleCodes);
        String primaryRole = primary == null ? null : primary.code;
        request.setAttribute(ACCESS_TOKEN_JTI_ATTRIBUTE, jti);
        request.setAttribute(ACCESS_TOKEN_EXPIRES_AT_ATTRIBUTE, expiresAt);
        VerifiedIdentityRequestWrapper wrapped = new VerifiedIdentityRequestWrapper(
                request, userId, email, primaryRole, rolesCsv, encodeRoleScopes(roleClaims));
        chain.doFilter(wrapped, response);
    }

    private String normalizedPath(HttpServletRequest request) {
        try {
            String path = request.getRequestURI();
            String contextPath = request.getContextPath();
            if (contextPath != null && !contextPath.isBlank() && path.startsWith(contextPath)) {
                path = path.substring(contextPath.length());
            }
            return normalizeDecodedPath(UriUtils.decode(path, StandardCharsets.UTF_8));
        } catch (RuntimeException ex) {
            return null;
        }
    }

    private String normalizeDecodedPath(String decodedPath) {
        Deque<String> segments = new ArrayDeque<>();
        for (String segment : decodedPath.split("/")) {
            if (segment.isBlank() || ".".equals(segment)) {
                continue;
            }
            if ("..".equals(segment)) {
                if (!segments.isEmpty()) {
                    segments.removeLast();
                }
                continue;
            }
            segments.addLast(segment);
        }
        return "/" + String.join("/", segments);
    }

    private boolean isPublic(String path) {
        return PUBLIC_PATHS.stream().anyMatch(path::startsWith);
    }

    private boolean requiresOperator(String path) {
        if (path.startsWith("/internal/authz/check")) {
            return false;
        }
        return path.startsWith("/internal/") || path.startsWith("/backoffice/");
    }

    /**
     * Mutating role/permission definitions and granting/revoking role assignments
     * are ADMIN-only —
     * that's the surface that can escalate a user to ADMIN, so it must not be
     * reachable by a lesser
     * operator.
     */
    private boolean requiresAdmin(String path, String method) {
        if (path.matches("/backoffice/users/\\d+/privacy-export.*"))
            return true;
        boolean mutating = !"GET".equalsIgnoreCase(method);
        if (!mutating)
            return false;
        if (path.matches("/internal/users/\\d+/assignments.*"))
            return true;
        if (path.matches("/backoffice/users/\\d+/password.*"))
            return true;
        if (path.matches("/backoffice/users/\\d+/email-verification.*"))
            return true;
        if (path.matches("/backoffice/users/\\d+/deactivate.*"))
            return true;
        return path.startsWith("/internal/roles");
    }

    private HttpServletRequest blankIdentity(HttpServletRequest request) {
        return new VerifiedIdentityRequestWrapper(request, null, null, null, null, null);
    }

    @SuppressWarnings("unchecked")
    private List<RoleClaim> extractRoleClaims(Claims claims) {
        Object raw = claims.get("roles");
        List<RoleClaim> out = new java.util.ArrayList<>();
        if (raw instanceof List<?> list) {
            for (Object element : list) {
                if (element instanceof Map<?, ?> map) {
                    Map<String, Object> m = (Map<String, Object>) map;
                    Object code = m.get("code");
                    if (code == null || code.toString().isBlank())
                        continue;
                    int rank = m.get("rank") instanceof Number n ? n.intValue() : 0;
                    boolean operator = Boolean.TRUE.equals(m.get("isOperator"));
                    Object scopeType = m.get("scopeType");
                    Object scopeId = m.get("scopeId");
                    out.add(new RoleClaim(
                            code.toString(),
                            rank,
                            operator,
                            scopeType == null ? "PLATFORM" : scopeType.toString(),
                            scopeId == null ? null : scopeId.toString()));
                } else if (element != null && !element.toString().isBlank()) {
                    out.add(new RoleClaim(element.toString(), 0, false, "PLATFORM", null));
                }
            }
        }
        return out;
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

    private void deny(HttpServletResponse response, HttpStatus status, String detail) throws IOException {
        response.setStatus(status.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        Map<String, Object> body = Map.of(
                "statusCode", status.value(),
                "title", status.getReasonPhrase(),
                "detail", detail);
        objectMapper.writeValue(response.getWriter(), body);
    }

    private record RoleClaim(String code, int rank, boolean isOperator, String scopeType, String scopeId) {
    }

    @SuppressWarnings("unused")
    private static String headerSink(GatewayHeaders headers) {
        return headers == null ? null : headers.toString();
    }
}
