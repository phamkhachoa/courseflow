package edu.courseflow.commonlibrary.security;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Collection;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;

@Component
public class InternalJwtService {

    private static final List<String> ROLE_RANK =
            List.of("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA", "STUDENT");

    private final InternalJwtProperties properties;

    public InternalJwtService(InternalJwtProperties properties) {
        this.properties = properties;
    }

    public boolean configured() {
        return properties.configured();
    }

    public void applyServiceToken(HttpHeaders headers) {
        applyServiceToken(headers, Set.of("internal:service"));
    }

    public void applyServiceToken(HttpHeaders headers, Collection<String> scopes) {
        String token = issueServiceToken(scopes == null ? Set.of() : scopes);
        applyBearer(headers, token);
    }

    public void applyUserToken(HttpHeaders headers, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new IllegalArgumentException("Current user is required for internal user JWT");
        }
        writeIdentityHeaders(headers, user);
        applyBearer(headers, issueUserToken(user));
    }

    public Claims verify(String bearerOrToken) {
        String token = bearerOrToken == null ? "" : bearerOrToken.trim();
        if (token.regionMatches(true, 0, "Bearer ", 0, 7)) {
            token = token.substring(7).trim();
        }
        if (token.isBlank()) {
            throw new JwtException("Internal JWT is missing");
        }
        Claims claims = Jwts.parser()
                .verifyWith(properties.signingKey())
                .clockSkewSeconds(properties.clockSkewSeconds())
                .build()
                .parseSignedClaims(token)
                .getPayload();
        validateIssuer(claims);
        validateAudience(claims);
        return claims;
    }

    private String issueUserToken(CurrentUser user) {
        Instant now = Instant.now();
        List<Map<String, Object>> roleAssignments = roleAssignments(user);
        Set<String> roles = new LinkedHashSet<>(user.roles());
        String primaryRole = user.role() == null || user.role().isBlank() ? primaryRole(roles) : user.role();
        if (primaryRole != null && !primaryRole.isBlank()) {
            roles.add(primaryRole);
        }
        return Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(properties.issuer())
                .subject(user.id().toString())
                .claim("aud", List.copyOf(properties.audiences()))
                .claim("token_use", "internal")
                .claim("actor_type", "user")
                .claim("azp", properties.serviceName())
                .claim("uid", user.id().toString())
                .claim("email", user.email())
                .claim("roles", List.copyOf(roles))
                .claim("role_assignments", roleAssignments)
                .claim("scope", "internal:user")
                .claim("scp", List.of("internal:user"))
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())))
                .signWith(properties.signingKey())
                .compact();
    }

    private String issueServiceToken(Collection<String> scopes) {
        Instant now = Instant.now();
        Set<String> normalizedScopes = normalizeScopes(scopes);
        return Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(properties.issuer())
                .subject("service:" + properties.serviceName())
                .claim("aud", List.copyOf(properties.audiences()))
                .claim("token_use", "internal")
                .claim("actor_type", "service")
                .claim("azp", properties.serviceName())
                .claim("scope", String.join(" ", normalizedScopes))
                .claim("scp", List.copyOf(normalizedScopes))
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())))
                .signWith(properties.signingKey())
                .compact();
    }

    private void applyBearer(HttpHeaders headers, String token) {
        String bearer = "Bearer " + token;
        headers.set(HttpHeaders.AUTHORIZATION, bearer);
        headers.set(GatewayHeaders.INTERNAL_AUTHORIZATION, bearer);
    }

    private void writeIdentityHeaders(HttpHeaders headers, CurrentUser user) {
        Set<String> roles = new LinkedHashSet<>(user.roles());
        String primaryRole = user.role() == null || user.role().isBlank() ? primaryRole(roles) : user.role();
        if (primaryRole != null && !primaryRole.isBlank()) {
            roles.add(primaryRole);
            headers.set(GatewayHeaders.USER_ROLE, primaryRole);
        }
        headers.set(GatewayHeaders.USER_ID, user.id().toString());
        if (user.email() != null && !user.email().isBlank()) {
            headers.set(GatewayHeaders.USER_EMAIL, user.email());
        }
        if (!roles.isEmpty()) {
            headers.set(GatewayHeaders.USER_ROLES, String.join(",", roles));
        }
        String encodedScopes = encodeRoleScopes(user.roleAssignments());
        if (!encodedScopes.isBlank()) {
            headers.set(GatewayHeaders.USER_ROLE_SCOPES, encodedScopes);
        }
    }

    private List<Map<String, Object>> roleAssignments(CurrentUser user) {
        Collection<CurrentUser.RoleAssignment> assignments = user.roleAssignments();
        if (assignments == null || assignments.isEmpty()) {
            return List.of();
        }
        return assignments.stream()
                .map(assignment -> {
                    Map<String, Object> role = new LinkedHashMap<>();
                    role.put("code", assignment.code());
                    role.put("scopeType", assignment.scopeType());
                    role.put("scopeId", assignment.scopeId());
                    return role;
                })
                .toList();
    }

    private String encodeRoleScopes(Collection<CurrentUser.RoleAssignment> assignments) {
        if (assignments == null || assignments.isEmpty()) {
            return "";
        }
        return assignments.stream()
                .map(assignment -> encode(assignment.code())
                        + "." + encode(assignment.scopeType())
                        + "." + encode(assignment.scopeId()))
                .collect(java.util.stream.Collectors.joining(","));
    }

    private String encode(String raw) {
        if (raw == null || raw.isBlank()) {
            return "";
        }
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    private String primaryRole(Set<String> roles) {
        if (roles == null || roles.isEmpty()) {
            return null;
        }
        return ROLE_RANK.stream()
                .filter(roles::contains)
                .findFirst()
                .orElse(roles.iterator().next());
    }

    private Set<String> normalizeScopes(Collection<String> scopes) {
        Set<String> normalized = scopes.stream()
                .filter(scope -> scope != null && !scope.isBlank())
                .map(String::trim)
                .collect(java.util.stream.Collectors.toCollection(LinkedHashSet::new));
        if (normalized.isEmpty()) {
            normalized.add("internal:service");
        }
        return normalized;
    }

    private void validateIssuer(Claims claims) {
        if (!properties.issuer().equals(claims.getIssuer())) {
            throw new JwtException("Invalid internal JWT issuer");
        }
    }

    private void validateAudience(Claims claims) {
        Object audienceClaim = claims.get("aud");
        if (audienceClaim instanceof String audience && properties.audiences().contains(audience)) {
            return;
        }
        if (audienceClaim instanceof Collection<?> audiences
                && audiences.stream().anyMatch(value -> properties.audiences().contains(String.valueOf(value)))) {
            return;
        }
        throw new JwtException("Invalid internal JWT audience");
    }
}
