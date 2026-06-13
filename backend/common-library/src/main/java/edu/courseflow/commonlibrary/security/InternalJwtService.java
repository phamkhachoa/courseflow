package edu.courseflow.commonlibrary.security;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.JwtBuilder;
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
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class InternalJwtService {

    private static final List<String> ROLE_RANK =
            List.of("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA", "STUDENT");

    private final InternalJwtProperties properties;
    private final RestClient tokenConverterClient;
    private final InternalJwksKeyLocator jwksKeyLocator;

    public InternalJwtService(InternalJwtProperties properties) {
        this(properties, null);
    }

    @Autowired
    public InternalJwtService(InternalJwtProperties properties,
                              ObjectProvider<RestClient.Builder> restClientBuilderProvider) {
        this.properties = properties;
        RestClient.Builder builder = restClientBuilderProvider == null
                ? RestClient.builder()
                : restClientBuilderProvider.getIfAvailable(RestClient::builder);
        this.tokenConverterClient = properties.tokenConverterUri().isBlank()
                ? builder.clone().build()
                : builder.clone().baseUrl(properties.tokenConverterUri()).build();
        this.jwksKeyLocator = new InternalJwksKeyLocator(properties, builder.clone().build());
    }

    public boolean configured() {
        return properties.configured();
    }

    public void applyServiceToken(HttpHeaders headers) {
        applyServiceToken(headers, Set.of(InternalScopes.SERVICE));
    }

    public void applyServiceToken(HttpHeaders headers, Collection<String> scopes) {
        if (properties.stsServiceTokenMode()) {
            applyBearer(headers, requestStsServiceToken(scopes == null ? Set.of() : scopes));
            return;
        }
        String token = issueServiceToken(scopes == null ? Set.of() : scopes);
        applyBearer(headers, token);
    }

    public void applyUserToken(HttpHeaders headers, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new IllegalArgumentException("Current user is required for internal user JWT");
        }
        writeIdentityHeaders(headers, user);
        if (properties.stsServiceTokenMode()) {
            applyBearer(headers, requestStsUserToken(user));
            return;
        }
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
        Claims claims = parse(token);
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
        JwtBuilder builder = Jwts.builder()
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
                .claim("scope", InternalScopes.USER)
                .claim("scp", List.of(InternalScopes.USER))
                .issuedAt(Date.from(now))
                .notBefore(Date.from(now.minusSeconds(1)))
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())));
        return sign(builder);
    }

    private String issueServiceToken(Collection<String> scopes) {
        Instant now = Instant.now();
        Set<String> normalizedScopes = normalizeScopes(scopes);
        JwtBuilder builder = Jwts.builder()
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
                .expiration(Date.from(now.plusSeconds(properties.ttlSeconds())));
        return sign(builder);
    }

    private Claims parse(String token) {
        if (properties.rs256()) {
            if (properties.jwksVerificationMode()) {
                return Jwts.parser()
                        .keyLocator(jwksKeyLocator)
                        .clockSkewSeconds(properties.clockSkewSeconds())
                        .build()
                        .parseSignedClaims(token)
                        .getPayload();
            }
            return Jwts.parser()
                    .verifyWith(properties.publicKey())
                    .clockSkewSeconds(properties.clockSkewSeconds())
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        }
        return Jwts.parser()
                .verifyWith(properties.signingKey())
                .clockSkewSeconds(properties.clockSkewSeconds())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    private String sign(JwtBuilder builder) {
        if (properties.rs256()) {
            return builder.signWith(properties.privateKey()).compact();
        }
        return builder.signWith(properties.signingKey()).compact();
    }

    private String requestStsServiceToken(Collection<String> scopes) {
        MultiValueMap<String, String> form = baseStsForm("client_credentials");
        form.add("scope", String.join(" ", normalizeScopes(scopes)));
        return requestStsToken(form);
    }

    private String requestStsUserToken(CurrentUser user) {
        MultiValueMap<String, String> form = baseStsForm("urn:courseflow:params:oauth:grant-type:trusted-user");
        if (user.internalToken() == null || user.internalToken().isBlank()) {
            throw new IllegalStateException("Trusted-user STS delegation requires the verified inbound internal JWT");
        }
        form.add("actor_token", user.internalToken());
        form.add("scope", InternalScopes.USER);
        return requestStsToken(form);
    }

    private MultiValueMap<String, String> baseStsForm(String grantType) {
        if (properties.tokenConverterUri().isBlank() || properties.stsClientSecret().isBlank()) {
            throw new IllegalStateException("TOKEN_CONVERTER_URI and COURSEFLOW_STS_CLIENT_SECRET are required"
                    + " when COURSEFLOW_INTERNAL_SERVICE_TOKEN_MODE=sts");
        }
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", grantType);
        form.add("client_id", properties.serviceName());
        form.add("client_secret", properties.stsClientSecret());
        form.add("audience", properties.primaryAudience());
        return form;
    }

    private String requestStsToken(MultiValueMap<String, String> form) {
        try {
            TokenExchangeResponse response = tokenConverterClient.post()
                    .uri("/oauth/token")
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .body(form)
                    .retrieve()
                    .body(TokenExchangeResponse.class);
            if (response == null || response.access_token() == null || response.access_token().isBlank()) {
                throw new IllegalStateException("Token converter returned an empty internal token");
            }
            return response.access_token();
        } catch (RestClientException ex) {
            throw new IllegalStateException("Could not obtain internal token from identity-token-converter-service", ex);
        }
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
            normalized.add(InternalScopes.SERVICE);
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

    private record TokenExchangeResponse(String access_token, String issued_token_type,
                                         String token_type, long expires_in, String scope) {
    }
}
