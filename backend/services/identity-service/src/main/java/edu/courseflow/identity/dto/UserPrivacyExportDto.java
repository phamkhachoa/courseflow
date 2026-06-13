package edu.courseflow.identity.dto;

import java.time.Instant;
import java.time.ZonedDateTime;
import java.util.List;

public record UserPrivacyExportDto(
        UserDto profile,
        AccountSecuritySnapshotDto accountSecurity,
        List<RoleGrantExportDto> roleAssignments,
        Instant exportedAt) {

    public record AccountSecuritySnapshotDto(
            boolean mustChangePassword,
            Instant passwordChangedAt,
            Instant lastLoginAt,
            Instant lockedUntil,
            Instant accessTokensValidAfter,
            boolean mfaEnabled,
            ZonedDateTime createdOn,
            String createdBy,
            ZonedDateTime lastModifiedOn,
            String lastModifiedBy) {
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
