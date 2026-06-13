package edu.courseflow.usermanagement.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class AccessControlUserDirectoryClient {

    private final RestClient client;
    private final InternalJwtService internalJwt;

    public AccessControlUserDirectoryClient(
            RestClient.Builder restClientBuilder,
            InternalJwtService internalJwt,
            @Value("${courseflow.user-management.access-control-service-url:${ACCESS_CONTROL_SERVICE_URI:${ACCESS_CONTROL_SERVICE_URL:http://access-control-service:8080}}}")
            String accessControlServiceUrl,
            @Value("${courseflow.user-management.access-control-timeout-ms:${ACCESS_CONTROL_TIMEOUT_MS:1500}}")
            long timeoutMs) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int boundedTimeout = (int) Math.max(250, Math.min(timeoutMs, 5000));
        requestFactory.setConnectTimeout(boundedTimeout);
        requestFactory.setReadTimeout(boundedTimeout);
        this.client = restClientBuilder.clone()
                .baseUrl(accessControlServiceUrl)
                .requestFactory(requestFactory)
                .build();
        this.internalJwt = internalJwt;
    }

    public List<AccessUserDirectoryItem> list(String query, int limit) {
        String trimmedQuery = query == null || query.isBlank() ? null : query.trim();
        return client.get()
                .uri(builder -> builder.path("/internal/users")
                        .queryParam("limit", limit)
                        .queryParamIfPresent("q", Optional.ofNullable(trimmedQuery))
                        .build())
                .headers(headers -> internalJwt.applyServiceToken(
                        headers, Set.of(InternalScopes.USER_DIRECTORY_READ)))
                .retrieve()
                .body(new ParameterizedTypeReference<>() {
                });
    }

    public AccessUserDirectoryItem get(long userId) {
        return client.get()
                .uri("/internal/users/{userId}", userId)
                .headers(headers -> internalJwt.applyServiceToken(
                        headers, Set.of(InternalScopes.USER_DIRECTORY_READ)))
                .retrieve()
                .body(AccessUserDirectoryItem.class);
    }

    public ResolvedIdentity provisionKeycloakUser(String issuer, String subject, String email) {
        return client.post()
                .uri("/internal/identities/provision-keycloak-user")
                .headers(headers -> internalJwt.applyServiceToken(
                        headers, Set.of(InternalScopes.IDENTITY_PROVISION)))
                .body(new ProvisionKeycloakUserRequest(
                        issuer,
                        subject,
                        email,
                        false,
                        List.of()))
                .retrieve()
                .body(ResolvedIdentity.class);
    }

    public AccessUserDirectoryItem deactivate(long userId, String reason) {
        return client.post()
                .uri("/internal/users/{userId}/deactivate", userId)
                .headers(headers -> internalJwt.applyServiceToken(
                        headers, Set.of(InternalScopes.USER_DIRECTORY_WRITE)))
                .body(new DeactivateAccessUserRequest(reason))
                .retrieve()
                .body(AccessUserDirectoryItem.class);
    }

    public List<RoleGrantExport> exportAssignments(long userId) {
        return client.get()
                .uri("/internal/users/{userId}/assignments:export", userId)
                .headers(headers -> internalJwt.applyServiceToken(
                        headers, Set.of(InternalScopes.ROLE_ASSIGNMENT_READ)))
                .retrieve()
                .body(new ParameterizedTypeReference<>() {
                });
    }

    public List<AccessUserDirectoryItem> batch(List<Long> userIds) {
        return client.post()
                .uri("/internal/users/summary:batch")
                .headers(headers -> internalJwt.applyServiceToken(
                        headers, Set.of(InternalScopes.USER_DIRECTORY_READ)))
                .body(new AccessUserDirectoryBatchRequest(userIds.stream()
                        .map(String::valueOf)
                        .toList()))
                .retrieve()
                .body(new ParameterizedTypeReference<>() {
                });
    }

    public boolean authorized(String userId, String permission, String scopeType, String scopeId) {
        AuthzCheckResult result = client.post()
                .uri("/internal/authz/check")
                .headers(headers -> internalJwt.applyServiceToken(
                        headers, Set.of(InternalScopes.AUTHZ_CHECK)))
                .body(new AuthzCheckRequest(userId, permission, scopeType, scopeId))
                .retrieve()
                .body(AuthzCheckResult.class);
        return result != null && result.allowed();
    }

    public record AccessUserDirectoryItem(
            String userId,
            String email,
            String status,
            String primaryRole,
            String externalIssuer,
            String externalSubject) {
    }

    private record AccessUserDirectoryBatchRequest(List<String> userIds) {
    }

    private record ProvisionKeycloakUserRequest(
            String issuer,
            String subject,
            String email,
            Boolean emailVerified,
            List<RoleAssignmentHint> roleAssignments) {
    }

    private record RoleAssignmentHint(String code, String scopeType, String scopeId) {
    }

    private record DeactivateAccessUserRequest(String reason) {
    }

    private record AuthzCheckRequest(String userId, String permission, String scopeType, String scopeId) {
    }

    private record AuthzCheckResult(String userId, String permission, String scopeType, String scopeId,
            boolean allowed) {
    }

    public record ResolvedIdentity(
            String userId,
            String externalIssuer,
            String externalSubject,
            String email,
            String status,
            List<RoleAssignmentHint> roleAssignments) {
    }

    public record RoleGrantExport(
            Long id,
            String roleId,
            String roleCode,
            String roleName,
            String scopeType,
            String scopeId,
            String grantedBy,
            Instant grantedAt,
            Instant expiresAt,
            Instant revokedAt,
            String revokedBy,
            Instant createdAt) {
    }
}
