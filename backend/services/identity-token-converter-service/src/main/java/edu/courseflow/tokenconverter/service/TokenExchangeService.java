package edu.courseflow.tokenconverter.service;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import edu.courseflow.tokenconverter.dto.TokenExchangeResponse;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class TokenExchangeService {

    public static final String TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange";
    public static final String CLIENT_CREDENTIALS_GRANT = "client_credentials";
    public static final String TRUSTED_USER_GRANT = "urn:courseflow:params:oauth:grant-type:trusted-user";
    public static final String ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token";

    private final ExternalTokenVerifier externalTokenVerifier;
    private final AccessControlIdentityResolver identityResolver;
    private final InternalTokenIssuer internalTokenIssuer;
    private final TokenConverterProperties properties;
    private final TokenConverterMetrics metrics;
    private final TokenConverterAudit audit;

    public TokenExchangeService(ExternalTokenVerifier externalTokenVerifier,
            AccessControlIdentityResolver identityResolver,
            InternalTokenIssuer internalTokenIssuer,
            TokenConverterProperties properties) {
        this(externalTokenVerifier, identityResolver, internalTokenIssuer, properties,
                TokenConverterMetrics.noop(), TokenConverterAudit.noop());
    }

    public TokenExchangeService(ExternalTokenVerifier externalTokenVerifier,
            AccessControlIdentityResolver identityResolver,
            InternalTokenIssuer internalTokenIssuer,
            TokenConverterProperties properties,
            TokenConverterMetrics metrics) {
        this(externalTokenVerifier, identityResolver, internalTokenIssuer, properties, metrics,
                TokenConverterAudit.noop());
    }

    @Autowired
    public TokenExchangeService(ExternalTokenVerifier externalTokenVerifier,
            AccessControlIdentityResolver identityResolver,
            InternalTokenIssuer internalTokenIssuer,
            TokenConverterProperties properties,
            TokenConverterMetrics metrics,
            TokenConverterAudit audit) {
        this.externalTokenVerifier = externalTokenVerifier;
        this.identityResolver = identityResolver;
        this.internalTokenIssuer = internalTokenIssuer;
        this.properties = properties;
        this.metrics = metrics;
        this.audit = audit;
    }

    public TokenExchangeResponse exchange(String grantType, String subjectTokenType, String subjectToken,
                                          String audience, String requestedScope) {
        return exchange(grantType, subjectTokenType, subjectToken, audience, requestedScope,
                null, null, null, null, null, null);
    }

    public TokenExchangeResponse exchange(String grantType, String subjectTokenType, String subjectToken,
                                          String audience, String requestedScope,
                                          String clientId, String clientSecret,
                                          String userId, String email, String roles,
                                          String roleAssignments) {
        return exchange(grantType, subjectTokenType, subjectToken, audience, requestedScope,
                clientId, clientSecret, userId, email, roles, roleAssignments, null);
    }

    public TokenExchangeResponse exchange(String grantType, String subjectTokenType, String subjectToken,
                                          String audience, String requestedScope,
                                          String clientId, String clientSecret,
                                          String userId, String email, String roles,
                                          String roleAssignments, String actorToken) {
        metrics.request(grantType);
        long startedNanos = System.nanoTime();
        try {
            TokenExchangeResponse response = doExchange(grantType, subjectTokenType, subjectToken, audience,
                    requestedScope, clientId, clientSecret, userId, email, roles, roleAssignments, actorToken);
            metrics.success(grantType, successActorType(grantType));
            metrics.duration(grantType, "success", startedNanos);
            return response;
        } catch (ResponseStatusException ex) {
            String reason = failureReason(ex);
            String status = String.valueOf(ex.getStatusCode().value());
            metrics.failure(grantType, reason, status);
            metrics.duration(grantType, "failure", startedNanos);
            audit.failure(new TokenConverterAudit.Event(
                    grantType,
                    requestedActorType(grantType),
                    requestedActorId(grantType, clientId, userId),
                    trimToNull(clientId),
                    trimToNull(audience),
                    List.of(),
                    null,
                    null,
                    status,
                    reason));
            throw ex;
        } catch (RuntimeException ex) {
            metrics.failure(grantType, "internal_error", "500");
            metrics.duration(grantType, "failure", startedNanos);
            audit.failure(new TokenConverterAudit.Event(
                    grantType,
                    requestedActorType(grantType),
                    requestedActorId(grantType, clientId, userId),
                    trimToNull(clientId),
                    trimToNull(audience),
                    List.of(),
                    null,
                    null,
                    "500",
                    "internal_error"));
            throw ex;
        }
    }

    private TokenExchangeResponse doExchange(String grantType, String subjectTokenType, String subjectToken,
                                             String audience, String requestedScope,
                                             String clientId, String clientSecret,
                                             String userId, String email, String roles,
                                             String roleAssignments, String actorToken) {
        if (!TOKEN_EXCHANGE_GRANT.equals(grantType)) {
            if (CLIENT_CREDENTIALS_GRANT.equals(grantType)) {
                return clientCredentials(clientId, clientSecret, audience, requestedScope);
            }
            if (TRUSTED_USER_GRANT.equals(grantType)) {
                return trustedUser(clientId, clientSecret, userId, email, roles, roleAssignments,
                        actorToken, audience, requestedScope);
            }
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported grant_type");
        }
        if (subjectTokenType != null && !subjectTokenType.isBlank()
                && !ACCESS_TOKEN_TYPE.equals(subjectTokenType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported subject_token_type");
        }
        if (subjectToken == null || subjectToken.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "subject_token is required");
        }
        requireServiceClient(clientId, clientSecret);
        serviceScopesForClient(clientId, "internal:token-exchange");
        String resolvedAudience = audience == null || audience.isBlank() ? properties.defaultAudience() : audience.trim();
        if (!properties.allowedAudiences().contains(resolvedAudience)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Audience is not allowed");
        }
        ExternalTokenClaims externalClaims = externalTokenVerifier.verify(subjectToken);
        ResolvedIdentity identity = identityResolver.resolve(externalClaims);
        InternalTokenIssuer.IssuedInternalToken issued = internalTokenIssuer.issue(
                identity,
                resolvedAudience,
                requestedScope);
        audit.success(new TokenConverterAudit.Event(
                TOKEN_EXCHANGE_GRANT,
                "user",
                identity.userId(),
                clientId.trim(),
                resolvedAudience,
                issued.scopes(),
                identity.externalIssuer(),
                identity.externalSubject(),
                "200",
                null));
        return new TokenExchangeResponse(
                issued.token(),
                ACCESS_TOKEN_TYPE,
                "Bearer",
                issued.expiresInSeconds(),
                String.join(" ", issued.scopes()));
    }

    private TokenExchangeResponse clientCredentials(String clientId, String clientSecret,
                                                    String audience, String requestedScope) {
        requireServiceClient(clientId, clientSecret);
        String resolvedAudience = allowedAudience(audience);
        List<String> scopes = serviceScopesForClient(clientId, requestedScope);
        InternalTokenIssuer.IssuedInternalToken issued =
                internalTokenIssuer.issueService(clientId.trim(), resolvedAudience, scopes);
        audit.success(new TokenConverterAudit.Event(
                CLIENT_CREDENTIALS_GRANT,
                "service",
                clientId.trim(),
                clientId.trim(),
                resolvedAudience,
                issued.scopes(),
                null,
                null,
                "200",
                null));
        return response(issued);
    }

    private TokenExchangeResponse trustedUser(String clientId, String clientSecret, String userId, String email,
                                              String roles, String roleAssignments,
                                              String actorToken,
                                              String audience, String requestedScope) {
        requireServiceClient(clientId, clientSecret);
        if (hasSelfAssertedUserClaims(userId, email, roles, roleAssignments)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "trusted-user grant requires actor_token and rejects self-asserted user claims");
        }
        String resolvedAudience = allowedAudience(audience);
        serviceScopesForClient(clientId, requestedScope == null || requestedScope.isBlank()
                ? "internal:user"
                : requestedScope);
        ResolvedIdentity identity = identityFromActorToken(actorToken, resolvedAudience);
        InternalTokenIssuer.IssuedInternalToken issued =
                internalTokenIssuer.issueTrustedUser(identity, resolvedAudience, requestedScope, clientId.trim());
        audit.success(new TokenConverterAudit.Event(
                TRUSTED_USER_GRANT,
                "user",
                identity.userId(),
                clientId.trim(),
                resolvedAudience,
                issued.scopes(),
                identity.externalIssuer(),
                identity.externalSubject(),
                "200",
                null));
        return response(issued);
    }

    private void requireServiceClient(String clientId, String clientSecret) {
        if (!properties.serviceClientAllowed(clientId)
                || !properties.serviceClientSecretMatches(clientId, clientSecret)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid service client credentials");
        }
    }

    private List<String> serviceScopesForClient(String clientId, String requestedScope) {
        try {
            return properties.serviceScopesForClient(clientId, requestedScope);
        } catch (IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, ex.getMessage());
        }
    }

    private String successActorType(String grantType) {
        if (CLIENT_CREDENTIALS_GRANT.equals(grantType)) {
            return "service";
        }
        if (TOKEN_EXCHANGE_GRANT.equals(grantType) || TRUSTED_USER_GRANT.equals(grantType)) {
            return "user";
        }
        return "unknown";
    }

    private String requestedActorType(String grantType) {
        if (CLIENT_CREDENTIALS_GRANT.equals(grantType)) {
            return "service";
        }
        if (TRUSTED_USER_GRANT.equals(grantType)) {
            return "user";
        }
        if (TOKEN_EXCHANGE_GRANT.equals(grantType)) {
            return "external_user";
        }
        return "unknown";
    }

    private String requestedActorId(String grantType, String clientId, String userId) {
        if (CLIENT_CREDENTIALS_GRANT.equals(grantType)) {
            return trimToNull(clientId);
        }
        if (TRUSTED_USER_GRANT.equals(grantType)) {
            return trimToNull(userId);
        }
        return null;
    }

    private String failureReason(ResponseStatusException ex) {
        String reason = ex.getReason();
        if (reason == null || reason.isBlank()) {
            return ex.getStatusCode().is4xxClientError() ? "client_error" : "server_error";
        }
        if (reason.startsWith("External token claim is missing")) {
            return "external_claim_missing";
        }
        if (reason.startsWith("Invalid role assignment")) {
            return "invalid_role_assignment";
        }
        return reason;
    }

    private String allowedAudience(String audience) {
        String resolvedAudience = audience == null || audience.isBlank() ? properties.defaultAudience() : audience.trim();
        if (!properties.allowedAudiences().contains(resolvedAudience)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Audience is not allowed");
        }
        return resolvedAudience;
    }

    private String trimToNull(String raw) {
        return raw == null || raw.isBlank() ? null : raw.trim();
    }

    private boolean hasSelfAssertedUserClaims(String userId, String email, String roles, String roleAssignments) {
        return trimToNull(userId) != null
                || trimToNull(email) != null
                || trimToNull(roles) != null
                || trimToNull(roleAssignments) != null;
    }

    private ResolvedIdentity identityFromActorToken(String actorToken, String expectedAudience) {
        Claims claims = verifiedInternalUserClaims(actorToken, expectedAudience);
        String userId = claimString(claims, "uid");
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "actor_token is missing uid");
        }
        List<ResolvedIdentity.RoleAssignment> assignments = roleAssignmentsFromClaims(claims);
        if (assignments.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "actor_token has no role assignments");
        }
        String externalIssuer = claimString(claims, "external_iss");
        String externalSubject = claimString(claims, "external_sub");
        return new ResolvedIdentity(
                userId,
                externalIssuer == null ? "courseflow-internal" : externalIssuer,
                externalSubject == null ? userId : externalSubject,
                claimString(claims, "email"),
                "ACTIVE",
                assignments);
    }

    private Claims verifiedInternalUserClaims(String actorToken, String expectedAudience) {
        String token = actorToken == null ? "" : actorToken.trim();
        if (token.regionMatches(true, 0, "Bearer ", 0, 7)) {
            token = token.substring(7).trim();
        }
        if (token.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "actor_token is required");
        }
        try {
            Claims claims = properties.internalJwtRs256()
                    ? Jwts.parser()
                            .verifyWith(properties.internalJwtPublicKey())
                            .clockSkewSeconds(properties.clockSkewSeconds())
                            .build()
                            .parseSignedClaims(token)
                            .getPayload()
                    : Jwts.parser()
                            .verifyWith(properties.internalJwtKey())
                            .clockSkewSeconds(properties.clockSkewSeconds())
                            .build()
                            .parseSignedClaims(token)
                            .getPayload();
            if (!properties.internalJwtIssuer().equals(claims.getIssuer())) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid actor_token issuer");
            }
            if (!"internal".equals(claims.get("token_use", String.class))) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid actor_token token_use");
            }
            if ("service".equals(claims.get("actor_type", String.class))) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "actor_token must be a user token");
            }
            if (!audienceMatches(claims, expectedAudience)) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid actor_token audience");
            }
            return claims;
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (JwtException | IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid actor_token");
        }
    }

    private boolean audienceMatches(Claims claims, String expectedAudience) {
        Object raw = claims.get("aud");
        if (raw instanceof String audience) {
            return expectedAudience.equals(audience);
        }
        if (raw instanceof Collection<?> audiences) {
            return audiences.stream().anyMatch(value -> expectedAudience.equals(String.valueOf(value)));
        }
        return false;
    }

    private String claimString(Claims claims, String name) {
        Object value = claims.get(name);
        return value == null || value.toString().isBlank() ? null : value.toString();
    }

    @SuppressWarnings("unchecked")
    private List<ResolvedIdentity.RoleAssignment> roleAssignmentsFromClaims(Claims claims) {
        Object rawAssignments = claims.get("role_assignments");
        if (rawAssignments instanceof List<?> assignments && !assignments.isEmpty()) {
            return assignments.stream()
                    .filter(Map.class::isInstance)
                    .map(raw -> (Map<String, Object>) raw)
                    .map(raw -> new ResolvedIdentity.RoleAssignment(
                            value(raw.get("code")),
                            value(raw.get("scopeType")),
                            value(raw.get("scopeId"))))
                    .filter(assignment -> assignment.code() != null && !assignment.code().isBlank())
                    .distinct()
                    .toList();
        }
        Object rawRoles = claims.get("roles");
        if (rawRoles instanceof List<?> roles) {
            return roles.stream()
                    .map(this::value)
                    .filter(role -> role != null && !role.isBlank())
                    .distinct()
                    .map(role -> new ResolvedIdentity.RoleAssignment(role, "PLATFORM", null))
                    .toList();
        }
        return List.of();
    }

    private String value(Object raw) {
        return raw == null || raw.toString().isBlank() ? null : raw.toString();
    }

    private TokenExchangeResponse response(InternalTokenIssuer.IssuedInternalToken issued) {
        return new TokenExchangeResponse(
                issued.token(),
                ACCESS_TOKEN_TYPE,
                "Bearer",
                issued.expiresInSeconds(),
                String.join(" ", issued.scopes()));
    }

}
