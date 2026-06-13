package edu.courseflow.tokenconverter.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.tokenconverter.config.AccessControlProperties;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

@Component
public class HttpAccessControlIdentityResolver implements AccessControlIdentityResolver {

    private final AccessControlProperties properties;
    private final InternalJwtService internalJwt;
    private final RestClient client;
    private final AccessControlIdentityResolver fallback = AccessControlIdentityResolver.legacyClaims();

    public HttpAccessControlIdentityResolver(
            AccessControlProperties properties,
            InternalJwtService internalJwt,
            RestClient.Builder restClientBuilder) {
        this.properties = properties;
        this.internalJwt = internalJwt;
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(properties.timeout());
        requestFactory.setReadTimeout(properties.timeout());
        this.client = restClientBuilder
                .baseUrl(properties.uri())
                .requestFactory(requestFactory)
                .build();
    }

    @Override
    public ResolvedIdentity resolve(ExternalTokenClaims externalClaims) {
        if (!properties.enabled()) {
            return fallback.resolve(externalClaims);
        }
        try {
            ResolveIdentityRequest request = toRequest(externalClaims);
            ResolvedIdentity resolved = client.post()
                    .uri("/internal/identities/resolve")
                    .headers(headers -> internalJwt.applyServiceToken(
                            headers, Set.of(InternalScopes.IDENTITY_RESOLVE)))
                    .body(request)
                    .retrieve()
                    .body(ResolvedIdentity.class);
            if (resolved == null || resolved.userId() == null || resolved.userId().isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "access-control returned no user");
            }
            return resolved;
        } catch (RuntimeException ex) {
            if (properties.required()) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "access-control identity resolution failed", ex);
            }
            return fallback.resolve(externalClaims);
        }
    }

    private ResolveIdentityRequest toRequest(ExternalTokenClaims claims) {
        Object legacyUserId = claims.get("uid");
        return new ResolveIdentityRequest(
                claims.issuer(),
                claims.subject(),
                claims.stringClaim("email") == null ? claims.subject() : claims.stringClaim("email"),
                Boolean.TRUE.equals(claims.get("email_verified")),
                legacyUserId == null ? null : legacyUserId.toString(),
                roleAssignments(claims.get("roles")));
    }

    @SuppressWarnings("unchecked")
    private List<RoleAssignmentHint> roleAssignments(Object rawRoles) {
        if (!(rawRoles instanceof Collection<?> roles)) {
            return List.of();
        }
        return roles.stream()
                .map(raw -> {
                    if (raw instanceof Map<?, ?> map) {
                        Object code = ((Map<String, Object>) map).get("code");
                        if (code == null || code.toString().isBlank()) {
                            return null;
                        }
                        return new RoleAssignmentHint(
                                code.toString(),
                                stringValue(((Map<String, Object>) map).get("scopeType"), "PLATFORM"),
                                stringValue(((Map<String, Object>) map).get("scopeId"), null));
                    }
                    if (raw != null && !raw.toString().isBlank()) {
                        return new RoleAssignmentHint(raw.toString(), "PLATFORM", null);
                    }
                    return null;
                })
                .filter(java.util.Objects::nonNull)
                .toList();
    }

    private String stringValue(Object value, String fallback) {
        return value == null || value.toString().isBlank() ? fallback : value.toString();
    }

    private record ResolveIdentityRequest(
            String issuer,
            String subject,
            String email,
            Boolean emailVerified,
            String legacyUserId,
            List<RoleAssignmentHint> roleAssignments) {
    }

    private record RoleAssignmentHint(String code, String scopeType, String scopeId) {
    }
}
