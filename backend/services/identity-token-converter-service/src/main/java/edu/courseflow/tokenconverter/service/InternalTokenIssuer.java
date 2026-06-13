package edu.courseflow.tokenconverter.service;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class InternalTokenIssuer {

    private final TokenConverterProperties properties;
    private final ScopeMapper scopeMapper;

    public InternalTokenIssuer(TokenConverterProperties properties, ScopeMapper scopeMapper) {
        this.properties = properties;
        this.scopeMapper = scopeMapper;
    }

    public IssuedInternalToken issue(Claims externalClaims, String audience, String requestedScope) {
        Instant now = Instant.now();
        String userId = String.valueOf(externalClaims.get("uid"));
        String email = externalClaims.getSubject();
        List<Map<String, Object>> roleAssignments = roleAssignments(externalClaims.get("roles"));
        List<String> roles = roleAssignments.stream()
                .map(role -> String.valueOf(role.get("code")))
                .filter(role -> role != null && !role.isBlank() && !"null".equals(role))
                .distinct()
                .toList();
        List<String> scopes = scopeMapper.scopesFor(roles, requestedScope);
        String token = Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(properties.internalJwtIssuer())
                .subject(userId)
                .claim("aud", List.of(audience))
                .claim("token_use", "internal")
                .claim("azp", "api-gateway")
                .claim("uid", userId)
                .claim("email", email)
                .claim("tenant_id", "default")
                .claim("roles", roles)
                .claim("role_assignments", roleAssignments)
                .claim("scope", String.join(" ", scopes))
                .claim("scp", scopes)
                .claim("external_iss", externalClaims.getIssuer())
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())))
                .signWith(properties.internalJwtKey())
                .compact();
        return new IssuedInternalToken(token, scopes, properties.ttlSeconds());
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> roleAssignments(Object rawRoles) {
        if (!(rawRoles instanceof Collection<?> roles)) {
            return List.of();
        }
        List<Map<String, Object>> result = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (Object raw : roles) {
            Map<String, Object> role = new LinkedHashMap<>();
            if (raw instanceof Map<?, ?> map) {
                Object code = ((Map<String, Object>) map).get("code");
                if (code == null || code.toString().isBlank()) {
                    continue;
                }
                role.put("code", code.toString());
                role.put("scopeType", stringValue(((Map<String, Object>) map).get("scopeType"), "PLATFORM"));
                role.put("scopeId", stringValue(((Map<String, Object>) map).get("scopeId"), null));
            } else if (raw != null && !raw.toString().isBlank()) {
                role.put("code", raw.toString());
                role.put("scopeType", "PLATFORM");
                role.put("scopeId", null);
            }
            String key = role.get("code") + ":" + role.get("scopeType") + ":" + role.get("scopeId");
            if (seen.add(key)) {
                result.add(role);
            }
        }
        return result;
    }

    private String stringValue(Object value, String fallback) {
        return value == null || value.toString().isBlank() ? fallback : value.toString();
    }

    public record IssuedInternalToken(String token, List<String> scopes, long expiresInSeconds) {
    }
}
