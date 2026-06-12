package edu.courseflow.identity.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.AuthzDtos.AssignRoleRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.AssignmentDto;
import edu.courseflow.identity.dto.AuthzDtos.AuthzCheckRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.AuthzCheckResultDto;
import edu.courseflow.identity.dto.AuthzDtos.PermissionDto;
import edu.courseflow.identity.model.Role;
import edu.courseflow.identity.model.UserRoleAssignment;
import edu.courseflow.identity.mapper.IdentityMapper;
import edu.courseflow.identity.repository.PermissionRepository;
import edu.courseflow.identity.repository.RolePermissionGrantRepository;
import edu.courseflow.identity.repository.RoleRepository;
import edu.courseflow.identity.repository.UserRoleAssignmentRepository;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Authorization engine. Policy: role hierarchy is inherited, explicit DENY wins
 * over ALLOW, a
 * platform-scoped ADMIN role grants all permissions unless explicitly denied,
 * default = deny.
 * Revoking is soft-delete (sets revoked_at), so the engine only sees live
 * assignments.
 */
@Service
public class AuthzService {

    private static final int MAX_ROLE_DEPTH = 20;

    private final PermissionRepository permissions;
    private final RoleRepository roles;
    private final UserRoleAssignmentRepository assignments;
    private final RolePermissionGrantRepository grants;
    private final IdentityMapper mapper;
    private final AccessTokenRevocationService accessTokenRevocations;
    private final SecurityAuditService audit;

    public AuthzService(PermissionRepository permissions,
            RoleRepository roles,
            UserRoleAssignmentRepository assignments,
            RolePermissionGrantRepository grants,
            IdentityMapper mapper,
            AccessTokenRevocationService accessTokenRevocations,
            SecurityAuditService audit) {
        this.permissions = permissions;
        this.roles = roles;
        this.assignments = assignments;
        this.grants = grants;
        this.mapper = mapper;
        this.accessTokenRevocations = accessTokenRevocations;
        this.audit = audit;
    }

    @Transactional(readOnly = true)
    public List<PermissionDto> listPermissions() {
        return permissions.findAllByOrderByCategoryAscCodeAsc().stream()
                .map(mapper::toDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<AssignmentDto> listAssignments(Long userId) {
        return assignments.findLiveByUserId(userId).stream()
                .map(mapper::toDto)
                .toList();
    }

    @Transactional
    public AssignmentDto assignRole(Long userId, AssignRoleRequestDto request, CurrentUser caller) {
        requireAdmin(caller);
        UUID roleId = UUID.fromString(request.roleId());
        Role role = roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        UserRoleAssignment assignment = assignments
                .findLiveExisting(userId, roleId, request.scopeType(), request.scopeId())
                .map(existing -> {
                    existing.updateGrant(request.grantedBy(), request.expiresAt());
                    return existing;
                })
                .orElseGet(() -> new UserRoleAssignment(
                        userId,
                        role,
                        request.scopeType(),
                        request.scopeId(),
                        request.grantedBy(),
                        request.expiresAt()));
        UserRoleAssignment saved = assignments.save(assignment);
        accessTokenRevocations.revokeAllForUser(userId);
        audit.record("ROLE_ASSIGNED", userId, null, request.grantedBy(), true, role.getCode());
        return mapper.toDto(saved);
    }

    @Transactional
    public void revokeAssignment(Long userId, Long assignmentId, String revokedBy, CurrentUser caller) {
        requireAdmin(caller);
        UserRoleAssignment assignment = assignments.findByIdAndUserId(assignmentId, userId)
                .orElseThrow(() -> new NotFoundException("ASSIGNMENT_NOT_FOUND"));
        assignment.revoke(revokedBy);
        accessTokenRevocations.revokeAllForUser(userId);
        audit.record("ROLE_REVOKED", userId, null, revokedBy, true, assignment.getRole().getCode());
    }

    @Transactional(readOnly = true)
    public AuthzCheckResultDto check(AuthzCheckRequestDto request) {
        String scopeType = request.scopeType() == null ? "PLATFORM" : request.scopeType();
        Long userId = parseUserId(request.userId());
        List<UserRoleAssignment> activeAssignments = assignments.findActiveForScope(
                userId, scopeType, request.scopeId(), Instant.now());

        Set<Role> effectiveRoles = resolveEffectiveRoles(activeAssignments.stream()
                .map(UserRoleAssignment::getRole)
                .toList());
        boolean explicitDeny = hasGrant(effectiveRoles, request.permission(), "DENY");
        boolean platformAdmin = activeAssignments.stream()
                .anyMatch(a -> "PLATFORM".equals(a.getScopeType()) && "ADMIN".equals(a.getRole().getCode()));
        boolean allowed = !explicitDeny
                && (platformAdmin || hasGrant(effectiveRoles, request.permission(), "ALLOW"));

        return new AuthzCheckResultDto(request.userId(), request.permission(), scopeType, request.scopeId(), allowed);
    }

    private Long parseUserId(String raw) {
        try {
            return Long.valueOf(raw);
        } catch (NumberFormatException ex) {
            throw new BadRequestException("INVALID_USER_ID");
        }
    }

    private void requireAdmin(CurrentUser caller) {
        if (caller == null || !caller.hasRole("ADMIN")) {
            throw new ForbiddenException("ADMIN_REQUIRED");
        }
    }

    private Set<Role> resolveEffectiveRoles(List<Role> directRoles) {
        Map<UUID, Role> resolved = new LinkedHashMap<>();
        for (Role direct : directRoles) {
            Role current = direct;
            int depth = 0;
            while (current != null && depth < MAX_ROLE_DEPTH) {
                if (resolved.putIfAbsent(current.getId(), current) != null)
                    break;
                current = current.getParentRole();
                depth++;
            }
        }
        return new LinkedHashSet<>(resolved.values());
    }

    private boolean hasGrant(Set<Role> effectiveRoles, String permission, String effect) {
        return effectiveRoles.stream()
                .flatMap(role -> grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId())
                        .stream())
                .anyMatch(grant -> permission.equals(grant.getPermission().getCode())
                        && effect.equalsIgnoreCase(grant.getEffect()));
    }

}
