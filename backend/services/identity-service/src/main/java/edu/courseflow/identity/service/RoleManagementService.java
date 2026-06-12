package edu.courseflow.identity.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.DuplicatedException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.identity.dto.AuthzDtos.CreateRoleRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.GrantPermissionRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.PermissionGrantDto;
import edu.courseflow.identity.dto.AuthzDtos.RoleDto;
import edu.courseflow.identity.dto.AuthzDtos.UpdateRoleRequestDto;
import edu.courseflow.identity.model.Permission;
import edu.courseflow.identity.model.Role;
import edu.courseflow.identity.model.RolePermissionGrant;
import edu.courseflow.identity.mapper.IdentityMapper;
import edu.courseflow.identity.repository.PermissionRepository;
import edu.courseflow.identity.repository.RolePermissionGrantRepository;
import edu.courseflow.identity.repository.RoleRepository;
import edu.courseflow.identity.repository.UserRoleAssignmentRepository;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * CRUD for dynamic roles and their permission grants. System roles
 * ({@code is_system = true}) are
 * structurally immutable: name/description/parent cannot change and they cannot
 * be deleted; only
 * their permission grants can be tuned by an admin.
 */
@Service
public class RoleManagementService {

    private static final int MAX_ROLE_DEPTH = 20;

    private final RoleRepository roles;
    private final PermissionRepository permissions;
    private final RolePermissionGrantRepository grants;
    private final UserRoleAssignmentRepository assignments;
    private final IdentityMapper mapper;

    public RoleManagementService(RoleRepository roles,
            PermissionRepository permissions,
            RolePermissionGrantRepository grants,
            UserRoleAssignmentRepository assignments,
            IdentityMapper mapper) {
        this.roles = roles;
        this.permissions = permissions;
        this.grants = grants;
        this.assignments = assignments;
        this.mapper = mapper;
    }

    @Transactional(readOnly = true)
    public List<RoleDto> listRoles() {
        // Single fetch of all roles + their grants. Avoids the N+1 the previous loop
        // introduced.
        List<Role> all = roles.findAllByOrderBySystemDescCodeAsc();
        return all.stream()
                .map(role -> toRoleDto(role, directGrants(role.getId())))
                .toList();
    }

    @Transactional(readOnly = true)
    public RoleDto getRole(UUID roleId) {
        Role role = roles.findWithParentRoleById(roleId)
                .orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        return toRoleDto(role, directGrants(roleId));
    }

    private List<PermissionGrantDto> directGrants(UUID roleId) {
        return grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(roleId).stream()
                .map(this::toPermissionGrantDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<PermissionGrantDto> effectivePermissions(UUID roleId) {
        Role role = roles.findWithParentRoleById(roleId)
                .orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        Map<String, PermissionGrantDto> resolved = new LinkedHashMap<>();
        Role current = role;
        int depth = 0;
        Set<UUID> seen = new HashSet<>();
        while (current != null && depth < MAX_ROLE_DEPTH && seen.add(current.getId())) {
            for (RolePermissionGrant grant : grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(
                    current.getId())) {
                PermissionGrantDto dto = toPermissionGrantDto(grant);
                PermissionGrantDto existing = resolved.get(dto.code());
                if (existing == null || "DENY".equalsIgnoreCase(dto.effect())) {
                    resolved.put(dto.code(), dto);
                }
            }
            current = current.getParentRole();
            depth++;
        }
        return resolved.values().stream()
                .sorted((left, right) -> {
                    int category = nullSafe(left.category()).compareTo(nullSafe(right.category()));
                    return category != 0 ? category : left.code().compareTo(right.code());
                })
                .toList();
    }

    @Transactional
    public RoleDto createRole(CreateRoleRequestDto request, String createdBy) {
        if (roles.existsByCode(request.code())) {
            throw new DuplicatedException("ROLE_CODE_EXISTS", request.code());
        }
        Role parent = resolveParent(request.parentRoleId());
        Role role = new Role(UUID.randomUUID(), request.code(), request.name(),
                request.description(), false,
                Boolean.TRUE.equals(request.isOperator()),
                request.rank() == null ? 0 : request.rank(),
                parent, createdBy);
        roles.save(role);
        return getRole(role.getId());
    }

    @Transactional
    public RoleDto updateRole(UUID roleId, UpdateRoleRequestDto request, String updatedBy) {
        Role existing = roles.findWithParentRoleById(roleId)
                .orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        if (existing.isSystem()) {
            throw new BadRequestException("SYSTEM_ROLE_IMMUTABLE");
        }
        Role parent = resolveParent(request.parentRoleId());
        if (parent != null && wouldCreateCycle(existing, parent)) {
            throw new BadRequestException("ROLE_HIERARCHY_CYCLE");
        }
        existing.setName(request.name());
        existing.setDescription(request.description());
        existing.setParentRole(parent);
        if (request.isOperator() != null)
            existing.setOperator(request.isOperator());
        if (request.rank() != null)
            existing.setRank(request.rank());
        existing.touch(updatedBy);
        return getRole(roleId);
    }

    @Transactional
    public void deleteRole(UUID roleId) {
        Role existing = roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        if (existing.isSystem()) {
            throw new BadRequestException("SYSTEM_ROLE_IMMUTABLE");
        }
        if (assignments.countLiveByRoleId(roleId) > 0) {
            throw new BadRequestException("ROLE_HAS_ACTIVE_ASSIGNMENTS");
        }
        roles.delete(existing);
    }

    @Transactional
    public RoleDto grantPermission(UUID roleId, GrantPermissionRequestDto request, String createdBy) {
        Role role = roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        String effect = request.effect().toUpperCase();
        if (!effect.equals("ALLOW") && !effect.equals("DENY")) {
            throw new BadRequestException("INVALID_EFFECT");
        }
        Permission permission = permissions.findById(request.permCode())
                .orElseThrow(() -> new NotFoundException("PERMISSION_NOT_FOUND"));
        RolePermissionGrant grant = grants.findByRole_IdAndPermission_Code(roleId, request.permCode())
                .orElseGet(() -> new RolePermissionGrant(role, permission, effect, createdBy));
        grant.setEffect(effect);
        grants.save(grant);
        return getRole(roleId);
    }

    @Transactional
    public RoleDto revokePermission(UUID roleId, String permCode) {
        roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        grants.deleteByRoleIdAndPermissionCode(roleId, permCode);
        return getRole(roleId);
    }

    private Role resolveParent(String parentRoleId) {
        if (parentRoleId == null || parentRoleId.isBlank())
            return null;
        return roles.findById(UUID.fromString(parentRoleId))
                .orElseThrow(() -> new NotFoundException("PARENT_ROLE_NOT_FOUND"));
    }

    private boolean wouldCreateCycle(Role child, Role candidateParent) {
        Role current = candidateParent;
        int depth = 0;
        Set<UUID> seen = new HashSet<>();
        while (current != null && depth < MAX_ROLE_DEPTH && seen.add(current.getId())) {
            if (current.getId().equals(child.getId()))
                return true;
            current = current.getParentRole();
            depth++;
        }
        return false;
    }

    private RoleDto toRoleDto(Role role, List<PermissionGrantDto> permissions) {
        return mapper.toDto(role, permissions);
    }

    private PermissionGrantDto toPermissionGrantDto(RolePermissionGrant grant) {
        return mapper.toDto(grant);
    }

    private String nullSafe(String value) {
        return value == null ? "" : value;
    }
}
