package edu.courseflow.tokenconverter.service;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import io.jsonwebtoken.JwtBuilder;
import io.jsonwebtoken.Jwts;
import java.time.Instant;
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

    public IssuedInternalToken issue(ResolvedIdentity identity, String audience, String requestedScope) {
        Instant now = Instant.now();
        List<Map<String, Object>> roleAssignments = roleAssignments(identity);
        List<String> roles = roleAssignments.stream()
                .map(role -> String.valueOf(role.get("code")))
                .filter(role -> role != null && !role.isBlank() && !"null".equals(role))
                .distinct()
                .toList();
        List<String> scopes = scopeMapper.scopesFor(roles, requestedScope);
        JwtBuilder builder = Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(properties.internalJwtIssuer())
                .subject(identity.userId())
                .claim("aud", List.of(audience))
                .claim("token_use", "internal")
                .claim("actor_type", "user")
                .claim("azp", "api-gateway")
                .claim("uid", identity.userId())
                .claim("email", identity.email())
                .claim("tenant_id", "default")
                .claim("roles", roles)
                .claim("role_assignments", roleAssignments)
                .claim("scope", String.join(" ", scopes))
                .claim("scp", scopes)
                .claim("external_iss", identity.externalIssuer())
                .claim("external_sub", identity.externalSubject())
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())));
        String token = sign(builder);
        return new IssuedInternalToken(token, scopes, properties.ttlSeconds());
    }

    public IssuedInternalToken issueTrustedUser(ResolvedIdentity identity, String audience, String requestedScope,
                                                String clientId) {
        return issueUser(identity, audience, requestedScope, clientId == null || clientId.isBlank()
                ? "trusted-service"
                : clientId.trim());
    }

    public IssuedInternalToken issueService(String clientId, String audience, Collection<String> scopes) {
        Instant now = Instant.now();
        List<String> grantedScopes = scopes == null ? List.of() : scopes.stream()
                .filter(scope -> scope != null && !scope.isBlank())
                .map(String::trim)
                .distinct()
                .toList();
        String azp = clientId == null || clientId.isBlank() ? "courseflow-service" : clientId.trim();
        JwtBuilder builder = Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(properties.internalJwtIssuer())
                .subject("service:" + azp)
                .claim("aud", List.of(audience))
                .claim("token_use", "internal")
                .claim("actor_type", "service")
                .claim("azp", azp)
                .claim("scope", String.join(" ", grantedScopes))
                .claim("scp", grantedScopes)
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())));
        String token = sign(builder);
        return new IssuedInternalToken(token, grantedScopes, properties.ttlSeconds());
    }

    private IssuedInternalToken issueUser(ResolvedIdentity identity, String audience, String requestedScope,
                                          String authorizedParty) {
        Instant now = Instant.now();
        List<Map<String, Object>> roleAssignments = roleAssignments(identity);
        List<String> roles = roleAssignments.stream()
                .map(role -> String.valueOf(role.get("code")))
                .filter(role -> role != null && !role.isBlank() && !"null".equals(role))
                .distinct()
                .toList();
        List<String> scopes = scopeMapper.scopesFor(roles, requestedScope);
        JwtBuilder builder = Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(properties.internalJwtIssuer())
                .subject(identity.userId())
                .claim("aud", List.of(audience))
                .claim("token_use", "internal")
                .claim("actor_type", "user")
                .claim("azp", authorizedParty)
                .claim("uid", identity.userId())
                .claim("email", identity.email())
                .claim("tenant_id", "default")
                .claim("roles", roles)
                .claim("role_assignments", roleAssignments)
                .claim("scope", String.join(" ", scopes))
                .claim("scp", scopes)
                .claim("external_iss", identity.externalIssuer())
                .claim("external_sub", identity.externalSubject())
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())));
        String token = sign(builder);
        return new IssuedInternalToken(token, scopes, properties.ttlSeconds());
    }

    private String sign(JwtBuilder builder) {
        if (properties.internalJwtRs256()) {
            return builder.header()
                    .keyId(properties.internalJwtKeyId())
                    .and()
                    .signWith(properties.internalJwtPrivateKey())
                    .compact();
        }
        return builder.signWith(properties.internalJwtKey()).compact();
    }

    private List<Map<String, Object>> roleAssignments(ResolvedIdentity identity) {
        if (identity.roleAssignments() == null || identity.roleAssignments().isEmpty()) {
            return List.of();
        }
        Set<String> seen = new LinkedHashSet<>();
        return identity.roleAssignments().stream()
                .filter(role -> role.code() != null && !role.code().isBlank())
                .map(role -> {
                    Map<String, Object> assignment = new LinkedHashMap<>();
                    assignment.put("code", role.code());
                    assignment.put("scopeType",
                            role.scopeType() == null || role.scopeType().isBlank() ? "PLATFORM" : role.scopeType());
                    assignment.put("scopeId", role.scopeId());
                    return assignment;
                })
                .filter(role -> seen.add(role.get("code") + ":" + role.get("scopeType") + ":" + role.get("scopeId")))
                .toList();
    }

    public record IssuedInternalToken(String token, List<String> scopes, long expiresInSeconds) {
    }
}
