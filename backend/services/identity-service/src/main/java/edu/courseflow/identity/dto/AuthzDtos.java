package edu.courseflow.identity.dto;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.List;

public final class AuthzDtos {

        private AuthzDtos() {
        }

        // ─── permissions ─────────────────────────────────────────────────────────

        public record PermissionDto(String code, String description, String category, String scopeType) {
        }

        public record GrantPermissionRequestDto(
                        @NotBlank String permCode,
                        @NotBlank String effect // ALLOW | DENY
        ) {
        }

        // ─── roles ───────────────────────────────────────────────────────────────

        public record PermissionGrantDto(String code, String description, String category, String effect) {
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

        // ─── assignments ─────────────────────────────────────────────────────────

        public record AssignmentDto(
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

        // ─── authz check ─────────────────────────────────────────────────────────

        public record AuthzCheckRequestDto(
                        @NotBlank String userId,
                        @NotBlank String permission,
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
