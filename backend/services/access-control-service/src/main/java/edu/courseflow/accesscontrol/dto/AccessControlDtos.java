package edu.courseflow.accesscontrol.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;

public final class AccessControlDtos {

    private AccessControlDtos() {
    }

    public record RoleAssignmentHint(
            @NotBlank String code,
            String scopeType,
            String scopeId) {
    }

    public record ResolveIdentityRequest(
            @NotBlank String issuer,
            @NotBlank String subject,
            @Email String email,
            Boolean emailVerified,
            List<RoleAssignmentHint> roleAssignments) {
    }

    public record ProvisionIdentityRequest(
            @NotBlank String userId,
            @NotBlank String issuer,
            @NotBlank String subject,
            @Email String email,
            Boolean emailVerified,
            List<RoleAssignmentHint> roleAssignments) {
    }

    public record ProvisionKeycloakUserRequest(
            @NotBlank String issuer,
            @NotBlank String subject,
            @Email String email,
            Boolean emailVerified,
            List<RoleAssignmentHint> roleAssignments) {
    }

    public record ResolvedRoleAssignmentDto(
            String code,
            String scopeType,
            String scopeId) {
    }

    public record ResolvedIdentityDto(
            String userId,
            String externalIssuer,
            String externalSubject,
            String email,
            String status,
            List<ResolvedRoleAssignmentDto> roleAssignments) {
    }

    public record AccessUserDirectoryItemDto(
            String userId,
            String email,
            String status,
            String primaryRole,
            String externalIssuer,
            String externalSubject) {
    }

    public record AccessUserDirectoryBatchRequest(
            @NotEmpty List<String> userIds) {
    }

    public record DeactivateAccessUserRequest(
            @NotBlank @Size(max = 255) String reason) {
    }

    public record AccessRoleGrantExportDto(
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

    public record PermissionDto(
            String code,
            String description,
            String category,
            String scopeType) {
    }

    public record PermissionGrantDto(
            String code,
            String description,
            String category,
            String effect) {
    }

    public record RoleDto(
            String id,
            String code,
            String name,
            String description,
            boolean isSystem,
            boolean isOperator,
            int rank,
            String parentRoleId,
            List<PermissionGrantDto> permissions) {
    }

    public record CreateRoleRequestDto(
            @NotBlank String code,
            @NotBlank String name,
            String description,
            String parentRoleId,
            Boolean isOperator,
            Integer rank) {
    }

    public record UpdateRoleRequestDto(
            String name,
            String description,
            String parentRoleId,
            Boolean isOperator,
            Integer rank) {
    }

    public record GrantPermissionRequestDto(
            @NotBlank String permCode,
            @NotBlank String effect) {
    }

    public record RoleAssignmentDto(
            Long id,
            Long userId,
            String roleId,
            String roleCode,
            String roleName,
            String scopeType,
            String scopeId,
            String grantedBy,
            Instant expiresAt,
            Instant createdAt) {
    }

    public record AssignRoleRequestDto(
            @NotBlank String roleId,
            @NotBlank String scopeType,
            String scopeId,
            String grantedBy,
            Instant expiresAt) {
    }

    public record AuthzCheckRequestDto(
            @NotBlank String userId,
            @NotBlank String permission,
            String scopeType,
            String scopeId,
            List<AuthzScopeDto> ancestorScopes) {
        public AuthzCheckRequestDto(String userId, String permission, String scopeType, String scopeId) {
            this(userId, permission, scopeType, scopeId, List.of());
        }
    }

    public record AuthzScopeDto(
            String scopeType,
            String scopeId) {
    }

    public record AuthzCheckResultDto(
            String userId,
            String permission,
            String scopeType,
            String scopeId,
            boolean allowed) {
    }
}
