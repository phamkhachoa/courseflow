package edu.courseflow.accesscontrol.service;

import edu.courseflow.accesscontrol.dto.AccessControlDtos.AccessUserDirectoryItemDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AccessRoleGrantExportDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AssignRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzCheckRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzCheckResultDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzScopeDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.CreateRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.DeactivateAccessUserRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.GrantPermissionRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.PermissionDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.PermissionGrantDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ProvisionIdentityRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ProvisionKeycloakUserRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ResolveIdentityRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ResolvedIdentityDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ResolvedRoleAssignmentDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.RoleAssignmentDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.RoleAssignmentHint;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.RoleDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.UpdateRoleRequestDto;
import edu.courseflow.accesscontrol.model.AccessControlAuditLog;
import edu.courseflow.accesscontrol.model.AccessUser;
import edu.courseflow.accesscontrol.model.ExternalIdentityLink;
import edu.courseflow.accesscontrol.model.Permission;
import edu.courseflow.accesscontrol.model.Role;
import edu.courseflow.accesscontrol.model.RolePermissionGrant;
import edu.courseflow.accesscontrol.model.UserRoleAssignment;
import edu.courseflow.accesscontrol.repository.AccessControlAuditLogRepository;
import edu.courseflow.accesscontrol.repository.AccessUserRepository;
import edu.courseflow.accesscontrol.repository.ExternalIdentityLinkRepository;
import edu.courseflow.accesscontrol.repository.PermissionRepository;
import edu.courseflow.accesscontrol.repository.RolePermissionGrantRepository;
import edu.courseflow.accesscontrol.repository.RoleRepository;
import edu.courseflow.accesscontrol.repository.UserRoleAssignmentRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.DuplicatedException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AccessControlService {

    private static final int MAX_ROLE_DEPTH = 20;
    private static final Set<String> ASSIGNMENT_SCOPE_TYPES =
            Set.of("PLATFORM", "TENANT", "APPLICATION", "ORG", "DEPARTMENT", "COURSE", "SECTION");
    private static final Set<String> PERMISSION_SCOPE_TYPES =
            Set.of("ANY", "PLATFORM", "TENANT", "APPLICATION", "ORG", "DEPARTMENT", "COURSE", "SECTION");
    private static final Map<String, Integer> SCOPE_DEPTH = Map.of(
            "PLATFORM", 0,
            "TENANT", 1,
            "APPLICATION", 2,
            "ORG", 1,
            "DEPARTMENT", 2,
            "COURSE", 3,
            "SECTION", 4);

    private final AccessUserRepository users;
    private final ExternalIdentityLinkRepository identityLinks;
    private final PermissionRepository permissions;
    private final RoleRepository roles;
    private final RolePermissionGrantRepository grants;
    private final UserRoleAssignmentRepository assignments;
    private final AccessControlAuditLogRepository auditLogs;
    private final AccessControlMetrics metrics;
    private final InternalJwtService internalJwtService;
    private final boolean auditAuthzAllowed;

    public AccessControlService(
            AccessUserRepository users,
            ExternalIdentityLinkRepository identityLinks,
            PermissionRepository permissions,
            RoleRepository roles,
            RolePermissionGrantRepository grants,
            UserRoleAssignmentRepository assignments,
            AccessControlAuditLogRepository auditLogs,
            AccessControlMetrics metrics,
            InternalJwtService internalJwtService,
            @Value("${courseflow.access-control.audit-authz-allowed:false}") boolean auditAuthzAllowed) {
        this.users = users;
        this.identityLinks = identityLinks;
        this.permissions = permissions;
        this.roles = roles;
        this.grants = grants;
        this.assignments = assignments;
        this.auditLogs = auditLogs;
        this.metrics = metrics;
        this.internalJwtService = internalJwtService;
        this.auditAuthzAllowed = auditAuthzAllowed;
    }

    @Transactional(readOnly = true)
    public List<PermissionDto> permissions() {
        return permissions(null);
    }

    @Transactional(readOnly = true)
    public List<PermissionDto> permissions(CurrentUser caller) {
        requireRoleAdministrationForUserCaller(caller);
        return permissions.findAllByOrderByCategoryAscCodeAsc().stream()
                .map(this::toPermissionDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<RoleDto> roles() {
        return roles(null);
    }

    @Transactional(readOnly = true)
    public List<RoleDto> roles(CurrentUser caller) {
        requireRoleAdministrationForUserCaller(caller);
        return roles.findAllByOrderBySystemDescCodeAsc().stream()
                .map(role -> toRoleDto(role, directGrants(role.getId())))
                .toList();
    }

    @Transactional(readOnly = true)
    public RoleDto role(UUID roleId) {
        return role(roleId, null);
    }

    @Transactional(readOnly = true)
    public RoleDto role(UUID roleId, CurrentUser caller) {
        requireRoleAdministrationForUserCaller(caller);
        Role role = roles.findWithParentRoleById(roleId)
                .orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        return toRoleDto(role, directGrants(roleId));
    }

    @Transactional(readOnly = true)
    public List<PermissionGrantDto> effectivePermissions(UUID roleId) {
        return effectivePermissions(roleId, null);
    }

    @Transactional(readOnly = true)
    public List<PermissionGrantDto> effectivePermissions(UUID roleId, CurrentUser caller) {
        requireRoleAdministrationForUserCaller(caller);
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
    public RoleDto createRole(CreateRoleRequestDto request, CurrentUser caller) {
        requirePermission(caller, "role:manage");
        String code = normalizeRequired(request.code(), "code").toUpperCase(Locale.ROOT);
        if (roles.existsByCode(code)) {
            throw new DuplicatedException("ROLE_CODE_EXISTS", code);
        }
        String callerTag = callerTag(caller);
        Role parent = resolveParent(request.parentRoleId());
        Role role = new Role(
                UUID.randomUUID(),
                code,
                normalizeRequired(request.name(), "name"),
                trimToNull(request.description()),
                false,
                Boolean.TRUE.equals(request.isOperator()),
                request.rank() == null ? 0 : request.rank(),
                parent,
                callerTag);
        roles.save(role);
        audit("ROLE_CREATED", null, callerTag, true, code);
        return role(role.getId());
    }

    @Transactional
    public RoleDto updateRole(UUID roleId, UpdateRoleRequestDto request, CurrentUser caller) {
        requirePermission(caller, "role:manage");
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
        existing.setDescription(trimToNull(request.description()));
        existing.setParentRole(parent);
        if (request.isOperator() != null) {
            existing.setOperator(request.isOperator());
        }
        if (request.rank() != null) {
            existing.setRank(request.rank());
        }
        existing.touch(callerTag(caller));
        audit("ROLE_UPDATED", null, callerTag(caller), true, existing.getCode());
        return role(roleId);
    }

    @Transactional
    public void deleteRole(UUID roleId, CurrentUser caller) {
        requirePermission(caller, "role:manage");
        Role existing = roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        if (existing.isSystem()) {
            throw new BadRequestException("SYSTEM_ROLE_IMMUTABLE");
        }
        if (assignments.countLiveByRoleId(roleId) > 0) {
            throw new BadRequestException("ROLE_HAS_ACTIVE_ASSIGNMENTS");
        }
        roles.delete(existing);
        audit("ROLE_DELETED", null, callerTag(caller), true, existing.getCode());
    }

    @Transactional
    public RoleDto grantPermission(UUID roleId, GrantPermissionRequestDto request, CurrentUser caller) {
        requirePermission(caller, "role:manage");
        Role role = roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        String effect = normalizeRequired(request.effect(), "effect").toUpperCase(Locale.ROOT);
        if (!effect.equals("ALLOW") && !effect.equals("DENY")) {
            throw new BadRequestException("INVALID_EFFECT");
        }
        String permissionCode = normalizeRequired(request.permCode(), "permCode");
        Permission permission = permissions.findById(permissionCode)
                .orElseThrow(() -> new NotFoundException("PERMISSION_NOT_FOUND"));
        RolePermissionGrant grant = grants.findByRole_IdAndPermission_Code(roleId, permissionCode)
                .orElseGet(() -> new RolePermissionGrant(role, permission, effect, callerTag(caller)));
        grant.setEffect(effect);
        grants.save(grant);
        audit("ROLE_PERMISSION_GRANTED", null, callerTag(caller), true, role.getCode() + ":" + permissionCode);
        return role(roleId);
    }

    @Transactional
    public RoleDto revokePermission(UUID roleId, String permCode, CurrentUser caller) {
        requirePermission(caller, "role:manage");
        Role role = roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        grants.deleteByRoleIdAndPermissionCode(roleId, permCode);
        audit("ROLE_PERMISSION_REVOKED", null, callerTag(caller), true, role.getCode() + ":" + permCode);
        return role(roleId);
    }

    @Transactional
    public ResolvedIdentityDto resolveIdentity(ResolveIdentityRequest request) {
        String issuer = normalizeRequired(request.issuer(), "issuer");
        String subject = normalizeRequired(request.subject(), "subject");
        AccessUser user = identityLinks.findActiveByIssuerAndSubject(issuer, subject)
                .map(link -> {
                    link.touchSeen();
                    return link.getUser();
                })
                .orElse(null);
        if (user == null) {
            throw new NotFoundException("EXTERNAL_IDENTITY_NOT_LINKED", issuer + ":" + subject);
        }
        if (!"ACTIVE".equals(user.getStatus())) {
            throw new BadRequestException("USER_NOT_ACTIVE");
        }
        return new ResolvedIdentityDto(
                String.valueOf(user.getId()),
                issuer,
                subject,
                user.getEmail(),
                user.getStatus(),
                resolvedAssignments(user.getId()));
    }

    @Transactional
    public ResolvedIdentityDto provisionIdentity(ProvisionIdentityRequest request, CurrentUser caller) {
        long userId = parseUserId(request.userId());
        String issuer = normalizeRequired(request.issuer(), "issuer");
        String subject = normalizeRequired(request.subject(), "subject");
        String email = normalizeEmail(request.email());
        String actor = callerTag(caller);

        AccessUser user = users.findById(userId).orElseGet(() -> new AccessUser(userId, email));
        user.updateEmail(email);
        users.save(user);

        ExternalIdentityLink link = identityLinks.findByIssuerAndSubject(issuer, subject).orElse(null);
        if (link != null && !userIdEquals(link, userId)) {
            audit("IDENTITY_PROVISION_FAILED", user, actor, false, issuer + ":" + subject);
            throw new BadRequestException("EXTERNAL_IDENTITY_ALREADY_LINKED");
        }
        if (link == null) {
            link = new ExternalIdentityLink(
                    user, "keycloak", issuer, subject, email, Boolean.TRUE.equals(request.emailVerified()));
        } else {
            link.relink(user, email, Boolean.TRUE.equals(request.emailVerified()));
        }
        identityLinks.save(link);

        grantRoleHints(user, request.roleAssignments(), actor);
        user.invalidateTokens();
        audit("IDENTITY_PROVISIONED", user, actor, true, issuer + ":" + subject);
        return new ResolvedIdentityDto(
                String.valueOf(user.getId()),
                issuer,
                subject,
                user.getEmail(),
                user.getStatus(),
                resolvedAssignments(user.getId()));
    }

    @Transactional
    public ResolvedIdentityDto provisionKeycloakUser(ProvisionKeycloakUserRequest request, CurrentUser caller) {
        String issuer = normalizeRequired(request.issuer(), "issuer");
        String subject = normalizeRequired(request.subject(), "subject");
        String email = normalizeEmail(request.email());
        String actor = callerTag(caller);

        ExternalIdentityLink existingLink = identityLinks.findByIssuerAndSubject(issuer, subject).orElse(null);
        if (existingLink != null && existingLink.getUser() != null) {
            AccessUser existingUser = existingLink.getUser();
            existingUser.updateEmail(email);
            grantRoleHints(existingUser, request.roleAssignments(), actor);
            audit("KEYCLOAK_USER_PROVISIONED_IDEMPOTENT", existingUser, actor, true, issuer + ":" + subject);
            return new ResolvedIdentityDto(
                    String.valueOf(existingUser.getId()),
                    issuer,
                    subject,
                    existingUser.getEmail(),
                    existingUser.getStatus(),
                    resolvedAssignments(existingUser.getId()));
        }

        AccessUser user = users.save(new AccessUser(email));
        ExternalIdentityLink link = new ExternalIdentityLink(
                user, "keycloak", issuer, subject, email, Boolean.TRUE.equals(request.emailVerified()));
        identityLinks.save(link);
        grantRoleHints(user, request.roleAssignments(), actor);
        user.invalidateTokens();
        audit("KEYCLOAK_USER_PROVISIONED", user, actor, true, issuer + ":" + subject);
        return new ResolvedIdentityDto(
                String.valueOf(user.getId()),
                issuer,
                subject,
                user.getEmail(),
                user.getStatus(),
                resolvedAssignments(user.getId()));
    }

    @Transactional(readOnly = true)
    public List<RoleAssignmentDto> listAssignments(long userId) {
        return listAssignments(userId, null);
    }

    @Transactional(readOnly = true)
    public List<RoleAssignmentDto> listAssignments(long userId, CurrentUser caller) {
        requireRoleAdministrationForUserCaller(caller);
        return assignments.findLiveByUserId(userId).stream()
                .map(this::toAssignmentDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<AccessRoleGrantExportDto> exportAssignments(long userId) {
        return exportAssignments(userId, null);
    }

    @Transactional(readOnly = true)
    public List<AccessRoleGrantExportDto> exportAssignments(long userId, CurrentUser caller) {
        requireRoleAdministrationForUserCaller(caller);
        ensureUserExists(userId);
        return assignments.findAllByUserId(userId).stream()
                .map(this::toRoleGrantExportDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<AccessUserDirectoryItemDto> userDirectory(String query, int limit) {
        return userDirectory(query, limit, null);
    }

    @Transactional(readOnly = true)
    public List<AccessUserDirectoryItemDto> userDirectory(String query, int limit, CurrentUser caller) {
        requireUserDirectoryReadForUserCaller(caller);
        int boundedLimit = Math.max(1, Math.min(limit, 200));
        String needle = query == null || query.isBlank() ? "" : query.trim().toLowerCase(Locale.ROOT);
        return users.searchDirectory(needle, PageRequest.of(0, boundedLimit)).stream()
                .map(this::toDirectoryItem)
                .toList();
    }

    @Transactional(readOnly = true)
    public AccessUserDirectoryItemDto userDirectoryItem(long userId) {
        return userDirectoryItem(userId, null);
    }

    @Transactional(readOnly = true)
    public AccessUserDirectoryItemDto userDirectoryItem(long userId, CurrentUser caller) {
        requireUserDirectoryReadForUserCaller(caller);
        return users.findById(userId)
                .map(this::toDirectoryItem)
                .orElseThrow(() -> new NotFoundException("ACCESS_USER_NOT_FOUND", userId));
    }

    @Transactional(readOnly = true)
    public List<AccessUserDirectoryItemDto> userDirectoryBatch(List<String> rawUserIds) {
        List<Long> userIds = parseUserIds(rawUserIds);
        if (userIds.isEmpty()) {
            return List.of();
        }
        Map<Long, AccessUser> byId = users.findAllById(userIds).stream()
                .collect(LinkedHashMap::new, (map, user) -> map.put(user.getId(), user), Map::putAll);
        return userIds.stream()
                .map(byId::get)
                .filter(Objects::nonNull)
                .map(this::toDirectoryItem)
                .toList();
    }

    @Transactional
    public AccessUserDirectoryItemDto deactivateUser(long userId, DeactivateAccessUserRequest request,
            CurrentUser caller) {
        requirePlatformAdministrationForUserCaller(caller);
        AccessUser user = ensureUserExists(userId);
        String actor = callerTag(caller);
        String reason = normalizeRequired(request.reason(), "reason");
        user.deactivate();
        assignments.findLiveByUserId(userId).forEach(assignment -> assignment.revoke(actor));
        audit("ACCESS_USER_DEACTIVATED", user, actor, true, detail("reason=", reason));
        return toDirectoryItem(user);
    }

    @Transactional
    public RoleAssignmentDto assignRole(long userId, AssignRoleRequestDto request, CurrentUser caller) {
        String scopeType = normalizeAssignmentScope(request.scopeType());
        String scopeId = normalizeScopeId(scopeType, request.scopeId());
        requireRoleAssignmentPermission(caller, scopeType, scopeId);
        AccessUser user = ensureUser(userId);
        UUID roleId = parseUuid(request.roleId(), "roleId");
        Role role = roles.findById(roleId).orElseThrow(() -> new NotFoundException("ROLE_NOT_FOUND"));
        String grantedBy = callerTag(caller);
        UserRoleAssignment assignment = assignments.findLiveExisting(userId, roleId, scopeType, scopeId)
                .map(existing -> {
                    existing.updateGrant(grantedBy, request.expiresAt());
                    return existing;
                })
                .orElseGet(() -> new UserRoleAssignment(user, role, scopeType, scopeId, grantedBy, request.expiresAt()));
        UserRoleAssignment saved = assignments.save(assignment);
        user.invalidateTokens();
        audit("ROLE_ASSIGNED", user, grantedBy, true, role.getCode());
        return toAssignmentDto(saved);
    }

    @Transactional
    public void revokeAssignment(long userId, long assignmentId, CurrentUser caller) {
        UserRoleAssignment assignment = assignments.findByIdAndUser_Id(assignmentId, userId)
                .orElseThrow(() -> new NotFoundException("ASSIGNMENT_NOT_FOUND"));
        requireRoleAssignmentPermission(caller, assignment.getScopeType(), assignment.getScopeId());
        String revokedBy = callerTag(caller);
        assignment.revoke(revokedBy);
        assignment.getUser().invalidateTokens();
        audit("ROLE_REVOKED", assignment.getUser(), revokedBy, true, assignment.getRole().getCode());
    }

    @Transactional
    public AuthzCheckResultDto check(AuthzCheckRequestDto request) {
        return check(request, null);
    }

    @Transactional
    public AuthzCheckResultDto check(AuthzCheckRequestDto request, CurrentUser caller) {
        long userId = parseUserId(request.userId());
        String scopeType = normalizeAssignmentScope(request.scopeType());
        String scopeId = normalizeScopeId(scopeType, request.scopeId());
        String permission = normalizeRequired(request.permission(), "permission");
        Permission permissionDefinition = permissions.findById(permission)
                .orElseThrow(() -> new NotFoundException("PERMISSION_NOT_FOUND"));
        requirePermissionScopeCompatible(permissionDefinition, scopeType);
        List<ScopeRef> candidateScopes = authorizationScopes(scopeType, scopeId, request.ancestorScopes(), caller);
        List<UserRoleAssignment> activeAssignments = assignments.findActiveByUserId(userId, Instant.now()).stream()
                .filter(assignment -> assignmentMatchesAnyScope(assignment, candidateScopes))
                .toList();
        Set<Role> effectiveRoles = resolveEffectiveRoles(activeAssignments.stream()
                .map(UserRoleAssignment::getRole)
                .toList());
        boolean explicitDeny = hasGrant(effectiveRoles, permission, "DENY");
        boolean platformAdmin = activeAssignments.stream()
                .anyMatch(assignment -> "PLATFORM".equals(assignment.getScopeType())
                        && "ADMIN".equals(assignment.getRole().getCode()));
        boolean allowGrant = hasGrant(effectiveRoles, permission, "ALLOW");
        boolean allowed = !explicitDeny && (platformAdmin || allowGrant);
        String reason = authorizationReason(explicitDeny, platformAdmin, allowGrant);
        metrics.authzCheck(allowed, reason, scopeType);
        if (!allowed || auditAuthzAllowed) {
            auditAuthorizationDecision(userId, permission, scopeType, scopeId, allowed,
                    reason);
        }
        return new AuthzCheckResultDto(request.userId(), permission, scopeType, scopeId, allowed);
    }

    private void grantRoleHints(AccessUser user, List<RoleAssignmentHint> hints, String grantedBy) {
        for (RoleAssignmentHint hint : normalizeRoleHints(hints)) {
            roles.findByCode(hint.code()).ifPresent(role -> assignments
                    .findLiveExisting(user.getId(), role.getId(), hint.scopeType(), hint.scopeId())
                    .orElseGet(() -> assignments.save(new UserRoleAssignment(
                            user,
                            role,
                            hint.scopeType(),
                            hint.scopeId(),
                            grantedBy,
                            null))));
        }
    }

    private List<RoleAssignmentHint> normalizeRoleHints(List<RoleAssignmentHint> hints) {
        if (hints == null || hints.isEmpty()) {
            return List.of();
        }
        Set<String> seen = new LinkedHashSet<>();
        List<RoleAssignmentHint> result = new ArrayList<>();
        for (RoleAssignmentHint hint : hints) {
            if (hint == null || hint.code() == null || hint.code().isBlank()) {
                continue;
            }
            String code = hint.code().trim().toUpperCase(Locale.ROOT);
            String scopeType = normalizeAssignmentScope(hint.scopeType());
            String scopeId = normalizeScopeId(scopeType, hint.scopeId());
            String key = code + ":" + scopeType + ":" + scopeId;
            if (seen.add(key)) {
                result.add(new RoleAssignmentHint(code, scopeType, scopeId));
            }
        }
        return result;
    }

    private List<ResolvedRoleAssignmentDto> resolvedAssignments(Long userId) {
        return assignments.findActiveByUserId(userId, Instant.now()).stream()
                .map(assignment -> new ResolvedRoleAssignmentDto(
                        assignment.getRole().getCode(),
                        assignment.getScopeType(),
                        assignment.getScopeId()))
                .toList();
    }

    private List<PermissionGrantDto> directGrants(UUID roleId) {
        return grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(roleId).stream()
                .map(this::toPermissionGrantDto)
                .toList();
    }

    private Set<Role> resolveEffectiveRoles(List<Role> directRoles) {
        Map<UUID, Role> resolved = new LinkedHashMap<>();
        for (Role direct : directRoles) {
            Role current = direct;
            int depth = 0;
            while (current != null && depth < MAX_ROLE_DEPTH) {
                if (resolved.putIfAbsent(current.getId(), current) != null) {
                    break;
                }
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

    private void requirePermissionScopeCompatible(Permission permission, String requestScopeType) {
        String permissionScope = normalizePermissionScope(permission.getScopeType());
        boolean compatible = switch (permissionScope) {
            case "ANY" -> true;
            case "PLATFORM" -> "PLATFORM".equals(requestScopeType);
            case "TENANT" -> Set.of("TENANT", "APPLICATION").contains(requestScopeType);
            case "APPLICATION" -> "APPLICATION".equals(requestScopeType);
            case "ORG" -> Set.of("ORG", "DEPARTMENT", "COURSE", "SECTION").contains(requestScopeType);
            case "DEPARTMENT" -> Set.of("DEPARTMENT", "COURSE", "SECTION").contains(requestScopeType);
            case "COURSE" -> Set.of("COURSE", "SECTION").contains(requestScopeType);
            case "SECTION" -> "SECTION".equals(requestScopeType);
            default -> false;
        };
        if (!compatible) {
            throw new BadRequestException("PERMISSION_SCOPE_MISMATCH");
        }
    }

    private List<ScopeRef> authorizationScopes(String requestScopeType, String requestScopeId,
            List<AuthzScopeDto> ancestors, CurrentUser caller) {
        Map<String, ScopeRef> scopes = new LinkedHashMap<>();
        addScope(scopes, new ScopeRef("PLATFORM", null));
        addScope(scopes, new ScopeRef(requestScopeType, requestScopeId));
        if (ancestors != null && !ancestors.isEmpty()) {
            requireTopologyAssertionScope(caller);
            for (AuthzScopeDto ancestor : ancestors) {
                if (ancestor == null) {
                    continue;
                }
                String ancestorScopeType = normalizeAssignmentScope(ancestor.scopeType());
                String ancestorScopeId = normalizeScopeId(ancestorScopeType, ancestor.scopeId());
                requireAncestorScope(requestScopeType, ancestorScopeType);
                addScope(scopes, new ScopeRef(ancestorScopeType, ancestorScopeId));
            }
        }
        return List.copyOf(scopes.values());
    }

    private void requireTopologyAssertionScope(CurrentUser caller) {
        if (caller == null || caller.internalToken() == null || caller.internalToken().isBlank()) {
            throw new ForbiddenException("AUTHZ_TOPOLOGY_ASSERTION_SCOPE_REQUIRED");
        }
        try {
            Claims claims = internalJwtService.verify(caller.internalToken());
            if (!"service".equals(claims.get("actor_type", String.class))) {
                throw new ForbiddenException("AUTHZ_TOPOLOGY_ASSERTION_SCOPE_REQUIRED");
            }
            Set<String> scopes = extractInternalScopes(claims);
            if (!scopes.contains("*") && !scopes.contains(InternalScopes.AUTHZ_ASSERT_TOPOLOGY)) {
                throw new ForbiddenException("AUTHZ_TOPOLOGY_ASSERTION_SCOPE_REQUIRED");
            }
        } catch (JwtException | IllegalArgumentException | IllegalStateException ex) {
            throw new ForbiddenException("AUTHZ_TOPOLOGY_ASSERTION_SCOPE_REQUIRED");
        }
    }

    private Set<String> extractInternalScopes(Claims claims) {
        Set<String> scopes = new LinkedHashSet<>();
        Object rawScope = claims.get("scope");
        if (rawScope != null) {
            Arrays.stream(rawScope.toString().split("\\s+"))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(scopes::add);
        }
        Object rawScp = claims.get("scp");
        if (rawScp instanceof List<?> list) {
            for (Object scope : list) {
                if (scope != null && !scope.toString().isBlank()) {
                    scopes.add(scope.toString().trim());
                }
            }
        }
        return scopes;
    }

    private void addScope(Map<String, ScopeRef> scopes, ScopeRef scope) {
        scopes.putIfAbsent(scope.scopeType() + ":" + nullSafe(scope.scopeId()), scope);
    }

    private void requireAncestorScope(String requestScopeType, String ancestorScopeType) {
        if ("PLATFORM".equals(ancestorScopeType)) {
            throw new BadRequestException("INVALID_SCOPE_ANCESTOR");
        }
        if ("APPLICATION".equals(requestScopeType)) {
            if (!"TENANT".equals(ancestorScopeType)) {
                throw new BadRequestException("INVALID_SCOPE_ANCESTOR");
            }
            return;
        }
        if ("TENANT".equals(requestScopeType)
                || "TENANT".equals(ancestorScopeType)
                || "APPLICATION".equals(ancestorScopeType)) {
            throw new BadRequestException("INVALID_SCOPE_ANCESTOR");
        }
        if (SCOPE_DEPTH.get(ancestorScopeType) >= SCOPE_DEPTH.get(requestScopeType)) {
            throw new BadRequestException("INVALID_SCOPE_ANCESTOR");
        }
    }

    private boolean assignmentMatchesAnyScope(UserRoleAssignment assignment, List<ScopeRef> scopes) {
        return scopes.stream().anyMatch(scope ->
                scope.scopeType().equals(assignment.getScopeType())
                        && Objects.equals(scope.scopeId(), assignment.getScopeId()));
    }

    private void auditAuthorizationDecision(long userId, String permission, String scopeType, String scopeId,
            boolean allowed, String reason) {
        AccessUser user = users.findById(userId).orElse(null);
        String eventType = allowed ? "AUTHZ_CHECK_ALLOWED" : "AUTHZ_CHECK_DENIED";
        audit(eventType, user, "authz-check", allowed,
                authorizationDetail(userId, permission, scopeType, scopeId, reason));
    }

    private String authorizationReason(boolean explicitDeny, boolean platformAdmin, boolean allowGrant) {
        if (explicitDeny) {
            return "explicit_deny";
        }
        if (platformAdmin) {
            return "platform_admin";
        }
        if (allowGrant) {
            return "allow_grant";
        }
        return "no_allow";
    }

    private void requireRoleAdministrationForUserCaller(CurrentUser caller) {
        if (isUserCaller(caller)) {
            requirePermission(caller, "role:manage", "PLATFORM", null);
        }
    }

    private void requireUserDirectoryReadForUserCaller(CurrentUser caller) {
        if (isUserCaller(caller)) {
            requirePermission(caller, "platform:admin", "PLATFORM", null);
        }
    }

    private void requirePlatformAdministrationForUserCaller(CurrentUser caller) {
        if (isUserCaller(caller)) {
            requirePermission(caller, "platform:admin", "PLATFORM", null);
        }
    }

    private boolean isUserCaller(CurrentUser caller) {
        return caller != null && caller.id() != null;
    }

    private void requirePermission(CurrentUser caller, String permission) {
        requirePermission(caller, permission, "PLATFORM", null);
    }

    private void requirePermission(CurrentUser caller, String permission, String scopeType, String scopeId) {
        if (caller == null || caller.id() == null) {
            throw new ForbiddenException("ACCESS_CONTROL_PERMISSION_REQUIRED");
        }
        AuthzCheckResultDto result = check(new AuthzCheckRequestDto(
                String.valueOf(caller.id()), permission, scopeType, scopeId));
        if (!result.allowed()) {
            throw new ForbiddenException(permission + " is required");
        }
    }

    private void requireRoleAssignmentPermission(CurrentUser caller, String scopeType, String scopeId) {
        if ("PLATFORM".equals(scopeType)) {
            requirePermission(caller, "role:manage", "PLATFORM", null);
            return;
        }
        requirePermission(caller, "user:assign-role", scopeType, scopeId);
    }

    private AccessUser ensureUser(long userId) {
        return users.findById(userId).orElseGet(() -> users.save(new AccessUser(userId, null)));
    }

    private AccessUser ensureUserExists(long userId) {
        return users.findById(userId).orElseThrow(() -> new NotFoundException("ACCESS_USER_NOT_FOUND", userId));
    }

    private boolean userIdEquals(ExternalIdentityLink link, long userId) {
        return link.getUser() != null && Objects.equals(link.getUser().getId(), userId);
    }

    private Role resolveParent(String parentRoleId) {
        if (parentRoleId == null || parentRoleId.isBlank()) {
            return null;
        }
        return roles.findById(parseUuid(parentRoleId, "parentRoleId"))
                .orElseThrow(() -> new NotFoundException("PARENT_ROLE_NOT_FOUND"));
    }

    private boolean wouldCreateCycle(Role child, Role candidateParent) {
        Role current = candidateParent;
        int depth = 0;
        Set<UUID> seen = new HashSet<>();
        while (current != null && depth < MAX_ROLE_DEPTH && seen.add(current.getId())) {
            if (current.getId().equals(child.getId())) {
                return true;
            }
            current = current.getParentRole();
            depth++;
        }
        return false;
    }

    private void audit(String eventType, AccessUser user, String actorId, boolean success, String detail) {
        auditLogs.save(new AccessControlAuditLog(eventType, user, actorId, success, detail));
    }

    private PermissionDto toPermissionDto(Permission permission) {
        return new PermissionDto(
                permission.getCode(),
                permission.getDescription(),
                permission.getCategory(),
                permission.getScopeType());
    }

    private RoleDto toRoleDto(Role role, List<PermissionGrantDto> permissions) {
        return new RoleDto(
                role.getId().toString(),
                role.getCode(),
                role.getName(),
                role.getDescription(),
                role.isSystem(),
                role.isOperator(),
                role.getRank(),
                role.getParentRole() == null ? null : role.getParentRole().getId().toString(),
                permissions);
    }

    private PermissionGrantDto toPermissionGrantDto(RolePermissionGrant grant) {
        Permission permission = grant.getPermission();
        return new PermissionGrantDto(
                permission.getCode(),
                permission.getDescription(),
                permission.getCategory(),
                grant.getEffect());
    }

    private RoleAssignmentDto toAssignmentDto(UserRoleAssignment assignment) {
        Role role = assignment.getRole();
        return new RoleAssignmentDto(
                assignment.getId(),
                assignment.getUserId(),
                role.getId().toString(),
                role.getCode(),
                role.getName(),
                assignment.getScopeType(),
                assignment.getScopeId(),
                assignment.getGrantedBy(),
                assignment.getExpiresAt(),
                assignment.getCreatedAt());
    }

    private AccessUserDirectoryItemDto toDirectoryItem(AccessUser user) {
        ExternalIdentityLink link = identityLinks.findFirstByUser_IdAndStatusOrderByIdDesc(user.getId(), "ACTIVE")
                .orElse(null);
        return new AccessUserDirectoryItemDto(
                String.valueOf(user.getId()),
                user.getEmail(),
                user.getStatus(),
                primaryRole(user.getId()),
                link == null ? null : link.getIssuer(),
                link == null ? null : link.getSubject());
    }

    private AccessRoleGrantExportDto toRoleGrantExportDto(UserRoleAssignment assignment) {
        Role role = assignment.getRole();
        return new AccessRoleGrantExportDto(
                assignment.getId(),
                role.getId().toString(),
                role.getCode(),
                role.getName(),
                assignment.getScopeType(),
                assignment.getScopeId(),
                assignment.getGrantedBy(),
                assignment.getGrantedAt(),
                assignment.getExpiresAt(),
                assignment.getRevokedAt(),
                assignment.getRevokedBy(),
                assignment.getCreatedAt());
    }

    private String primaryRole(Long userId) {
        return assignments.findActiveByUserId(userId, Instant.now()).stream()
                .map(UserRoleAssignment::getRole)
                .filter(Objects::nonNull)
                .sorted((left, right) -> {
                    int rank = Integer.compare(right.getRank(), left.getRank());
                    return rank != 0 ? rank : left.getCode().compareTo(right.getCode());
                })
                .map(Role::getCode)
                .findFirst()
                .orElse(null);
    }

    private long parseUserId(String raw) {
        try {
            return Long.parseLong(normalizeRequired(raw, "userId"));
        } catch (NumberFormatException ex) {
            throw new BadRequestException("INVALID_USER_ID");
        }
    }

    private List<Long> parseUserIds(List<String> rawUserIds) {
        if (rawUserIds == null) {
            return List.of();
        }
        Set<Long> ids = new LinkedHashSet<>();
        for (String raw : rawUserIds) {
            ids.add(parseUserId(raw));
        }
        return List.copyOf(ids);
    }

    private UUID parseUuid(String raw, String field) {
        try {
            return UUID.fromString(normalizeRequired(raw, field));
        } catch (IllegalArgumentException ex) {
            throw new BadRequestException("INVALID_" + field.toUpperCase(Locale.ROOT));
        }
    }

    private String normalizeRequired(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new BadRequestException("MISSING_" + field.toUpperCase(Locale.ROOT));
        }
        return value.trim();
    }

    private String normalizeEmail(String value) {
        return value == null || value.isBlank() ? null : value.trim().toLowerCase(Locale.ROOT);
    }

    private String normalizeAssignmentScope(String scopeType) {
        String normalized = scopeType == null || scopeType.isBlank()
                ? "PLATFORM"
                : scopeType.trim().toUpperCase(Locale.ROOT);
        if (!ASSIGNMENT_SCOPE_TYPES.contains(normalized)) {
            throw new BadRequestException("INVALID_SCOPE_TYPE");
        }
        return normalized;
    }

    private String normalizePermissionScope(String scopeType) {
        String normalized = scopeType == null || scopeType.isBlank()
                ? "ANY"
                : scopeType.trim().toUpperCase(Locale.ROOT);
        if (!PERMISSION_SCOPE_TYPES.contains(normalized)) {
            throw new BadRequestException("INVALID_PERMISSION_SCOPE_TYPE");
        }
        return normalized;
    }

    private String normalizeScopeId(String scopeType, String rawScopeId) {
        String scopeId = trimToNull(rawScopeId);
        if ("PLATFORM".equals(scopeType)) {
            if (scopeId != null) {
                throw new BadRequestException("PLATFORM_SCOPE_ID_NOT_ALLOWED");
            }
            return null;
        }
        if (scopeId == null) {
            throw new BadRequestException("SCOPE_ID_REQUIRED");
        }
        if ("APPLICATION".equals(scopeType)) {
            int separator = scopeId.indexOf(':');
            if (separator <= 0 || separator != scopeId.lastIndexOf(':') || separator == scopeId.length() - 1) {
                throw new BadRequestException("INVALID_APPLICATION_SCOPE_ID");
            }
        }
        return scopeId;
    }

    private String trimToNull(String raw) {
        return raw == null || raw.isBlank() ? null : raw.trim();
    }

    private String callerTag(CurrentUser caller) {
        if (caller == null) {
            return "system";
        }
        if (caller.id() != null) {
            return "user:" + caller.id();
        }
        return caller.email() == null ? "system" : caller.email();
    }

    private String nullSafe(String value) {
        return value == null ? "" : value;
    }

    private String detail(String prefix, String value) {
        String detail = prefix + value;
        return detail.length() > 255 ? detail.substring(0, 255) : detail;
    }

    private String authorizationDetail(long userId, String permission, String scopeType, String scopeId, String reason) {
        return detail("", "userId=" + userId
                + ";permission=" + permission
                + ";scopeType=" + scopeType
                + ";scopeId=" + nullSafe(scopeId)
                + ";reason=" + reason);
    }

    private record ScopeRef(String scopeType, String scopeId) {
    }
}
