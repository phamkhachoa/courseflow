package edu.courseflow.usermanagement.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;
import java.util.Map;

public final class UserProfileDtos {

    private UserProfileDtos() {
    }

    public record UserProfileDto(
            String userId,
            String displayName,
            String avatarUrl,
            String bio,
            String locale,
            String timezone,
            String visibility) {
    }

    public record UpdateMyProfileRequest(
            @NotBlank @Size(max = 255) String displayName,
            @Size(max = 2000) String bio,
            String avatarUrl,
            String locale,
            String timezone,
            String visibility) {
    }

    public record ProvisionUserProfileRequest(
            @NotBlank String userId,
            @NotBlank @Size(max = 255) String displayName,
            @Size(max = 2000) String bio,
            String avatarUrl,
            String locale,
            String timezone,
            String visibility) {
    }

    public record ProfileSummaryBatchRequest(
            @NotEmpty List<String> userIds) {
    }

    public record ProfileSummaryDto(
            String userId,
            String displayName,
            String avatarUrl) {
    }

    public record UserDirectoryItemDto(
            String userId,
            String displayName,
            String avatarUrl,
            String locale,
            String timezone,
            String visibility) {
    }

    public record AdminUserDto(
            Long id,
            String email,
            String fullName,
            String role,
            String status) {
    }

    public record CurrentUserDto(
            Long id,
            String email,
            String fullName,
            String avatarUrl,
            String role,
            String status,
            boolean emailVerified,
            boolean mfaEnabled) {
    }

    public record CreateAdminUserRequest(
            @NotBlank @Email String email,
            @NotBlank @Size(max = 255) String fullName,
            Boolean sendSetupEmail) {
    }

    public record DeactivateAdminUserRequest(
            @NotBlank @Size(max = 255) String reason) {
    }

    public record AdminUserPrivacyExportDto(
            AdminUserDto profile,
            AccountSecuritySnapshotDto accountSecurity,
            List<RoleGrantExportDto> roleAssignments,
            Instant exportedAt) {
    }

    public record AccountSecuritySnapshotDto(
            String keycloakSubject,
            boolean enabled,
            boolean emailVerified,
            List<String> requiredActions,
            Map<String, List<String>> attributes) {
    }

    public record RoleGrantExportDto(
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
